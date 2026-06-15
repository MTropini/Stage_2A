from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


@dataclass(frozen=True)
class PatchRecord:
    patch_id: str
    site_id: str
    patch_type: str
    label: int
    rgb_path: Path
    lidar_path: Path


class ImagePathDataset:
    def __init__(self, paths: list[Path], labels: list[int], transform) -> None:
        self.paths = paths
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int):
        image = Image.open(self.paths[index]).convert("RGB")
        return self.transform(image), self.labels[index]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare RGB, LiDAR and RGB+LiDAR ResNet-18 embedding baselines."
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports_qgis" / "dataset_audit.csv",
    )
    parser.add_argument(
        "--exclude-types",
        nargs="*",
        default=["tres_large"],
        help="Patch types to exclude. Default excludes very large context views.",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--torch-cache-dir",
        type=Path,
        default=PROJECT_ROOT / "models" / "torch_cache",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.torch_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TORCH_HOME"] = str(args.torch_cache_dir)

    try:
        import torch
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, classification_report, f1_score
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from torch import nn
        from torch.utils.data import DataLoader
        from torchvision import models, transforms
    except ModuleNotFoundError:
        print("PyTorch, torchvision and scikit-learn are required. Install with:")
        print("python -m pip install -r requirements.txt")
        return 1

    records = _load_records(args.audit_csv, set(args.exclude_types))
    if not records:
        print(f"No usable paired records found in: {args.audit_csv}")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    transform = _build_transform(transforms, args.image_size)
    labels = np.asarray([record.label for record in records], dtype=np.int64)
    site_ids = np.asarray([record.site_id for record in records])

    print(f"Device: {device}")
    print(f"Samples used: {len(records)}")
    print(f"Sites used: {len({record.site_id for record in records})}")
    print(f"Excluded patch types: {args.exclude_types or 'none'}")
    _print_counts(records)

    extractor = _build_feature_extractor(models, nn).to(device)

    rgb_features = _features_for_paths(
        paths=[record.rgb_path for record in records],
        labels=labels.tolist(),
        transform=transform,
        batch_size=args.batch_size,
        extractor=extractor,
        device=device,
        torch=torch,
        DataLoader=DataLoader,
    )
    lidar_features = _features_for_paths(
        paths=[record.lidar_path for record in records],
        labels=labels.tolist(),
        transform=transform,
        batch_size=args.batch_size,
        extractor=extractor,
        device=device,
        torch=torch,
        DataLoader=DataLoader,
    )
    fused_features = np.concatenate([rgb_features, lidar_features], axis=1)

    print(f"RGB embedding shape: {rgb_features.shape}")
    print(f"LiDAR embedding shape: {lidar_features.shape}")
    print(f"Fused embedding shape: {fused_features.shape}")

    classifier_factory = lambda: make_pipeline(
        StandardScaler(),
        LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            random_state=args.random_state,
        ),
    )

    summaries = []
    for name, features in [
        ("RGB only", rgb_features),
        ("LiDAR only", lidar_features),
        ("RGB + LiDAR", fused_features),
    ]:
        print()
        summary = _evaluate_leave_one_site_out(
            name=name,
            features=features,
            labels=labels,
            site_ids=site_ids,
            classifier_factory=classifier_factory,
            accuracy_score=accuracy_score,
            f1_score=f1_score,
            classification_report=classification_report,
        )
        summaries.append((name, *summary))

    print()
    print("Summary")
    for name, accuracy_mean, accuracy_std, f1_mean, f1_std in summaries:
        print(
            f"- {name}: accuracy={accuracy_mean:.3f} +/- {accuracy_std:.3f}, "
            f"F1 archeologique={f1_mean:.3f} +/- {f1_std:.3f}"
        )

    return 0


def _load_records(audit_csv: Path, excluded_types: set[str]) -> list[PatchRecord]:
    with audit_csv.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    records = []
    for row in rows:
        if row["status"] != "ok":
            continue
        if row["patch_type"] in excluded_types:
            continue
        if not row["lidar_path"]:
            continue
        records.append(
            PatchRecord(
                patch_id=row["patch_id"],
                site_id=row["site_id"],
                patch_type=row["patch_type"],
                label=1 if row["label"] == "archeologique" else 0,
                rgb_path=Path(row["rgb_path"]),
                lidar_path=Path(row["lidar_path"]),
            )
        )
    return records


def _build_transform(transforms, image_size: int):
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


def _build_feature_extractor(models, nn):
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Identity()
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad = False
    return model


def _features_for_paths(
    paths: list[Path],
    labels: list[int],
    transform,
    batch_size: int,
    extractor,
    device,
    torch,
    DataLoader,
) -> np.ndarray:
    dataset = ImagePathDataset(paths, labels, transform)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    embeddings = []
    with torch.no_grad():
        for images, _ in loader:
            embeddings.append(extractor(images.to(device)).cpu().numpy())
    return np.vstack(embeddings).astype(np.float32)


def _evaluate_leave_one_site_out(
    name: str,
    features: np.ndarray,
    labels: np.ndarray,
    site_ids: np.ndarray,
    classifier_factory,
    accuracy_score,
    f1_score,
    classification_report,
) -> tuple[float, float, float, float]:
    all_true = []
    all_pred = []
    fold_scores = []

    print(f"{name} leave-one-site-out")
    for test_site in sorted(set(site_ids)):
        train_mask = site_ids != test_site
        test_mask = site_ids == test_site

        classifier = classifier_factory()
        classifier.fit(features[train_mask], labels[train_mask])
        predictions = classifier.predict(features[test_mask])

        accuracy = accuracy_score(labels[test_mask], predictions)
        f1 = f1_score(labels[test_mask], predictions, zero_division=0)
        fold_scores.append((accuracy, f1))
        all_true.extend(labels[test_mask].tolist())
        all_pred.extend(predictions.tolist())

        print(
            f"- test={test_site}: accuracy={accuracy:.3f}, "
            f"F1 archeologique={f1:.3f}, n={int(test_mask.sum())}"
        )

    fold_scores_array = np.asarray(fold_scores, dtype=np.float32)
    accuracy_mean = float(fold_scores_array[:, 0].mean())
    accuracy_std = float(fold_scores_array[:, 0].std())
    f1_mean = float(fold_scores_array[:, 1].mean())
    f1_std = float(fold_scores_array[:, 1].std())

    print(
        f"Mean: accuracy={accuracy_mean:.3f} +/- {accuracy_std:.3f}, "
        f"F1 archeologique={f1_mean:.3f} +/- {f1_std:.3f}"
    )
    print(
        classification_report(
            all_true,
            all_pred,
            target_names=["non_archeologique", "archeologique"],
            zero_division=0,
        )
    )
    return accuracy_mean, accuracy_std, f1_mean, f1_std


def _print_counts(records: list[PatchRecord]) -> None:
    for label_name, label in [("non_archeologique", 0), ("archeologique", 1)]:
        print(f"- {label_name}: {sum(record.label == label for record in records)}")
    for patch_type in sorted({record.patch_type for record in records}):
        print(f"- {patch_type}: {sum(record.patch_type == patch_type for record in records)}")


if __name__ == "__main__":
    raise SystemExit(main())


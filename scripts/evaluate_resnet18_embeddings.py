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


class PatchDataset:
    def __init__(self, records: list[PatchRecord], transform) -> None:
        self.records = records
        self.transform = transform

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        record = self.records[index]
        image = Image.open(record.rgb_path).convert("RGB")
        return self.transform(image), record.label


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate pretrained ResNet-18 embeddings with leave-one-site-out validation."
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
        print(f"No usable records found in: {args.audit_csv}")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    transform = _build_transform(transforms, args.image_size)
    loader = DataLoader(
        PatchDataset(records, transform),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )

    print(f"Device: {device}")
    print(f"Samples used: {len(records)}")
    print(f"Sites used: {len({record.site_id for record in records})}")
    print(f"Excluded patch types: {args.exclude_types or 'none'}")
    _print_counts(records)

    extractor = _build_feature_extractor(models, nn).to(device)
    features, labels = _extract_embeddings(extractor, loader, device, torch)
    site_ids = np.asarray([record.site_id for record in records])

    print(f"Embedding shape: {features.shape}")
    _evaluate_leave_one_site_out(
        features=features,
        labels=labels,
        site_ids=site_ids,
        random_state=args.random_state,
        classifier_factory=lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                random_state=args.random_state,
            ),
        ),
        accuracy_score=accuracy_score,
        f1_score=f1_score,
        classification_report=classification_report,
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
        records.append(
            PatchRecord(
                patch_id=row["patch_id"],
                site_id=row["site_id"],
                patch_type=row["patch_type"],
                label=1 if row["label"] == "archeologique" else 0,
                rgb_path=Path(row["rgb_path"]),
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


def _extract_embeddings(model, loader, device, torch) -> tuple[np.ndarray, np.ndarray]:
    embeddings = []
    labels = []
    with torch.no_grad():
        for images, batch_labels in loader:
            batch_embeddings = model(images.to(device)).cpu().numpy()
            embeddings.append(batch_embeddings)
            labels.extend(batch_labels.numpy().tolist())
    return np.vstack(embeddings).astype(np.float32), np.asarray(labels, dtype=np.int64)


def _evaluate_leave_one_site_out(
    features: np.ndarray,
    labels: np.ndarray,
    site_ids: np.ndarray,
    random_state: int,
    classifier_factory,
    accuracy_score,
    f1_score,
    classification_report,
) -> None:
    all_true = []
    all_pred = []
    fold_scores = []

    print("ResNet-18 embeddings leave-one-site-out")
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
    print(
        f"Mean: accuracy={fold_scores_array[:, 0].mean():.3f} "
        f"+/- {fold_scores_array[:, 0].std():.3f}, "
        f"F1 archeologique={fold_scores_array[:, 1].mean():.3f} "
        f"+/- {fold_scores_array[:, 1].std():.3f}"
    )
    print(
        classification_report(
            all_true,
            all_pred,
            target_names=["non_archeologique", "archeologique"],
            zero_division=0,
        )
    )


def _print_counts(records: list[PatchRecord]) -> None:
    for label_name, label in [("non_archeologique", 0), ("archeologique", 1)]:
        print(f"- {label_name}: {sum(record.label == label for record in records)}")
    for patch_type in sorted({record.patch_type for record in records}):
        print(f"- {patch_type}: {sum(record.patch_type == patch_type for record in records)}")


if __name__ == "__main__":
    raise SystemExit(main())


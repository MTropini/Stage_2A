from __future__ import annotations

import argparse
import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATTERN = re.compile(r"^(candidat\d+)")


@dataclass(frozen=True)
class TrainingRecord:
    label: int
    rgb_path: Path
    lidar_path: Path


@dataclass(frozen=True)
class CandidateRecord:
    patch_id: str
    candidate_id: str
    patch_type: str
    rgb_path: Path
    lidar_path: Path


class ImagePathDataset:
    def __init__(self, paths: list[Path], transform) -> None:
        self.paths = paths
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int):
        image = Image.open(self.paths[index]).convert("RGB")
        return self.transform(image)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict archaeological probability for unknown RGB+LiDAR candidate patches."
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "dataset_audit.csv",
    )
    parser.add_argument(
        "--candidate-rgb-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "candidates_qgis" / "rgb",
    )
    parser.add_argument(
        "--candidate-lidar-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "candidates_qgis" / "lidar",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "candidates_qgis" / "candidate_predictions.csv",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "data" / "candidates_qgis" / "candidate_predictions.md",
    )
    parser.add_argument("--threshold", type=float, default=0.45)
    parser.add_argument("--c-value", type=float, default=0.03)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=224)
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
        from torch import nn
        from torch.utils.data import DataLoader
        from torchvision import models, transforms
    except ModuleNotFoundError:
        print("PyTorch, torchvision and scikit-learn are required.")
        return 1

    training_records = _load_training_records(args.audit_csv)
    candidate_records = _load_candidate_records(
        args.candidate_rgb_dir, args.candidate_lidar_dir
    )
    if not training_records or not candidate_records:
        print("Training records or candidate records are missing.")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    transform = _build_transform(transforms, args.image_size)
    extractor = _build_extractor(models, nn).to(device)

    print(f"Device: {device}")
    print(f"Training samples: {len(training_records)}")
    print(f"Candidate patches: {len(candidate_records)}")

    train_features = _fused_features(
        training_records, transform, args.batch_size, extractor, device, torch, DataLoader
    )
    candidate_features = _fused_features(
        candidate_records, transform, args.batch_size, extractor, device, torch, DataLoader
    )
    labels = np.asarray([record.label for record in training_records], dtype=np.int64)

    classifier = LogisticRegression(
        C=args.c_value,
        class_weight=None,
        max_iter=1000,
        random_state=42,
        solver="liblinear",
    )
    classifier.fit(train_features, labels)
    probabilities = classifier.predict_proba(candidate_features)
    class_to_index = {
        int(class_label): class_index
        for class_index, class_label in enumerate(classifier.classes_)
    }
    archaeological_probabilities = probabilities[:, class_to_index[1]]

    rows = []
    for record, probability in zip(candidate_records, archaeological_probabilities):
        rows.append(
            {
                "candidate_id": record.candidate_id,
                "patch_id": record.patch_id,
                "patch_type": record.patch_type,
                "probability_archeologique": f"{float(probability):.6f}",
                "prediction": (
                    "archeologique" if probability >= args.threshold else "non_archeologique"
                ),
                "priority": _priority(float(probability)),
                "threshold": f"{args.threshold:.2f}",
                "rgb_path": str(record.rgb_path),
                "lidar_path": str(record.lidar_path),
                "training_compatibility": (
                    "context_only" if record.patch_type == "tres_large" else "comparable"
                ),
            }
        )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, args.output_csv)
    _write_markdown(rows, args.output_md, args.threshold)
    _print_summary(rows, args.output_csv, args.output_md)
    return 0


def _load_training_records(audit_csv: Path) -> list[TrainingRecord]:
    with audit_csv.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    return [
        TrainingRecord(
            label=1 if row["label"] == "archeologique" else 0,
            rgb_path=Path(row["rgb_path"]),
            lidar_path=Path(row["lidar_path"]),
        )
        for row in rows
        if row["status"] == "ok"
        and row["patch_type"] != "tres_large"
        and row["rgb_path"]
        and row["lidar_path"]
    ]


def _load_candidate_records(rgb_dir: Path, lidar_dir: Path) -> list[CandidateRecord]:
    rgb_paths = {path.stem: path for path in rgb_dir.glob("*.png")}
    lidar_paths = {
        path.stem.removesuffix("_lidar"): path for path in lidar_dir.glob("*.png")
    }
    records = []
    for patch_id in sorted(set(rgb_paths) & set(lidar_paths)):
        match = CANDIDATE_PATTERN.match(patch_id)
        candidate_id = match.group(1) if match else "unknown"
        records.append(
            CandidateRecord(
                patch_id=patch_id,
                candidate_id=candidate_id,
                patch_type=_patch_type(patch_id),
                rgb_path=rgb_paths[patch_id],
                lidar_path=lidar_paths[patch_id],
            )
        )
    return records


def _patch_type(patch_id: str) -> str:
    if "tres_large" in patch_id:
        return "tres_large"
    if patch_id.endswith("_large"):
        return "large"
    if "_patch" in patch_id:
        return "patch"
    return "unknown"


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


def _build_extractor(models, nn):
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Identity()
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad = False
    return model


def _fused_features(records, transform, batch_size, extractor, device, torch, DataLoader):
    rgb_features = _features(
        [record.rgb_path for record in records],
        transform,
        batch_size,
        extractor,
        device,
        torch,
        DataLoader,
    )
    lidar_features = _features(
        [record.lidar_path for record in records],
        transform,
        batch_size,
        extractor,
        device,
        torch,
        DataLoader,
    )
    return np.concatenate([rgb_features, lidar_features], axis=1)


def _features(paths, transform, batch_size, extractor, device, torch, DataLoader):
    loader = DataLoader(
        ImagePathDataset(paths, transform),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )
    embeddings = []
    with torch.no_grad():
        for images in loader:
            embeddings.append(extractor(images.to(device)).cpu().numpy())
    return np.vstack(embeddings).astype(np.float32)


def _priority(probability: float) -> str:
    if probability < 0.30:
        return "faible"
    if probability < 0.45:
        return "incertaine"
    if probability < 0.70:
        return "a_examiner"
    return "prioritaire"


def _write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(rows: list[dict[str, str]], output_path: Path, threshold: float) -> None:
    lines = [
        "# Predictions ResNet RGB + LiDAR - candidats inconnus",
        "",
        f"Seuil de decision : `{threshold:.2f}`",
        "",
        "| Candidat | Patch | Type | P(archeologique) | Prediction | Priorite | Compatibilite |",
        "|---|---|---|---:|---|---|---|",
    ]
    for row in sorted(rows, key=lambda item: float(item["probability_archeologique"]), reverse=True):
        lines.append(
            f"| {row['candidate_id']} | {row['patch_id']} | {row['patch_type']} | "
            f"{float(row['probability_archeologique']):.3f} | {row['prediction']} | "
            f"{row['priority']} | {row['training_compatibility']} |"
        )

    lines.extend(["", "## Synthese par candidat", ""])
    for candidate_id in sorted({row["candidate_id"] for row in rows}):
        comparable = [
            row
            for row in rows
            if row["candidate_id"] == candidate_id
            and row["training_compatibility"] == "comparable"
        ]
        probabilities = [float(row["probability_archeologique"]) for row in comparable]
        lines.append(
            f"- `{candidate_id}` : moyenne patch+large = {np.mean(probabilities):.3f}, "
            f"maximum = {max(probabilities):.3f}"
        )

    lines.extend(
        [
            "",
            "> Ces scores servent a prioriser une verification humaine. Ils ne constituent pas une preuve archeologique.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_summary(rows, output_csv, output_md):
    print("Candidate predictions:")
    for row in sorted(rows, key=lambda item: float(item["probability_archeologique"]), reverse=True):
        print(
            f"- {row['patch_id']}: P={float(row['probability_archeologique']):.3f}, "
            f"{row['prediction']}, {row['priority']}"
        )
    print(f"CSV: {output_csv}")
    print(f"Markdown: {output_md}")


if __name__ == "__main__":
    raise SystemExit(main())

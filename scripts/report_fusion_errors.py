from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


@dataclass(frozen=True)
class PatchRecord:
    sample_uid: str
    dataset_source: str
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
        description="Report image-level errors for the RGB+LiDAR ResNet-18 fusion model."
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "dataset_audit.csv",
        help="Combined RGB/LiDAR audit CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "fusion_error_report.csv",
        help="Detailed per-image prediction report.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "fusion_error_report.md",
        help="Human-readable error summary.",
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
        from sklearn.metrics import accuracy_score, f1_score
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

    labels = np.asarray([record.label for record in records], dtype=np.int64)
    site_ids = np.asarray([record.site_id for record in records])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    transform = _build_transform(transforms, args.image_size)

    print(f"Device: {device}")
    print(f"Samples used: {len(records)}")
    print(f"Sites used: {len(set(site_ids))}")
    print(f"Excluded patch types: {args.exclude_types or 'none'}")

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
    features = np.concatenate([rgb_features, lidar_features], axis=1)

    report_rows = _leave_one_site_out_predictions(
        records=records,
        features=features,
        labels=labels,
        site_ids=site_ids,
        classifier_factory=lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                random_state=args.random_state,
            ),
        ),
    )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(report_rows, args.output_csv)
    _write_markdown(report_rows, args.output_md, args)
    _print_summary(report_rows, args.output_csv, args.output_md, accuracy_score, f1_score)
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
        if not row["rgb_path"] or not row["lidar_path"]:
            continue
        records.append(
            PatchRecord(
                sample_uid=row.get("sample_uid", row["patch_id"]),
                dataset_source=row.get("dataset_source", "unknown"),
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


def _leave_one_site_out_predictions(
    records: list[PatchRecord],
    features: np.ndarray,
    labels: np.ndarray,
    site_ids: np.ndarray,
    classifier_factory,
) -> list[dict[str, str]]:
    report_rows: list[dict[str, str]] = []

    for test_site in sorted(set(site_ids)):
        train_mask = site_ids != test_site
        test_indices = np.flatnonzero(site_ids == test_site)
        classifier = classifier_factory()
        classifier.fit(features[train_mask], labels[train_mask])
        probabilities = classifier.predict_proba(features[test_indices])
        class_to_index = {
            int(class_label): class_index
            for class_index, class_label in enumerate(classifier.classes_)
        }

        for local_index, record_index in enumerate(test_indices):
            record = records[int(record_index)]
            probability_arch = float(probabilities[local_index, class_to_index[1]])
            prediction = 1 if probability_arch >= 0.5 else 0
            true_label = int(labels[record_index])
            error_type = _error_type(true_label, prediction)

            report_rows.append(
                {
                    "sample_uid": record.sample_uid,
                    "dataset_source": record.dataset_source,
                    "patch_id": record.patch_id,
                    "site_id": record.site_id,
                    "patch_type": record.patch_type,
                    "true_label": _label_name(true_label),
                    "predicted_label": _label_name(prediction),
                    "probability_archeologique": f"{probability_arch:.6f}",
                    "confidence": f"{max(probability_arch, 1.0 - probability_arch):.6f}",
                    "error_type": error_type,
                    "rgb_path": str(record.rgb_path),
                    "lidar_path": str(record.lidar_path),
                }
            )

    return sorted(report_rows, key=lambda row: row["sample_uid"])


def _label_name(label: int) -> str:
    return "archeologique" if label == 1 else "non_archeologique"


def _error_type(true_label: int, prediction: int) -> str:
    if true_label == prediction:
        return "correct"
    if true_label == 1 and prediction == 0:
        return "false_negative"
    return "false_positive"


def _write_csv(report_rows: list[dict[str, str]], output_path: Path) -> None:
    fieldnames = [
        "sample_uid",
        "dataset_source",
        "patch_id",
        "site_id",
        "patch_type",
        "true_label",
        "predicted_label",
        "probability_archeologique",
        "confidence",
        "error_type",
        "rgb_path",
        "lidar_path",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)


def _write_markdown(
    report_rows: list[dict[str, str]],
    output_path: Path,
    args: argparse.Namespace,
) -> None:
    false_negatives = [
        row for row in report_rows if row["error_type"] == "false_negative"
    ]
    false_positives = [
        row for row in report_rows if row["error_type"] == "false_positive"
    ]
    correct = [row for row in report_rows if row["error_type"] == "correct"]

    lines = [
        "# RGB + LiDAR fusion error report",
        "",
        "## Summary",
        "",
        f"- Samples: {len(report_rows)}",
        f"- Correct: {len(correct)}",
        f"- False negatives: {len(false_negatives)}",
        f"- False positives: {len(false_positives)}",
        f"- Excluded patch types: {', '.join(args.exclude_types) or 'none'}",
        "",
        "## Errors By Site",
        "",
        "| Site | False negatives | False positives |",
        "|---|---:|---:|",
    ]

    sites = sorted({row["site_id"] for row in report_rows})
    for site in sites:
        site_rows = [row for row in report_rows if row["site_id"] == site]
        lines.append(
            f"| {site} | "
            f"{sum(row['error_type'] == 'false_negative' for row in site_rows)} | "
            f"{sum(row['error_type'] == 'false_positive' for row in site_rows)} |"
        )

    lines.extend(
        [
            "",
            "## High-Confidence False Negatives",
            "",
            "| Patch | Site | Type | P(arch.) | RGB | LiDAR |",
            "|---|---|---|---:|---|---|",
        ]
    )
    for row in _top_errors(false_negatives, reverse=False):
        lines.append(_error_table_line(row))

    lines.extend(
        [
            "",
            "## High-Confidence False Positives",
            "",
            "| Patch | Site | Type | P(arch.) | RGB | LiDAR |",
            "|---|---|---|---:|---|---|",
        ]
    )
    for row in _top_errors(false_positives, reverse=True):
        lines.append(_error_table_line(row))

    lines.extend(
        [
            "",
            "## Error Counts By Patch Type",
            "",
            "| Patch type | False negatives | False positives |",
            "|---|---:|---:|",
        ]
    )
    patch_types = sorted({row["patch_type"] for row in report_rows})
    for patch_type in patch_types:
        type_rows = [row for row in report_rows if row["patch_type"] == patch_type]
        lines.append(
            f"| {patch_type} | "
            f"{sum(row['error_type'] == 'false_negative' for row in type_rows)} | "
            f"{sum(row['error_type'] == 'false_positive' for row in type_rows)} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _top_errors(rows: list[dict[str, str]], reverse: bool) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: float(row["probability_archeologique"]),
        reverse=reverse,
    )[:25]


def _error_table_line(row: dict[str, str]) -> str:
    return (
        f"| {row['patch_id']} | {row['site_id']} | {row['patch_type']} | "
        f"{float(row['probability_archeologique']):.3f} | "
        f"{Path(row['rgb_path']).as_posix()} | {Path(row['lidar_path']).as_posix()} |"
    )


def _print_summary(report_rows, output_csv, output_md, accuracy_score, f1_score) -> None:
    labels = np.asarray(
        [1 if row["true_label"] == "archeologique" else 0 for row in report_rows],
        dtype=np.int64,
    )
    predictions = np.asarray(
        [1 if row["predicted_label"] == "archeologique" else 0 for row in report_rows],
        dtype=np.int64,
    )
    errors = [row for row in report_rows if row["error_type"] != "correct"]
    counts = Counter(row["error_type"] for row in report_rows)

    print(f"Accuracy: {accuracy_score(labels, predictions):.3f}")
    print(f"F1 archeologique: {f1_score(labels, predictions, zero_division=0):.3f}")
    print(f"Correct: {counts['correct']}")
    print(f"False negatives: {counts['false_negative']}")
    print(f"False positives: {counts['false_positive']}")
    print("Errors by site:")
    for site in sorted({row["site_id"] for row in errors}):
        site_errors = [row for row in errors if row["site_id"] == site]
        site_counts = Counter(row["error_type"] for row in site_errors)
        print(
            f"- {site}: false_negative={site_counts['false_negative']}, "
            f"false_positive={site_counts['false_positive']}"
        )
    print(f"CSV report: {output_csv}")
    print(f"Markdown report: {output_md}")


if __name__ == "__main__":
    raise SystemExit(main())

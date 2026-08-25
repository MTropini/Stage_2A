from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from itertools import product
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


@dataclass(frozen=True)
class TrialConfig:
    scaler: str
    class_weight: str
    c_value: float


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
        description="Tune the RGB+LiDAR ResNet-18 embedding classifier with leave-one-site-out validation."
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
        default=PROJECT_ROOT / "data" / "combined" / "fusion_hyperparameter_search.csv",
        help="CSV output for every hyperparameter trial.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "fusion_hyperparameter_search.md",
        help="Human-readable summary of the best trials.",
    )
    parser.add_argument(
        "--exclude-types",
        nargs="*",
        default=["tres_large"],
        help="Patch types to exclude. Default excludes very large context views.",
    )
    parser.add_argument(
        "--scalers",
        nargs="*",
        default=["standard", "robust", "normalizer", "none"],
        choices=["standard", "robust", "normalizer", "none"],
    )
    parser.add_argument(
        "--class-weights",
        nargs="*",
        default=["balanced", "none"],
        choices=["balanced", "none"],
    )
    parser.add_argument(
        "--c-values",
        nargs="*",
        type=float,
        default=[0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0],
    )
    parser.add_argument(
        "--thresholds",
        nargs="*",
        type=float,
        default=[0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7],
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
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
        )
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import Normalizer, RobustScaler, StandardScaler
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

    print(f"Device: {device}")
    print(f"Samples used: {len(records)}")
    print(f"Sites used: {len(set(site_ids))}")
    print(f"Excluded patch types: {args.exclude_types or 'none'}")

    transform = _build_transform(transforms, args.image_size)
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
    print(f"Fused embedding shape: {features.shape}")

    base_trials = [
        TrialConfig(scaler=scaler, class_weight=class_weight, c_value=c_value)
        for scaler, class_weight, c_value, threshold in product(
            args.scalers,
            args.class_weights,
            args.c_values,
            [0.5],
        )
    ]
    print(f"Classifier trials: {len(base_trials)}")
    print(f"Thresholds per trial: {len(args.thresholds)}")

    results = []
    for index, config in enumerate(base_trials, start=1):
        probabilities = _leave_one_site_out_probabilities(
            features=features,
            labels=labels,
            site_ids=site_ids,
            config=config,
            random_state=args.random_state,
            LogisticRegression=LogisticRegression,
            make_pipeline=make_pipeline,
            StandardScaler=StandardScaler,
            RobustScaler=RobustScaler,
            Normalizer=Normalizer,
        )
        for threshold in args.thresholds:
            results.append(
                _evaluate_threshold(
                    labels=labels,
                    site_ids=site_ids,
                    probabilities=probabilities,
                    config=config,
                    threshold=threshold,
                    accuracy_score=accuracy_score,
                    precision_score=precision_score,
                    recall_score=recall_score,
                    f1_score=f1_score,
                )
            )
        if index % 5 == 0 or index == len(base_trials):
            best = max(results, key=lambda row: (row["f1_archeologique"], row["recall_archeologique"]))
            print(
                f"Classifier trial {index}/{len(base_trials)} - current best: "
                f"F1={best['f1_archeologique']:.3f}, "
                f"recall={best['recall_archeologique']:.3f}, "
                f"threshold={best['threshold']:.2f}, "
                f"C={best['c_value']}, scaler={best['scaler']}, "
                f"class_weight={best['class_weight']}"
            )

    results = sorted(
        results,
        key=lambda row: (
            row["f1_archeologique"],
            row["recall_archeologique"],
            row["accuracy"],
        ),
        reverse=True,
    )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(results, args.output_csv)
    _write_markdown(results, args.output_md)
    _print_summary(results, args.output_csv, args.output_md)
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


def _leave_one_site_out_probabilities(
    features: np.ndarray,
    labels: np.ndarray,
    site_ids: np.ndarray,
    config: TrialConfig,
    random_state: int,
    LogisticRegression,
    make_pipeline,
    StandardScaler,
    RobustScaler,
    Normalizer,
) -> np.ndarray:
    probabilities = np.zeros(labels.shape[0], dtype=np.float32)

    for test_site in sorted(set(site_ids)):
        train_mask = site_ids != test_site
        test_mask = site_ids == test_site
        classifier = _build_classifier(
            config=config,
            random_state=random_state,
            LogisticRegression=LogisticRegression,
            make_pipeline=make_pipeline,
            StandardScaler=StandardScaler,
            RobustScaler=RobustScaler,
            Normalizer=Normalizer,
        )
        classifier.fit(features[train_mask], labels[train_mask])
        fold_probabilities = classifier.predict_proba(features[test_mask])
        class_to_index = {
            int(class_label): class_index
            for class_index, class_label in enumerate(classifier.classes_)
        }
        probabilities[test_mask] = fold_probabilities[:, class_to_index[1]]

    return probabilities


def _evaluate_threshold(
    labels: np.ndarray,
    site_ids: np.ndarray,
    probabilities: np.ndarray,
    config: TrialConfig,
    threshold: float,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
) -> dict[str, float | str]:
    predictions = probabilities >= threshold
    fold_f1_scores = []

    for test_site in sorted(set(site_ids)):
        test_mask = site_ids == test_site
        fold_f1_scores.append(
            f1_score(labels[test_mask], predictions[test_mask], zero_division=0)
        )

    false_negatives = int(((labels == 1) & (predictions == 0)).sum())
    false_positives = int(((labels == 0) & (predictions == 1)).sum())
    true_positives = int(((labels == 1) & (predictions == 1)).sum())
    true_negatives = int(((labels == 0) & (predictions == 0)).sum())

    return {
        "scaler": config.scaler,
        "class_weight": config.class_weight,
        "c_value": config.c_value,
        "threshold": threshold,
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision_archeologique": float(
            precision_score(labels, predictions, zero_division=0)
        ),
        "recall_archeologique": float(
            recall_score(labels, predictions, zero_division=0)
        ),
        "f1_archeologique": float(f1_score(labels, predictions, zero_division=0)),
        "fold_f1_mean": float(np.mean(fold_f1_scores)),
        "fold_f1_std": float(np.std(fold_f1_scores)),
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "true_positives": true_positives,
        "true_negatives": true_negatives,
    }


def _build_classifier(
    config: TrialConfig,
    random_state: int,
    LogisticRegression,
    make_pipeline,
    StandardScaler,
    RobustScaler,
    Normalizer,
):
    class_weight = None if config.class_weight == "none" else config.class_weight
    classifier = LogisticRegression(
        C=config.c_value,
        class_weight=class_weight,
        max_iter=1000,
        random_state=random_state,
        solver="liblinear",
    )
    if config.scaler == "standard":
        return make_pipeline(StandardScaler(), classifier)
    if config.scaler == "robust":
        return make_pipeline(RobustScaler(), classifier)
    if config.scaler == "normalizer":
        return make_pipeline(Normalizer(), classifier)
    return classifier


def _write_csv(results: list[dict[str, float | str]], output_path: Path) -> None:
    fieldnames = [
        "rank",
        "scaler",
        "class_weight",
        "c_value",
        "threshold",
        "accuracy",
        "precision_archeologique",
        "recall_archeologique",
        "f1_archeologique",
        "fold_f1_mean",
        "fold_f1_std",
        "false_negatives",
        "false_positives",
        "true_positives",
        "true_negatives",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for rank, row in enumerate(results, start=1):
            writer.writerow({"rank": rank, **row})


def _write_markdown(results: list[dict[str, float | str]], output_path: Path) -> None:
    baseline = _find_baseline(results)
    lines = [
        "# Fusion Hyperparameter Search",
        "",
        "## Best Trials By F1 Archeologique",
        "",
        "| Rank | Scaler | Class weight | C | Threshold | Accuracy | Precision | Recall | F1 | FN | FP |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(results[:20], start=1):
        lines.append(_trial_line(rank, row))

    if baseline is not None:
        lines.extend(
            [
                "",
                "## Current Baseline Equivalent",
                "",
                "| Scaler | Class weight | C | Threshold | Accuracy | Precision | Recall | F1 | FN | FP |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
                _trial_line(None, baseline),
            ]
        )

    recall_sorted = sorted(
        results,
        key=lambda row: (
            row["recall_archeologique"],
            row["f1_archeologique"],
            row["accuracy"],
        ),
        reverse=True,
    )
    lines.extend(
        [
            "",
            "## Best Trials By Recall Archeologique",
            "",
            "| Rank | Scaler | Class weight | C | Threshold | Accuracy | Precision | Recall | F1 | FN | FP |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for rank, row in enumerate(recall_sorted[:20], start=1):
        lines.append(_trial_line(rank, row))

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_baseline(results: list[dict[str, float | str]]) -> dict[str, float | str] | None:
    for row in results:
        if (
            row["scaler"] == "standard"
            and row["class_weight"] == "balanced"
            and float(row["c_value"]) == 1.0
            and float(row["threshold"]) == 0.5
        ):
            return row
    return None


def _trial_line(rank: int | None, row: dict[str, float | str]) -> str:
    prefix = f"| {rank} |" if rank is not None else "|"
    return (
        f"{prefix} {row['scaler']} | {row['class_weight']} | "
        f"{float(row['c_value']):.3g} | {float(row['threshold']):.2f} | "
        f"{float(row['accuracy']):.3f} | "
        f"{float(row['precision_archeologique']):.3f} | "
        f"{float(row['recall_archeologique']):.3f} | "
        f"{float(row['f1_archeologique']):.3f} | "
        f"{int(row['false_negatives'])} | {int(row['false_positives'])} |"
    )


def _print_summary(
    results: list[dict[str, float | str]],
    output_csv: Path,
    output_md: Path,
) -> None:
    best = results[0]
    baseline = _find_baseline(results)
    print("Best by F1 archeologique:")
    print(
        f"- scaler={best['scaler']}, class_weight={best['class_weight']}, "
        f"C={best['c_value']}, threshold={best['threshold']}"
    )
    print(
        f"- accuracy={best['accuracy']:.3f}, precision={best['precision_archeologique']:.3f}, "
        f"recall={best['recall_archeologique']:.3f}, F1={best['f1_archeologique']:.3f}"
    )
    print(
        f"- false_negatives={best['false_negatives']}, "
        f"false_positives={best['false_positives']}"
    )

    if baseline is not None:
        print("Baseline equivalent:")
        print(
            f"- accuracy={baseline['accuracy']:.3f}, "
            f"precision={baseline['precision_archeologique']:.3f}, "
            f"recall={baseline['recall_archeologique']:.3f}, "
            f"F1={baseline['f1_archeologique']:.3f}"
        )

    print(f"CSV report: {output_csv}")
    print(f"Markdown report: {output_md}")


if __name__ == "__main__":
    raise SystemExit(main())

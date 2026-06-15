from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.features import extract_image_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Random Forest baselines on QGIS RGB/LiDAR exports."
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports_qgis" / "dataset_audit.csv",
        help="CSV produced by scripts/audit_exported_dataset.py.",
    )
    parser.add_argument(
        "--exclude-types",
        nargs="*",
        default=[],
        help="Patch types to exclude, for example: --exclude-types tres_large",
    )
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--feature-max-side",
        type=int,
        default=768,
        help="Resize images so their largest side is at most this size before feature extraction.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, classification_report, f1_score
    except ModuleNotFoundError:
        print("scikit-learn is required. Install it with:")
        print("python -m pip install -r requirements.txt")
        return 1

    args = parse_args()
    rows = _load_rows(args.audit_csv, excluded_types=set(args.exclude_types))

    if not rows:
        print(f"No usable rows found in {args.audit_csv}")
        return 1

    labels = np.asarray([_label_to_int(row["label"]) for row in rows], dtype=np.int64)
    site_ids = np.asarray([row["site_id"] for row in rows])

    rgb_features = np.vstack(
        [
            extract_image_features(Path(row["rgb_path"]), max_side=args.feature_max_side)
            for row in rows
        ]
    )
    multimodal_features = np.vstack(
        [
            np.concatenate(
                [
                    extract_image_features(
                        Path(row["rgb_path"]), max_side=args.feature_max_side
                    ),
                    extract_image_features(
                        Path(row["lidar_path"]), max_side=args.feature_max_side
                    ),
                ]
            )
            for row in rows
        ]
    )

    print(f"Samples used: {len(rows)}")
    print(f"Sites used: {len(set(site_ids))}")
    print(f"Excluded patch types: {args.exclude_types or 'none'}")
    _print_counts(rows)

    print()
    _evaluate_leave_one_site_out(
        "RGB only",
        rgb_features,
        labels,
        site_ids,
        args.n_estimators,
        args.random_state,
        RandomForestClassifier,
        accuracy_score,
        f1_score,
        classification_report,
    )

    print()
    _evaluate_leave_one_site_out(
        "RGB + LiDAR",
        multimodal_features,
        labels,
        site_ids,
        args.n_estimators,
        args.random_state,
        RandomForestClassifier,
        accuracy_score,
        f1_score,
        classification_report,
    )
    return 0


def _load_rows(audit_csv: Path, excluded_types: set[str]) -> list[dict[str, str]]:
    with audit_csv.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    usable = []
    for row in rows:
        if row["status"] != "ok":
            continue
        if row["patch_type"] in excluded_types:
            continue
        if not row["lidar_path"]:
            continue
        usable.append(row)
    return usable


def _label_to_int(label: str) -> int:
    if label == "archeologique":
        return 1
    if label == "non_archeologique":
        return 0
    raise ValueError(f"Unknown label: {label}")


def _print_counts(rows: list[dict[str, str]]) -> None:
    labels = sorted({row["label"] for row in rows})
    for label in labels:
        print(f"- {label}: {sum(row['label'] == label for row in rows)}")

    patch_types = sorted({row["patch_type"] for row in rows})
    for patch_type in patch_types:
        print(f"- {patch_type}: {sum(row['patch_type'] == patch_type for row in rows)}")


def _evaluate_leave_one_site_out(
    name: str,
    features: np.ndarray,
    labels: np.ndarray,
    site_ids: np.ndarray,
    n_estimators: int,
    random_state: int,
    model_cls,
    accuracy_score,
    f1_score,
    classification_report,
) -> None:
    print(f"{name} leave-one-site-out")

    all_true = []
    all_pred = []
    fold_scores = []

    for test_site in sorted(set(site_ids)):
        train_mask = site_ids != test_site
        test_mask = site_ids == test_site

        model = model_cls(
            n_estimators=n_estimators,
            random_state=random_state,
            class_weight="balanced",
            n_jobs=-1,
        )
        model.fit(features[train_mask], labels[train_mask])
        predictions = model.predict(features[test_mask])

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


if __name__ == "__main__":
    raise SystemExit(main())

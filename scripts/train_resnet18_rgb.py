from __future__ import annotations

import argparse
import csv
import os
import random
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
        description="Train/evaluate a ResNet-18 RGB classifier with leave-one-site-out validation."
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
        default=["tres_large"],
        help="Patch types to exclude. Default excludes very large context views.",
    )
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--torch-cache-dir",
        type=Path,
        default=PROJECT_ROOT / "models" / "torch_cache",
        help="Directory used to store pretrained PyTorch weights.",
    )
    parser.add_argument(
        "--fine-tune",
        action="store_true",
        help="Fine-tune the full ResNet instead of training only the final classifier.",
    )
    parser.add_argument(
        "--no-pretrained",
        action="store_true",
        help="Use random ResNet weights instead of ImageNet pretrained weights.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        import torch
        from sklearn.metrics import accuracy_score, classification_report, f1_score
        from torch import nn
        from torch.utils.data import DataLoader
        from torchvision import models, transforms
    except ModuleNotFoundError:
        print("PyTorch, torchvision and scikit-learn are required. Install with:")
        print("python -m pip install -r requirements.txt")
        return 1

    args = parse_args()
    args.torch_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TORCH_HOME"] = str(args.torch_cache_dir)
    _set_seed(args.random_state)

    records = _load_records(args.audit_csv, set(args.exclude_types))
    if not records:
        print(f"No usable records found in: {args.audit_csv}")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_transform, test_transform = _build_transforms(
        transforms,
        image_size=args.image_size,
        pretrained=not args.no_pretrained,
    )

    print(f"Device: {device}")
    print(f"Samples used: {len(records)}")
    print(f"Sites used: {len({record.site_id for record in records})}")
    print(f"Excluded patch types: {args.exclude_types or 'none'}")
    print(f"Pretrained: {not args.no_pretrained}")
    print(f"Fine-tune full model: {args.fine_tune}")
    _print_counts(records)

    all_true: list[int] = []
    all_pred: list[int] = []
    fold_scores = []

    for test_site in sorted({record.site_id for record in records}):
        train_records = [record for record in records if record.site_id != test_site]
        test_records = [record for record in records if record.site_id == test_site]

        train_loader = DataLoader(
            PatchDataset(train_records, train_transform),
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=0,
        )
        test_loader = DataLoader(
            PatchDataset(test_records, test_transform),
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=0,
        )

        model = _build_model(
            models=models,
            nn=nn,
            pretrained=not args.no_pretrained,
            fine_tune=args.fine_tune,
        ).to(device)

        optimizer = torch.optim.AdamW(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            lr=args.learning_rate,
            weight_decay=args.weight_decay,
        )
        loss_fn = nn.CrossEntropyLoss(weight=_class_weights(train_records, torch, device))

        for epoch in range(1, args.epochs + 1):
            loss = _train_one_epoch(model, train_loader, optimizer, loss_fn, device, torch)
            if epoch == args.epochs:
                print(f"- test={test_site} epoch={epoch}/{args.epochs} loss={loss:.4f}")

        true_labels, predictions = _predict(model, test_loader, device, torch)
        accuracy = accuracy_score(true_labels, predictions)
        f1 = f1_score(true_labels, predictions, zero_division=0)
        fold_scores.append((accuracy, f1))
        all_true.extend(true_labels)
        all_pred.extend(predictions)

        print(
            f"  result test={test_site}: accuracy={accuracy:.3f}, "
            f"F1 archeologique={f1:.3f}, n={len(test_records)}"
        )

    fold_scores_array = np.asarray(fold_scores, dtype=np.float32)
    print()
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


def _build_transforms(transforms, image_size: int, pretrained: bool):
    if pretrained:
        mean = [0.485, 0.456, 0.406]
        std = [0.229, 0.224, 0.225]
    else:
        mean = [0.5, 0.5, 0.5]
        std = [0.5, 0.5, 0.5]

    train_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.08),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )
    test_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )
    return train_transform, test_transform


def _build_model(models, nn, pretrained: bool, fine_tune: bool):
    weights = None
    if pretrained:
        try:
            weights = models.ResNet18_Weights.DEFAULT
        except AttributeError:
            weights = "DEFAULT"

    model = models.resnet18(weights=weights)

    if not fine_tune:
        for parameter in model.parameters():
            parameter.requires_grad = False

    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, 2)
    return model


def _class_weights(records: list[PatchRecord], torch, device):
    counts = np.bincount([record.label for record in records], minlength=2).astype(np.float32)
    weights = counts.sum() / np.maximum(counts, 1.0)
    weights = weights / weights.mean()
    return torch.tensor(weights, dtype=torch.float32, device=device)


def _train_one_epoch(model, loader, optimizer, loss_fn, device, torch) -> float:
    model.train()
    total_loss = 0.0
    total_items = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(images)
        loss = loss_fn(logits, labels)
        loss.backward()
        optimizer.step()

        total_loss += float(loss.item()) * int(labels.shape[0])
        total_items += int(labels.shape[0])

    return total_loss / max(total_items, 1)


def _predict(model, loader, device, torch) -> tuple[list[int], list[int]]:
    model.eval()
    true_labels = []
    predictions = []

    with torch.no_grad():
        for images, labels in loader:
            logits = model(images.to(device))
            batch_predictions = logits.argmax(dim=1).cpu().tolist()
            predictions.extend(batch_predictions)
            true_labels.extend(labels.tolist())

    return true_labels, predictions


def _print_counts(records: list[PatchRecord]) -> None:
    for label_name, label in [("non_archeologique", 0), ("archeologique", 1)]:
        print(f"- {label_name}: {sum(record.label == label for record in records)}")

    for patch_type in sorted({record.patch_type for record in records}):
        print(f"- {patch_type}: {sum(record.patch_type == patch_type for record in records)}")


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


if __name__ == "__main__":
    raise SystemExit(main())

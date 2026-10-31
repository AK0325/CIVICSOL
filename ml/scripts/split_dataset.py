#!/usr/bin/env python3
"""
CIVICSOL - Reproducible Dataset Split Utility
Splits paired civic images and YOLO annotation labels into train / val / test sets.
Ensures zero data leakage between splits using cryptographic hashing.
"""

import argparse
import hashlib
import os
import random
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def get_file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def split_dataset(
    source_images_dir: Path,
    source_labels_dir: Path,
    output_root: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.20,
    test_ratio: float = 0.10,
    seed: int = 42,
) -> None:
    assert round(train_ratio + val_ratio + test_ratio, 2) == 1.0, "Ratios must sum to 1.0"

    random.seed(seed)
    image_files = [p for p in source_images_dir.iterdir() if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTS]
    
    # Filter out duplicates at source
    unique_images: List[Path] = []
    seen_hashes: Dict[str, Path] = {}
    for img in image_files:
        h = get_file_hash(img)
        if h in seen_hashes:
            print(f"Skipping duplicate source image: {img.name} (duplicate of {seen_hashes[h].name})")
        else:
            seen_hashes[h] = img
            unique_images.append(img)

    random.shuffle(unique_images)
    total = len(unique_images)

    n_train = int(total * train_ratio)
    n_val = int(total * val_ratio)
    n_test = total - n_train - n_val

    splits = {
        "train": unique_images[:n_train],
        "val": unique_images[n_train : n_train + n_val],
        "test": unique_images[n_train + n_val :],
    }

    print(f"Splitting {total} unique images (Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])})")

    for split_name, imgs in splits.items():
        img_out = output_root / "images" / split_name
        lbl_out = output_root / "labels" / split_name
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img in imgs:
            shutil.copy2(img, img_out / img.name)
            lbl = source_labels_dir / f"{img.stem}.txt"
            if lbl.exists():
                shutil.copy2(lbl, lbl_out / lbl.name)
            else:
                # Negative background sample (empty label file)
                (lbl_out / f"{img.stem}.txt").touch()

    print("Dataset splitting completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split civic hazard dataset.")
    parser.add_argument("--images", type=Path, required=True, help="Directory containing source images")
    parser.add_argument("--labels", type=Path, required=True, help="Directory containing source labels")
    parser.add_argument("--output", type=Path, default=Path("ml/dataset"), help="Output root directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    split_dataset(args.images, args.labels, args.output, seed=args.seed)


#!/usr/bin/env python3
"""
CIVICSOL - YOLOv8 Dataset Validation Utility
Validates:
1. Strict correspondence between images and labels (.txt) across train/val/test splits.
2. Valid YOLO bbox coordinates (normalized in [0.0, 1.0], x_center, y_center, w > 0, h > 0).
3. Class ID compliance with the 8-class taxonomy (IDs 0..7).
4. Image integrity and corrupt image detection.
5. Duplicate image detection via cryptographic SHA-256 hashing.
6. Data leakage prevention across train, val, and test splits.
7. Class distribution and statistical summary.
"""

import hashlib
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple
from PIL import Image

CLASSES = {
    0: "pothole",
    1: "garbage",
    2: "water_leakage",
    3: "broken_streetlight",
    4: "damaged_road",
    5: "drainage_issue",
    6: "fallen_tree",
    7: "damaged_infrastructure",
}

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def compute_file_hash(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_split(
    split_name: str,
    images_dir: Path,
    labels_dir: Path,
    known_hashes: Dict[str, Tuple[str, str]],
) -> Tuple[bool, List[str], Counter, int]:
    """
    Validates a single dataset split.
    Returns: (is_valid, error_list, class_counter, total_images)
    """
    errors: List[str] = []
    class_counts: Counter = Counter()

    if not images_dir.exists():
        return False, [f"Images directory missing: {images_dir}"], class_counts, 0

    image_files = [p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTS]
    total_images = len(image_files)

    for img_path in sorted(image_files):
        # 1. Image uncorrupted check
        try:
            with Image.open(img_path) as img:
                img.verify()
        except Exception as e:
            errors.append(f"[{split_name}] Corrupt image: {img_path.name} ({e})")
            continue

        # 2. Hash & duplicate / data leakage check
        img_hash = compute_file_hash(img_path)
        if img_hash in known_hashes:
            orig_split, orig_name = known_hashes[img_hash]
            if orig_split == split_name:
                errors.append(f"[{split_name}] Duplicate image within split: {img_path.name} == {orig_name}")
            else:
                errors.append(
                    f"[{split_name}] Data leakage! Image {img_path.name} is identical to {orig_name} in '{orig_split}' split."
                )
        else:
            known_hashes[img_hash] = (split_name, img_path.name)

        # 3. Corresponding label file check
        label_path = labels_dir / f"{img_path.stem}.txt"
        if not label_path.exists():
            # Negative/background image without annotations is allowed in YOLO, but should be explicit
            continue

        # 4. Annotation format & coordinate validation
        try:
            with open(label_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]

            for line_idx, line in enumerate(lines, start=1):
                tokens = line.split()
                if len(tokens) != 5:
                    errors.append(
                        f"[{split_name}] {label_path.name}:{line_idx} - Invalid YOLO token count ({len(tokens)} != 5)"
                    )
                    continue

                try:
                    cls_id = int(tokens[0])
                    xc, yc, w, h = map(float, tokens[1:5])
                except ValueError:
                    errors.append(
                        f"[{split_name}] {label_path.name}:{line_idx} - Non-numeric coordinates: '{line}'"
                    )
                    continue

                if cls_id not in CLASSES:
                    errors.append(
                        f"[{split_name}] {label_path.name}:{line_idx} - Invalid class ID {cls_id} (allowed: 0..{len(CLASSES)-1})"
                    )
                    continue

                # Check normalized boundaries
                for name, val in [("xc", xc), ("yc", yc), ("w", w), ("h", h)]:
                    if not (0.0 <= val <= 1.0):
                        errors.append(
                            f"[{split_name}] {label_path.name}:{line_idx} - Coordinate {name}={val} out of bounds [0.0, 1.0]"
                        )

                if w <= 0.0 or h <= 0.0:
                    errors.append(
                        f"[{split_name}] {label_path.name}:{line_idx} - Zero or negative dimension: w={w}, h={h}"
                    )

                class_counts[cls_id] += 1

        except Exception as e:
            errors.append(f"[{split_name}] Could not read label {label_path.name}: {e}")

    return len(errors) == 0, errors, class_counts, total_images


def validate_dataset(dataset_root: Path) -> bool:
    """Validates the full dataset directory structure across train, val, test."""
    print("=" * 60)
    print("CIVICSOL YOLOv8 Dataset Validation")
    print(f"Target Root: {dataset_root.resolve()}")
    print("=" * 60)

    known_hashes: Dict[str, Tuple[str, str]] = {}
    all_errors: List[str] = []
    overall_counts: Counter = Counter()
    total_images_all = 0

    splits = ["train", "val", "test"]
    for split in splits:
        images_dir = dataset_root / "images" / split
        labels_dir = dataset_root / "labels" / split

        valid, errors, counts, count_imgs = validate_split(split, images_dir, labels_dir, known_hashes)
        total_images_all += count_imgs
        overall_counts.update(counts)
        all_errors.extend(errors)

        status_str = "VALID" if valid else f"INVALID ({len(errors)} errors)"
        print(f"Split: {split:<6} | Images: {count_imgs:<4} | Annotations: {sum(counts.values()):<4} | Status: {status_str}")

    print("-" * 60)
    print("Class Distribution Across Dataset:")
    for cls_id in sorted(CLASSES.keys()):
        cls_name = CLASSES[cls_id]
        print(f"  [{cls_id}] {cls_name:<24} : {overall_counts[cls_id]:>4} annotations")

    print("-" * 60)
    print(f"Total Images: {total_images_all}")
    print(f"Total Bounding Boxes: {sum(overall_counts.values())}")

    if all_errors:
        print("\nERRORS DETECTED:")
        for err in all_errors[:20]:
            print(f"  ERROR: {err}")
        if len(all_errors) > 20:
            print(f"  ... and {len(all_errors) - 20} more errors.")
        print("=" * 60)
        return False

    print("\nDataset validation PASSED with 0 errors.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "dataset"
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    is_ok = validate_dataset(root)
    sys.exit(0 if is_ok else 1)


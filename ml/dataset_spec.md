# CIVICSOL — Civic Hazard Object Detection Dataset Specification

## 1. Overview
This specification governs the computer vision dataset for CIVICSOL's municipal hazard detector. The dataset trains an Ultralytics YOLOv8 architecture to automatically identify, locate, and classify civic infrastructure defects and municipal sanitation issues from citizen-uploaded photographs.

---

## 2. 8-Class Municipal Hazard Taxonomy

The dataset is partitioned into exactly 8 municipal classes aligned with municipal department dispatch boundaries:

| Class ID | Class Name | Target Category | Description & Visual Characteristics | Minimum BBox Rules |
| :--- | :--- | :--- | :--- | :--- |
| `0` | `pothole` | Road Damage | Asphalt depressions, roadbed craters, pavement breakups. | Enclose entire perimeter of depression. |
| `1` | `garbage` | Garbage | Uncollected roadside refuse, overflowing bins, open garbage piles. | Bounding box enclosing continuous pile/dumpster. |
| `2` | `water_leakage` | Water Leakage | Burst pipelines, surface pooling from water supply pipe breaks, gushing hydrants. | Bounding box on surface pooling and source rupture. |
| `3` | `broken_streetlight` | Street Light | Unlit/damaged streetlamps, dangling luminaires, damaged lamp poles. | Enclose luminaire fixture and immediate mast section. |
| `4` | `damaged_road` | Road Damage | Large-scale road fractures, collapsed asphalt edges, missing pavers. | Enclose structural asphalt failure zone. |
| `5` | `drainage_issue` | Drainage | Clogged storm water drains, missing/broken manhole covers, sewer overflow. | Enclose manhole opening or clogged grate. |
| `6` | `fallen_tree` | Tree / Greenery | Fallen trunks or large tree branches obstructing roads, walkways, or power lines. | Enclose tree trunk or fallen branch obstruction. |
| `7` | `damaged_infrastructure` | Public Infra | Collapsed railings, broken pedestrian footpaths, fractured bus shelters, damaged barriers. | Enclose structural defect on public asset. |

---

## 3. Directory Structure

```text
ml/
├── dataset/
│   ├── data.yaml
│   ├── images/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── labels/
│       ├── train/
│       ├── val/
│       └── test/
├── scripts/
│   ├── validate_dataset.py
│   ├── split_dataset.py
│   └── ...
├── dataset_spec.md
├── yolo_detector.py
└── training/
    ├── weights/
    │   └── best.pt
    └── plots/
```

---

## 4. Annotation Standards & Format

- **Format:** Standard Darknet/YOLO normalized format (`.txt` per image with identical basename).
- **Line Structure:** `<class_id> <x_center> <y_center> <width> <height>`
  - `<class_id>`: Integer in [0, 7]
  - `<x_center>`, `<y_center>`: Float normalized to image width/height in [0.0, 1.0]
  - `<width>`, `<height>`: Float normalized in (0.0, 1.0]
- **Tight Bounding Boxes:** Bounding boxes must fit tightly around the visible defect with no more than 10% excessive background padding.
- **Occlusion Policy:** Partially occluded objects (>30% visible) must still be labeled.
- **Negative Background Samples:** 10% of total training images should contain normal clean streets, intact infrastructure, and closed bins with empty label files (0 annotations) to prevent false positives.

---

## 5. Data Integrity, Deduplication & Leakage Prevention

1. **Cryptographic Deduplication:** All images are indexed by SHA-256 hash. Duplicate images are strictly pruned.
2. **Zero Leakage:** No image with the same hash or burst capture sequence may appear in more than one split (Train, Val, or Test).
3. **Split Proportions:** 70% Train, 20% Validation, 10% Test.

---

## 6. Dataset Sources and Licensing

1. **Permitted Sources:**
   - Original citizen-submitted photographs captured during civic testing (CC BY 4.0 / Municipal Public Domain).
   - Publicly available datasets licensed under CC BY 4.0, CC0, or Open Data Commons (e.g., Roboflow Universe Public Civic Datasets, OpenStreetView, Road Damage Dataset RDD2022).
2. **Prohibited:**
   - Unlicensed proprietary imagery, private CCTV feeds without consent, copyrighted stock photography.
   - Fabricated annotations or arbitrary coordinates.

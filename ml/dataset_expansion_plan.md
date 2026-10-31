# CIVICSOL — YOLOv8 Dataset Expansion & Model Improvement Plan

**Target Model:** CivicYOLO-v8 (Ultralytics YOLOv8n)  
**Current Production Model:** [`ml/training/weights/best.pt`](ml/training/weights/best.pt) (Validation mAP@50: 0.0503, Precision: 0.5211, Recall: 0.2500)  
**Dataset Specification:** [`ml/dataset_spec.md`](ml/dataset_spec.md)  
**Configuration File:** [`ml/dataset/data.yaml`](ml/dataset/data.yaml)

---

## 1. Dataset Quality & Class Imbalance Audit

### 1.1 Current Baseline Metrics
A complete audit was conducted using [`ml/scripts/validate_dataset.py`](ml/scripts/validate_dataset.py) and [`ml/training/training_report.json`](ml/training/training_report.json):
- **Total Images:** 36 (Train: 25, Val: 7, Test: 4)
- **Total Bounding Boxes:** 39

```
Class Distribution Across Dataset:
  [0] pothole                  : 12 annotations (30.8%)
  [1] garbage                  :  9 annotations (23.1%)
  [2] water_leakage            :  3 annotations (7.7%)
  [3] broken_streetlight       :  3 annotations (7.7%)
  [4] damaged_road             :  3 annotations (7.7%)
  [5] drainage_issue           :  3 annotations (7.7%)
  [6] fallen_tree              :  3 annotations (7.7%)
  [7] damaged_infrastructure   :  3 annotations (7.7%)
```

### 1.2 Identified Quality & Training Deficits
1. **Severe Imbalance:** Potholes and garbage constitute 53.9% of the dataset. Six civic classes (`water_leakage`, `broken_streetlight`, `damaged_road`, `drainage_issue`, `fallen_tree`, `damaged_infrastructure`) each have only 3 annotations.
2. **Extreme Low Sample Size:** 36 images cannot capture the domain shift of real urban infrastructure (night vs. day lighting, weather conditions, varied road surfaces, camera angles, perspective distortion).
3. **High False Negative Rate:** Validation Recall of 0.25 indicates that 75% of actual civic hazards in validation images are missed due to underrepresented classes having insufficient training gradient steps.
4. **Single-Box Bias:** Existing annotations primarily annotate one central object per image, whereas real civic photos frequently feature clusters (multiple potholes, distributed garbage piles, concurrent street light and pole damage).

---

## 2. Dataset Expansion Roadmap

### 2.1 Target Distribution
To achieve production-grade detection ($\ge 0.70$ mAP@50), the dataset will be systematically expanded to **1,000+ verified images** with at least **125 annotations per class**:

| Class ID | Class Label | Current Annotations | Target Annotations | Expansion Multiplier |
|:---:|---|:---:|:---:|:---:|
| 0 | `pothole` | 12 | 160 | $13.3\times$ |
| 1 | `garbage` | 9 | 150 | $16.7\times$ |
| 2 | `water_leakage` | 3 | 125 | $41.7\times$ |
| 3 | `broken_streetlight` | 3 | 125 | $41.7\times$ |
| 4 | `damaged_road` | 3 | 130 | $43.3\times$ |
| 5 | `drainage_issue` | 3 | 125 | $41.7\times$ |
| 6 | `fallen_tree` | 3 | 125 | $41.7\times$ |
| 7 | `damaged_infrastructure`| 3 | 125 | $41.7\times$ |
| **Total** | | **39** | **1,065** | **$27.3\times$** |

### 2.2 Sourcing Strategy
1. **Active Learning from Citizen Uploads:**
   - Ingest citizen reports resolved and verified by municipal officers.
   - Run automated pre-annotation using current `best.pt`.
   - Send candidate detections to authority inspection queue for human verification.
2. **Open-Source Civic Datasets:**
   - Integrate open municipal datasets (e.g., Road Damage Dataset RDD2022, TACO garbage dataset, Cityscapes infrastructure).
   - Re-map external taxonomies strictly to CIVICSOL's 8 standard classes.
3. **Hard Negative Mining:**
   - Add clean pavement, intact streetlights, manicured trees, and clean drains as negative samples (zero bounding boxes) to minimize false positives.

---

## 3. Annotation Protocol & Quality Assurance Guidelines

1. **Tight Bounding Boxes:** Coordinates must tightly enclose the hazard without excessive background margins ($< 5\%$ background padding).
2. **Multi-Instance Rule:** Every visible hazard in the frame must be annotated. If 4 potholes are visible, 4 distinct bounding boxes must be drawn.
3. **Truncation & Occlusion:** If an object is partially obscured ($< 50\%$ occluded), annotate the visible portion. Discard objects occluded $> 80\%$.
4. **Validation Automation:** All newly collected images and annotations must pass [`ml/scripts/validate_dataset.py`](ml/scripts/validate_dataset.py) verifying normalization, SHA-256 deduplication, and zero cross-split leakage.

---

## 4. Model Training & Hyperparameter Optimization

### 4.1 Recommended Training Configuration
```python
training_params = {
    "model": "yolov8n.pt",       # Nano architecture for sub-100ms edge inference
    "epochs": 50,                # Extended convergence schedule
    "batch": 16,                 # Stable batch normalization
    "imgsz": 640,                # High-resolution input
    "optimizer": "AdamW",        # Weight decay for generalization
    "lr0": 0.001,                # Initial learning rate
    "lrf": 0.01,                 # Cosine decay factor
    "mosaic": 0.8,               # Mosaic augmentation for multi-scale resilience
    "mixup": 0.15,               # Mixup augmentation for occlusion robustness
    "degrees": 10.0,             # Rotation jitter (+/- 10 deg)
    "hsv_h": 0.015,              # Hue augmentation
    "hsv_s": 0.7,                # Saturation augmentation
    "hsv_v": 0.4,                # Value/brightness augmentation
}
```

---

## 5. Model Replacement Policy & Acceptance Gate

> [!CRITICAL]
> **Production Gate Invariant:** Do NOT replace the current model weights [`ml/training/weights/best.pt`](ml/training/weights/best.pt) without verified metric improvements across all 8 classes.

### Verification Gate Criteria:
1. **Validation mAP@50:** $\ge 0.50$ (currently $0.0503$).
2. **Validation Recall:** $\ge 0.45$ (currently $0.2500$).
3. **Per-Class Recall:** Every class must achieve $> 0.30$ recall on the holdout validation set.
4. **Zero Regression:** High-confidence detections on real citizen uploads (`uploads/civic_upload_1.jpg` and `uploads/civic_upload_2.jpg`) must maintain or exceed current detection precision.
5. **Inference Latency:** Average CPU inference time must remain $< 300\text{ ms}$ on 640x640 images.


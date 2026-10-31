# CIVICSOL — Final YOLOv8 Model Training Report

**Model Name:** CivicYOLO-v8  
**Experiment ID:** `civicsol_v1_exp_20261031_073259`  
**Base Architecture:** YOLOv8n (Ultralytics, COCO Pretrained)  
**Experiment Directory:** `ml/training/experiments/civicsol_v1_exp_20261031_073259/`  
**Experiment Best Weights:** `ml/training/experiments/civicsol_v1_exp_20261031_073259/weights/best.pt`  
**Baseline Preserved Weights:** `ml/training/weights/best.pt` (SHA-256: `d40e57fca471827607d1ca92239658aad382404045ae9db764436791287c36ae`)  
**Training Date:** October 31, 2026  
**Operating Status:** **EXPERIMENTAL / ADVISORY ONLY (Acceptance Gates Not Met)**  
**Promotion Verdict:** **PROMOTION STOPPED** (Requires 1,000+ Image Dataset Expansion)  

---

## 1. Executive Summary

In Phase 3 of the **CIVICSOL V1.0** engineering charter, a dedicated training run of the CIVICSOL YOLOv8n object detection model was conducted.

### Core Safeguards Enforced:
1. **Preservation of Baseline Model:** The existing production weights at `ml/training/weights/best.pt` were strictly preserved and were **not overwritten**.
2. **Experiment Isolation:** The training was executed inside an isolated, versioned experiment directory (`ml/training/experiments/civicsol_v1_exp_20261031_073259/`), containing best weights, last weights, training plots, confusion matrices, and machine-readable evaluation results.
3. **Hardware Acceleration:** Automatically detected and utilized Apple Silicon Metal Performance Shaders (`mps`) on Apple M4 with CPU fallback.
4. **Reproducibility & Augmentation:** Fixed random seed (`seed=42`), mosaic augmentation ($0.5$), mixup ($0.1$), rotation jitter ($\pm 5^\circ$), and color HSV jitter.
5. **Independent Split Evaluation:** Evaluated across a validation split ($7$ images) and a completely separate test split ($4$ images).

---

## 2. Training Hyperparameters & Execution Details

| Hyperparameter / Environment Setting | Value | Description |
| :--- | :--- | :--- |
| **Model Architecture** | YOLOv8n (Nano) | 73 layers, 3,134,408 parameters |
| **Pretrained Weights** | `yolov8n.pt` | Initialized from COCO base weights |
| **Hardware Device** | `mps` (Apple M4) | Apple Silicon Metal Performance Shaders (PyTorch 2.5.1) |
| **Dataset Configuration** | `ml/dataset/data.yaml` | 8-class municipal civic taxonomy |
| **Total Images** | 36 | 25 Train, 7 Val, 4 Test |
| **Total Annotations** | 39 | 27 Train, 8 Val, 4 Test |
| **Epochs** | 10 | Extended training schedule |
| **Batch Size** | 8 | Mini-batch accumulation |
| **Image Resolution (`imgsz`)** | 640 | $640 \times 640$ pixels letterboxed |
| **Optimizer** | AdamW (`lr=0.000833`) | Weight decay 0.0005, momentum 0.9 |
| **Patience** | 10 | Early stopping threshold |
| **Training Duration** | 54.02 seconds | 10 complete epochs on Apple M4 |

---

## 3. Quantitative Evaluation Metrics

### 3.1 Validation Set Performance (7 images, 8 annotations)

| Metric | Measured Result | Experimental Gate Target | Gate Status |
| :--- | :---: | :---: | :---: |
| **Overall Precision (P)** | 0.9556 (95.6%) | $\ge 0.70$ | **PASSED** |
| **Overall Recall (R)** | 0.0833 (8.33%) | $\ge 0.45$ | **FAILED** |
| **Validation $\text{mAP@50}$** | **0.1332 (13.32%)** | $\ge \mathbf{0.50}$ | **FAILED** |
| **Validation $\text{mAP@50-95}$** | 0.0347 (3.47%) | $\ge 0.30$ | **FAILED** |

### 3.2 Test Set Performance (4 images, 4 annotations)

| Metric | Measured Result | Experimental Gate Target | Gate Status |
| :--- | :---: | :---: | :---: |
| **Test Precision (P)** | 0.7031 (70.3%) | $\ge 0.65$ | **PASSED** |
| **Test Recall (R)** | 0.2500 (25.0%) | $\ge 0.40$ | **FAILED** |
| **Test $\text{mAP@50}$** | **0.2653 (26.53%)** | $\ge \mathbf{0.45}$ | **FAILED** |
| **Test $\text{mAP@50-95}$** | 0.1290 (12.90%) | $\ge 0.20$ | **FAILED** |
| **Inference Latency** | **45.4 ms / image** | $\le 100\text{ ms}$ | **PASSED** |

### 3.3 Per-Class Performance Breakdown

| Class ID | Civic Category | Val Instances | Val $\text{AP@50}$ | Test Instances | Test $\text{AP@50}$ | Evaluation Notes |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| `0` | `pothole` | 2 | 0.0000 | 0 | — | Low sample size; small feature loss |
| `1` | `garbage` | 3 | 0.5150 | 1 | 0.9950 | High recall on large distinct mounds |
| `2` | `water_leakage` | 1 | 0.0045 | 0 | — | Water reflection requires wet road training |
| `3` | `broken_streetlight` | 0 | — | 1 | 0.0000 | Night scenes needed |
| `4` | `damaged_road` | 0 | — | 0 | — | No val/test representation |
| `5` | `drainage_issue` | 0 | — | 0 | — | No val/test representation |
| `6` | `fallen_tree` | 1 | 0.0134 | 1 | 0.0663 | Confounded with background shrubs |
| `7` | `damaged_infrastructure` | 0 | — | 1 | 0.0000 | Insufficient sample diversity |

---

## 4. Root Cause of Gate Failure & Honest Model Classification

1. **Dataset Volume Bottleneck:** Training deep vision models on 25 training images cannot achieve generalized feature representation across 8 complex civic classes.
2. **Missing Test Classes:** Six classes have 0 test samples in the seed dataset.
3. **Formal Verdict:**
   - **Acceptance Gate 1 (Val $\text{mAP@50} \ge 0.50$):** **FAILED (0.1332 < 0.50)**
   - **Acceptance Gate 2 (Test $\text{mAP@50} \ge 0.45$):** **FAILED (0.2653 < 0.45)**
   - **Acceptance Gate 3 (Recall $\ge 0.45$):** **FAILED (0.0833 < 0.45)**
   - **Model Classification:** **EXPERIMENTAL**
   - **Promotion Status:** **STOPPED / RETAINED AS ADVISORY**
   - **Active Weights:** `ml/training/weights/best.pt` remains preserved as the baseline model.

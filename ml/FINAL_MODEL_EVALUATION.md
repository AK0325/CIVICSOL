# CIVICSOL — Final YOLOv8 Model Evaluation & Gate Assessment

**Evaluation Date:** October 31, 2026  
**Auditor:** Antigravity AI Engineering Team  
**Evaluated Artifacts:**
- Active Baseline Model: `ml/training/weights/best.pt`
- Versioned Experiment Run: `ml/training/experiments/civicsol_v1_exp_20261031_073259/weights/best.pt`
**Evaluation Scope:** Validation set, test set, per-class AP, confusion matrix, inference latency, edge cases, and acceptance gates.  
**Pilot Operating Status:** **ADVISORY ONLY (Human-in-the-Loop Safeguards Enforced)**  
**Promotion Verdict:** **MODEL PROMOTION STOPPED (Experimental Gates Not Met)**  

---

## 1. Experimental Acceptance Gates Audit

| Gate | Criterion | Target Threshold | Measured Result (Experiment) | Measured Result (Baseline) | Gate Status |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **Gate 1** | Overall Validation $\text{mAP@50}$ | $\ge 0.50$ (50.0%) | **0.1332 (13.3%)** | 0.0503 (5.03%) | **FAILED** |
| **Gate 2** | Overall Test $\text{mAP@50}$ | $\ge 0.45$ (45.0%) | **0.2653 (26.5%)** | 0.0191 (1.91%) | **FAILED** |
| **Gate 3** | Overall Recall (Validation) | $\ge 0.45$ (45.0%) | **0.0833 (8.33%)** | 0.2500 (25.0%) | **FAILED** |
| **Gate 4** | Inference Latency | $\le 100\text{ ms}$ / image | **45.4 ms / image** | 48.0 ms / image | **PASSED** |
| **Gate 5** | Agnostic NMS Cross-Class Suppression | Enabled ($\text{IoU} \le 0.45$) | Active ($\text{IoU} = 0.45$) | Active ($\text{IoU} = 0.45$) | **PASSED** |
| **Gate 6** | Low-Confidence Advisory Flagging | Flag detections $< 45\%$ | Status `LOW_CONFIDENCE` | Status `LOW_CONFIDENCE` | **PASSED** |
| **Gate 7** | Clean Image Negative Handling | No detections on clean streets | 0 false alarms | 0 false alarms | **PASSED** |
| **Gate 8** | Corrupt/Non-Image Input Handling | Graceful rejection without crash | `INVALID_IMAGE` status | `INVALID_IMAGE` status | **PASSED** |
| **Gate 9** | Missing Weights Graceful Degradation | Fallback without service interruption | `MODEL_UNAVAILABLE` | `MODEL_UNAVAILABLE` | **PASSED** |
| **Gate 10** | Human-in-the-Loop Governance | No autonomous status or dispatch | Mandatory officer action | Mandatory officer action | **PASSED** |

---

## 2. Detailed Per-Class Evaluation

### 2.1 Class Performance Matrix (Experiment `civicsol_v1_exp_20261031_073259`)

| Class ID | Class Label | Val Instances | Val Precision | Val Recall | Val $\text{mAP@50}$ | Test Instances | Test $\text{mAP@50}$ | Evaluation Notes |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `0` | `pothole` | 2 | 1.0000 | 0.0000 | 0.0000 | 0 | — | Small sample size; missed edge features |
| `1` | `garbage` | 3 | 0.8230 | 0.3330 | 0.5150 | 1 | 0.9950 | High precision on distinctive color contrast |
| `2` | `water_leakage` | 1 | 1.0000 | 0.0000 | 0.0045 | 0 | — | Low contrast against dry asphalt |
| `3` | `broken_streetlight` | 0 | — | — | — | 1 | 0.0000 | Absence of night-time training imagery |
| `4` | `damaged_road` | 0 | — | — | — | 0 | — | 0 samples in val/test split |
| `5` | `drainage_issue` | 0 | — | — | — | 0 | — | 0 samples in val/test split |
| `6` | `fallen_tree` | 1 | 1.0000 | 0.0000 | 0.0134 | 1 | 0.0663 | Overlaps with background foliage |
| `7` | `damaged_infrastructure` | 0 | — | — | — | 1 | 0.0000 | Complex multi-part geometric structure |
| **Overall** | **All 8 Classes** | **7** | **0.9556** | **0.0833** | **0.1332** | **4** | **0.2653** | **Acceptance Gates Not Met** |

---

## 3. False-Positive and False-Negative Defect Analysis

### 3.1 Class Overlap Defect & Runtime Mitigation
- **Observed Behavior:** On complex civic scenes (such as uncollected waste heaps), standard YOLO inference fires competing detections (`fallen_tree` and `water_leakage`) on the same spatial region.
- **Resolution:** `ml/yolo_detector.py` enforces class-agnostic NMS (`agnostic_nms=True`, `iou=0.45`). When tested on `test/garbage_1.jpg`, detections were reduced from 8 overlapping boxes to 3 non-overlapping boxes.

### 3.2 Low-Confidence Detection Safeguard
- **Defect:** Bounding boxes with marginal confidence (e.g., $38\%$) risk being interpreted as confirmed municipal hazards.
- **Resolution:** Any detection with confidence below $45\%$ triggers `status: "LOW_CONFIDENCE"` and `is_low_confidence: True`. In the Authority Command Center, a prominent orange alert banner is displayed:
  > ⚠️ Low Confidence Detection (< 45%): Visual verification by officer required before dispatch.

### 3.3 Authority False-Positive Feedback Loop
- **Operational Control:** Authorized field officers can flag incorrect bounding boxes using the "Flag False Positive" button in the Authority View Details interface. The feedback (class name, bounding box coordinates, and officer explanation) is recorded in `analysis_metadata` and logged into the PostgreSQL `audit_logs` table for future active-learning retraining.

---

## 4. Model Registry & Promotion Verdict

- **Active Inference Model:** `ml/training/weights/best.pt` (Baseline preserved intact).
- **New Experiment:** `ml/training/experiments/civicsol_v1_exp_20261031_073259/weights/best.pt` (Recorded in `ml/model_registry.json`).
- **Promotion Status:** **STOPPED / EXPERIMENTAL ONLY**.
- **Reason:** Model does not meet Gates 1, 2, and 3 ($\text{mAP@50} = 0.1332 < 0.50$, Recall $= 0.0833 < 0.45$).
- **Deployment Policy:** Approved strictly for **ADVISORY USE IN CONTROLLED PILOT** under human municipal governance. All official dispatch, department routing, and status resolution actions require explicit authority officer confirmation.

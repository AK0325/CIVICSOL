# CIVICSOL — Suspicious & Fraudulent Submission Detection Report

**Date:** October 31, 2026  
**Component:** Civic Submission Authenticity & Fraud Risk Assessment Engine  
**Module:** `backend/ai/suspicious_detector.py`  
**Integration Points:** `backend/ai/pipeline.py`, `frontend/src/pages/authority/IssueDetails.jsx`  
**Status:** FULLY IMPLEMENTED & VERIFIED  

---

## 1. Threat Model & Municipal Vulnerabilities

In municipal civic engagement platforms where citizens receive civic credits, gamified badges, and community leaderboard status, platforms face distinct fraud vectors:

1. **Credit Gaming & Replay Spam:**
   Citizens submitting the same photograph repeatedly across different wards to accumulate civic credits (+20 credits per valid report with image and GPS).
2. **Geographical Fabrications (Stock/Internet Photos):**
   Submitting downloaded or stock photographs from remote locations to fabricate complaints in a municipal jurisdiction.
3. **Burst Submissions (Automated Bots/Scripts):**
   Rapid submission spikes from a single citizen account (e.g., > 3 reports within 5 minutes) designed to overwhelm municipal dispatchers or exploit rate limits.
4. **Contradictory Claims (Evidence Conflicts):**
   Reporting severe structural hazards with generic or unrelated photo evidence (e.g., reporting a collapsed road while submitting a photo of a clear lawn or park bench).

---

## 2. Risk Evaluation Engine Architecture

The engine in `backend/ai/suspicious_detector.py` evaluates every submitted civic issue across four empirical risk dimensions:

### Dimension 1: Reused Image Across Distant Coordinates (> 1 km)
- Computes SHA-256 and 64-bit dHash of the issue image.
- Compares against historical submissions in PostgreSQL.
- If an exact SHA-256 match or high perceptual match ($\ge 95\%$) is found at a distance greater than 1,000 meters ($> 1\text{ km}$):
  - **Risk Score Addition:** $+45$ points
  - **Factor Logged:** `"Image evidence matches prior Issue #X located Y km away."`

### Dimension 2: Submission Burst Frequency
- Checks submissions from the same `user_id` within the last 5 minutes.
- If recent submissions $\ge 3$:
  - **Risk Score Addition:** $+30$ points
  - **Factor Logged:** `"High submission burst: Citizen account submitted N reports in 5 minutes."`
- If recent submissions $== 2$:
  - **Risk Score Addition:** $+15$ points
  - **Factor Logged:** `"Elevated submission rate: Citizen account submitted N reports in 5 minutes."`

### Dimension 3: Contradictory Evidence (Vision vs Citizen Description)
- Reconciles Gemini description extraction against YOLO computer vision detections.
- If `evidence_consistency == "INCONSISTENT"`:
  - **Risk Score Addition:** $+20$ points
  - **Factor Logged:** `"Evidence conflict: [explanation from grounding engine]"`

### Dimension 4: Image File Integrity & Anomaly Check
- If image byte size $< 3\text{ KB}$:
  - **Risk Score Addition:** $+15$ points
  - **Factor Logged:** `"Suspiciously small image file size (< 3KB)."`
- If resolution $< 100 \times 100\text{ px}$:
  - **Risk Score Addition:** $+10$ points
  - **Factor Logged:** `"Low resolution evidence (WxH px)."`

---

## 3. Classification Tiers & Advisory Recommendations

Total risk score is clamped between 0 and 100 points:

| Risk Score Range | Classification Tier | Required Authority Action | Advisory Recommendation |
| :---: | :--- | :---: | :--- |
| **0 – 14** | `NORMAL` | Standard Dispatch | "Genuine citizen report; proceed with standard municipal dispatch." |
| **15 – 34** | `LOW_RISK` | Standard Dispatch | "Minor observations noted; standard dispatch." |
| **35 – 59** | `REVIEW_REQUIRED` | Review Required | "Advisory review flag: Review evidence details during officer assignment." |
| **60 – 100** | `HIGH_RISK` | Visual Verification | "High risk indicator: Officer visual inspection required prior to field dispatch." |
| **Format Errors** | `INVALID_EVIDENCE` | Citizen Resubmission | "Invalid image file; request citizen resubmission." |

---

## 4. Human-in-the-Loop Safeguards

1. **Zero Autonomous Rejection:**
   Under no circumstances does the AI engine auto-reject, delete, or hide a citizen submission based on a high risk score.
2. **Authority Command Center Section E2:**
   The Authority View Details interface (`frontend/src/pages/authority/IssueDetails.jsx`) displays a dedicated **Suspicious Submission Risk Assessment** panel with a visual score meter, risk level badge, specific triggering factors, and municipal recommendation.
3. **Evidence Preservation:**
   All images and coordinates are permanently retained for municipal auditability and verification.


# CIVICSOL — Duplicate Detection & Exact API Replay Prevention Report

**Date:** October 31, 2026  
**Component:** Civic Multi-Factor Duplicate Engine & Exact API Replay Protection  
**Modules:** `backend/ai/duplicate_detector.py`, `backend/routes/issues.py`  
**Status:** FULLY IMPLEMENTED & VERIFIED  

---

## 1. Forensic Audit of Target Duplicate Issues (#3, #4, #5, #27, #56)

During system audits, several duplicate issues were discovered in the local PostgreSQL database:
- Issue #3: Garbage dumped on main road corner
- Issue #4: Garbage dumped on main road corner
- Issue #5: Garbage dumped on main road corner
- Issue #27: Garbage dumped on main road corner
- Issue #56: Garbage dumped on main road corner

### Findings:
1. **Identical Cryptographic Checksum:**
   Computing the SHA-256 hash across the evidence images for all 5 issues yielded the identical hash:
   `4eeeb1173cd35024b819fbbd9dae6fa39f5f0883311910cf321ec9ef71974720`
2. **Identical GPS Coordinates:**
   Latitude: `23.033863`, Longitude: `72.585022`
3. **Root Cause:**
   Automated end-to-end integration test runs and rapid re-submissions re-uploaded the seed image `garbage_1.jpg` without checking for identical cryptographic replays from the same citizen. Each submission created an independent row in `civic_issues` and awarded +20 civic credits.

---

## 2. Five-Factor Weighted Duplicate Scoring Algorithm

To distinguish between exact client replays, legitimate duplicate reports of the same real-world issue by different citizens, and distinct civic issues at the same intersection, a multi-factor composite scoring model was implemented in `backend/ai/duplicate_detector.py`:

$$\text{Composite Duplicate Score} = w_{\text{geo}} S_{\text{geo}} + w_{\text{img}} S_{\text{img}} + w_{\text{cat}} S_{\text{cat}} + w_{\text{desc}} S_{\text{desc}} + w_{\text{time}} S_{\text{time}}$$

### Factor Weights & Scoring Rules

| Factor | Weight ($w_i$) | Metric / Calculation | Scoring Function |
| :--- | :---: | :--- | :--- |
| **GPS Distance** | 25% | Haversine formula ($d$ in meters) | $S_{\text{geo}} = 1.0 - \frac{d}{R_{\max}}$ (for $d \le R_{\max} = 500\text{m}$) |
| **Visual Similarity** | 30% | 64-bit Difference Hash (dHash) & SHA-256 | SHA-256 exact match: 1.0<br>dHash Hamming similarity normalized above chance baseline ($0.65$): $\frac{\text{sim} - 0.65}{0.35} \times 0.30$ |
| **Civic Category** | 20% | Strict & Partial Category Matching | Exact match: 0.20<br>Substring match: 0.10<br>Disjoint: 0.00 |
| **Description** | 15% | Word-level Jaccard Similarity | Tokenized text intersection over union $\times 0.15$ |
| **Time Proximity** | 10% | Difference in hours ($\Delta t$) | $\le 24\text{h}$: 0.10<br>$\le 72\text{h}$: 0.06<br>$\le 168\text{h}$ (7 days): 0.03 |

---

## 3. Classification Tiers & Decision Rules

Candidate issues within 500 meters are scored and classified into four distinct tiers:

1. **`EXACT_REPLAY` (Score: 100.0%):**
   - Triggered by identical SHA-256 file hash, OR
   - Category match with $\ge 90.0\%$ composite score, OR
   - Perceptual image match ($\ge 95\%$) within 30 meters and 4 hours.
2. **`HIGH_CONFIDENCE_DUPLICATE` (Score: 70.0% – 89.9%):**
   - Matching category or strong visual similarity ($\ge 85\%$) with composite score $\ge 70\%$.
3. **`POSSIBLE_DUPLICATE` (Score: 40.0% – 69.9%):**
   - Matching category or visual similarity ($\ge 70\%$) with composite score $\ge 40\%$.
4. **`UNIQUE_REPORT` (Score: < 40.0%):**
   - Different civic issues (e.g., broken streetlight vs pothole) at the same location. Without category or image match, maximum proximity and time score cannot exceed 35%.

---

## 4. Exact API Replay Protection in `POST /issues/`

In `backend/routes/issues.py`, an idempotency check intercepts exact API replays before creating database records:

1. Computes the SHA-256 hash of the uploaded image bytes.
2. Checks submissions by the same user within the last 15 minutes.
3. If the image SHA-256 matches an existing submission AND category/title align:
   - Returns the existing issue record with `is_replay: true`.
   - Awards **0 credits** (`credits_earned: 0`), preventing credit duplication.
   - Bypasses duplicate database creation.

---

## 5. Authority Governance & Audit Logging

In alignment with human-in-the-loop policies:
- Duplicate warnings are purely advisory in the UI.
- Genuine reports by different citizens are **never auto-rejected**.
- Authority officers have dedicated controls:
  - **LINK DUPLICATE:** Associates the duplicate report to the primary issue for unified tracking without closing it.
  - **MERGE DUPLICATE:** Available only to `DEPARTMENT_OFFICER` and `SUPER_ADMIN`. Transitions duplicate issue status to `Resolved`, sets `resolution_notes`, and logs an immutable `AuditLog` entry.


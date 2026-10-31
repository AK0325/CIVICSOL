"""
CIVICSOL - Multi-Factor Duplicate and Proximity Detection Engine
Identifies potentially related or duplicate civic reports based on 5 weighted signals:
1. Geographic proximity (Haversine distance in meters, 25% weight)
2. Image perceptual similarity (dHash 64-bit + SHA-256 exact match, 30% weight)
3. Category similarity (Exact vs partial civic domain, 20% weight)
4. Citizen description token similarity (Jaccard index, 15% weight)
5. Temporal proximity (Submission timestamp delta, 10% weight)

Classifications:
- UNIQUE_REPORT (< 40% duplicate score)
- POSSIBLE_DUPLICATE (40% - 69% duplicate score)
- HIGH_CONFIDENCE_DUPLICATE (70% - 89% duplicate score)
- EXACT_REPLAY (>= 90% duplicate score or identical SHA-256 image replay)

Safety Policy:
- Never merges or deletes reports automatically without authorized officer action.
- Surfaces candidate similar reports and clear evidence breakdown to municipal authorities.
"""

import hashlib
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from PIL import Image
from sqlalchemy.orm import Session

from backend.models import CivicIssue


BASE_DIR = Path(__file__).resolve().parents[2]
EARTH_RADIUS_METERS = 6371000.0

STOPWORDS: Set[str] = {
    "the", "and", "for", "with", "near", "from", "this", "that", "there",
    "is", "are", "was", "were", "has", "have", "been", "very", "here",
    "in", "on", "at", "to", "of", "by", "an", "a",
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance in meters between two GPS coordinates."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_METERS * c


def _tokenize(text: Optional[str]) -> Set[str]:
    if not text:
        return set()
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def text_jaccard_similarity(text_a: Optional[str], text_b: Optional[str]) -> float:
    """Compute Jaccard similarity [0.0 .. 1.0] between two text descriptions."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return round(intersection / union, 3) if union > 0 else 0.0


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_image_sha256(image_path: Union[str, Path, None]) -> Optional[str]:
    """Computes SHA-256 digest of image file for fast exact duplicate replay detection."""
    if not image_path:
        return None
    p = Path(image_path)
    if not p.is_absolute():
        p = BASE_DIR / str(image_path).lstrip("/")
    if not p.exists() or not p.is_file():
        return None
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def compute_image_dhash(image_path: Union[str, Path, None], hash_size: int = 8) -> Optional[str]:
    """
    Computes a 64-bit difference hash (dHash) for an image.
    Fast, robust against slight compression, resizing, and brightness variations.
    """
    if not image_path:
        return None
    p = Path(image_path)
    if not p.is_absolute():
        p = BASE_DIR / str(image_path).lstrip("/")
    if not p.exists() or not p.is_file():
        return None
    try:
        with Image.open(p) as img:
            # Convert to grayscale and resize to (hash_size + 1, hash_size)
            resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(resized.get_flattened_data()) if hasattr(resized, "get_flattened_data") else list(resized.getdata())
            
            # Compare adjacent pixels
            diff = []
            for row in range(hash_size):
                row_start = row * (hash_size + 1)
                for col in range(hash_size):
                    left_px = pixels[row_start + col]
                    right_px = pixels[row_start + col + 1]
                    diff.append("1" if left_px > right_px else "0")
            
            # Convert bitstring to hex string (16 characters for 64 bits)
            bitstring = "".join(diff)
            hex_hash = f"{int(bitstring, 2):016x}"
            return hex_hash
    except Exception:
        return None


def image_perceptual_similarity(hash_a: Optional[str], hash_b: Optional[str]) -> float:
    """
    Calculates similarity [0.0 .. 1.0] from Hamming distance of two 64-bit dHash strings.
    1.0 = identical perceptual structure, 0.0 = completely distinct.
    """
    if not hash_a or not hash_b or len(hash_a) != 16 or len(hash_b) != 16:
        return 0.0
    try:
        int_a = int(hash_a, 16)
        int_b = int(hash_b, 16)
        xor_diff = int_a ^ int_b
        hamming_dist = bin(xor_diff).count("1")
        # 64 bits total. Hamming distance <= 10 is usually the same or very similar image
        similarity = max(0.0, 1.0 - (hamming_dist / 64.0))
        return round(similarity, 3)
    except Exception:
        return 0.0


def find_similar_nearby_issues(
    db: Session,
    issue_id: int,
    latitude: float,
    longitude: float,
    category: Optional[str],
    title: Optional[str] = None,
    description: Optional[str] = None,
    image_path: Optional[str] = None,
    created_at: Optional[datetime] = None,
    max_radius_meters: float = 500.0,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Finds nearby and potentially duplicate issues using 5-factor weighted scoring:
    - GPS distance: 25%
    - Image similarity (dHash / SHA-256): 30%
    - Category match: 20%
    - Description text similarity: 15%
    - Temporal proximity: 10%
    """
    lat_delta = (max_radius_meters / 111320.0) * 1.5
    cos_lat = max(0.1, abs(math.cos(math.radians(latitude))))
    lon_delta = (max_radius_meters / (111320.0 * cos_lat)) * 1.5

    candidates = (
        db.query(CivicIssue)
        .filter(
            CivicIssue.id != issue_id,
            CivicIssue.latitude >= latitude - lat_delta,
            CivicIssue.latitude <= latitude + lat_delta,
            CivicIssue.longitude >= longitude - lon_delta,
            CivicIssue.longitude <= longitude + lon_delta,
        )
        .all()
    )

    target_text = f"{title or ''} {description or ''}".strip()
    target_cat = (category or "").strip().lower()
    target_time = _to_utc(created_at) or datetime.now(timezone.utc)
    
    # Precompute target image hashes
    target_sha256 = compute_image_sha256(image_path)
    target_dhash = compute_image_dhash(image_path)

    similar_list: List[Dict[str, Any]] = []

    for cand in candidates:
        dist_m = haversine_distance_meters(latitude, longitude, cand.latitude, cand.longitude)
        if dist_m > max_radius_meters:
            continue

        # 1. GPS proximity score (0.0 .. 0.25) - 25% weight
        geo_norm = max(0.0, 1.0 - (dist_m / max_radius_meters))
        geo_score = geo_norm * 0.25

        # 2. Image similarity score (0.0 .. 0.30) - 30% weight
        cand_sha256 = compute_image_sha256(cand.image_path)
        cand_dhash = compute_image_dhash(cand.image_path)
        exact_sha_match = bool(target_sha256 and cand_sha256 and target_sha256 == cand_sha256)
        
        if exact_sha_match:
            img_sim = 1.0
            img_score = 0.30
        elif target_dhash and cand_dhash:
            img_sim = image_perceptual_similarity(target_dhash, cand_dhash)
            # Binary dHash Hamming similarity for independent random images has expected value of 0.50 (chance).
            # Only genuine perceptual correlation (similarity >= 0.65) contributes to duplicate score.
            if img_sim >= 0.65:
                normalized_sim = (img_sim - 0.65) / 0.35
                img_score = normalized_sim * 0.30
            else:
                img_score = 0.0
        else:
            img_sim = 0.0
            img_score = 0.0

        # 3. Category match score (0.0 .. 0.20) - 20% weight
        cand_cat = (cand.category or "").strip().lower()
        if target_cat and cand_cat:
            if target_cat == cand_cat:
                cat_match = True
                cat_score = 0.20
            elif target_cat in cand_cat or cand_cat in target_cat:
                cat_match = True
                cat_score = 0.10
            else:
                cat_match = False
                cat_score = 0.0
        else:
            cat_match = False
            cat_score = 0.0

        # 4. Description similarity score (0.0 .. 0.15) - 15% weight
        cand_text = f"{cand.title or ''} {cand.description or ''}".strip()
        desc_sim = text_jaccard_similarity(target_text, cand_text)
        desc_score = desc_sim * 0.15

        # 5. Temporal proximity score (0.0 .. 0.10) - 10% weight
        cand_time = _to_utc(cand.created_at)
        time_diff_hours: Optional[float] = None
        time_score = 0.0
        if cand_time:
            time_diff_hours = round(abs((target_time - cand_time).total_seconds()) / 3600.0, 1)
            if time_diff_hours <= 24:
                time_score = 0.10
            elif time_diff_hours <= 72:
                time_score = 0.06
            elif time_diff_hours <= 168:
                time_score = 0.03

        composite_score = round(min(1.0, geo_score + img_score + cat_score + desc_score + time_score) * 100.0, 1)

        # Classification decision rules
        if exact_sha_match:
            classification = "EXACT_REPLAY"
        elif cat_match and (composite_score >= 90.0 or (img_sim >= 0.95 and dist_m <= 30.0 and (time_diff_hours is not None and time_diff_hours <= 4.0))):
            classification = "EXACT_REPLAY"
        elif composite_score >= 70.0 and (cat_match or img_sim >= 0.85):
            classification = "HIGH_CONFIDENCE_DUPLICATE"
        elif composite_score >= 40.0 and (cat_match or img_sim >= 0.70):
            classification = "POSSIBLE_DUPLICATE"
        else:
            classification = "UNIQUE_REPORT"

        reasons: List[str] = [f"{round(dist_m, 1)}m away"]
        if exact_sha_match:
            reasons.append("identical image file (SHA-256 match)")
        elif img_sim >= 0.80:
            reasons.append(f"{round(img_sim * 100)}% image visual similarity")
        if cat_match:
            reasons.append("matching category")
        if desc_sim >= 0.25:
            reasons.append(f"{round(desc_sim * 100)}% text description overlap")
        if time_diff_hours is not None and time_diff_hours <= 48:
            reasons.append(f"reported within {time_diff_hours}h")

        similar_list.append({
            "issue_id": cand.id,
            "title": cand.title,
            "category": cand.category,
            "status": cand.status,
            "severity": cand.severity,
            "priority": cand.priority,
            "location": cand.location,
            "latitude": cand.latitude,
            "longitude": cand.longitude,
            "distance_meters": round(dist_m, 1),
            "image_similarity": round(img_sim, 3),
            "image_similarity_percent": round(img_sim * 100.0, 1),
            "description_similarity": desc_sim,
            "description_similarity_percent": round(desc_sim * 100.0, 1),
            "category_match": cat_match,
            "time_difference_hours": time_diff_hours,
            "similarity_score": round(composite_score / 100.0, 3),
            "similarity_percent": composite_score,
            "duplicate_score": composite_score,
            "classification": classification,
            "match_reasons": reasons,
            "created_at": cand.created_at.isoformat() if cand.created_at else None,
        })

    similar_list.sort(key=lambda item: (item["duplicate_score"], -item["distance_meters"]), reverse=True)
    return similar_list[:limit]


def detect_similar_nearby_issues(
    db: Session,
    issue_id: int,
    latitude: float,
    longitude: float,
    category: Optional[str] = None,
    predicted_category: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    image_path: Optional[str] = None,
    created_at: Optional[datetime] = None,
    max_radius_meters: float = 500.0,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Finds and formats candidate similar nearby reports for authority review.
    Computes overall duplicate classification and highest duplicate score.
    Does not merge or delete reports automatically.
    """
    effective_cat = predicted_category or category
    sim_list = find_similar_nearby_issues(
        db=db,
        issue_id=issue_id,
        latitude=latitude,
        longitude=longitude,
        category=effective_cat,
        title=title,
        description=description,
        image_path=image_path,
        created_at=created_at,
        max_radius_meters=max_radius_meters,
        limit=limit,
    )

    if not sim_list:
        overall_classification = "UNIQUE_REPORT"
        highest_score = 0.0
        primary_id = None
    else:
        top_cand = sim_list[0]
        highest_score = top_cand["duplicate_score"]
        primary_id = top_cand["issue_id"]
        # Determine overall classification from highest tier present
        if any(c["classification"] == "EXACT_REPLAY" for c in sim_list):
            overall_classification = "EXACT_REPLAY"
        elif any(c["classification"] == "HIGH_CONFIDENCE_DUPLICATE" for c in sim_list):
            overall_classification = "HIGH_CONFIDENCE_DUPLICATE"
        elif any(c["classification"] == "POSSIBLE_DUPLICATE" for c in sim_list):
            overall_classification = "POSSIBLE_DUPLICATE"
        else:
            overall_classification = "UNIQUE_REPORT"

    return {
        "overall_classification": overall_classification,
        "highest_duplicate_score": highest_score,
        "primary_duplicate_id": primary_id,
        "duplicate_count": len(sim_list),
        "similar_issues": sim_list,
    }

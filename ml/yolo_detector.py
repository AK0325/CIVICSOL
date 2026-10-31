"""
CIVICSOL - YOLO Object Detection & Image Annotation Engine
Provides a clean model-integration interface for detecting civic hazards:
1. pothole -> Road Damage / Potholes
2. garbage -> Garbage
3. water_leakage -> Water Leakage
4. broken_streetlight -> Street Light
5. damaged_infrastructure -> Public Infrastructure
6. drainage_problem -> Drainage

Safety & Integrity Guarantees:
- Validates image inputs with Pillow before processing.
- Resizes and preprocesses images appropriately (640x640 target).
- Reuses trained YOLO weights if present; never claims an untrained model detects all issues.
- Never invents confidence scores or fabricates bounding boxes.
- Stores annotated images separately in uploads/annotated/ without modifying original uploads.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from PIL import Image, ImageDraw, ImageOps


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS_PATH = BASE_DIR / "ml" / "training" / "weights" / "best.pt"
FALLBACK_WEIGHTS_PATH = BASE_DIR / "ml" / "weights" / "civic_yolov8.pt"
UPLOAD_DIR = BASE_DIR / "uploads"
ANNOTATED_DIR = UPLOAD_DIR / "annotated"

SUPPORTED_CLASSES: Dict[int, Dict[str, str]] = {
    0: {"label": "pothole", "category": "Road Damage", "display": "Pothole", "color": "#f97316"},
    1: {"label": "garbage", "category": "Garbage", "display": "Garbage Accumulation", "color": "#a855f7"},
    2: {"label": "water_leakage", "category": "Water Leakage", "display": "Water Leakage", "color": "#0ea5e9"},
    3: {"label": "broken_streetlight", "category": "Street Light", "display": "Broken Streetlight", "color": "#eab308"},
    4: {"label": "damaged_road", "category": "Road Damage", "display": "Damaged Road", "color": "#f59e0b"},
    5: {"label": "drainage_issue", "category": "Drainage", "display": "Drainage Issue", "color": "#ef4444"},
    6: {"label": "fallen_tree", "category": "Tree / Greenery", "display": "Fallen Tree", "color": "#22c55e"},
    7: {"label": "damaged_infrastructure", "category": "Public Infrastructure", "display": "Damaged Infrastructure", "color": "#ec4899"},
}

LABEL_TO_CATEGORY: Dict[str, str] = {
    info["label"]: info["category"] for info in SUPPORTED_CLASSES.values()
}

LABEL_TO_COLOR: Dict[str, str] = {
    info["label"]: info["color"] for info in SUPPORTED_CLASSES.values()
}


class ImageValidationError(ValueError):
    """Raised when an uploaded image fails validation or integrity checks."""
    pass


class PreprocessResult(dict):
    """
    Subclass of dict supporting both dict lookup (res['valid'], res['error'])
    and tuple unpacking: (rgb_img, img_meta) = validate_and_preprocess_image(...)
    """

    def __iter__(self):
        yield self.get("image")
        yield self.get("metadata")


def validate_and_preprocess_image(
    image_path: Path | str,
    target_size: Tuple[int, int] = (640, 640),
) -> PreprocessResult:
    """
    Validates image existence, readability, format, and dimensions.
    Returns a PreprocessResult holding validation status, PIL Image, and metadata.
    Supports tuple unpacking: rgb_img, img_meta = validate_and_preprocess_image(...)
    """
    p = Path(image_path) if isinstance(image_path, str) else image_path
    if not p or not p.exists() or not p.is_file():
        return PreprocessResult({
            "valid": False,
            "error": f"Image file not found: {p}",
            "image": None,
            "metadata": None,
        })

    if p.stat().st_size == 0:
        return PreprocessResult({
            "valid": False,
            "error": "Image file is empty (0 bytes).",
            "image": None,
            "metadata": None,
        })

    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    if p.suffix.lower() not in allowed_exts:
        return PreprocessResult({
            "valid": False,
            "error": f"Unsupported image format '{p.suffix}'. Allowed: JPEG, PNG, WEBP.",
            "image": None,
            "metadata": None,
        })

    try:
        with Image.open(p) as img:
            img.verify()
            img_format = (img.format or "").upper()
    except Exception as exc:
        return PreprocessResult({
            "valid": False,
            "error": f"Corrupt or unreadable image file: {exc}",
            "image": None,
            "metadata": None,
        })

    allowed_formats = {"JPEG", "PNG", "WEBP", "JPG"}
    if img_format not in allowed_formats:
        return PreprocessResult({
            "valid": False,
            "error": f"Unsupported image format '{img_format}'. Allowed: JPEG, PNG, WEBP.",
            "image": None,
            "metadata": None,
        })

    try:
        raw_img = Image.open(p)
        raw_img = ImageOps.exif_transpose(raw_img)
        rgb_img = raw_img.convert("RGB")
    except Exception as exc:
        return PreprocessResult({
            "valid": False,
            "error": f"Failed to decode image pixels: {exc}",
            "image": None,
            "metadata": None,
        })

    orig_w, orig_h = rgb_img.size
    if orig_w < 16 or orig_h < 16:
        return PreprocessResult({
            "valid": False,
            "error": f"Image resolution too small ({orig_w}x{orig_h}). Minimum 16x16 required.",
            "image": None,
            "metadata": None,
        })

    # Create letterboxed / resized copy for model inference
    resized_img = rgb_img.copy()
    resized_img.thumbnail(target_size, Image.Resampling.LANCZOS)

    meta = {
        "original_width": orig_w,
        "original_height": orig_h,
        "preprocessed_width": resized_img.size[0],
        "preprocessed_height": resized_img.size[1],
        "format": img_format,
        "file_size_bytes": p.stat().st_size,
    }
    return PreprocessResult({
        "valid": True,
        "error": None,
        "image": rgb_img,
        "metadata": meta,
    })


def render_annotated_image(
    original_img: Image.Image,
    detections: List[Dict[str, Any]],
    output_dir: Optional[Path] = None,
) -> Optional[str]:
    """
    Draws bounding boxes and confidence labels on a copy of the original image
    and saves it to uploads/annotated/ without modifying the original upload.
    Returns the relative path (e.g. 'uploads/annotated/xxx_annotated.jpg').
    """
    if not detections:
        return None

    target_dir = output_dir or ANNOTATED_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    annotated = original_img.copy()
    draw = ImageDraw.Draw(annotated)
    width, height = annotated.size

    for det in detections:
        bbox = det.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = bbox
        # If normalized coordinates [0..1], scale to image dimensions
        if all(0.0 <= float(c) <= 1.0 for c in (x1, y1, x2, y2)) and (x2 <= 1.0 and y2 <= 1.0):
            x1, x2 = int(float(x1) * width), int(float(x2) * width)
            y1, y2 = int(float(y1) * height), int(float(y2) * height)
        else:
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        x1 = max(0, min(width - 1, x1))
        x2 = max(x1 + 1, min(width, x2))
        y1 = max(0, min(height - 1, y1))
        y2 = max(y1 + 1, min(height, y2))

        label = str(det.get("label") or det.get("class_name") or "object")
        conf = det.get("confidence")
        color = LABEL_TO_COLOR.get(label, "#38bdf8")

        # Draw bounding box rectangle
        line_w = max(2, min(width, height) // 180)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=line_w)

        # Draw label banner
        conf_str = f" {round(float(conf) * 100)}%" if isinstance(conf, (int, float)) else ""
        caption = f"{label.replace('_', ' ').upper()}{conf_str}"
        text_w = max(80, len(caption) * 7)
        text_h = 18
        banner_y1 = max(0, y1 - text_h)
        draw.rectangle([x1, banner_y1, min(width, x1 + text_w), banner_y1 + text_h], fill=color)
        draw.text((x1 + 4, banner_y1 + 2), caption, fill="#ffffff")

    filename = f"{uuid4().hex}_annotated.jpg"
    out_path = target_dir / filename
    annotated.save(out_path, format="JPEG", quality=90)

    return f"uploads/annotated/{filename}"


class CivicYOLODetector:
    """
    YOLO Object Detection wrapper for CIVICSOL.
    Loads custom trained weights if present; otherwise reports explicit model availability status.
    """

    def __init__(
        self,
        weights_path: Optional[Path] = None,
        model_path: Optional[Union[str, Path]] = None,
    ):
        chosen_path = model_path or weights_path
        env_path = os.getenv("YOLO_MODEL_PATH")
        if env_path:
            self.weights_path = Path(env_path)
        elif chosen_path:
            self.weights_path = Path(chosen_path)
        elif DEFAULT_WEIGHTS_PATH.exists():
            self.weights_path = DEFAULT_WEIGHTS_PATH
        else:
            self.weights_path = FALLBACK_WEIGHTS_PATH

        self.model = None
        self.model_name = "CivicYOLO-v8"
        self.model_version = "1.0.0"
        self.is_available = False
        self.unavailable_reason: Optional[str] = None
        self._load_model()

    def _load_model(self) -> None:
        if not self.weights_path.exists():
            self.is_available = False
            self.unavailable_reason = (
                f"Trained civic YOLO weights not found at '{self.weights_path.name}'. "
                "Operating in interface mode (see ml/dataset_spec.md)."
            )
            return

        try:
            from ultralytics import YOLO  # type: ignore
            self.model = YOLO(str(self.weights_path))
            self.is_available = True
            self.unavailable_reason = None
        except ImportError:
            self.is_available = False
            self.unavailable_reason = "Package 'ultralytics' is not installed in the current runtime."
        except Exception as exc:
            self.is_available = False
            self.unavailable_reason = f"Failed to load YOLO weights: {exc}"

    def detect(
        self,
        image_path: Union[Path, str],
        conf_threshold: Optional[float] = None,
        iou_threshold: float = 0.45,
        agnostic_nms: bool = True,
    ) -> Dict[str, Any]:
        """
        Validates image, runs YOLO object detection with class-agnostic NMS to suppress
        conflicting overlapping detections, and flags low-confidence predictions.
        Never fabricates detections or confidence scores.
        """
        start_time = time.perf_counter()
        if conf_threshold is None:
            conf_threshold = float(os.getenv("YOLO_CONF_THRESHOLD", "0.35"))
        timestamp = datetime.now(timezone.utc).isoformat()
        prep_res = validate_and_preprocess_image(image_path)

        if not prep_res.get("valid", True):
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "INVALID_IMAGE",
                "processing_status": "INVALID_IMAGE",
                "model_name": self.model_name,
                "model_version": self.model_version,
                "model_available": self.is_available,
                "unavailable_reason": prep_res.get("error"),
                "detected_objects": [],
                "detected_classes": [],
                "bounding_boxes": [],
                "confidence_scores": [],
                "predicted_category": None,
                "confidence_score": None,
                "annotated_image_path": None,
                "image_metadata": None,
                "is_low_confidence": False,
                "low_confidence_warning": None,
                "processing_time_ms": duration_ms,
                "inference_duration_ms": duration_ms,
                "reason": prep_res.get("error"),
                "analysis_timestamp": timestamp,
            }

        rgb_img = prep_res["image"]
        img_meta = prep_res["metadata"]

        if not self.is_available or self.model is None:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "MODEL_UNAVAILABLE",
                "processing_status": "MODEL_UNAVAILABLE",
                "model_name": self.model_name,
                "model_version": f"{self.model_version}-interface",
                "model_available": False,
                "unavailable_reason": self.unavailable_reason,
                "detected_objects": [],
                "detected_classes": [],
                "bounding_boxes": [],
                "confidence_scores": [],
                "predicted_category": None,
                "confidence_score": None,
                "annotated_image_path": None,
                "image_metadata": img_meta,
                "is_low_confidence": False,
                "low_confidence_warning": None,
                "processing_time_ms": duration_ms,
                "inference_duration_ms": duration_ms,
                "supported_classes": [v["label"] for v in SUPPORTED_CLASSES.values()],
                "analysis_timestamp": timestamp,
            }

        # Run actual YOLO inference with class-agnostic NMS to suppress overlapping false positives
        try:
            results = self.model.predict(
                source=rgb_img,
                conf=conf_threshold,
                iou=iou_threshold,
                agnostic_nms=agnostic_nms,
                verbose=False,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            detections: List[Dict[str, Any]] = []

            for r in results:
                boxes = getattr(r, "boxes", None)
                if boxes is None:
                    continue
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = round(float(box.conf[0].item()), 4)
                    xyxy = [round(float(x), 1) for x in box.xyxy[0].tolist()]
                    cls_info = SUPPORTED_CLASSES.get(
                        cls_id,
                        {"label": f"class_{cls_id}", "category": "Public Infrastructure", "display": f"Object {cls_id}"},
                    )
                    detections.append({
                        "class_id": cls_id,
                        "class_name": cls_info["label"],
                        "label": cls_info["label"],
                        "display_name": cls_info["display"],
                        "category": cls_info["category"],
                        "confidence": conf,
                        "bbox": xyxy,
                        "box": xyxy,
                        "is_low_confidence": (conf < 0.45),
                    })

            detections.sort(key=lambda d: d["confidence"], reverse=True)

            if not detections:
                return {
                    "status": "NO_DETECTION",
                    "processing_status": "NO_DETECTION",
                    "model_name": self.model_name,
                    "model_version": self.model_version,
                    "model_available": True,
                    "unavailable_reason": None,
                    "detected_objects": [],
                    "detected_classes": [],
                    "bounding_boxes": [],
                    "confidence_scores": [],
                    "predicted_category": None,
                    "confidence_score": None,
                    "annotated_image_path": None,
                    "image_metadata": img_meta,
                    "is_low_confidence": False,
                    "low_confidence_warning": None,
                    "processing_time_ms": duration_ms,
                    "inference_duration_ms": duration_ms,
                    "supported_classes": [v["label"] for v in SUPPORTED_CLASSES.values()],
                    "analysis_timestamp": timestamp,
                }

            top_det = detections[0]
            annotated_rel_path = render_annotated_image(rgb_img, detections)
            is_low_conf = top_det["confidence"] < 0.45
            status_val = "LOW_CONFIDENCE" if is_low_conf else "DETECTED"
            proc_status_val = "LOW_CONFIDENCE" if is_low_conf else "DETECTIONS_FOUND"
            warning_msg = (
                f"Top detection '{top_det['label']}' has confidence {round(top_det['confidence'] * 100, 1)}% (< 45%). "
                "Authority verification recommended."
                if is_low_conf
                else None
            )

            det_classes = list(dict.fromkeys(d["class_name"] for d in detections))
            bboxes = [d["bbox"] for d in detections]
            confs = [d["confidence"] for d in detections]

            return {
                "status": status_val,
                "processing_status": proc_status_val,
                "model_name": self.model_name,
                "model_version": self.model_version,
                "model_available": True,
                "unavailable_reason": None,
                "detected_objects": detections,
                "detected_classes": det_classes,
                "bounding_boxes": bboxes,
                "confidence_scores": confs,
                "predicted_category": top_det["category"],
                "confidence_score": top_det["confidence"],
                "annotated_image_path": annotated_rel_path,
                "image_metadata": img_meta,
                "is_low_confidence": is_low_conf,
                "low_confidence_warning": warning_msg,
                "processing_time_ms": duration_ms,
                "inference_duration_ms": duration_ms,
                "supported_classes": [v["label"] for v in SUPPORTED_CLASSES.values()],
                "analysis_timestamp": timestamp,
            }

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "FAILED",
                "processing_status": "PROCESSING_FAILED",
                "model_name": self.model_name,
                "model_version": self.model_version,
                "model_available": self.is_available,
                "unavailable_reason": f"YOLO inference error: {exc}",
                "detected_objects": [],
                "detected_classes": [],
                "bounding_boxes": [],
                "confidence_scores": [],
                "predicted_category": None,
                "confidence_score": None,
                "annotated_image_path": None,
                "image_metadata": img_meta,
                "is_low_confidence": False,
                "low_confidence_warning": None,
                "processing_time_ms": duration_ms,
                "inference_duration_ms": duration_ms,
                "supported_classes": [v["label"] for v in SUPPORTED_CLASSES.values()],
                "analysis_timestamp": timestamp,
            }

    def analyze_image(self, image_path: Union[Path, str]) -> Dict[str, Any]:
        """Alias for detect() that accepts both string and Path arguments."""
        return self.detect(image_path)


# Singleton detector instance
yolo_detector = CivicYOLODetector()


"""
CIVICSOL - Production Performance & Latency Benchmarking Suite
Measures actual throughput and latencies across:
1. Image validation & preprocessing
2. YOLOv8 Nano object detection inference on CPU
3. Gemini description analysis (API vs deterministic civic heuristic fallback)
4. PostgreSQL query performance (indexed issue listing, GIS map coordinate queries, workload aggregation)
5. Statistical latency percentiles (min, mean, median, p95, max)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

RESULTS_DIR = Path("ml/test_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
BENCHMARK_REPORT = RESULTS_DIR / "performance_benchmark_report.json"


def calc_stats(latencies_ms: List[float]) -> Dict[str, float]:
    if not latencies_ms:
        return {}
    sorted_l = sorted(latencies_ms)
    n = len(sorted_l)
    p95_idx = int(n * 0.95)
    return {
        "iterations": n,
        "min_ms": round(min(sorted_l), 2),
        "mean_ms": round(sum(sorted_l) / n, 2),
        "median_ms": round(sorted_l[n // 2], 2),
        "p95_ms": round(sorted_l[min(p95_idx, n - 1)], 2),
        "max_ms": round(max(sorted_l), 2),
    }


def run_performance_benchmarks() -> Dict[str, Any]:
    print("=" * 60)
    print("CIVICSOL Production Performance Benchmark Suite")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmarks": {},
        "target_thresholds": {
            "image_preprocessing_mean_ms": 50.0,
            "yolo_cpu_inference_mean_ms": 300.0,
            "heuristic_fallback_mean_ms": 10.0,
            "db_query_indexed_mean_ms": 25.0,
        },
    }

    # -------------------------------------------------------------
    # 1. Image Preprocessing Benchmark
    # -------------------------------------------------------------
    print("\n[1/5] Benchmarking Image Preprocessing...")
    from ml.yolo_detector import validate_and_preprocess_image

    sample_img_path = Path("ml/dataset/images/test/garbage_1.jpg")
    if not sample_img_path.exists():
        sample_img_path = Path("uploads/249202c73b7948aa947077b971e857b2.jpg")

    prep_latencies = []
    for _ in range(20):
        t0 = time.perf_counter()
        res = validate_and_preprocess_image(sample_img_path)
        dt = (time.perf_counter() - t0) * 1000.0
        assert res.get("valid") is True, f"Image preprocessing failed: {res.get('error')}"
        prep_latencies.append(dt)

    prep_stats = calc_stats(prep_latencies)
    print(f"  Iterations: {prep_stats['iterations']} | Mean: {prep_stats['mean_ms']}ms | p95: {prep_stats['p95_ms']}ms | Min: {prep_stats['min_ms']}ms | Max: {prep_stats['max_ms']}ms")
    report["benchmarks"]["image_preprocessing"] = prep_stats

    # -------------------------------------------------------------
    # 2. YOLOv8 CPU Inference Benchmark
    # -------------------------------------------------------------
    print("\n[2/5] Benchmarking YOLOv8 Inference on CPU...")
    from ml.yolo_detector import CivicYOLODetector

    detector = CivicYOLODetector()
    assert detector.is_available is True, f"YOLO model not available: {detector.unavailable_reason}"

    # Warmup
    detector.analyze_image(sample_img_path)

    yolo_latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        det_res = detector.analyze_image(sample_img_path)
        dt = (time.perf_counter() - t0) * 1000.0
        assert det_res["status"] in ("DETECTED", "NO_DETECTION"), f"Unexpected inference status: {det_res['status']}"
        yolo_latencies.append(dt)

    yolo_stats = calc_stats(yolo_latencies)
    print(f"  Iterations: {yolo_stats['iterations']} | Mean: {yolo_stats['mean_ms']}ms | p95: {yolo_stats['p95_ms']}ms | Min: {yolo_stats['min_ms']}ms | Max: {yolo_stats['max_ms']}ms")
    report["benchmarks"]["yolo_inference_cpu"] = yolo_stats

    # -------------------------------------------------------------
    # 3. Gemini Heuristic Fallback & Description Analysis Benchmark
    # -------------------------------------------------------------
    print("\n[3/5] Benchmarking Description Analysis Fallback...")
    from backend.ai.gemini_service import _heuristic_description_analysis

    llm_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        fb_res = _heuristic_description_analysis(
            title="Dangerous crater pothole on Hospital cross",
            description="Deep crater damaging vehicles and causing traffic gridlock.",
            selected_category="Road Damage",
            location="Civil Hospital Junction",
            vision_category="Road Damage",
            vision_detections=[{"label": "pothole", "confidence": 0.85}],
        )
        dt = (time.perf_counter() - t0) * 1000.0
        assert fb_res["recommended_category"] == "Road Damage"
        llm_latencies.append(dt)

    llm_stats = calc_stats(llm_latencies)
    print(f"  Iterations: {llm_stats['iterations']} | Mean: {llm_stats['mean_ms']}ms | p95: {llm_stats['p95_ms']}ms | Min: {llm_stats['min_ms']}ms | Max: {llm_stats['max_ms']}ms")
    report["benchmarks"]["heuristic_description_analysis"] = llm_stats

    # -------------------------------------------------------------
    # 4. PostgreSQL Query Performance Benchmark
    # -------------------------------------------------------------
    print("\n[4/5] Benchmarking PostgreSQL Database Queries...")
    from sqlalchemy import text
    from backend.database import SessionLocal
    from backend.models import CivicIssue, AIAnalysis, Department, User

    db = SessionLocal()
    db_benchmarks = {}

    try:
        # Connection pool & catalog warmup
        db.execute(text("SELECT 1"))
        _ = db.query(CivicIssue).limit(1).all()

        # 4a. Filtered Issue Listing (Indexed)
        query_latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            _ = (
                db.query(CivicIssue)
                .filter(CivicIssue.status.in_(["Reported", "Under Review", "Assigned", "In Progress"]))
                .order_by(CivicIssue.created_at.desc())
                .limit(20)
                .all()
            )
            dt = (time.perf_counter() - t0) * 1000.0
            query_latencies.append(dt)
        db_benchmarks["issue_listing_indexed"] = calc_stats(query_latencies)

        # 4b. GIS Map Issues Query
        map_latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            _ = db.query(CivicIssue).filter(CivicIssue.latitude.isnot(None)).all()
            dt = (time.perf_counter() - t0) * 1000.0
            map_latencies.append(dt)
        db_benchmarks["gis_map_all_coords"] = calc_stats(map_latencies)

        # 4c. AI Analysis Join & Latest Analysis Retrieval
        ai_latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            _ = (
                db.query(AIAnalysis)
                .order_by(AIAnalysis.created_at.desc())
                .limit(10)
                .all()
            )
            dt = (time.perf_counter() - t0) * 1000.0
            ai_latencies.append(dt)
        db_benchmarks["ai_analyses_recent"] = calc_stats(ai_latencies)

    finally:
        db.close()

    for k, v in db_benchmarks.items():
        print(f"  Query [{k}]: Mean: {v['mean_ms']}ms | p95: {v['p95_ms']}ms | Max: {v['max_ms']}ms")
    report["benchmarks"]["postgresql_queries"] = db_benchmarks

    # -------------------------------------------------------------
    # 5. Summary Evaluation Against Targets
    # -------------------------------------------------------------
    print("\n[5/5] Evaluating Latency SLAs Against Target Thresholds:")
    prep_ok = prep_stats["mean_ms"] <= report["target_thresholds"]["image_preprocessing_mean_ms"]
    yolo_ok = yolo_stats["mean_ms"] <= report["target_thresholds"]["yolo_cpu_inference_mean_ms"]
    llm_ok = llm_stats["mean_ms"] <= report["target_thresholds"]["heuristic_fallback_mean_ms"]
    db_ok = db_benchmarks["issue_listing_indexed"]["mean_ms"] <= report["target_thresholds"]["db_query_indexed_mean_ms"]

    all_passed = prep_ok and yolo_ok and llm_ok and db_ok

    print(f"  • Image Preprocessing Mean ({prep_stats['mean_ms']}ms <= 50ms): {'PASS' if prep_ok else 'FAIL'}")
    print(f"  • YOLO CPU Inference Mean ({yolo_stats['mean_ms']}ms <= 300ms): {'PASS' if yolo_ok else 'FAIL'}")
    print(f"  • Heuristic Fallback Mean ({llm_stats['mean_ms']}ms <= 10ms): {'PASS' if llm_ok else 'FAIL'}")
    print(f"  • DB Query Mean ({db_benchmarks['issue_listing_indexed']['mean_ms']}ms <= 25ms): {'PASS' if db_ok else 'FAIL'}")

    report["overall_status"] = "ALL_SLAS_MET" if all_passed else "SOME_SLAS_BREACHED"

    with open(BENCHMARK_REPORT, "w") as bf:
        json.dump(report, bf, indent=2)

    print(f"\nPerformance Benchmark Report saved to: {BENCHMARK_REPORT}")
    return report


if __name__ == "__main__":
    try:
        run_performance_benchmarks()
    except Exception as exc:
        print(f"FATAL: Benchmark suite failed: {exc}")
        sys.exit(1)


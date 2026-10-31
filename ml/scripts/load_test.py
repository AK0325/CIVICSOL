"""
CIVICSOL - Concurrent Load & Stress Testing Suite
Simulates concurrent citizen submissions with real image uploads and AI processing.
Measures:
1. End-to-end API response latency under concurrency (10 concurrent submissions)
2. HTTP error rates and status code distribution
3. Memory consumption (RSS delta)
4. AI processing triage outcomes
5. Bottleneck identification
"""

import concurrent.futures
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

BASE_URL = os.getenv("CIVICSOL_API_URL", "http://127.0.0.1:8000")
RESULTS_DIR = Path("ml/test_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOAD_REPORT_PATH = RESULTS_DIR / "load_test_report.json"


def get_memory_rss_mb() -> float:
    """Return max RSS in MB for current process."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # On macOS, ru_maxrss is in bytes; on Linux, in KB
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024.0 * 1024.0)
    return usage.ru_maxrss / 1024.0


def submit_single_issue(task_id: int, token: str, sample_image_bytes: bytes, timeout: float = 60.0) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    files = {"image": (f"load_test_{task_id}.jpg", sample_image_bytes, "image/jpeg")}
    data = {
        "title": f"Concurrent Load Test Civic Issue #{task_id}",
        "description": f"Automated load testing report #{task_id}: road surface hazard and debris.",
        "category": "Road Damage",
        "severity": "Medium",
        "location": f"Load Testing Zone Cross #{task_id}",
        "latitude": 23.0200 + (task_id * 0.001),
        "longitude": 72.5700 + (task_id * 0.001),
    }

    t0 = time.perf_counter()
    status_code = 0
    error_msg = None
    ai_status = None
    issue_id = None

    try:
        res = requests.post(f"{BASE_URL}/issues/", headers=headers, files=files, data=data, timeout=timeout)
        status_code = res.status_code
        dt = (time.perf_counter() - t0) * 1000.0

        if status_code == 200:
            rj = res.json()
            issue_id = rj.get("issue", {}).get("id") or rj.get("id")
            ai_status = rj.get("ai_analysis", {}).get("processing_status")
        else:
            error_msg = res.text[:200]
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        error_msg = str(exc)

    return {
        "task_id": task_id,
        "latency_ms": round(dt, 2),
        "status_code": status_code,
        "issue_id": issue_id,
        "ai_status": ai_status,
        "error": error_msg,
    }


def run_load_test(concurrency: int = 10) -> Dict[str, Any]:
    print("=" * 60)
    print(f"CIVICSOL Load & Concurrency Benchmark (Workers: {concurrency})")
    print(f"Target URL: {BASE_URL}")
    print(f"Timestamp:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Generate citizen token
    from backend.auth.security import create_access_token
    citizen_token = create_access_token({"sub": "1", "role": "CITIZEN", "citizen_id": "CIT-ANKIT"})

    # 2. Prepare sample image
    sample_img_path = Path("ml/dataset/images/test/garbage_1.jpg")
    if not sample_img_path.exists():
        sample_img_path = Path("uploads/249202c73b7948aa947077b971e857b2.jpg")
    assert sample_img_path.exists(), "Sample test image not found"
    sample_bytes = sample_img_path.read_bytes()

    mem_before = get_memory_rss_mb()
    t_start = time.perf_counter()

    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(submit_single_issue, i, citizen_token, sample_bytes)
            for i in range(1, concurrency + 1)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    total_time_s = time.perf_counter() - t_start
    mem_after = get_memory_rss_mb()

    # Aggregate statistics
    latencies = [r["latency_ms"] for r in results]
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    p95_idx = int(n * 0.95)

    success_count = sum(1 for r in results if r["status_code"] == 200)
    error_count = n - success_count
    error_rate_pct = round((error_count / n) * 100.0, 2)
    rps = round(n / total_time_s, 2)

    stats = {
        "concurrency": concurrency,
        "total_requests": n,
        "successful_requests": success_count,
        "failed_requests": error_count,
        "error_rate_percent": error_rate_pct,
        "total_duration_seconds": round(total_time_s, 2),
        "requests_per_second": rps,
        "latency_stats_ms": {
            "min_ms": min(latencies_sorted),
            "mean_ms": round(sum(latencies_sorted) / n, 2),
            "median_ms": latencies_sorted[n // 2],
            "p95_ms": latencies_sorted[min(p95_idx, n - 1)],
            "max_ms": max(latencies_sorted),
        },
        "memory_rss_mb": {
            "before_mb": round(mem_before, 2),
            "after_mb": round(mem_after, 2),
            "delta_mb": round(mem_after - mem_before, 2),
        },
        "ai_processing_distribution": {},
        "bottlenecks": [],
    }

    # Count AI statuses
    for r in results:
        st = r.get("ai_status") or "FAILED_OR_NONE"
        stats["ai_processing_distribution"][st] = stats["ai_processing_distribution"].get(st, 0) + 1

    # Identify bottlenecks
    if stats["latency_stats_ms"]["p95_ms"] > 3000.0:
        stats["bottlenecks"].append("External Gemini API or synchronous ML inference latency under burst concurrency.")
    if error_rate_pct > 0.0:
        stats["bottlenecks"].append(f"HTTP errors occurred: {error_count} requests failed.")

    print(f"\nResults Summary:")
    print(f"  • Total Requests:    {n}")
    print(f"  • Successful:        {success_count} ({100.0 - error_rate_pct}%)")
    print(f"  • Failed:            {error_count} ({error_rate_pct}%)")
    print(f"  • Duration:          {stats['total_duration_seconds']}s ({rps} req/sec)")
    print(f"  • Latency Mean:      {stats['latency_stats_ms']['mean_ms']} ms")
    print(f"  • Latency Median:    {stats['latency_stats_ms']['median_ms']} ms")
    print(f"  • Latency p95:       {stats['latency_stats_ms']['p95_ms']} ms")
    print(f"  • Latency Max:       {stats['latency_stats_ms']['max_ms']} ms")
    print(f"  • Memory RSS Delta:  +{stats['memory_rss_mb']['delta_mb']} MB")
    print(f"  • AI Outcomes:       {stats['ai_processing_distribution']}")

    with open(LOAD_REPORT_PATH, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\nLoad Test Report saved to: {LOAD_REPORT_PATH}")
    return stats


if __name__ == "__main__":
    try:
        run_load_test(concurrency=10)
    except Exception as exc:
        print(f"FATAL: Load test failed: {exc}")
        sys.exit(1)


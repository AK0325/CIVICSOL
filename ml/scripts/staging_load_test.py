"""
CIVICSOL - Multi-Tier Staging Load & Concurrency Benchmark Suite
Evaluates asynchronous API response performance and Celery queue metrics across:
- 10 concurrent citizen submissions
- 25 concurrent citizen submissions
- 50 concurrent citizen submissions

Measures:
1. Response Latency: Min, p50 (median), p95, p99, Mean, Max (ms)
2. Throughput: Requests per Second (RPS)
3. HTTP Reliability & Error Rate (%)
4. Process Memory Consumption (RSS before/after/delta)
5. CPU Time (User + System time)
6. Celery Broker Queue Depth in Redis
"""

import concurrent.futures
import json
import os
import resource
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import redis
import requests

BASE_URL = os.getenv("CIVICSOL_API_URL", "http://127.0.0.1:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
RESULTS_DIR = Path("ml/test_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = RESULTS_DIR / "staging_load_test_report.json"


def get_memory_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024.0 * 1024.0)
    return usage.ru_maxrss / 1024.0


def get_celery_queue_depth(broker_url: str = REDIS_URL) -> int:
    try:
        r = redis.from_url(broker_url, socket_timeout=2)
        # In Celery with Redis broker, default queue key is 'celery'
        return r.llen("celery")
    except Exception:
        return 0


def submit_issue(task_id: int, token: str, sample_bytes: bytes, timeout: float = 30.0) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    files = {"image": (f"load_test_tier_{task_id}.jpg", sample_bytes, "image/jpeg")}
    data = {
        "title": f"Staging Load Benchmark Issue #{task_id}",
        "description": f"Automated concurrency load benchmark #{task_id}: municipal hazard verification.",
        "category": "Road Damage",
        "severity": "Medium",
        "location": f"Staging Concurrency Cross #{task_id}",
        "latitude": 23.0200 + (task_id * 0.0005),
        "longitude": 72.5700 + (task_id * 0.0005),
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


def execute_tier(concurrency: int, token: str, sample_bytes: bytes) -> Dict[str, Any]:
    print("\n" + "-" * 60)
    print(f"RUNNING LOAD TIER: {concurrency} Concurrent Submissions")
    print("-" * 60)

    queue_depth_before = get_celery_queue_depth()
    mem_before = get_memory_rss_mb()
    t_start = time.perf_counter()
    cpu_start = time.process_time()

    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(submit_issue, i, token, sample_bytes)
            for i in range(1, concurrency + 1)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    total_time_s = time.perf_counter() - t_start
    cpu_duration = time.process_time() - cpu_start
    mem_after = get_memory_rss_mb()
    queue_depth_after = get_celery_queue_depth()

    latencies = [r["latency_ms"] for r in results]
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    p50_idx = int(n * 0.50)
    p95_idx = int(n * 0.95)
    p99_idx = int(n * 0.99)

    success_count = sum(1 for r in results if r["status_code"] == 200)
    error_count = n - success_count
    error_rate_pct = round((error_count / n) * 100.0, 2)
    rps = round(n / total_time_s, 2) if total_time_s > 0 else 0

    tier_stats = {
        "concurrency": concurrency,
        "total_requests": n,
        "successful_requests": success_count,
        "failed_requests": error_count,
        "error_rate_percent": error_rate_pct,
        "total_duration_seconds": round(total_time_s, 3),
        "requests_per_second": rps,
        "cpu_time_seconds": round(cpu_duration, 3),
        "latency_stats_ms": {
            "min_ms": min(latencies_sorted),
            "p50_median_ms": latencies_sorted[p50_idx],
            "p95_ms": latencies_sorted[min(p95_idx, n - 1)],
            "p99_ms": latencies_sorted[min(p99_idx, n - 1)],
            "mean_ms": round(sum(latencies_sorted) / n, 2),
            "max_ms": max(latencies_sorted),
        },
        "memory_rss_mb": {
            "before_mb": round(mem_before, 2),
            "after_mb": round(mem_after, 2),
            "delta_mb": round(mem_after - mem_before, 2),
        },
        "celery_queue_depth": {
            "before": queue_depth_before,
            "after": queue_depth_after,
        },
        "ai_processing_distribution": {},
    }

    for r in results:
        st = r.get("ai_status") or "NONE_OR_FAILED"
        tier_stats["ai_processing_distribution"][st] = tier_stats["ai_processing_distribution"].get(st, 0) + 1

    print(f"  • Completed Requests:   {n}/{concurrency} ({100.0 - error_rate_pct}% success)")
    print(f"  • Total Duration:       {tier_stats['total_duration_seconds']}s ({rps} req/sec)")
    print(f"  • Latency Min:          {tier_stats['latency_stats_ms']['min_ms']} ms")
    print(f"  • Latency p50 (Median): {tier_stats['latency_stats_ms']['p50_median_ms']} ms")
    print(f"  • Latency p95:          {tier_stats['latency_stats_ms']['p95_ms']} ms")
    print(f"  • Latency p99:          {tier_stats['latency_stats_ms']['p99_ms']} ms")
    print(f"  • Latency Mean:         {tier_stats['latency_stats_ms']['mean_ms']} ms")
    print(f"  • Latency Max:          {tier_stats['latency_stats_ms']['max_ms']} ms")
    print(f"  • Process RSS Delta:    +{tier_stats['memory_rss_mb']['delta_mb']} MB")
    print(f"  • CPU Time:             {tier_stats['cpu_time_seconds']}s")
    print(f"  • Celery Queue Depth:   {queue_depth_after} queued")
    print(f"  • AI Status Breakdown:  {tier_stats['ai_processing_distribution']}")

    return tier_stats


def run_full_load_benchmark(tiers: List[int] = [10, 25, 50]) -> Dict[str, Any]:
    print("=" * 60)
    print("CIVICSOL STAGING MULTI-TIER CONCURRENCY LOAD BENCHMARK")
    print(f"Target URL:    {BASE_URL}")
    print(f"Redis Broker:  {REDIS_URL}")
    print(f"Timestamp:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Generate auth token
    from backend.auth.security import create_access_token
    token = create_access_token({"sub": "1", "role": "CITIZEN", "citizen_id": "CIT-STAGING-LOAD"})

    # 2. Prepare sample image
    img_path = Path("ml/dataset/images/test/garbage_1.jpg")
    if not img_path.exists():
        img_path = Path("uploads/249202c73b7948aa947077b971e857b2.jpg")
    assert img_path.exists(), "Sample test image not found"
    sample_bytes = img_path.read_bytes()

    overall_results = {
        "timestamp": datetime.now().isoformat(),
        "target_url": BASE_URL,
        "tiers": {},
    }

    for tier in tiers:
        stats = execute_tier(tier, token, sample_bytes)
        overall_results["tiers"][f"concurrency_{tier}"] = stats
        time.sleep(1.0)  # Brief cooldown between tiers

    with open(REPORT_PATH, "w") as f:
        json.dump(overall_results, f, indent=2)

    print("\n" + "=" * 60)
    print(f"Multi-Tier Load Benchmark Complete! Saved to: {REPORT_PATH}")
    print("=" * 60)
    return overall_results


if __name__ == "__main__":
    try:
        run_full_load_benchmark([10, 25, 50])
    except Exception as exc:
        print(f"FATAL: Load benchmark failed: {exc}")
        sys.exit(1)


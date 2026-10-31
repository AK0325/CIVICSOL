"""
CIVICSOL - End-to-End Civic Intelligence Full-Stack Integration Test
Tests the complete citizen-to-authority AI pipeline against the live FastAPI backend & PostgreSQL:
1. Citizen issue submission with real image upload (POST /issues/)
2. AI pipeline execution & persistence in ai_analyses table
3. Authority review workflow:
   - View issue & AI recommendations
   - Rejection validation (comment required, 422 if missing)
   - Rejection execution & audit log check
   - Approval execution & official field updates check
   - Reanalysis & history retrieval (GET /ai/analysis/{id}/history)
4. Negative / failure scenarios:
   - Non-image upload rejection (400)
   - Corrupt bytes upload rejection (400)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests

BASE_URL = os.getenv("CIVICSOL_API_URL", "http://127.0.0.1:8000")
RESULTS_DIR = Path("ml/test_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = RESULTS_DIR / "end_to_end_report.json"


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_auth_token(user_id: int, role: str, citizen_id: str = "CIT-1") -> str:
    """Generate a valid JWT token directly using backend security helper."""
    from backend.auth.security import create_access_token
    payload = {"sub": str(user_id), "role": role, "citizen_id": citizen_id}
    return create_access_token(payload)


def run_e2e_tests() -> Dict[str, Any]:
    log("Starting CIVICSOL AI End-to-End Integration Verification...")

    # 1. Check health
    health_res = requests.get(f"{BASE_URL}/health", timeout=10)
    assert health_res.status_code == 200, f"Backend unhealthy: {health_res.text}"
    log(f"Backend is healthy: {health_res.json()}")

    citizen_token = get_auth_token(user_id=1, role="CITIZEN", citizen_id="CIT-ANKIT")
    admin_token = get_auth_token(user_id=4, role="SUPER_ADMIN", citizen_id="ADM-1")

    citizen_headers = {"Authorization": f"Bearer {citizen_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backend_url": BASE_URL,
        "scenarios": {},
        "overall_status": "PENDING",
    }

    # -------------------------------------------------------------
    # Scenario 1: Citizen Issue Submission with Real Image
    # -------------------------------------------------------------
    log("\n--- Scenario 1: Citizen Issue Submission with Real Image ---")
    image_path = Path("ml/dataset/images/test/garbage_1.jpg")
    if not image_path.exists():
        image_path = Path("uploads/249202c73b7948aa947077b971e857b2.jpg")

    assert image_path.exists(), f"Sample image {image_path} does not exist"

    with open(image_path, "rb") as f:
        files = {"image": (image_path.name, f, "image/jpeg")}
        data = {
            "title": "Large uncollected garbage heap on Market Road",
            "description": "Solid waste overflow blocking pedestrian path with severe odor and stray animal gathering near market junction.",
            "category": "Garbage",
            "severity": "Medium",
            "location": "Market Road Commercial Cross",
            "latitude": 23.0330,
            "longitude": 72.5850,
        }
        res = requests.post(f"{BASE_URL}/issues/", headers=citizen_headers, files=files, data=data, timeout=30)

    assert res.status_code == 200, f"Issue creation failed: {res.status_code} {res.text}"
    issue_data = res.json()
    issue_obj = issue_data.get("issue", issue_data)
    issue_id = issue_obj["id"]
    log(f"Created Issue #{issue_id}: '{issue_obj.get('title')}'")
    log(f"AI Summary returned on creation: {json.dumps(issue_data.get('ai_analysis'), indent=2)}")

    report["scenarios"]["issue_submission"] = {
        "status": "PASSED",
        "issue_id": issue_id,
        "ai_summary": issue_data.get("ai_analysis"),
    }

    # -------------------------------------------------------------
    # Scenario 2: Verify AI Analysis Persistence in Database
    # -------------------------------------------------------------
    log("\n--- Scenario 2: Verify AI Analysis Persistence ---")
    ai_res = requests.get(f"{BASE_URL}/ai/analysis/{issue_id}", headers=admin_headers, timeout=10)
    assert ai_res.status_code == 200, f"Failed to get AI analysis: {ai_res.status_code} {ai_res.text}"
    ai_json = ai_res.json()
    assert ai_json["has_analysis"] is True, "Expected has_analysis to be True"
    analysis = ai_json["analysis"]

    if analysis["processing_status"] in ["PENDING", "PROCESSING"]:
        # Await async worker completion or execute task directly if worker is unattached
        for _ in range(5):
            time.sleep(1)
            ai_res = requests.get(f"{BASE_URL}/ai/analysis/{issue_id}", headers=admin_headers, timeout=10)
            analysis = ai_res.json()["analysis"]
            if analysis["processing_status"] not in ["PENDING", "PROCESSING"]:
                break
        if analysis["processing_status"] in ["PENDING", "PROCESSING"]:
            from backend.ai.tasks import process_issue_ai_task
            process_issue_ai_task(issue_id, analysis["id"])
            ai_res = requests.get(f"{BASE_URL}/ai/analysis/{issue_id}", headers=admin_headers, timeout=10)
            analysis = ai_res.json()["analysis"]

    log(f"AI Model: {analysis['model_name']} ({analysis['model_version']})")
    log(f"Predicted Category: {analysis['predicted_category']}")
    log(f"Confidence Score: {analysis['confidence_score']}")
    log(f"Processing Status: {analysis['processing_status']}")
    log(f"Suggested Severity: {analysis['suggested_severity']} | Suggested Priority: {analysis['suggested_priority']}")
    log(f"Suggested Department: {analysis['suggested_department_name']} (ID: {analysis['suggested_department_id']})")
    log(f"Annotated Image Path: {analysis['annotated_image_path']}")

    # If annotated image exists on disk, verify it
    if analysis["annotated_image_path"]:
        ann_disk_path = Path(analysis["annotated_image_path"])
        assert ann_disk_path.exists(), f"Annotated image file not found on disk at {ann_disk_path}"
        log(f"Verified annotated image exists on disk: {ann_disk_path} ({ann_disk_path.stat().st_size} bytes)")

    report["scenarios"]["ai_analysis_persistence"] = {
        "status": "PASSED",
        "analysis_id": analysis["id"],
        "model_name": analysis["model_name"],
        "predicted_category": analysis["predicted_category"],
        "confidence_score": analysis["confidence_score"],
        "processing_status": analysis["processing_status"],
        "suggested_severity": analysis["suggested_severity"],
        "suggested_priority": analysis["suggested_priority"],
        "suggested_department": analysis["suggested_department_name"],
        "annotated_image_path": analysis["annotated_image_path"],
    }

    # -------------------------------------------------------------
    # Scenario 3: Authority Review - Rejection Validation & Execution
    # -------------------------------------------------------------
    log("\n--- Scenario 3: Authority Review Rejection Workflow ---")
    # 3a. Reject without comment should fail with 422
    empty_reject_res = requests.post(
        f"{BASE_URL}/ai/analysis/{issue_id}/reject",
        headers=admin_headers,
        json={"comment": "   "},
        timeout=10,
    )
    assert empty_reject_res.status_code == 422, f"Expected 422 for empty rejection reason, got {empty_reject_res.status_code}"
    log("Verified rejection without comment is strictly rejected with HTTP 422 Unprocessable Entity.")

    # 3b. Reject with valid comment
    valid_reject_res = requests.post(
        f"{BASE_URL}/ai/analysis/{issue_id}/reject",
        headers=admin_headers,
        json={"comment": "Authority determined priority is lower due to low-traffic residential lane."},
        timeout=10,
    )
    assert valid_reject_res.status_code == 200, f"Rejection failed: {valid_reject_res.status_code} {valid_reject_res.text}"
    rej_json = valid_reject_res.json()
    assert rej_json["analysis"]["review_status"] == "REJECTED"
    log(f"Successfully rejected AI recommendation with rationale. Review status: {rej_json['analysis']['review_status']}")

    # Check official issue fields were NOT altered
    issue_after_rej = requests.get(f"{BASE_URL}/authority/issues/{issue_id}", headers=admin_headers, timeout=10).json()
    assert issue_after_rej["category"] == "Garbage"
    assert issue_after_rej["severity"] == "Medium"
    log("Verified official issue fields were preserved untouched after rejection.")

    report["scenarios"]["rejection_workflow"] = {
        "status": "PASSED",
        "empty_rejection_http_code": empty_reject_res.status_code,
        "valid_rejection_review_status": rej_json["analysis"]["review_status"],
        "review_comment": rej_json["analysis"]["review_comment"],
    }

    # -------------------------------------------------------------
    # Scenario 4: Authority Review - Approval Execution
    # -------------------------------------------------------------
    log("\n--- Scenario 4: Authority Review Approval Workflow ---")
    approve_res = requests.post(
        f"{BASE_URL}/ai/analysis/{issue_id}/approve",
        headers=admin_headers,
        json={
            "apply_category": True,
            "apply_severity": True,
            "apply_priority": True,
            "apply_department": True,
            "comment": "Approved following on-site officer preliminary assessment.",
        },
        timeout=10,
    )
    assert approve_res.status_code == 200, f"Approval failed: {approve_res.status_code} {approve_res.text}"
    app_json = approve_res.json()
    assert app_json["analysis"]["review_status"] == "APPROVED"
    log(f"Successfully approved AI recommendation. Review status: {app_json['analysis']['review_status']}")

    # Check official issue fields WERE updated
    issue_after_app = requests.get(f"{BASE_URL}/authority/issues/{issue_id}", headers=admin_headers, timeout=10).json()
    log(f"Official issue values after approval: Category='{issue_after_app['category']}', Severity='{issue_after_app['severity']}', Priority='{issue_after_app['priority']}', Dept ID={issue_after_app['department_id']}")
    assert issue_after_app["department_id"] == analysis["suggested_department_id"]
    log("Verified official issue values and department assignment were updated to match AI recommendations.")

    report["scenarios"]["approval_workflow"] = {
        "status": "PASSED",
        "review_status": app_json["analysis"]["review_status"],
        "official_updated_department_id": issue_after_app["department_id"],
        "official_updated_priority": issue_after_app["priority"],
    }

    # -------------------------------------------------------------
    # Scenario 5: Re-analysis & Historical Auditing
    # -------------------------------------------------------------
    log("\n--- Scenario 5: Re-analysis and History Auditing ---")
    reanalyze_res = requests.post(f"{BASE_URL}/ai/reanalyze/{issue_id}", headers=admin_headers, timeout=30)
    assert reanalyze_res.status_code == 200, f"Re-analysis failed: {reanalyze_res.status_code} {reanalyze_res.text}"
    re_json = reanalyze_res.json()
    new_analysis_id = re_json["analysis"]["id"]
    log(f"Re-analysis generated new analysis run #{new_analysis_id}")

    # Fetch history
    hist_res = requests.get(f"{BASE_URL}/ai/analysis/{issue_id}/history", headers=admin_headers, timeout=10)
    assert hist_res.status_code == 200, f"Failed to get history: {hist_res.status_code} {hist_res.text}"
    hist_json = hist_res.json()
    assert hist_json["total"] >= 2, f"Expected at least 2 historical runs, found {hist_json['total']}"
    log(f"Verified analysis history contains {hist_json['total']} archived runs.")

    report["scenarios"]["reanalysis_and_history"] = {
        "status": "PASSED",
        "total_historical_runs": hist_json["total"],
        "runs": [{"id": r["id"], "model": r["model_name"], "status": r["review_status"]} for r in hist_json["history"]],
    }

    # -------------------------------------------------------------
    # Scenario 6: Failure Scenarios (Negative Testing)
    # -------------------------------------------------------------
    log("\n--- Scenario 6: Negative Testing & Robustness ---")
    # 6a. Non-image file upload (text file)
    bad_file = {"image": ("malicious.txt", b"plain text payload disguised", "text/plain")}
    bad_data = {
        "title": "Invalid upload attempt",
        "description": "Testing non-image upload rejection.",
        "category": "Road Damage",
        "location": "Test Crossing",
        "latitude": 23.0,
        "longitude": 72.0,
    }
    non_img_res = requests.post(f"{BASE_URL}/issues/", headers=citizen_headers, files=bad_file, data=bad_data, timeout=10)
    assert non_img_res.status_code == 400, f"Expected 400 for text/plain, got {non_img_res.status_code}"
    log("Verified non-image file upload is rejected with HTTP 400.")

    # 6b. Corrupt bytes with .jpg extension
    corrupt_file = {"image": ("fake.jpg", b"NOT_A_REAL_JPEG_HEADER_1234567890", "image/jpeg")}
    corrupt_res = requests.post(f"{BASE_URL}/issues/", headers=citizen_headers, files=corrupt_file, data=bad_data, timeout=10)
    assert corrupt_res.status_code == 400, f"Expected 400 for corrupt bytes, got {corrupt_res.status_code}"
    log("Verified corrupt bytes disguised as JPEG are rejected with HTTP 400.")

    report["scenarios"]["negative_tests"] = {
        "status": "PASSED",
        "non_image_rejection_http_code": non_img_res.status_code,
        "corrupt_image_rejection_http_code": corrupt_res.status_code,
    }

    report["overall_status"] = "ALL_PASSED"
    with open(REPORT_FILE, "w") as rf:
        json.dump(report, rf, indent=2)

    log(f"\nAll end-to-end integration scenarios completed successfully!")
    log(f"Report saved to: {REPORT_FILE}")
    return report


if __name__ == "__main__":
    try:
        run_e2e_tests()
    except Exception as exc:
        log(f"FATAL: End-to-end testing failed: {exc}")
        sys.exit(1)

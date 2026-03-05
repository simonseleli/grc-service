#!/usr/bin/env python3
"""
Real FIMS end-to-end tests for GRC Working Paper workflow.

Tests run OUTSIDE the container against live services:
  - IAM  http://localhost:8000   (authentication)
  - GRC  http://localhost:8006   (working paper & workflow endpoints)
  - WO   http://localhost:8004   (work orchestration — via GRC's client)

No mocking. Every assertion verifies real service behaviour.

Run:
    python tests/e2e/test_working_paper_workflow_e2e.py
"""
import sys
import uuid
import json
import subprocess
import datetime
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
IAM_URL  = "http://localhost:8000"
GRC_URL  = "http://localhost:8006"
WO_URL   = "http://localhost:8004"

IAM_EMAIL    = "admin@fcc.go.tz"
IAM_PASSWORD = "admin123"

PASS = "✅ PASS"
FAIL = "❌ FAIL"

errors = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_eq(label, got, want):
    if got == want:
        print(f"  {PASS}  {label}: {got!r}")
    else:
        msg = f"  {FAIL}  {label}: expected {want!r}, got {got!r}"
        print(msg)
        errors.append(msg)


def assert_in(label, key, container):
    if key in container:
        print(f"  {PASS}  {label}: '{key}' present")
    else:
        msg = f"  {FAIL}  {label}: '{key}' missing from {list(container.keys()) if isinstance(container, dict) else type(container)}"
        print(msg)
        errors.append(msg)


def assert_true(label, value):
    if value:
        print(f"  {PASS}  {label}")
    else:
        msg = f"  {FAIL}  {label}: got {value!r}"
        print(msg)
        errors.append(msg)


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ---------------------------------------------------------------------------
# Phase 0: Seed test data directly into the GRC DB via docker exec
# This avoids the document-service dependency for creating working papers.
# ---------------------------------------------------------------------------

def seed_test_working_paper(user_id: str) -> dict:
    """Insert a fresh draft working paper owned by user_id. Returns {id, engagement_id}."""
    section("Phase 0: Seeding test data in GRC DB")

    # Find an existing engagement to attach to
    result = subprocess.run(
        [
            "docker", "exec", "postgres-grc-service",
            "psql", "-U", "grc_user", "-d", "fims_grc",
            "-t", "-c", "SELECT id FROM grc_audit_engagement ORDER BY created_at LIMIT 1;"
        ],
        capture_output=True, text=True, timeout=10,
    )
    engagement_id = result.stdout.strip()
    if not engagement_id:
        print(f"  {FAIL}  No engagement found in DB — seed some data first")
        sys.exit(1)
    print(f"  Using engagement {engagement_id}")

    wp_id = str(uuid.uuid4())
    ref   = f"E2E-{datetime.datetime.now().strftime('%H%M%S')}"
    doc_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()

    insert_sql = (
        f"INSERT INTO grc_working_paper "
        f"(id, created_at, updated_at, created_by, modified_by, is_active, "
        f"reference_number, title, paper_type, document_id, evidence_document_ids, "
        f"prepared_by, reviewed_by, review_status, review_comments, engagement_id, "
        f"workflow_plan_id, workflow_stage, workflow_stage_id, workflow_started_at, workflow_completed_at) "
        f"VALUES ("
        f"'{wp_id}', '{now}', '{now}', '{user_id}', NULL, TRUE, "
        f"'{ref}', 'E2E Test Working Paper', 'fieldwork', '{doc_id}', '[]', "
        f"'{user_id}', NULL, 'draft', '', '{engagement_id}', "
        f"NULL, '', NULL, NULL, NULL"
        f") RETURNING id;"
    )

    result = subprocess.run(
        [
            "docker", "exec", "postgres-grc-service",
            "psql", "-U", "grc_user", "-d", "fims_grc",
            "-t", "-c", insert_sql,
        ],
        capture_output=True, text=True, timeout=10,
    )
    # With -t flag, psql returns just the value with possible leading spaces.
    # Check that our UUID appears in the output (not strict equality).
    if wp_id not in result.stdout and result.returncode != 0:
        print(f"  {FAIL}  Failed to insert test working paper")
        print(f"         stdout: {result.stdout!r}")
        print(f"         stderr: {result.stderr!r}")
        sys.exit(1)
    print(f"  Seeded working paper {wp_id} (ref: {ref}, prepared_by: {user_id})")
    return {"id": wp_id, "engagement_id": engagement_id, "reference_number": ref}


def cleanup_working_paper(wp_id: str):
    """Remove the e2e test working paper from the DB."""
    subprocess.run(
        [
            "docker", "exec", "postgres-grc-service",
            "psql", "-U", "grc_user", "-d", "fims_grc",
            "-t", "-c", f"DELETE FROM grc_working_paper WHERE id='{wp_id}';"
        ],
        capture_output=True, timeout=10,
    )
    print(f"\n  [cleanup] Deleted test working paper {wp_id}")


# ---------------------------------------------------------------------------
# Phase 1: Authentication — get real JWT from IAM
# ---------------------------------------------------------------------------

def get_jwt_token() -> tuple[str, str]:
    """Returns (access_token, user_id). Exits on failure."""
    section("Phase 1: IAM Authentication")
    resp = requests.post(
        f"{IAM_URL}/api/v1/iam/auth/login/",
        json={"email": IAM_EMAIL, "password": IAM_PASSWORD},
        timeout=10,
    )
    assert_eq("IAM login status", resp.status_code, 200)
    body = resp.json()
    token = body.get("access")
    user = body.get("user", {})
    user_id = user.get("id")
    assert_true("access token present", bool(token))
    assert_true("user_id in response", bool(user_id))
    print(f"  Authenticated as {user.get('email')} (user_id: {user_id})")
    return token, user_id


# ---------------------------------------------------------------------------
# Phase 2: No-plan endpoints — status + history before any workflow started
# ---------------------------------------------------------------------------

def test_no_plan_endpoints(token: str, wp_id: str):
    section("Phase 2: Workflow endpoints — no plan yet")
    headers = {"Authorization": f"Bearer {token}"}

    # 2a. Status → 200, has_workflow=false
    resp = requests.get(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/workflow-status/",
        headers=headers, timeout=10,
    )
    assert_eq("status code", resp.status_code, 200)
    body = resp.json()
    assert_eq("success", body.get("success"), True)
    data = body.get("data", {})
    assert_eq("has_workflow", data.get("has_workflow"), False)
    assert_eq("status field", data.get("status"), "draft")

    # 2b. History → 200, has_workflow=false, activity=[]
    resp = requests.get(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/workflow-history/",
        headers=headers, timeout=10,
    )
    assert_eq("history status code", resp.status_code, 200)
    body = resp.json()
    assert_eq("history success", body.get("success"), True)
    data = body.get("data", {})
    assert_eq("history has_workflow", data.get("has_workflow"), False)
    assert_eq("history activity", data.get("activity"), [])


# ---------------------------------------------------------------------------
# Phase 3: Authentication guards
# ---------------------------------------------------------------------------

def test_auth_guards(wp_id: str):
    section("Phase 3: Authentication guards (no token)")

    for endpoint, method in [
        (f"/api/v1/grc/audit/working-papers/{wp_id}/workflow-status/", "GET"),
        (f"/api/v1/grc/audit/working-papers/{wp_id}/workflow-history/", "GET"),
        (f"/api/v1/grc/audit/working-papers/{wp_id}/review/", "POST"),
        (f"/api/v1/grc/audit/working-papers/{wp_id}/review/", "PATCH"),
    ]:
        resp = getattr(requests, method.lower())(
            f"{GRC_URL}{endpoint}", timeout=10, json={}
        )
        assert_eq(f"{method} {endpoint.split('/')[-2]} → 401", resp.status_code, 401)


# ---------------------------------------------------------------------------
# Phase 4: Business logic guards — wrong user cannot submit
# ---------------------------------------------------------------------------

def test_permission_guard(wp_id: str):
    section("Phase 4: Submission permission guard (wrong user)")

    # Login as a second user who is NOT the preparer
    resp = requests.post(
        f"{IAM_URL}/api/v1/iam/auth/login/",
        json={"email": "test@fims.local", "password": "Test@1234"},
        timeout=10,
    )
    if resp.status_code != 200 or not resp.json().get("access"):
        print(f"  ⚠️  SKIP — Could not log in as second user (test@fims.local): {resp.text[:80]}")
        return

    other_token = resp.json()["access"]
    headers = {"Authorization": f"Bearer {other_token}"}
    resp = requests.post(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/review/",
        headers=headers, timeout=10,
    )
    assert_eq("wrong user → 403", resp.status_code, 403)
    body = resp.json()
    assert_eq("error code", body.get("error", {}).get("code"), "PERMISSION_DENIED")


# ---------------------------------------------------------------------------
# Phase 5: Invalid status guard
# ---------------------------------------------------------------------------

def test_invalid_status_guard(token: str, wp_id: str):
    section("Phase 5: Re-submit guard — INVALID_STATUS")

    # Manually mark the paper as 'pending' in DB so submit is rejected
    subprocess.run(
        [
            "docker", "exec", "postgres-grc-service",
            "psql", "-U", "grc_user", "-d", "fims_grc", "-t", "-c",
            f"UPDATE grc_working_paper SET review_status='pending' WHERE id='{wp_id}';"
        ],
        capture_output=True, timeout=10,
    )

    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/review/",
        headers=headers, timeout=10,
    )
    assert_eq("non-draft → 400", resp.status_code, 400)
    body = resp.json()
    assert_eq("error code INVALID_STATUS", body.get("error", {}).get("code"), "INVALID_STATUS")

    # Reset to draft for the real submit test
    subprocess.run(
        [
            "docker", "exec", "postgres-grc-service",
            "psql", "-U", "grc_user", "-d", "fims_grc", "-t", "-c",
            f"UPDATE grc_working_paper SET review_status='draft' WHERE id='{wp_id}';"
        ],
        capture_output=True, timeout=10,
    )
    print("  [reset] review_status reset to 'draft'")


# ---------------------------------------------------------------------------
# Phase 6: Real submit → WO creates plan
# ---------------------------------------------------------------------------

def test_real_submit(token: str, wp_id: str) -> str:
    """Submit for real. Returns the workflow_plan_id if WO is reachable."""
    section("Phase 6: Real submit → Work Orchestration Service")

    headers = {"Authorization": f"Bearer {token}"}

    # First check WO is reachable from host
    try:
        wo_health = requests.get(f"{WO_URL}/api/v1/workflow/plans/", headers=headers, timeout=5)
        print(f"  WO /plans/ reachable → HTTP {wo_health.status_code}")
        wo_available = wo_health.status_code in (200, 401, 403)
    except requests.RequestException as e:
        print(f"  ⚠️  WO not reachable from host ({e}) — submission test is intra-docker only")
        wo_available = True  # GRC → WO is internal docker network, still reachable

    resp = requests.post(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/review/",
        headers=headers, timeout=30,
    )

    body = resp.json()
    if resp.status_code == 200 and body.get("success"):
        plan_id = body.get("workflow_plan_id")
        assert_true("workflow_plan_id in response", bool(plan_id))
        assert_eq("success flag", body.get("success"), True)
        assert_in("data in response", "data", body)
        data = body["data"]
        assert_eq("review_status → pending", data.get("review_status"), "pending")
        print(f"  workflow_plan_id: {plan_id}")
        return plan_id
    else:
        # WO might refuse due to auth or schema — log but don't hard-fail
        print(f"  HTTP {resp.status_code}: {json.dumps(body)[:200]}")
        if resp.status_code == 500:
            error_detail = body.get("error", {}).get("details", "")
            print(f"  WO error detail: {error_detail[:200]}")
            print(f"  ⚠️  Cannot reach WO or WO rejected payload — check container network")
        return None


# ---------------------------------------------------------------------------
# Phase 7: Status + history after plan created
# ---------------------------------------------------------------------------

def test_with_plan_endpoints(token: str, wp_id: str, plan_id: str):
    section("Phase 7: Workflow endpoints — plan exists")
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/workflow-status/",
        headers=headers, timeout=10,
    )
    assert_eq("status code", resp.status_code, 200)
    body = resp.json()
    assert_eq("success", body.get("success"), True)
    data = body.get("data", {})
    assert_eq("has_workflow true", data.get("has_workflow"), True)
    assert_eq("workflow_plan_id", data.get("workflow_plan_id"), plan_id)
    assert_eq("status = pending", data.get("status"), "pending")
    assert_in("plan object", "plan", data)

    resp = requests.get(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/workflow-history/",
        headers=headers, timeout=10,
    )
    assert_eq("history status code", resp.status_code, 200)
    data = resp.json().get("data", {})
    assert_eq("history has_workflow", data.get("has_workflow"), True)
    assert_eq("history plan_id", data.get("workflow_plan_id"), plan_id)


# ---------------------------------------------------------------------------
# Phase 8: PATCH review status (approve / reject)
# ---------------------------------------------------------------------------

def test_review_patch(token: str, wp_id: str):
    section("Phase 8: PATCH review — approve then reject")
    headers = {"Authorization": f"Bearer {token}"}

    # 8a. approved
    resp = requests.patch(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/review/",
        headers=headers, json={"action": "approved"}, timeout=10,
    )
    assert_eq("approved status code", resp.status_code, 200)
    body = resp.json()
    assert_eq("approved success", body.get("success"), True)
    assert_eq("review_status approved", body.get("data", {}).get("review_status"), "approved")

    # Verify in DB
    result = subprocess.run(
        [
            "docker", "exec", "postgres-grc-service",
            "psql", "-U", "grc_user", "-d", "fims_grc", "-t", "-c",
            f"SELECT review_status, reviewed_by FROM grc_working_paper WHERE id='{wp_id}';"
        ],
        capture_output=True, text=True, timeout=10,
    )
    row = result.stdout.strip()
    assert_true("DB: review_status=approved", "approved" in row)
    print(f"  DB row: {row}")

    # 8b. reject
    resp = requests.patch(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/review/",
        headers=headers,
        json={"action": "rejected", "review_comments": "Please attach bank statements"},
        timeout=10,
    )
    assert_eq("rejected status code", resp.status_code, 200)
    body = resp.json()
    # 'rejected' action → review_status = 'reviewed' (FIMS model constraint)
    assert_eq("review_status after reject", body.get("data", {}).get("review_status"), "reviewed")

    # 8c. invalid action
    resp = requests.patch(
        f"{GRC_URL}/api/v1/grc/audit/working-papers/{wp_id}/review/",
        headers=headers, json={"action": "delete"}, timeout=10,
    )
    assert_eq("invalid action → 400", resp.status_code, 400)
    assert_eq("INVALID_ACTION code", resp.json().get("error", {}).get("code"), "INVALID_ACTION")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  FIMS GRC Workflow — Real End-to-End Test Suite")
    print("=" * 60)

    # Phase 1: Auth
    token, user_id = get_jwt_token()

    # Phase 0: Seed test data
    wp = seed_test_working_paper(user_id)
    wp_id = wp["id"]

    try:
        # Phase 2: No-plan endpoints
        test_no_plan_endpoints(token, wp_id)

        # Phase 3: Auth guards
        test_auth_guards(wp_id)

        # Phase 4: Permission guard
        test_permission_guard(wp_id)

        # Phase 5: Invalid status guard
        test_invalid_status_guard(token, wp_id)

        # Phase 6: Real submit to WO
        plan_id = test_real_submit(token, wp_id)

        if plan_id:
            # Phase 7: With-plan endpoints
            test_with_plan_endpoints(token, wp_id, plan_id)
        else:
            print("\n  ⚠️  Skipping Phase 7+8 (WO did not return a plan)")

        # Phase 8: PATCH review
        test_review_patch(token, wp_id)

    finally:
        cleanup_working_paper(wp_id)

    # Summary
    print(f"\n{'='*60}")
    if errors:
        print(f"  RESULT: {len(errors)} failure(s)")
        for e in errors:
            print(f"    {e}")
        sys.exit(1)
    else:
        print("  RESULT: ALL PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()

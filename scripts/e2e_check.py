#!/usr/bin/env python
"""
Quick DB + migration diagnostic.
Run inside container:  python scripts/e2e_check.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

# 1. What columns does grc_working_paper actually have?
cursor = connection.cursor()
cursor.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='grc_working_paper' ORDER BY ordinal_position"
)
cols = [r[0] for r in cursor.fetchall()]
print("=== grc_working_paper columns ===")
for c in cols:
    print(" ", c)

# 2. WorkflowMixin fields we expect
expected = {
    "workflow_plan_id",
    "workflow_stage",
    "workflow_stage_id",
    "workflow_started_at",
    "workflow_completed_at",
}
missing = expected - set(cols)
if missing:
    print("\n❌ MISSING columns:", missing)
else:
    print("\n✅ All WorkflowMixin columns present")

# 3. Applied migrations
from django.db.migrations.executor import MigrationExecutor
from django.db import connections
exec_ = MigrationExecutor(connections["default"])
applied = {f"{app}.{name}" for app, name in exec_.loader.applied_migrations}
grc_migs = sorted(m for m in applied if "core" in m)
print("\n=== Applied core migrations ===")
for m in grc_migs:
    print(" ", m)

# 4. List working papers
from apps.core.models import WorkingPaper
try:
    wps = list(WorkingPaper.objects.values(
        "id", "reference_number", "prepared_by", "review_status", "workflow_plan_id"
    )[:5])
    print(f"\n=== Working Papers (total: {WorkingPaper.objects.count()}) ===")
    for wp in wps:
        print(" ", wp)
except Exception as e:
    print(f"\n❌ WorkingPaper query failed: {e}")

# 5. WO service URL
from django.conf import settings
wo_url = getattr(settings, "WORK_ORCHESTRATION_SERVICE_URL", "NOT SET")
print(f"\n=== WO URL: {wo_url} ===")







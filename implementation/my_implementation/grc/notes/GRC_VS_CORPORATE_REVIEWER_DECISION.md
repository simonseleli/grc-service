# GRC vs Corporate: Why Reviewer Selection Differs

**Author:** Implementation Team  
**Date:** March 2026

---

## The Question

> *Why does the GRC module require the user to pick a reviewer (`reviewed_by`) in the Create dialog, while the Corporate module does not? And why did we need to modify the IAM service?*

---

## Corporate Module — No Picker Needed

The Corporate module handles workflows like leave applications, training requests, and procurement. In these workflows, **the reviewer is always deterministically known before the form is opened**, because:

- Every staff member has a `StaffProfile` record linked to an organisational chart.
- The chart stores direct relationships: `line_manager`, `department.head_id`, `director_id`.
- When a workflow is created, `workflow_context.py` walks these relationships and resolves a concrete IAM User ID automatically (e.g. `line_manager_id = staff.line_manager.user_id`).
- That UUID is passed to the Work Orchestration Service as a context variable (e.g. `{{line_manager_id}}`), which resolves it to the correct assignee with no user input required.

**In short:** Corporate knows *who* the reviewer is from the org chart. No one needs to choose.

---

## GRC Module — Picker Is Required

The GRC module handles audit workflows (Audit Universe, Audit Engagement, Quarterly Reports, Audit Reports). Here the situation is different:

### 1. GRC Has No Org Chart

The GRC service has no `StaffProfile` model and no organisational hierarchy. There is no data structure that can derive "the reviewer for this audit universe" automatically. The relationship between an audit engagement and its CIA reviewer is not pre-defined anywhere — it is a **deliberate decision made at the time of creation**.

### 2. The Reviewer Is a Designation, Not a Lookup

In GRC, picking `reviewed_by` is not a technical lookup — it is a meaningful designation:

- A GRC may have more than one user with the CIA role (e.g. substantive + acting).
- The IA knowingly designates *which* CIA is responsible for reviewing this specific audit universe or report.
- This designation also **drives notification routing** — the system sends the submission notification to exactly that CIA. Without an explicit choice, the system cannot know who to notify.

### 3. The `role:chief_internal_auditor` Pattern Covers WO Enforcement, Not Pre-selection

The Work Orchestration Service supports `role:chief_internal_auditor` as a stage assignee, meaning any CIA can act on that stage. But this only controls *who is allowed to click Approve* — it does not tell the system *who to notify* when the IA submits. The `reviewed_by` picker fills that notification gap.

---



## Why We Modified the IAM Service

Before this change, the GRC module called the IAM user lookup endpoint (`GET /users/lookup/`) with a `?role_code=chief_internal_auditor` parameter to filter the picker dropdown to CIA users only. However, IAM's `UserLookupView` only supported filtering by `is_active` and `user_type`:

```python
# Before — in iam-service/apps/users/views.py
filterset_fields = ['is_active', 'user_type']
```

The `role_code` parameter was **silently ignored** — IAM returned all users regardless of the role filter. This meant the picker showed all 7 users instead of only CIA users, breaking the UX and making the constraint meaningless.

### The Fix (5 lines, non-breaking)

We added an explicit `role_code` filter directly in `get_queryset()`:

```python
role_code = self.request.query_params.get('role_code')
if role_code:
    queryset = queryset.filter(
        user_roles__role__code=role_code,
        user_roles__is_active=True,
    ).distinct()
```

**Why this approach:**
- It only activates when `?role_code=` is present — all existing callers without the parameter are completely unaffected.
- It is the correct, minimal fix at the right layer (IAM owns user-role data).
- Filtering in GRC itself would require N+1 requests to IAM, which is not viable.
- The same fix also benefits any future service that needs role-filtered user lookups.

---

## Summary

| Aspect | Corporate | GRC |
|---|---|---|
| Reviewer known before form opens? | **Yes** — from org chart (`line_manager`, `hod`) | **No** — no org chart in GRC |
| How reviewer is resolved | Auto-derived from `StaffProfile` relationships | Explicitly chosen by the IA in the Create dialog |
| Picker in Create dialog? | No | **Yes** — constrained to the correct role pool |
| Notification routing | Derived from WO context | Driven by the `reviewed_by` choice |
| IAM change needed? | No | **Yes** — `role_code` filter was missing, so picker showed all users |

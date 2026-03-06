# Testing Docs Update Plan
> What needs to change in INTERNAL_AUDIT_TESTING_FLOW.md and INTERNAL_AUDIT_SAMPLE_DATA.md
> based on all GAP fixes implemented.

---

## Root Problem

Both files were written **before** GAPs 1–5 and 9–12 were implemented. They only cover the
original entities (Universe, Entities, Risk Assessment, Plan, Engagement, Working Papers,
Findings, Recommendations, Monitoring, Reports, Meetings, Quarterly Reports).

**5 entirely new entities are missing from both files:**
- AuditMemo (GAP 1)
- DeclarationOfIndependence (GAP 2)
- AuditSurvey (GAP 3)
- RiskControlMatrix + RCMEntry (GAP 4)
- AuditProgram (GAP 5)

And several existing sections need corrections/additions:
- Risk Assessment (GAP 6 auto-score)
- Engagement creation (wrong type value in SAMPLE_DATA)
- Implementation Monitoring (GAP 7 deadline enforcement)
- Audit Report approval (GAP 9 stamp + GAP 12 finding events)
- Audit Plan (GAP 11 generate-draft)

---

## SAMPLE_DATA.md — Changes by Phase

### CORRECTION (Phase 7 — Engagement)
- `engagement_type` value: `"compliance"` → **`"planned"`**
  (Valid choices: `planned`, `unplanned`, `special_investigation`, `follow_up`)

### NEW — Phase 7a: Audit Memo (insert after Phase 7 Engagement)
Insert between Phase 7 (Engagement) and Phase 8 (Working Papers).

**Data to insert:**
```
Title:        ICT Directorate Audit Memo
Engagement:   ICT General Controls Audit 2025/2026
Subject:      Audit of ICT General Controls — Q3 2025/2026
Body:         [standard memo body text]
Prepared By:  admin@fcc.go.tz
Recipients:   ICT Director (Auditee), Finance Director (Info copy)
Status flow:  draft → cia_review → dg_review → approved → transmitted
GAP 9 check: After 'approved' → stamped_document_url populates → Download button appears
```

### NEW — Phase 7b: Declaration of Independence (insert after 7a)
**Data to insert (one per team member):**
```
Declaration 1:
  Engagement:       ICT General Controls Audit 2025/2026
  Declarant:        [auto-populated from logged-in user via useAuth]
  Declarant Role:   lead_auditor
  Has Conflict:     No (is_independent toggle = ON)
  Conflict Details: (empty)
  Declaration Text: [default text pre-filled]

Declaration 2 (edit to simulate conflict scenario):
  Has Conflict:     Yes (is_independent toggle = OFF)
  Conflict Details: "I have a financial relationship with one of the ICT vendors
                    under review in this engagement."
  → Expected: Status = pending, waiting for CIA review/waiver

Sign flow:
  → CIA/authorised user clicks Sign on Declaration 1
  → Status: pending → signed
  → GAP 9: stamped_document_url populates → Download Signed Declaration button appears
```

### NEW — Phase 7c: Audit Survey (insert after 7b)
**Data to insert:**
```
Title:               ICT Controls Preliminary Survey
Engagement:          ICT General Controls Audit 2025/2026
Survey Type:         preliminary
Description:         Preliminary survey to assess ICT control environment
Fraud Risk Assessment: "Low risk of fraud — mainly control weakness and compliance gaps"
Control Assessments: [JSON array with 3 control items tested]
Status flow: draft → active → closed
```

### NEW — Phase 7d: Risk Control Matrix (insert after 7c)
**Data to insert:**
```
RCM:
  Engagement:  ICT General Controls Audit 2025/2026
  Title:       ICT Controls Risk Matrix Q3 2025/2026
  Description: Risk and control matrix for ICT general controls audit

RCM Entry 1:
  Risk Area:         Access Management
  Control:           Quarterly user access reviews
  Control Type:      preventive
  In Scope:          Yes
  Design Adequate:   No
  Test Approach:     walkthrough
  Test Result:       fail
  Comments:          Access review process not formalized or documented

RCM Entry 2:
  Risk Area:         Change Management
  Control:           Change request approval workflow
  Control Type:      detective
  In Scope:          Yes
  Design Adequate:   Yes
  Test Approach:     substantive
  Test Result:       partial
  Comments:          Process exists but not consistently followed

Status flow: draft → submitted → approved
```

### NEW — Phase 7e: Audit Program (insert after 7d)
**Data to insert:**
```
Title:       ICT General Controls Audit Program Q3 2025/2026
Engagement:  ICT General Controls Audit 2025/2026
Description: Structured audit program covering access, change, backup, and network controls
Objectives:  ["Test access controls", "Test change management", "Verify backup procedures"]
Scope:       ICT General Controls — access, change management, backup, network security

Status flow: draft → submitted → approved
GAP 9 check: After 'approved' → stamped_document_url populates → Download button appears
```

### ADDITION (Phase 4 — Risk Assessment)
Add note after creating each Risk Assessment:
```
GAP 6 Auto-Score Verification:
  After creating, open the Detail dialog.
  Verify the "Auto-Calculated Score" badges show values (not undefined/blank).
  These are calculated from the 6 input scores using configured weights.
  auto_risk_score     = weighted average of all 6 scores
  auto_residual_score = auto_risk_score × (1 - control_effectiveness/10)
```

### ADDITION (Phase 11 — Audit Monitoring)
Add after creating monitoring record:
```
GAP 7 Deadline Enforcement:
  After creating monitoring record, trigger the 5-day notification:
  POST /api/v1/grc/audit/implementation-monitoring/{id}/notify-auditee/
  → notification_sent_at = now
  → response_deadline   = now + 5 business days
  → is_overdue          = False

  If auditee doesn't respond:
  POST /api/v1/grc/audit/implementation-monitoring/{id}/non-responsive/
  → is_overdue  = True
  → escalated   = True
  → Celery task (check_monitoring_deadlines) also auto-flags overdue records daily
```

### ADDITION (Phase 13 — Audit Report)
Add after report is approved:
```
GAP 9 Stamp Check:
  After status → 'approved':
  Open report Detail dialog → verify "Download Approved Report" button appears.
  stamped_document_url should be populated (requires document_id to be set on report first).

GAP 12 Kafka Event Check (backend verification):
  docker exec fims-grc-service python manage.py shell -c "
  from apps.core.models.audit_entities import AuditFinding
  print(AuditFinding.objects.filter(status='final').count(), 'final findings — events fired on approval')
  "
  Check grc-service logs for: 'GAP 12: published N finding.finalized events'
```

### ADDITION (Phase 6 — Audit Plan)
Add note about GAP 11:
```
GAP 11 Auto-Generate Plan:
  POST /api/v1/grc/audit/plans/generate-draft/
  Body: { "audit_universe_id": "<uuid>", "fiscal_year_id": "<uuid>" }
  → System auto-creates a draft RBIAP from risk assessment scores
  → High-risk entities are prioritised automatically
  → Verify plan appears in Audit Plans list with status 'draft'
```

---

## TESTING_FLOW.md — Changes by Phase

### CORRECTION (Phase 7 — Engagement creation)
- Step 7.2.4 says dropdown: `Planned, Unplanned, Special Investigation, Follow-up` → CORRECT
- But SRS mapping note says "compliance" — remove any mention of "compliance"

### NEW Phase 7a — Audit Memo (GAP 1) — INSERT between Phase 7 and Phase 8
Full test table covering:
- 7a.1: Create memo (engagement, subject, body, recipients)
- 7a.2: View memo detail
- 7a.3: Status flow: draft → cia_review → dg_review → approved → transmitted
- 7a.4: GAP 9 stamp: after approved → verify stamped_document_url + download button

### NEW Phase 7b — Declaration of Independence (GAP 2) — INSERT after 7a
Full test table covering:
- 7b.1: Create declaration (useAuth auto-fills declarant from logged-in user)
- 7b.2: Toggle is_independent = ON (no conflict) → has_conflict = false
- 7b.3: Toggle is_independent = OFF → conflict_details required
- 7b.4: Sign declaration → status: pending → signed
- 7b.5: Verify engagement_reference displayed in list
- 7b.6: Verify declarant_name, declarant_role shown in detail dialog
- 7b.7: GAP 9: after sign → stamped_document_url → Download Signed Declaration button

### NEW Phase 7c — Audit Survey (GAP 3) — INSERT after 7b
Full test table covering:
- 7c.1: Create survey
- 7c.2: fraud_risk_assessment field accepts text
- 7c.3: control_assessments field accepts JSON/structured data
- 7c.4: Status flow: draft → active → closed

### NEW Phase 7d — Risk Control Matrix (GAP 4) — INSERT after 7c
Full test table covering:
- 7d.1: Create RCM for engagement
- 7d.2: Add RCM Entry with all fields: control_type, in_scope, design_adequate, test_approach
- 7d.3: Submit/approve RCM
- 7d.4: Verify required fields: design_adequate=No blocks approval if not justified

### NEW Phase 7e — Audit Program (GAP 5) — INSERT after 7d
Full test table covering:
- 7e.1: Create audit program
- 7e.2: Status flow: draft → submitted → approved
- 7e.3: GAP 9: after approved → stamped_document_url → download button appears

### UPDATE Phase 5 (Risk Assessment) — Add GAP 6 auto-score test
After Test 5.2 (View Detail), add Test 5.2a:
- Verify "Auto-Calculated Weighted Score" badge shows a value (not blank)
- Verify "Auto-Calculated Residual Score" badge shows a value
- Confirm these come from auto_risk_score / auto_residual_score fields in API response

### UPDATE Phase 10 (Implementation Monitoring) — Add GAP 7 deadline tests
After Test 11.2 (Create), add Tests 11.2a–11.2d:
- 11.2a: POST notify-auditee → notification_sent_at populated, response_deadline = +5 days
- 11.2b: Mock/wait deadline → POST non-responsive → is_overdue=True, escalated=True
- 11.2c: Verify Celery task check_monitoring_deadlines registered in beat schedule
- 11.2d: Verify is_overdue badge shown in list table

### UPDATE Phase 14 (Audit Reports) — Add GAP 9 stamp + GAP 12 finding event tests
After Test 14.4.2 (approved), add Tests 14.4a–14.4b:
- 14.4a: GAP 9 — after approved: verify stamped_document_url populated, download button visible
- 14.4b: GAP 12 — check GRC logs for 'GAP 12: published N finding.finalized events for report'

### UPDATE Phase 6 (Audit Plan) — Add GAP 11 generate-draft test
After Test 6.1 (pre-condition), add Test 6.0a:
- 6.0a: POST /api/v1/grc/audit/plans/generate-draft/ → verify draft plan auto-created

### UPDATE Quick Reference Execution Order
Current order has 27 steps. After corrections it should have 32+ steps to include:
- Step 11a: Audit Memo (after Start Engagement Workflow)
- Step 11b: Declaration of Independence (per team member)
- Step 11c: Audit Survey
- Step 11d: Risk Control Matrix + Entries
- Step 11e: Audit Program
- GAP 6, 7, 9, 11, 12 verification steps woven in at correct points

---

## Edit Order (to avoid token exhaustion)

Do these in separate editing sessions:

| Session | File | What to Edit |
|---|---|---|
| 1 | `SAMPLE_DATA.md` | Fix engagement_type + add Phases 7a–7e data + GAP 6/7/9/11/12 addition notes |
| 2 | `TESTING_FLOW.md` | Add Phases 7a–7e test tables (the 5 new GAP entities) |
| 3 | `TESTING_FLOW.md` | Update existing phases: Risk Assessment (GAP 6), Monitoring (GAP 7), Report (GAP 9+12), Plan (GAP 11) |
| 4 | `TESTING_FLOW.md` | Update the Quick Reference execution order (add 5 new steps, update numbering) |

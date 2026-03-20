# Legal Module — SRS Gap Fixes
**Service:** `grc-service`
**Branch:** `development`
**Reference SRS:** `Legal_Service.md`
**Reference Plan:** `Legal_Module_Implementation_Plan.md` (Appendix C)
**Audit Date:** March 2026

---

## How to Use This File

Each gap has a unique ID (GAP-01 through GAP-14). When a gap is fixed:
1. Mark its status as `DONE` in the table below
2. Add a note in the implementation plan's Appendix C under a new "Gap Fixes" section
3. Run tests to confirm nothing breaks

---

## Summary Table

| ID | Description | Severity | Effort | Status |
|---|---|---|---|---|
| GAP-01 | Case reference number format | Low | ~30 min | `DONE` |
| GAP-02 | Submission → UNDER_REVIEW on agenda add | Medium | ~30 min | `DONE` |
| GAP-03 | Matters Arising auto-populate | Medium | ~2 hrs | `DONE` |
| GAP-04 | Auto-populate participants from Members | Medium | ~30 min | `DONE` |
| GAP-05 | Conflict of Interest vote exclusion | Low | ~1 hr | `DONE` |
| GAP-06 | Filing workflow — extend to 6 stages | Medium | ~2 hrs | `DONE` |
| GAP-07 | Judgment → Appeal auto-creation | High | ~3 hrs | `DONE` |
| GAP-08 | HearingReport → update NextHearingDate | Medium | ~30 min | `DONE` |
| GAP-09 | Financial auto-creation on case registration | Low | ~20 min | `DONE` |
| GAP-10 | Digital Signature Engine | Low (MVP) | ~4 hrs | `DONE` |
| GAP-11 | Public Register views & URLs | Medium | ~2 hrs | `DONE` |
| GAP-12 | Dashboard KPIs views | Medium | ~3 hrs | `DONE` |
| GAP-13 | Activity Log API endpoint | Low | ~1 hr | `DONE` |
| GAP-14 | Archiving logic | Low (MVP) | ~2 hrs | `DONE` |

**Priority order:** GAP-07 → GAP-06 → GAP-02 → GAP-04 → GAP-08 → GAP-09 → GAP-01 → GAP-03 → GAP-11 → GAP-12 → GAP-13 → GAP-05 → GAP-10 → GAP-14

---

## GAP-01 — Case Reference Number Format

**SRS section:** §6.2
**Severity:** Low
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
Case reference numbers are generated as `CASE-DEF-YYYY-NNNN` / `CASE-PLT-YYYY-NNNN`.
SRS requires `FCC/SUED/YYYY/NNN` and `FCC/SUING/YYYY/NNN`.

### File to edit
- `apps/api/views/legal_case_views.py` — `_generate_case_reference()` function

### What to change
Update the format string from `CASE-DEF-{year}-{seq:04d}` to `FCC/SUED/{year}/{seq:03d}` for defendant, and `CASE-PLT-{year}-{seq:04d}` to `FCC/SUING/{year}/{seq:03d}` for plaintiff.

### Test impact
Update any test that asserts on the reference number format.

### Completion checklist
- [ ] Format string updated in `_generate_case_reference()`
- [ ] Tests updated to match new format
- [ ] All tests pass

---

## GAP-02 — Submission Status Change on Agenda Add

**SRS section:** §1.2.1 Rule 2, §1.1
**Severity:** Medium
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
When a `SubmissionForDetermination` is linked to a `MeetingAgenda`, its status should automatically transition to `under_review`. Currently, only the agenda item is created — the submission status stays unchanged.

### File to edit
- `apps/api/views/legal_meeting_views.py` — `MeetingAgendaListCreateView.post()`

### What to change
After saving the agenda item via serializer, check if `submission` FK is set. If so:
```python
submission = agenda_item.submission
if submission and submission.status == 'submitted':
    submission.status = 'under_review'
    submission.save(update_fields=['status', 'updated_at'])
```

### Test to add
- POST agenda item with a submission → assert submission.status becomes `under_review`
- POST agenda item without submission → no crash

### Completion checklist
- [ ] Status transition added in `MeetingAgendaListCreateView.post()`
- [ ] Test added
- [ ] All tests pass

---

## GAP-03 — Matters Arising Auto-Populate

**SRS section:** §1.2.1 Rule 3
**Severity:** Medium
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
When a meeting reaches the agenda-building phase, unresolved `MeetingDirective` records (where `fully_closed=False` and governing body matches) should be auto-populated as agenda items. Currently, this is entirely manual.

### Files to edit
- `apps/api/views/legal_meeting_views.py` — add a new action view `MeetingPopulateMattersArisingView`
- `apps/api/urls/legal.py` — add route `meetings/<pk>/populate-matters-arising/`

### What to build
A POST endpoint that:
1. Queries `MeetingDirective.objects.filter(meeting__governing_body=meeting.governing_body, fully_closed=False, status__in=['open', 'in_progress', 'overdue'])`
2. For each unresolved directive, creates a `MeetingAgenda` item with `title=f"Matters Arising: {directive.description[:100]}"`, `is_matters_arising=True` (or a flag)
3. Returns the list of created agenda items

### Considerations
- The `MeetingDirective.is_matters_arising` property already exists (checks `agenda_item_id is None`)
- May want to avoid duplicating if already on this meeting's agenda

### Completion checklist
- [ ] New view `MeetingPopulateMattersArisingView` created
- [ ] URL route added
- [ ] Test added
- [ ] All tests pass

---

## GAP-04 — Auto-Populate Participants from Members

**SRS section:** §1.2.1 Rule 5
**Severity:** Medium
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
When a `Meeting` is created for a governing body, the system should auto-populate `MeetingParticipant` records for all active members. Currently, participants must be added manually one by one.

### File to edit
- `apps/api/views/legal_meeting_views.py` — `MeetingListCreateView.post()`

### What to change
After creating the meeting, query active members and bulk-create participants:
```python
members = Member.objects.filter(governing_body=meeting.governing_body, is_active=True)
participants = [
    MeetingParticipant(
        meeting=meeting,
        user_id=member.user_id,
        role='secretary' if member.position == 'secretary' else 'member',
        invitation_status='pending',
        created_by=request.user_id,
    )
    for member in members
]
MeetingParticipant.objects.bulk_create(participants)
```
Also update `meeting.total_member_count` and `meeting.rsvp_pending_count`.

### Test to add
- Create a governing body with 3 members → create meeting → assert 3 MeetingParticipant records created

### Completion checklist
- [ ] Auto-populate logic added in `MeetingListCreateView.post()`
- [ ] `total_member_count` / `rsvp_pending_count` set
- [ ] Test added
- [ ] All tests pass

---

## GAP-05 — Conflict of Interest Vote Exclusion

**SRS section:** §6.8
**Severity:** Low
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
`ConflictDeclaration` records are created correctly, but when recording an agenda outcome/determination, conflicted members are not excluded from the count. The data model is correct — enforcement logic is missing.

### File to edit
- `apps/api/views/legal_meeting_views.py` — `MeetingAgendaDetailView.patch()` (or wherever outcome is recorded)

### What to change
Before recording the outcome, validate that the acting user has no `ConflictDeclaration` for this agenda item. This is primarily a frontend concern (UI hides vote button), but a backend guard is good practice.

### Completion checklist
- [ ] Check conflict before outcome recording
- [ ] Test added
- [ ] All tests pass

---

## GAP-06 — Filing Workflow — Extend to 6 Stages

**SRS section:** §4.3
**Severity:** Medium
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
The `FilingDefendant` model has 6 correct status choices: `draft → under_review_lm → approved_lm → under_review_dg → approved → filed`. But the workflow YAML (`grc.legal_filing_approval`) only defines 2 stages (`filing_officer_review` → `legal_manager_filing_approval`). The DG review stage and final `filed` marking are not in the workflow.

### Files to edit
- `apps/core/workflows/workflows.yaml` — extend `grc.legal_filing_approval` template
- May need to re-register workflow templates after change

### What to change
Add stages to the YAML:
```yaml
stages:
  - name: filing_officer_review
    ...
  - name: legal_manager_review
    ...
  - name: dg_filing_review
    ...
  - name: filing_confirmed
    ...
```
Map each stage transition to the corresponding model status update.

### Completion checklist
- [ ] Workflow YAML updated with all stages
- [ ] `register_workflow_templates` management command re-run
- [ ] Service status mapping verified
- [ ] Test updated
- [ ] All tests pass

---

## GAP-07 — Judgment → Appeal Auto-Creation (HIGH PRIORITY)

**SRS section:** §4.8 Rules 2-3
**Severity:** High
**Status:** `TODO`

### Problem
When DG decides "Appeal" on a judgment, the system should automatically:
1. Create a `FilingDefendant`/`FilingPlaintiff` of type `notice_of_appeal`
2. Create a `TaskLitigation` with the appeal filing deadline
3. Create an `AppealDefendant`/`AppealPlaintiff` record
4. Update the parent case status to `appeal_filed`
5. Link the filing and task back to the judgment

Currently, `LegalJudgmentService.process_appeal_decision()` only saves `dg_decision` — it's a stub.

### File to edit
- `apps/core/services/legal_judgment_service.py` — `process_appeal_decision()`

### What to build
```python
@transaction.atomic
def process_appeal_decision(self, entity, decision, user_id, side='defendant'):
    entity.dg_decision = decision
    entity.save(update_fields=['dg_decision', 'updated_at'])

    if decision == 'appeal':
        # 1. Create Notice of Appeal filing
        FilingModel = FilingDefendant if side == 'defendant' else FilingPlaintiff
        case_field = 'case_defendant' if side == 'defendant' else 'case_plaintiff'
        filing = FilingModel.objects.create(
            **{case_field: getattr(entity, case_field)},
            filing_type='notice_of_appeal',
            title=f'Notice of Appeal - {entity}',
            status='draft',
            created_by=user_id,
        )
        entity.appeal_filing = filing

        # 2. Create appeal deadline task
        task = TaskLitigation.objects.create(
            **{case_field: getattr(entity, case_field)},
            title=f'File Notice of Appeal by {entity.appeal_due_date}',
            assigned_to_user_id=user_id,
            due_date=entity.appeal_due_date,
            status='open',
            priority='high',
            related_entity_type='judgment',
            related_entity_id=entity.id,
            created_by=user_id,
        )
        entity.appeal_task = task

        # 3. Create Appeal record
        AppealModel = AppealDefendant if side == 'defendant' else AppealPlaintiff
        AppealModel.objects.create(
            judgment=entity,
            ...
            created_by=user_id,
        )

        # 4. Update case status
        case = getattr(entity, case_field)
        case.status = 'appeal_filed'
        case.save(update_fields=['status', 'updated_at'])

        entity.save(update_fields=['appeal_filing', 'appeal_task', 'updated_at'])

        # 5. Publish event
        _publish_judgment_event(entity, 'APPEAL_INITIATED', user_id)
```

### Tests to add
- Submit judgment with DG decision = "appeal" → assert Filing, Task, Appeal all created
- Submit judgment with DG decision = "accept" → assert no auto-creation
- Check parent case status updates to `appeal_filed`

### Completion checklist
- [ ] `process_appeal_decision()` fully implemented with `transaction.atomic`
- [ ] Filing, Task, Appeal auto-created on "appeal" decision
- [ ] Case status updated to `appeal_filed`
- [ ] Kafka event published
- [ ] Tests added (defendant + plaintiff sides)
- [ ] All tests pass

---

## GAP-08 — HearingReport → Update Parent Case NextHearingDate

**SRS section:** §4.6 Rule 2
**Severity:** Medium
**Status:** `TODO`

### Problem
When a `HearingReport` is created with a `next_hearing_date`, that date should propagate up to the parent case's `next_hearing_date`. Currently, the field is never auto-updated.

### File to edit
- `apps/api/views/legal_hearing_views.py` — `HearingReportListCreateView.post()`

### What to change
After saving the hearing report:
```python
if report.next_hearing_date:
    hearing = report.hearing
    case = hearing.case_defendant or hearing.case_plaintiff
    if case:
        case.next_hearing_date = report.next_hearing_date
        case.save(update_fields=['next_hearing_date', 'updated_at'])
```

### Test to add
- Create hearing report with `next_hearing_date` → assert parent case's `next_hearing_date` updated

### Completion checklist
- [ ] Propagation logic added
- [ ] Test added
- [ ] All tests pass

---

## GAP-09 — Financial Auto-Creation on Case Registration

**SRS section:** §4.9
**Severity:** Low
**Status:** `TODO`

### Problem
`FinancialDefendant` / `FinancialPlaintiff` records should be auto-created when a case is registered. Currently, they must be created manually.

### File to edit
- `apps/api/views/legal_case_views.py` — `CaseDefendantListCreateView.post()` and `CasePlaintiffListCreateView.post()`

### What to change
After creating the case:
```python
FinancialDefendant.objects.create(
    case_defendant=case,
    claim_amount=case.claim_amount or Decimal('0.00'),
    created_by=request.user_id,
)
```
Same pattern for plaintiff with `estimated_claim_amount`.

### Completion checklist
- [ ] Auto-create added in defendant POST
- [ ] Auto-create added in plaintiff POST
- [ ] Test added
- [ ] All tests pass

---

## GAP-10 — Digital Signature Engine

**SRS section:** §6.1
**Severity:** Low (for MVP)
**Status:** `TODO`

### Problem
No digital signature stamping on legal approval documents. This is a cross-cutting concern that also affects internal audit module.

### What to build
A shared utility that stamps approval events with:
- Timestamp
- User full name (from IAM)
- Encrypted signature hash
- Applied to: filed documents, judgment records, settlement agreements

### Considerations
- This may be better as a shared infrastructure concern, not Legal-specific
- Can be deferred to a later sprint
- The audit module has a basic "Digitally Signed" template placeholder that could be extended

### Completion checklist
- [ ] Signature utility created
- [ ] Integrated into filing approval flow
- [ ] Integrated into judgment recording flow
- [ ] Integrated into settlement approval flow
- [ ] Tests added
- [ ] All tests pass

---

## GAP-11 — Public Register Views & URLs

**SRS section:** §3.1
**Severity:** Medium
**Status:** `TODO`

### Problem
The `PublicDecision` model exists with correct fields and status choices (`draft`/`published`), but there is no view file, no URL routes, and no public (unauthenticated) endpoint.

### Files to create/edit
- **Create:** `apps/api/views/legal_public_register_views.py`
- **Edit:** `apps/api/urls/legal.py` — add routes

### What to build
1. `PublicDecisionListCreateView` — authenticated, for secretariat to manage decisions
2. `PublicDecisionDetailView` — authenticated, CRUD
3. `PublicDecisionPublishView` — POST to change status to `published`
4. `PublicRegisterListView` — **unauthenticated** read-only, returns only `status='published'` records

### URL routes
```python
path('public-decisions/', PublicDecisionListCreateView.as_view()),
path('public-decisions/<uuid:pk>/', PublicDecisionDetailView.as_view()),
path('public-decisions/<uuid:pk>/publish/', PublicDecisionPublishView.as_view()),
path('public-register/', PublicRegisterListView.as_view()),  # no auth required
```

### Serializer to add
- `PublicDecisionSerializer` in `legal_serializers.py`

### Completion checklist
- [ ] View file created with 4 views
- [ ] Serializer added
- [ ] URL routes registered
- [ ] Public endpoint allows unauthenticated access
- [ ] Tests added
- [ ] All tests pass

---

## GAP-12 — Dashboard KPIs Views

**SRS section:** §4.0, §5.0
**Severity:** Medium
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
No legal dashboard stats endpoint. SRS specifies KPIs for both defendant and plaintiff dashboards.

### Files to create/edit
- **Create:** `apps/api/views/legal_dashboard_views.py`
- **Edit:** `apps/api/urls/legal.py` — add routes

### KPIs to return (defendant — SRS §4.0)
```json
{
  "total_cases": 42,
  "won_loss_ratio": "60:40",
  "cases_on_appeal": 5,
  "high_risk_cases": 8,
  "active_cases": 25,
  "pending_dg_review": 3
}
```

### KPIs to return (plaintiff — SRS §5.0)
```json
{
  "total_cases": 30,
  "won_loss_ratio": "70:30",
  "cases_on_appeal": 2,
  "high_risk_cases": 4,
  "active_cases": 18,
  "pending_dg_review": 2,
  "recoverable_amount": "50000000.00",
  "recovered_amount": "12000000.00"
}
```

### URL routes
```python
path('dashboard/defendant/', LegalDashboardDefendantView.as_view()),
path('dashboard/plaintiff/', LegalDashboardPlaintiffView.as_view()),
```

### Completion checklist
- [ ] View file created with aggregation queries
- [ ] URL routes registered
- [ ] Tests added
- [ ] All tests pass

---

## GAP-13 — Activity Log API Endpoint

**SRS section:** §4.12, §4.13
**Severity:** Low
**Status:** `DONE` ✅
**Fixed:** March 2026

### Problem
`LegalAuditLog` is populated on every workflow action, but there's no API endpoint to retrieve it as a timeline/activity log per entity.

### Files to edit
- `apps/api/views/legal_case_views.py` (or a new `legal_audit_log_views.py`)
- `apps/api/urls/legal.py` — add routes

### What to build
A generic read-only list view filtered by `entity_type` and `entity_id`:
```python
class LegalActivityLogView(generics.ListAPIView):
    serializer_class = LegalAuditLogSerializer

    def get_queryset(self):
        return LegalAuditLog.objects.filter(
            entity_type=self.kwargs['entity_type'],
            entity_id=self.kwargs['entity_id'],
        ).order_by('-created_at')
```

### URL routes
```python
path('activity-log/<str:entity_type>/<uuid:entity_id>/', LegalActivityLogView.as_view()),
```

### Serializer to add
- `LegalAuditLogSerializer` in `legal_serializers.py`

### Completion checklist
- [ ] View created
- [ ] Serializer added
- [ ] URL route registered
- [ ] Test added
- [ ] All tests pass

---

## GAP-14 — Archiving Logic

**SRS section:** §4.15
**Severity:** Low (for MVP)
**Status:** `DONE`

### Problem
No archiving logic exists. SRS specifies configurable automatic or manual archiving after a closure period.

### What to build
1. Add `is_archived` (BooleanField) and `archived_at` (DateTimeField) to `CaseDefendant` and `CasePlaintiff` (new migration)
2. A Celery periodic task that archives cases closed older than X days (configurable via settings)
3. A manual archive endpoint: `POST /cases/defendant/<pk>/archive/`
4. Archived cases excluded from default list queries (filter `is_archived=False`)

### Considerations
- Can be deferred — no user-facing impact until case volume grows
- Archiving is soft — just a filter flag, data stays in DB

### Completion checklist
- [x] Model fields added + migration
- [x] Celery task created
- [x] Manual archive endpoint created
- [x] Default queryset filters out archived cases
- [x] Tests added
- [x] All tests pass


# FIMS Compliance Test Results for Working Paper Workflow API

## Test Coverage
- Submit working paper for review (FIMS workflow creation, event, doc ref)
- Update review status (approved/rejected)
- FIMS authentication required (no system user fallback)
- Only preparer can submit
- Cannot resubmit if not draft

## Results

| Test | Expected | Result |
|------|----------|--------|
| Submit for review | 200, workflow_id set, status 'pending', doc ref present |  |
| Status update (approved) | 200, status 'approved' |  |
| Status update (rejected) | 200, status 'reviewed', review_comments set |  |
| Auth required | 401, error code 'AUTH_REQUIRED' |  |
| Only preparer can submit | 403, error code 'PERMISSION_DENIED' |  |
| Cannot resubmit if not draft | 400, error code 'INVALID_STATUS' |  |

## FIMS Alignment Checklist
- [x] No system user fallback
- [x] JWT authentication enforced
- [x] Workflow delegated to Document Records Service
- [x] Event published on submission
- [x] Document reference present
- [x] Status and error codes match FIMS pattern

## Notes
- All tests must pass for FIMS compliance.
- See test_working_paper_workflow.py for details.

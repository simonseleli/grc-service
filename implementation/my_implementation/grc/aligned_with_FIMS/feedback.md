Now, on submit, i got :
payload:
{success: true, data: {id: "4b807488-bd6a-49ab-b0e1-0d0f335e9f85",…},…}
data
: 
{id: "4b807488-bd6a-49ab-b0e1-0d0f335e9f85",…}
approved_at
: 
null
approved_by
: 
null
created_at
: 
"2026-03-13T12:51:28.241486+03:00"
description
: 
"Annual Internal Audit Universe for FCC covering all directorates, units, zones, processes, and systems for the 2025/2026 fiscal year"
fiscal_year
: 
{id: "67fdfe4b-abd4-4f99-96e0-d1b23270181f", year_code: "2025/2026", name: "Fiscal Year 2025/2026",…}
id
: 
"4b807488-bd6a-49ab-b0e1-0d0f335e9f85"
is_active
: 
true
reviewed_by
: 
"6cf919b4-8dbf-4f8a-8b48-885e1b9fb77c"
status
: 
"under_review"
updated_at
: 
"2026-03-13T12:51:28.241500+03:00"
workflow_plan_id
: 
"d40af701-a4d6-40c1-8bed-629184e86e27"
message
: 
"Audit universe submitted for approval via workflow"
success
: 
true
workflow_plan_id
: 
"d40af701-a4d6-40c1-8bed-629184e86e27"


response:
{
    "success": true,
    "data": {
        "id": "4b807488-bd6a-49ab-b0e1-0d0f335e9f85",
        "description": "Annual Internal Audit Universe for FCC covering all directorates, units, zones, processes, and systems for the 2025/2026 fiscal year",
        "status": "under_review",
        "fiscal_year": {
            "id": "67fdfe4b-abd4-4f99-96e0-d1b23270181f",
            "year_code": "2025/2026",
            "name": "Fiscal Year 2025/2026",
            "start_date": "2025-07-01",
            "end_date": "2026-06-30",
            "is_active": true,
            "created_at": "2026-02-10T13:30:42.916667+03:00",
            "updated_at": "2026-02-10T13:30:42.916679+03:00"
        },
        "reviewed_by": "6cf919b4-8dbf-4f8a-8b48-885e1b9fb77c",
        "approved_by": null,
        "approved_at": null,
        "workflow_plan_id": "d40af701-a4d6-40c1-8bed-629184e86e27",
        "is_active": true,
        "created_at": "2026-03-13T12:51:28.241486+03:00",
        "updated_at": "2026-03-13T12:51:28.241500+03:00"
    },
    "message": "Audit universe submitted for approval via workflow",
    "workflow_plan_id": "d40af701-a4d6-40c1-8bed-629184e86e27"
}

so from here i can see the WO console well
with these details:

its Header:
equest URL
http://localhost:8080/api/v1/workflow/plans/d40af701-a4d6-40c1-8bed-629184e86e27/
Request Method
GET
Status Code
200 OK
Remote Address
[::1]:8080
Referrer Policy
same-origin

respose:
{
    "data": {
        "id": "d40af701-a4d6-40c1-8bed-629184e86e27",
        "workflow_type": "grc",
        "status": "active",
        "created_by": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
        "tags": [],
        "metadata": {
            "status": "draft",
            "context": {
                "applicant_id": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
                "fiscal_year_id": "67fdfe4b-abd4-4f99-96e0-d1b23270181f",
                "audit_universe_id": "4b807488-bd6a-49ab-b0e1-0d0f335e9f85"
            },
            "entity_id": "4b807488-bd6a-49ab-b0e1-0d0f335e9f85",
            "description": "Annual Internal Audit Universe for FCC covering all directorates, units, zones, processes, and systems for the 2025/2026 fiscal year",
            "entity_type": "audit_universe",
            "fiscal_year": "2025/2026",
            "subject_ref": "4b807488-bd6a-49ab-b0e1-0d0f335e9f85",
            "template_code": "grc.audit_universe_approval",
            "entity_detail_path": "/service/grc/audit-universe"
        },
        "stages": [
            {
                "id": "bc9b38b9-1702-4b73-bca7-0c6f0fc998eb",
                "name": "CIA Review",
                "definition_key": "cia_review",
                "order": 1,
                "status": "in_progress",
                "assignees": [],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return",
                        "next_state": "rejected",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "status_on_complete": "approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "breachStrategy": "notify",
                    "durationMinutes": 4320
                },
                "is_locked": false,
                "is_completed": false,
                "is_active": true,
                "user_can_act": false,
                "user_already_acted": false,
                "action_blocked_reason": "You cannot approve your own request",
                "assignee_names": []
            }
        ],
        "tasks": [],
        "user_can_approve": false,
        "user_can_reject": false,
        "action_blocked_reason": "You cannot approve your own request",
        "current_stage": {
            "id": "bc9b38b9-1702-4b73-bca7-0c6f0fc998eb",
            "name": "CIA Review",
            "definition_key": "cia_review",
            "order": 1,
            "status": "in_progress",
            "assignees": [],
            "actions": [
                {
                    "name": "approve",
                    "label": "Approve",
                    "next_state": "completed",
                    "metadata": {}
                },
                {
                    "name": "return",
                    "label": "Return",
                    "next_state": "rejected",
                    "metadata": {}
                }
            ],
            "metadata": {
                "status_on_complete": "approved"
            },
            "form_schema": {},
            "due_at": null,
            "sla": {
                "breachStrategy": "notify",
                "durationMinutes": 4320
            },
            "is_locked": false,
            "is_completed": false,
            "is_active": true,
            "user_can_act": false,
            "user_already_acted": false,
            "action_blocked_reason": "You cannot approve your own request",
            "assignee_names": []
        },
        "is_view_only": false,
        "viewer_context": {
            "is_initiator": true,
            "is_applicant": true,
            "is_assignee": false,
            "is_superuser": false,
            "can_view": true,
            "view_type": "initiator"
        }
    }
}


Workflow Console
Audit Universe

under_review
Open in New Tab

Audit Universe
4b807488-bd6a-49ab-b0e1-0d0f335e9f85
Your Request
View full details
active

Staff
User b5524372...
grc
You are viewing your own request. You can track progress and comments, but cannot approve or take actions on this workflow.
Workflow Progress
Current: CIA Review
1 stages
0 completed
1 in progress
0 pending
●
CIA Review
In Progress
You cannot approve your own request
Current Stage
CIA Review
No assignees
Activity
MS
WorkflowStarted
3m ago
• Mary Simba



now, i loged in as:
John Mbwana

cia@fcc.go.tz


and try to access that:
403, forbiden:
Request URL
http://localhost:8080/api/v1/workflow/plans/d40af701-a4d6-40c1-8bed-629184e86e27/
Request Method
GET
Status Code
403 Forbidden
Remote Address
[::1]:8080

prview:
{detail: "You do not have permission to perform this action."}
detail
: 
"You do not have permission to perform this action."


what is wrong here?
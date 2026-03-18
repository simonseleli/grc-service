meeting logs:

as LA:
i created meeting in Audit Engagement:

{engagement_id: "dfaf71de-682a-48e8-9a49-35126acb1896", meeting_type: "entry",…}
agenda
: 
"Introduction of audit team members and scope of the engagement\nPresentation of audit objectives and methodology\nOverview of key risk areas identified during planning\nDiscussion of audit timeline and key milestones\nLogistics: document requests, staff availability, access requirements\nQuestions from ICT Directorate management"
engagement_id
: 
"dfaf71de-682a-48e8-9a49-35126acb1896"
location
: 
"ICT Directorate Board Room, HQ Building, 3rd Floor"
meeting_type
: 
"entry"
scheduled_date
: 
"2026-03-18T09:23:00"
title
: 
"ICT Audit Entry Conference — March 2026"


response:
{
    "success": true,
    "data": {
        "id": "94f8e15e-9026-4e40-bb43-4242a0b40382",
        "engagement": "dfaf71de-682a-48e8-9a49-35126acb1896",
        "engagement_title": "ICT General Controls Audit 2025/2026",
        "engagement_reference": "ENG-20252026-001",
        "reference_number": "MTG-ENG-20252026-001-ENTRY-001",
        "meeting_type": "entry",
        "meeting_type_display": "Entry Meeting",
        "title": "ICT Audit Entry Conference — March 2026",
        "scheduled_date": "2026-03-18T09:23:00+03:00",
        "actual_date": null,
        "location": "ICT Directorate Board Room, HQ Building, 3rd Floor",
        "attendees": [],
        "agenda": "Introduction of audit team members and scope of the engagement\nPresentation of audit objectives and methodology\nOverview of key risk areas identified during planning\nDiscussion of audit timeline and key milestones\nLogistics: document requests, staff availability, access requirements\nQuestions from ICT Directorate management",
        "minutes": "",
        "key_discussions": "",
        "clarifications": "",
        "agreed_observations": "",
        "action_items": [],
        "status": "scheduled",
        "status_display": "Scheduled",
        "organized_by": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
        "minutes_document_id": null,
        "attendance_document_id": null,
        "notification_sent": false,
        "notification_date": null,
        "draft_report_id": null,
        "is_active": true,
        "created_at": "2026-03-17T21:27:01.762310+03:00",
        "updated_at": "2026-03-17T21:27:01.762335+03:00"
    },
    "message": "Meeting scheduled successfully"
}



i updated prgress and set to in_progress:

i updated the other fields as:
Request URL
http://localhost:8080/api/v1/grc/audit/meetings/94f8e15e-9026-4e40-bb43-4242a0b40382/
Request Method
PATCH
Status Code
200 OK
Remote Address
[::1]:8080
Referrer Policy
strict-origin-when-cross-origin


response:
{
    "success": true,
    "data": {
        "id": "94f8e15e-9026-4e40-bb43-4242a0b40382",
        "engagement": "dfaf71de-682a-48e8-9a49-35126acb1896",
        "engagement_title": "ICT General Controls Audit 2025/2026",
        "engagement_reference": "ENG-20252026-001",
        "reference_number": "MTG-ENG-20252026-001-ENTRY-001",
        "meeting_type": "entry",
        "meeting_type_display": "Entry Meeting",
        "title": "ICT Audit Entry Conference — March 2026",
        "scheduled_date": "2026-03-18T09:23:00+03:00",
        "actual_date": null,
        "location": "ICT Directorate Board Room, HQ Building, 3rd Floor",
        "attendees": [
            {
                "name": "Mary Simba",
                "title": "Lead Auditor",
                "role": "auditor",
                "present": true
            },
            {
                "name": "David Omondi",
                "title": "Audit Team Member",
                "role": "auditee",
                "present": true
            },
            {
                "name": "ICT Director",
                "title": "Director of ICT",
                "role": "auditee",
                "present": true
            },
            {
                "name": "ICT Systems Manager",
                "title": "Systems Manager",
                "role": "auditee",
                "present": true
            }
        ],
        "agenda": "Introduction of audit team members and scope of the engagement\nPresentation of audit objectives and methodology\nOverview of key risk areas identified during planning\nDiscussion of audit timeline and key milestones\nLogistics: document requests, staff availability, access requirements\nQuestions from ICT Directorate management",
        "minutes": "The entry conference was held on 1 March 2026 at 09:00hrs. The Lead Auditor introduced the audit team and presented the audit scope, objectives and methodology. ICT Directorate management acknowledged the audit timeline and committed to providing requested documents within 5 working days. Key logistics were agreed including room allocation and staff availability schedule.",
        "key_discussions": "1. Audit scope confirmed — access controls, change management, backup and recovery in scope.\\n2. ICT Director committed to designating a liaison officer by 3 March 2026.\\n3. Document request list to be submitted by audit team within 2 working days.\\n4. Audit timeline: fieldwork 1–28 March, preliminary findings 5 April.",
        "clarifications": "",
        "agreed_observations": "",
        "action_items": [],
        "status": "in_progress",
        "status_display": "In Progress",
        "organized_by": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
        "minutes_document_id": "3ffc18d6-a7d0-4fb3-a9e8-1f562c4eefe2",
        "attendance_document_id": "6bcda314-8cce-477a-a8fa-eb069311c256",
        "notification_sent": false,
        "notification_date": null,
        "draft_report_id": null,
        "is_active": true,
        "created_at": "2026-03-17T21:27:01.762310+03:00",
        "updated_at": "2026-03-17T21:40:10.943173+03:00"
    }
}




now i updated the meeting to completed as:
Request URL
http://localhost:8080/api/v1/grc/audit/meetings/94f8e15e-9026-4e40-bb43-4242a0b40382/update-status/
Request Method
POST
Status Code
200 OK
Remote Address
[::1]:8080
Referrer Policy
strict-origin-when-cross-origin


response:
{
    "success": true,
    "data": {
        "id": "94f8e15e-9026-4e40-bb43-4242a0b40382",
        "engagement": "dfaf71de-682a-48e8-9a49-35126acb1896",
        "engagement_title": "ICT General Controls Audit 2025/2026",
        "engagement_reference": "ENG-20252026-001",
        "reference_number": "MTG-ENG-20252026-001-ENTRY-001",
        "meeting_type": "entry",
        "meeting_type_display": "Entry Meeting",
        "title": "ICT Audit Entry Conference — March 2026",
        "scheduled_date": "2026-03-18T09:23:00+03:00",
        "actual_date": null,
        "location": "ICT Directorate Board Room, HQ Building, 3rd Floor",
        "attendees": [
            {
                "name": "Mary Simba",
                "role": "auditor",
                "title": "Lead Auditor",
                "present": true
            },
            {
                "name": "David Omondi",
                "role": "auditee",
                "title": "Audit Team Member",
                "present": true
            },
            {
                "name": "ICT Director",
                "role": "auditee",
                "title": "Director of ICT",
                "present": true
            },
            {
                "name": "ICT Systems Manager",
                "role": "auditee",
                "title": "Systems Manager",
                "present": true
            }
        ],
        "agenda": "Introduction of audit team members and scope of the engagement\nPresentation of audit objectives and methodology\nOverview of key risk areas identified during planning\nDiscussion of audit timeline and key milestones\nLogistics: document requests, staff availability, access requirements\nQuestions from ICT Directorate management",
        "minutes": "The entry conference was held on 1 March 2026 at 09:00hrs. The Lead Auditor introduced the audit team and presented the audit scope, objectives and methodology. ICT Directorate management acknowledged the audit timeline and committed to providing requested documents within 5 working days. Key logistics were agreed including room allocation and staff availability schedule.",
        "key_discussions": "1. Audit scope confirmed — access controls, change management, backup and recovery in scope.\\n2. ICT Director committed to designating a liaison officer by 3 March 2026.\\n3. Document request list to be submitted by audit team within 2 working days.\\n4. Audit timeline: fieldwork 1–28 March, preliminary findings 5 April.",
        "clarifications": "",
        "agreed_observations": "",
        "action_items": [],
        "status": "completed",
        "status_display": "Completed",
        "organized_by": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
        "minutes_document_id": "3ffc18d6-a7d0-4fb3-a9e8-1f562c4eefe2",
        "attendance_document_id": "6bcda314-8cce-477a-a8fa-eb069311c256",
        "notification_sent": false,
        "notification_date": null,
        "draft_report_id": null,
        "is_active": true,
        "created_at": "2026-03-17T21:27:01.762310+03:00",
        "updated_at": "2026-03-17T21:42:45.427264+03:00"
    },
    "message": "Meeting status updated from 'in_progress' to 'completed'."
}






grc logs:
fims-grc-service         | User auditor@fcc.go.tz has 23 GRC permissions. First 10: ['grc:audit_dashboard:view', 'grc:audit_declaration:manage', 'grc:audit_declaration:sign', 'grc:audit_engagement:manage', 'grc:audit_finding:manage', 'grc:audit_meeting:manage', 'grc:audit_memo:manage', 'grc:audit_memo:view', 'grc:audit_monitoring:update', 'grc:audit_plan:manage']
fims-grc-service         | JWT validated for user b5524372-f0f7-4cc3-b11f-462d84f0a592 accessing /api/v1/grc/audit/meetings/94f8e15e-9026-4e40-bb43-4242a0b40382/update-status/
fims-grc-service         | Authenticated user b5524372-f0f7-4cc3-b11f-462d84f0a592 via JWT token
fims-grc-service         | Permission granted: user=auditor@fcc.go.tz, permission=grc:audit_meeting:manage
fims-grc-service         | (0.005) SELECT "grc_audit_meeting"."id", "grc_audit_meeting"."created_at", "grc_audit_meeting"."updated_at", "grc_audit_meeting"."created_by", "grc_audit_meeting"."modified_by", "grc_audit_meeting"."is_active", "grc_audit_meeting"."engagement_id", "grc_audit_meeting"."reference_number", "grc_audit_meeting"."meeting_type", "grc_audit_meeting"."title", "grc_audit_meeting"."scheduled_date", "grc_audit_meeting"."actual_date", "grc_audit_meeting"."location", "grc_audit_meeting"."attendees", "grc_audit_meeting"."agenda", "grc_audit_meeting"."minutes", "grc_audit_meeting"."key_discussions", "grc_audit_meeting"."clarifications", "grc_audit_meeting"."agreed_observations", "grc_audit_meeting"."action_items", "grc_audit_meeting"."status", "grc_audit_meeting"."organized_by", "grc_audit_meeting"."minutes_document_id", "grc_audit_meeting"."attendance_document_id", "grc_audit_meeting"."notification_sent", "grc_audit_meeting"."notification_date", "grc_audit_meeting"."draft_report_id", "grc_audit_engagement"."id", "grc_audit_engagement"."created_at", "grc_audit_engagement"."updated_at", "grc_audit_engagement"."created_by", "grc_audit_engagement"."modified_by", "grc_audit_engagement"."is_active", "grc_audit_engagement"."workflow_plan_id", "grc_audit_engagement"."workflow_stage", "grc_audit_engagement"."workflow_stage_id", "grc_audit_engagement"."workflow_started_at", "grc_audit_engagement"."workflow_completed_at", "grc_audit_engagement"."reference_number", "grc_audit_engagement"."audit_plan_id", "grc_audit_engagement"."auditable_entity_id", "grc_audit_engagement"."title", "grc_audit_engagement"."engagement_type", "grc_audit_engagement"."status", "grc_audit_engagement"."lead_auditor", "grc_audit_engagement"."audit_team", "grc_audit_engagement"."scope", "grc_audit_engagement"."objectives", "grc_audit_engagement"."methodology", "grc_audit_engagement"."planned_start_date", "grc_audit_engagement"."planned_end_date", "grc_audit_engagement"."actual_start_date", "grc_audit_engagement"."actual_end_date", "grc_audit_engagement"."entry_meeting_date", "grc_audit_engagement"."exit_meeting_date" FROM "grc_audit_meeting" INNER JOIN "grc_audit_engagement" ON ("grc_audit_meeting"."engagement_id" = "grc_audit_engagement"."id") WHERE "grc_audit_meeting"."id" = '94f8e15e-9026-4e40-bb43-4242a0b40382'::uuid LIMIT 21; args=(UUID('94f8e15e-9026-4e40-bb43-4242a0b40382'),); alias=default
fims-grc-service         | (0.000) BEGIN; args=None; alias=default
fims-grc-service         | (0.001) UPDATE "grc_audit_meeting" SET "updated_at" = '2026-03-17T18:42:45.427264+00:00'::timestamptz, "status" = 'completed' WHERE "grc_audit_meeting"."id" = '94f8e15e-9026-4e40-bb43-4242a0b40382'::uuid; args=(datetime.datetime(2026, 3, 17, 18, 42, 45, 427264, tzinfo=datetime.timezone.utc), 'completed', UUID('94f8e15e-9026-4e40-bb43-4242a0b40382')); alias=default
fims-grc-service         | (0.008) COMMIT; args=None; alias=default
fims-grc-service         | User auditor@fcc.go.tz has 23 GRC permissions. First 10: ['grc:audit_dashboard:view', 'grc:audit_declaration:manage', 'grc:audit_declaration:sign', 'grc:audit_engagement:manage', 'grc:audit_finding:manage', 'grc:audit_meeting:manage', 'grc:audit_memo:manage', 'grc:audit_memo:view', 'grc:audit_monitoring:update', 'grc:audit_plan:manage']
fims-grc-service         | JWT validated for user b5524372-f0f7-4cc3-b11f-462d84f0a592 accessing /api/v1/grc/audit/meetings/
fims-grc-service         | Authenticated user b5524372-f0f7-4cc3-b11f-462d84f0a592 via JWT token
fims-grc-service         | Permission denied: user=auditor@fcc.go.tz, required=grc:audit_meeting:view, available=['grc:audit_dashboard:view', 'grc:audit_declaration:manage', 'grc:audit_declaration:sign', 'grc:audit_engagement:manage', 'grc:audit_finding:manage', 'grc:audit_meeting:manage', 'grc:audit_memo:manage', 'grc:audit_memo:view', 'grc:audit_monitoring:update', 'grc:audit_plan:manage']...
fims-grc-service         | Permission granted: user=auditor@fcc.go.tz, permission=grc:audit_meeting:manage
fims-grc-service         | (0.002) SELECT COUNT(*) AS "__count" FROM "grc_audit_meeting"; args=(); alias=default
fims-grc-service         | (0.004) SELECT "grc_audit_meeting"."id", "grc_audit_meeting"."created_at", "grc_audit_meeting"."updated_at", "grc_audit_meeting"."created_by", "grc_audit_meeting"."modified_by", "grc_audit_meeting"."is_active", "grc_audit_meeting"."engagement_id", "grc_audit_meeting"."reference_number", "grc_audit_meeting"."meeting_type", "grc_audit_meeting"."title", "grc_audit_meeting"."scheduled_date", "grc_audit_meeting"."actual_date", "grc_audit_meeting"."location", "grc_audit_meeting"."attendees", "grc_audit_meeting"."agenda", "grc_audit_meeting"."minutes", "grc_audit_meeting"."key_discussions", "grc_audit_meeting"."clarifications", "grc_audit_meeting"."agreed_observations", "grc_audit_meeting"."action_items", "grc_audit_meeting"."status", "grc_audit_meeting"."organized_by", "grc_audit_meeting"."minutes_document_id", "grc_audit_meeting"."attendance_document_id", "grc_audit_meeting"."notification_sent", "grc_audit_meeting"."notification_date", "grc_audit_meeting"."draft_report_id", "grc_audit_engagement"."id", "grc_audit_engagement"."created_at", "grc_audit_engagement"."updated_at", "grc_audit_engagement"."created_by", "grc_audit_engagement"."modified_by", "grc_audit_engagement"."is_active", "grc_audit_engagement"."workflow_plan_id", "grc_audit_engagement"."workflow_stage", "grc_audit_engagement"."workflow_stage_id", "grc_audit_engagement"."workflow_started_at", "grc_audit_engagement"."workflow_completed_at", "grc_audit_engagement"."reference_number", "grc_audit_engagement"."audit_plan_id", "grc_audit_engagement"."auditable_entity_id", "grc_audit_engagement"."title", "grc_audit_engagement"."engagement_type", "grc_audit_engagement"."status", "grc_audit_engagement"."lead_auditor", "grc_audit_engagement"."audit_team", "grc_audit_engagement"."scope", "grc_audit_engagement"."objectives", "grc_audit_engagement"."methodology", "grc_audit_engagement"."planned_start_date", "grc_audit_engagement"."planned_end_date", "grc_audit_engagement"."actual_start_date", "grc_audit_engagement"."actual_end_date", "grc_audit_engagement"."entry_meeting_date", "grc_audit_engagement"."exit_meeting_date" FROM "grc_audit_meeting" INNER JOIN "grc_audit_engagement" ON ("grc_audit_meeting"."engagement_id" = "grc_audit_engagement"."id") ORDER BY "grc_audit_meeting"."scheduled_date" DESC LIMIT 20; args=(); alias=default
^C^Csimons@IPS-DEV001:~/Coding/FIMS/grc-service$ 



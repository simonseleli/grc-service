Part A:
as John Mbwana

cia@fcc.go.tz

now, i approve as:

http://localhost:3001/service/grc/audit-universe/477c2087-95bb-410f-b04e-578edfa842fe


Request URL
http://localhost:8080/api/v1/workflow/plans/099e48ba-e475-4ef9-97d8-ab14db38f713/stages/3d989f40-319e-45c3-8101-b34e0d56b0b6/actions/
Request Method
POST
Status Code
200 OK
Remote Address
[::1]:8080
Referrer Policy
same-origin

response

{
    "data": {
        "plan": {
            "id": "099e48ba-e475-4ef9-97d8-ab14db38f713",
            "workflow_type": "grc",
            "status": "completed",
            "created_by": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
            "tags": [],
            "metadata": {
                "status": "draft",
                "context": {
                    "applicant_id": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
                    "fiscal_year_id": "67fdfe4b-abd4-4f99-96e0-d1b23270181f",
                    "audit_universe_id": "477c2087-95bb-410f-b04e-578edfa842fe"
                },
                "entity_id": "477c2087-95bb-410f-b04e-578edfa842fe",
                "description": "Annual Internal Audit Universe for FCC covering all directorates, units, zones, processes, and systems for the 2025/2026 fiscal year",
                "entity_type": "audit_universe",
                "fiscal_year": "2025/2026",
                "subject_ref": "477c2087-95bb-410f-b04e-578edfa842fe",
                "template_code": "grc.audit_universe_approval",
                "entity_detail_path": "/service/grc/audit-universe"
            },
            "stages": [
                {
                    "id": "3d989f40-319e-45c3-8101-b34e0d56b0b6",
                    "name": "CIA Review",
                    "definition_key": "cia_review",
                    "order": 1,
                    "status": "completed",
                    "assignees": [
                        "role:chief_internal_auditor"
                    ],
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
                        "comments": [
                            {
                                "actor": "6cf919b4-8dbf-4f8a-8b48-885e1b9fb77c",
                                "comment": "Annual Internal Audit Universe for FCC covering all departments, regional offices, operational processes, and supporting information systems for the 2026/2027 fiscal year"
                            }
                        ],
                        "status_on_complete": "approved"
                    },
                    "form_schema": {},
                    "due_at": null,
                    "sla": {
                        "breachStrategy": "notify",
                        "durationMinutes": 4320
                    }
                }
            ],
            "tasks": []
        },
        "stage": {
            "id": "3d989f40-319e-45c3-8101-b34e0d56b0b6",
            "name": "CIA Review",
            "definition_key": "cia_review",
            "order": 1,
            "status": "completed",
            "assignees": [
                "role:chief_internal_auditor"
            ],
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
                "comments": [
                    {
                        "actor": "6cf919b4-8dbf-4f8a-8b48-885e1b9fb77c",
                        "comment": "Annual Internal Audit Universe for FCC covering all departments, regional offices, operational processes, and supporting information systems for the 2026/2027 fiscal year"
                    }
                ],
                "status_on_complete": "approved"
            },
            "form_schema": {},
            "due_at": null,
            "sla": {
                "breachStrategy": "notify",
                "durationMinutes": 4320
            }
        }
    }
}



but now, when, when i click the button View full details, it real takes me to the new page that shows almost the same things, 
as
http://localhost:3001/service/grc/audit-universe/477c2087-95bb-410f-b04e-578edfa842fe

{
    "data": {
        "id": "099e48ba-e475-4ef9-97d8-ab14db38f713",
        "workflow_type": "grc",
        "status": "completed",
        "created_by": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
        "tags": [],
        "metadata": {
            "status": "draft",
            "context": {
                "applicant_id": "b5524372-f0f7-4cc3-b11f-462d84f0a592",
                "fiscal_year_id": "67fdfe4b-abd4-4f99-96e0-d1b23270181f",
                "audit_universe_id": "477c2087-95bb-410f-b04e-578edfa842fe"
            },
            "entity_id": "477c2087-95bb-410f-b04e-578edfa842fe",
            "description": "Annual Internal Audit Universe for FCC covering all directorates, units, zones, processes, and systems for the 2025/2026 fiscal year",
            "entity_type": "audit_universe",
            "fiscal_year": "2025/2026",
            "subject_ref": "477c2087-95bb-410f-b04e-578edfa842fe",
            "template_code": "grc.audit_universe_approval",
            "entity_detail_path": "/service/grc/audit-universe"
        },
        "stages": [
            {
                "id": "3d989f40-319e-45c3-8101-b34e0d56b0b6",
                "name": "CIA Review",
                "definition_key": "cia_review",
                "order": 1,
                "status": "completed",
                "assignees": [
                    "role:chief_internal_auditor"
                ],
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
                    "comments": [
                        {
                            "actor": "6cf919b4-8dbf-4f8a-8b48-885e1b9fb77c",
                            "comment": "Annual Internal Audit Universe for FCC covering all departments, regional offices, operational processes, and supporting information systems for the 2026/2027 fiscal year"
                        }
                    ],
                    "status_on_complete": "approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "breachStrategy": "notify",
                    "durationMinutes": 4320
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Chief Internal Auditor"
                ]
            }
        ],
        "tasks": [],
        "user_can_approve": false,
        "user_can_reject": false,
        "action_blocked_reason": null,
        "current_stage": null,
        "is_view_only": true,
        "viewer_context": {
            "is_initiator": false,
            "is_applicant": false,
            "is_assignee": true,
            "is_superuser": false,
            "can_view": true,
            "view_type": "assignee"
        }
    }
}




Part A:
But i tried to the one from my senior hosted via his tunnel:

as admin:

there is the deference when you are in WO console and when you click the click to viw details,
see, 

http://fcc-staff.tunnel.ictpack.net/service/work-orchestration/console/f743df02-60c0-4422-8276-a5d4e772cd47

Request URL
http://fcc-staff.tunnel.ictpack.net/api/v1/workflow/plans/f743df02-60c0-4422-8276-a5d4e772cd47/
Request Method
GET
Status Code
200 OK
Remote Address
102.214.30.32:80


response:
{
    "data": {
        "id": "f743df02-60c0-4422-8276-a5d4e772cd47",
        "workflow_type": "corporate_hr",
        "status": "completed",
        "created_by": "acdaa8ce-03b2-47f1-84b2-d9f67dc5c2cd",
        "tags": [],
        "metadata": {
            "context": {
                "hod_id": "b67dac8b-0830-4a99-9be6-2f23c3b88989",
                "entity_id": "cfd50e95-7924-4cc5-9655-20361911a217",
                "leave_type": "LT-ANNUAL",
                "entity_type": "leave_application",
                "applicant_id": "b636ca93-00d8-4352-a873-97678a9bde8c",
                "department_id": null,
                "is_paid_leave": true,
                "supervisor_id": "b67dac8b-0830-4a99-9be6-2f23c3b88989",
                "applicant_name": "Dennis Mwambungu",
                "days_requested": 9,
                "department_name": null,
                "line_manager_id": "b67dac8b-0830-4a99-9be6-2f23c3b88989",
                "request_leave_passage": false,
                "request_salary_advance": false
            },
            "end_date": "2026-04-14",
            "entity_id": "cfd50e95-7924-4cc5-9655-20361911a217",
            "leave_type": "Annual Leave",
            "start_date": "2026-04-06",
            "entity_type": "leave_application",
            "subject_ref": "cfd50e95-7924-4cc5-9655-20361911a217",
            "applicant_id": "b636ca93-00d8-4352-a873-97678a9bde8c",
            "template_code": "corporate.leave_application",
            "applicant_name": "Dennis Mwambungu",
            "days_requested": 9,
            "application_number": "LV-42DE22D6",
            "entity_detail_path": "/service/corporate/leave-applications"
        },
        "stages": [
            {
                "id": "006f40bb-4f71-4b1d-b1b0-d74303dd5a8d",
                "name": "Head/Manager Approval",
                "definition_key": "leave_head_approval",
                "order": 1,
                "status": "completed",
                "assignees": [
                    "b67dac8b-0830-4a99-9be6-2f23c3b88989"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "Comments"
                        }
                    ],
                    "status_on_complete": "hod_approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "breachStrategy": "notify",
                    "durationMinutes": 1440
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Lucia Mwambene"
                ]
            },
            {
                "id": "d43ded9e-fbf9-47cd-8d58-50d002da1f1b",
                "name": "HR Verification",
                "definition_key": "leave_hr_verification",
                "order": 2,
                "status": "completed",
                "assignees": [
                    "role:hr_officer"
                ],
                "actions": [
                    {
                        "name": "verify",
                        "label": "Verify & Forward",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "badilisha dates"
                        },
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "ssdsdsds"
                        }
                    ],
                    "status_on_complete": "hr_verified"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 480
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": false,
                "action_blocked_reason": null,
                "assignee_names": [
                    "Hr Officer"
                ]
            },
            {
                "id": "bf69d88a-ffe8-4286-918b-3413663bdcb7",
                "name": "HRAM Review",
                "definition_key": "leave_hram_review",
                "order": 3,
                "status": "completed",
                "assignees": [
                    "role:hr_admin_manager"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve for Payment",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "dsdsdsdsdsd"
                        }
                    ],
                    "status_on_complete": "hram_approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 720
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Hr Admin Manager"
                ]
            },
            {
                "id": "7765d050-5016-40dc-84a1-4c70cc0347d5",
                "name": "Director/DCS Approval",
                "definition_key": "leave_director_approval",
                "order": 4,
                "status": "completed",
                "assignees": [
                    "role:director_corporate_services"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "wsdsdsdsdd"
                        }
                    ],
                    "status_on_complete": "director_approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 1440
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Director Corporate Services"
                ]
            },
            {
                "id": "a8e4133b-10b5-48a6-b11f-6e6ec7f83870",
                "name": "DG Approval",
                "definition_key": "leave_dg_approval",
                "order": 5,
                "status": "completed",
                "assignees": [
                    "role:director_general"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "dsdsdsdsd"
                        }
                    ],
                    "condition": "{{is_paid_leave}}",
                    "conditional": true,
                    "status_on_complete": "approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 1440
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Director General"
                ]
            }
        ],
        "tasks": [],
        "user_can_approve": false,
        "user_can_reject": false,
        "action_blocked_reason": null,
        "current_stage": null,
        "is_view_only": true,
        "viewer_context": {
            "is_initiator": false,
            "is_applicant": false,
            "is_assignee": false,
            "is_superuser": true,
            "can_view": true,
            "view_type": "admin"
        }
    }
}




now,, when i click View full details


it takes me to: http://fcc-staff.tunnel.ictpack.net/service/corporate/leave-applications/cfd50e95-7924-4cc5-9655-20361911a217

and its contests are so many:


{
    "data": {
        "id": "f743df02-60c0-4422-8276-a5d4e772cd47",
        "workflow_type": "corporate_hr",
        "status": "completed",
        "created_by": "acdaa8ce-03b2-47f1-84b2-d9f67dc5c2cd",
        "tags": [],
        "metadata": {
            "context": {
                "hod_id": "b67dac8b-0830-4a99-9be6-2f23c3b88989",
                "entity_id": "cfd50e95-7924-4cc5-9655-20361911a217",
                "leave_type": "LT-ANNUAL",
                "entity_type": "leave_application",
                "applicant_id": "b636ca93-00d8-4352-a873-97678a9bde8c",
                "department_id": null,
                "is_paid_leave": true,
                "supervisor_id": "b67dac8b-0830-4a99-9be6-2f23c3b88989",
                "applicant_name": "Dennis Mwambungu",
                "days_requested": 9,
                "department_name": null,
                "line_manager_id": "b67dac8b-0830-4a99-9be6-2f23c3b88989",
                "request_leave_passage": false,
                "request_salary_advance": false
            },
            "end_date": "2026-04-14",
            "entity_id": "cfd50e95-7924-4cc5-9655-20361911a217",
            "leave_type": "Annual Leave",
            "start_date": "2026-04-06",
            "entity_type": "leave_application",
            "subject_ref": "cfd50e95-7924-4cc5-9655-20361911a217",
            "applicant_id": "b636ca93-00d8-4352-a873-97678a9bde8c",
            "template_code": "corporate.leave_application",
            "applicant_name": "Dennis Mwambungu",
            "days_requested": 9,
            "application_number": "LV-42DE22D6",
            "entity_detail_path": "/service/corporate/leave-applications"
        },
        "stages": [
            {
                "id": "006f40bb-4f71-4b1d-b1b0-d74303dd5a8d",
                "name": "Head/Manager Approval",
                "definition_key": "leave_head_approval",
                "order": 1,
                "status": "completed",
                "assignees": [
                    "b67dac8b-0830-4a99-9be6-2f23c3b88989"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "Comments"
                        }
                    ],
                    "status_on_complete": "hod_approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "breachStrategy": "notify",
                    "durationMinutes": 1440
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Lucia Mwambene"
                ]
            },
            {
                "id": "d43ded9e-fbf9-47cd-8d58-50d002da1f1b",
                "name": "HR Verification",
                "definition_key": "leave_hr_verification",
                "order": 2,
                "status": "completed",
                "assignees": [
                    "role:hr_officer"
                ],
                "actions": [
                    {
                        "name": "verify",
                        "label": "Verify & Forward",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "badilisha dates"
                        },
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "ssdsdsds"
                        }
                    ],
                    "status_on_complete": "hr_verified"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 480
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": false,
                "action_blocked_reason": null,
                "assignee_names": [
                    "Hr Officer"
                ]
            },
            {
                "id": "bf69d88a-ffe8-4286-918b-3413663bdcb7",
                "name": "HRAM Review",
                "definition_key": "leave_hram_review",
                "order": 3,
                "status": "completed",
                "assignees": [
                    "role:hr_admin_manager"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve for Payment",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "dsdsdsdsdsd"
                        }
                    ],
                    "status_on_complete": "hram_approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 720
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Hr Admin Manager"
                ]
            },
            {
                "id": "7765d050-5016-40dc-84a1-4c70cc0347d5",
                "name": "Director/DCS Approval",
                "definition_key": "leave_director_approval",
                "order": 4,
                "status": "completed",
                "assignees": [
                    "role:director_corporate_services"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "wsdsdsdsdd"
                        }
                    ],
                    "status_on_complete": "director_approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 1440
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Director Corporate Services"
                ]
            },
            {
                "id": "a8e4133b-10b5-48a6-b11f-6e6ec7f83870",
                "name": "DG Approval",
                "definition_key": "leave_dg_approval",
                "order": 5,
                "status": "completed",
                "assignees": [
                    "role:director_general"
                ],
                "actions": [
                    {
                        "name": "approve",
                        "label": "Approve",
                        "next_state": "completed",
                        "metadata": {}
                    },
                    {
                        "name": "reject",
                        "label": "Reject",
                        "next_state": "rejected",
                        "metadata": {}
                    },
                    {
                        "name": "return",
                        "label": "Return for Amendment",
                        "next_state": "returned",
                        "metadata": {}
                    }
                ],
                "metadata": {
                    "comments": [
                        {
                            "actor": "fda6573b-2335-4c2f-a176-f969662998f6",
                            "comment": "dsdsdsdsd"
                        }
                    ],
                    "condition": "{{is_paid_leave}}",
                    "conditional": true,
                    "status_on_complete": "approved"
                },
                "form_schema": {},
                "due_at": null,
                "sla": {
                    "durationMinutes": 1440
                },
                "is_locked": false,
                "is_completed": true,
                "is_active": false,
                "user_can_act": false,
                "user_already_acted": true,
                "action_blocked_reason": "You have already acted on this stage",
                "assignee_names": [
                    "Director General"
                ]
            }
        ],
        "tasks": [],
        "user_can_approve": false,
        "user_can_reject": false,
        "action_blocked_reason": null,
        "current_stage": null,
        "is_view_only": true,
        "viewer_context": {
            "is_initiator": false,
            "is_applicant": false,
            "is_assignee": false,
            "is_superuser": true,
            "can_view": true,
            "view_type": "admin"
        }
    }
}


so, i can notice that, the click to view details, it take me to the respective service to see the details indeed,
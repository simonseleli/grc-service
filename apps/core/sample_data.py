from __future__ import annotations

from datetime import date

AUDIT_PLANS = [
    {
        "id": "rbiap-2024-001",
        "title": "FY 2024/2025 Risk Based Internal Audit Plan",
        "status": "Approved",
        "createdAt": "2024-06-15",
        "updatedAt": "2024-07-10",
        "fiscalYear": "2024/2025",
        "auditUniverse": "All Directorates, Units and Zones",
        "riskAssessment": "Completed",
        "approvedBy": "Audit Committee",
        "planType": "Annual",
        "priorityAreas": [
            "Procurement & Supply Chain",
            "Financial Management",
            "IT Security",
        ],
    },
    {
        "id": "rbiap-2023-001",
        "title": "FY 2023/2024 Risk Based Internal Audit Plan",
        "status": "Completed",
        "createdAt": "2023-06-20",
        "updatedAt": "2024-06-30",
        "fiscalYear": "2023/2024",
        "auditUniverse": "All Directorates and Units",
        "riskAssessment": "Completed",
        "approvedBy": "Audit Committee",
        "planType": "Annual",
        "priorityAreas": [
            "Human Capital",
            "Compliance Monitoring",
        ],
    },
]

AUDIT_ENGAGEMENTS = [
    {
        "id": "eng-2024-010",
        "title": "IT Systems Security Audit",
        "status": "Ongoing",
        "createdAt": "2024-10-01",
        "updatedAt": "2024-10-20",
        "auditableArea": "Information Technology",
        "leadAuditor": "James Omondi",
        "auditTeam": "James Omondi, Sarah Kimani, David Oloo",
        "entryMeetingDate": "2024-10-05",
        "exitMeetingDate": "2024-11-15",
        "findings": 8,
        "reportStatus": "Draft",
        "engagementDate": "2024-09-15",
        "auditScope": "Review cybersecurity posture and IAM controls",
    },
    {
        "id": "eng-2024-006",
        "title": "Human Resource Management Audit",
        "status": "Completed",
        "createdAt": "2024-07-10",
        "updatedAt": "2024-09-25",
        "auditableArea": "Human Resources",
        "leadAuditor": "Lucy Wambui",
        "auditTeam": "Lucy Wambui, Peter Kamau, Grace Wanjiku",
        "entryMeetingDate": "2024-07-15",
        "exitMeetingDate": "2024-09-10",
        "findings": 5,
        "reportStatus": "Final",
        "engagementDate": "2024-04-20",
        "auditScope": "Review recruitment, payroll, and compliance controls",
    },
]

AUDIT_MONITORING = [
    {
        "id": "mon-2024-003",
        "title": "Procurement Policy Compliance",
        "status": "Implemented",
        "createdAt": "2024-06-15",
        "updatedAt": "2024-09-30",
        "auditReference": "IA-Q2-2024-003",
        "recommendation": "Strengthen procurement authorization controls",
        "auditee": "Procurement Department",
        "implementationDeadline": "2024-09-30",
        "implementationStatus": "Completed",
        "evidenceProvided": "Updated procurement manual and training records",
    },
    {
        "id": "mon-2024-007",
        "title": "Asset Register Update",
        "status": "In Progress",
        "createdAt": "2024-04-20",
        "updatedAt": "2024-10-15",
        "auditReference": "IA-Q1-2024-007",
        "recommendation": "Complete physical verification and update asset register",
        "auditee": "Finance Department",
        "implementationDeadline": "2024-11-30",
        "implementationStatus": "Ongoing",
        "evidenceProvided": "Partial verification completed - 60%",
    },
]

LAST_REFRESH = date.today().isoformat()

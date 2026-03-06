"""
Event types constants for GRC Service
Defines all event types used for Governance, Risk & Compliance
"""

# GRC Audit Engagement Events
AUDIT_ENGAGEMENT_EVENTS = {
    'ENGAGEMENT_CREATED': 'grc.audit.engagement.created',
    'ENGAGEMENT_UPDATED': 'grc.audit.engagement.updated',
    'ENGAGEMENT_STARTED': 'grc.audit.engagement.started',
    'ENGAGEMENT_COMPLETED': 'grc.audit.engagement.completed',
    'ENGAGEMENT_CANCELLED': 'grc.audit.engagement.cancelled',
}

# GRC Working Paper Events
WORKING_PAPER_EVENTS = {
    'WORKING_PAPER_CREATED': 'grc.working.paper.created',
    'WORKING_PAPER_UPDATED': 'grc.working.paper.updated',
    'WORKING_PAPER_SUBMITTED': 'grc.working.paper.submitted',
    'WORKING_PAPER_REVIEWED': 'grc.working.paper.reviewed',
    'WORKING_PAPER_APPROVED': 'grc.working.paper.approved',
    'WORKING_PAPER_REJECTED': 'grc.working.paper.rejected',
}

# GRC Audit Finding Events
AUDIT_FINDING_EVENTS = {
    'FINDING_CREATED': 'grc.audit.finding.created',
    'FINDING_UPDATED': 'grc.audit.finding.updated',
    'FINDING_ESCALATED': 'grc.audit.finding.escalated',
    'FINDING_RESOLVED': 'grc.audit.finding.resolved',
    'FINDING_CLOSED': 'grc.audit.finding.closed',
    # GAP 12 — Risk Management integration (SRS Req 41)
    # Published when an audit report is formally approved by CIA.
    # Consumed by the Risk Management System (Phase 2) to create org risk entries.
    'FINDING_FINALIZED': 'grc.audit.finding.finalized',
    # Semantic alias: same event, explicitly named for clarity in audit report approval flow
    'FINDING_APPROVED': 'grc.audit.finding.approved',
}

# GRC Audit Plan Events
AUDIT_PLAN_EVENTS = {
    'PLAN_CREATED': 'grc.audit.plan.created',
    'PLAN_UPDATED': 'grc.audit.plan.updated',
    'PLAN_APPROVED': 'grc.audit.plan.approved',
    'PLAN_PUBLISHED': 'grc.audit.plan.published',
}

# GRC Risk Assessment Events
RISK_ASSESSMENT_EVENTS = {
    'RISK_IDENTIFIED': 'grc.risk.identified',
    'RISK_ASSESSED': 'grc.risk.assessed',
    'RISK_MITIGATED': 'grc.risk.mitigated',
    'RISK_ESCALATED': 'grc.risk.escalated',
}

# GRC Audit Report Events
AUDIT_REPORT_EVENTS = {
    'REPORT_GENERATED': 'grc.audit.report.generated',
    'REPORT_PUBLISHED': 'grc.audit.report.published',
    'REPORT_APPROVED': 'grc.audit.report.approved',
}

# GRC Audit Meeting Events
AUDIT_MEETING_EVENTS = {
    'MEETING_SCHEDULED': 'grc.audit.meeting.scheduled',
    'MEETING_STARTED': 'grc.audit.meeting.started',
    'MEETING_COMPLETED': 'grc.audit.meeting.completed',
    'MEETING_CANCELLED': 'grc.audit.meeting.cancelled',
}

# GRC Quarterly Audit Report Events
QUARTERLY_REPORT_EVENTS = {
    'QUARTERLY_REPORT_CREATED':   'grc.audit.quarterly_report.created',
    'QUARTERLY_REPORT_UPDATED':   'grc.audit.quarterly_report.updated',
    'QUARTERLY_REPORT_APPROVED':  'grc.audit.quarterly_report.approved',
    'QUARTERLY_REPORT_SUBMITTED': 'grc.audit.quarterly_report.submitted',
}

# GRC Audit Memo Events (GAP 1)
AUDIT_MEMO_EVENTS = {
    'MEMO_CREATED': 'grc.audit.memo.created',
    'MEMO_UPDATED': 'grc.audit.memo.updated',
    'MEMO_SUBMITTED': 'grc.audit.memo.submitted',
    'MEMO_APPROVED': 'grc.audit.memo.approved',
    'MEMO_TRANSMITTED': 'grc.audit.memo.transmitted',
}

# GRC Declaration of Independence Events (GAP 2)
DECLARATION_EVENTS = {
    'DECLARATION_CREATED': 'grc.audit.declaration.created',
    'DECLARATION_SIGNED': 'grc.audit.declaration.signed',
}

# GRC Audit Survey Events (GAP 3)
AUDIT_SURVEY_EVENTS = {
    'SURVEY_CREATED': 'grc.audit.survey.created',
    'SURVEY_COMPLETED': 'grc.audit.survey.completed',
}

# GRC Risk Control Matrix Events (GAP 4)
RCM_EVENTS = {
    'RCM_CREATED': 'grc.audit.rcm.created',
    'RCM_SUBMITTED': 'grc.audit.rcm.submitted',
    'RCM_APPROVED': 'grc.audit.rcm.approved',
}

# GRC Audit Program Events (GAP 5)
AUDIT_PROGRAM_EVENTS = {
    'PROGRAM_CREATED': 'grc.audit.program.created',
    'PROGRAM_SUBMITTED': 'grc.audit.program.submitted',
    'PROGRAM_APPROVED': 'grc.audit.program.approved',
}

# All GRC event types combined
ALL_GRC_EVENT_TYPES = {
    **AUDIT_ENGAGEMENT_EVENTS,
    **WORKING_PAPER_EVENTS,
    **AUDIT_FINDING_EVENTS,
    **AUDIT_PLAN_EVENTS,
    **RISK_ASSESSMENT_EVENTS,
    **AUDIT_REPORT_EVENTS,
    **AUDIT_MEETING_EVENTS,
    **QUARTERLY_REPORT_EVENTS,
    **AUDIT_MEMO_EVENTS,
    **DECLARATION_EVENTS,
    **AUDIT_SURVEY_EVENTS,
    **RCM_EVENTS,
    **AUDIT_PROGRAM_EVENTS,
}

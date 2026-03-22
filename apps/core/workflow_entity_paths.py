"""
Maps GRC workflow entity types to frontend detail paths (FIMS pattern)
"""
ENTITY_DETAIL_PATHS = {
    'working_paper':    '/service/grc/working-papers',
    'audit_universe':   '/service/grc/audit-universe',
    'audit_plan':       '/service/grc/audit-plans',
    'audit_engagement': '/service/grc/engagements',
    'audit_report':     '/service/grc/reports',
    # SRS Gap entities
    'audit_memo':       '/service/grc/audit-memos',
    'audit_program':    '/service/grc/audit-programs',
    # P2-GAP 1
    'engagement_notification': '/service/grc/engagement-notifications',
    # P2-GAP 2
    'quarterly_audit_report':  '/service/grc/quarterly-reports',
    # Legal Module
    'meeting':              '/service/grc/legal/meetings/{entity_id}',
    'minutes':              '/service/grc/legal/meetings/{entity_id}/minutes',
    'case_defendant':       '/service/grc/legal/cases/defendant/{entity_id}',
    'case_plaintiff':       '/service/grc/legal/cases/plaintiff/{entity_id}',
    'filing_defendant':     '/service/grc/legal/cases/defendant/{entity_id}/filings',
    'filing_plaintiff':     '/service/grc/legal/cases/plaintiff/{entity_id}/filings',
    'settlement_defendant': '/service/grc/legal/cases/defendant/{entity_id}/settlements',
    'settlement_plaintiff': '/service/grc/legal/cases/plaintiff/{entity_id}/settlements',
    'judgment_defendant':   '/service/grc/legal/cases/defendant/{entity_id}/judgments',
    'judgment_plaintiff':   '/service/grc/legal/cases/plaintiff/{entity_id}/judgments',
    # Risk Management & Quality Assurance Module
    'risk_champion_appointment':    '/service/grc/risk/champions',
    'departmental_risk_register':   '/service/grc/risk/dept-registers',
    'institutional_risk_register':  '/service/grc/risk/institutional-registers',
    'risk_treatment_action_plan':   '/service/grc/risk/rtap',
    'quarterly_performance_report': '/service/grc/risk/quarterly-reports',
    'quality_auditor_appointment':  '/service/grc/risk/quality-auditors',
    'qms_audit_program':            '/service/grc/risk/qms-programs',
    'qms_audit_plan':               '/service/grc/risk/qms-plans',
}

def get_entity_detail_path(entity_type: str):
    return ENTITY_DETAIL_PATHS.get(entity_type)

def add_entity_detail_path_to_metadata(metadata: dict, entity_type: str) -> dict:
    path = get_entity_detail_path(entity_type)
    if path:
        metadata = {**metadata, 'entity_detail_path': path}
    return metadata

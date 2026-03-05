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
}

def get_entity_detail_path(entity_type: str):
    return ENTITY_DETAIL_PATHS.get(entity_type)

def add_entity_detail_path_to_metadata(metadata: dict, entity_type: str) -> dict:
    path = get_entity_detail_path(entity_type)
    if path:
        metadata['entity_detail_path'] = path
    return metadata

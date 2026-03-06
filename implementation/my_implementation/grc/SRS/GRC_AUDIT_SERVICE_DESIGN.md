# GRC Audit Service - System Design Document

## 1. Executive Summary

This document outlines the system design for the **GRC (Governance, Risk, and Compliance) Service** for the FCC (Free Competition Commission) FIMS platform, starting with the **Internal Audit Module**. The service follows the established microservices architecture patterns used across other FIMS services (IAM, Document Records, Work Orchestration).

### 1.1 Scope

The GRC Service encompasses three main modules:
1. **Internal Audit System** (Phase 1 - Current Focus)
2. **Risk Management System** (Phase 2)
3. **Legal Services Management** (Phase 3)

This document focuses on Phase 1: Internal Audit System implementation.

---

## 2. Architecture Overview

### 2.1 Microservices Integration

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  API Gateway                                    │
│                            (nginx + rate limiting)                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│  IAM Service  │◄────────────►│  GRC Service  │◄────────────►│  Document     │
│   (Auth &     │  JWT/Kafka   │   (Audit,     │  REST/Kafka  │  Records      │
│  Permissions) │              │  Risk, Legal) │              │  Service      │
└───────────────┘              └───────────────┘              └───────────────┘
                                        │
                                        │ REST/Kafka
                                        ▼
                              ┌───────────────────┐
                              │ Work Orchestration│
                              │     Service       │
                              │ (Workflows/Tasks) │
                              └───────────────────┘
```

### 2.2 Technology Stack

Following the established FIMS patterns:

---------------------------------------------------------------------------
| Component                | Technology                                   |
|--------------------------|----------------------------------------------|
| **Backend Framework**    | Django 4.2.x + Django REST Framework 3.14.x  |
| **Database**             | PostgreSQL 15                                |
| **Cache**                | Redis 7                                      |
| **Message Broker**       | Apache Kafka (Confluent)                     |
| **Task Queue**           | Celery + Redis                               |
| **API Documentation**    | drf-spectacular                              |
| **Authentication**       | JWT (via IAM Service)                        |
| **Containerization**     | Docker + Docker Compose                      |
---------------------------------------------------------------------------

---

## 3. Internal Audit Module - Domain Model

### 3.1 Configuration Management & Lookup Tables

**Key Design Decision:** Based on supervisor feedback, the system uses configurable lookup tables instead of free-text fields for standardization and analytics.

#### 3.1.1 Core Configuration Entities

**Fiscal Year & Quarter Management:**

---------------------------------------------------------------------------------------
| Entity: FiscalYear                                                                  |
|---------------------------------------------------------------------------------------|
| Field                  | Type       | Description                                  |
|------------------------|------------|----------------------------------------------|
| id                     | UUID       | Primary key                                  |
| year_code              | CharField  | Unique code (e.g., "2024/2025")              |
| name                   | CharField  | Display name                                 |
| start_date             | Date       | Fiscal year start                            |
| end_date               | Date       | Fiscal year end                              |
| is_active              | Boolean    | Currently active year                        |
| created_by             | UUID       | Configuration manager                        |
| created_at             | DateTime   | Creation timestamp                           |
---------------------------------------------------------------------------------------

---------------------------------------------------------------------------------------
| Entity: Quarter                                                                     |
|---------------------------------------------------------------------------------------|
| Field                  | Type       | Description                                  |
|------------------------|------------|----------------------------------------------|
| id                     | UUID       | Primary key                                  |
| fiscal_year            | ForeignKey | Parent fiscal year                           |
| quarter_number         | Integer    | 1, 2, 3, 4                                   |
| name                   | CharField  | "Q1", "Q2", "Q3", "Q4"                      |
| start_date             | Date       | Quarter start                                |
| end_date               | Date       | Quarter end                                  |
| is_active              | Boolean    | Currently active quarter                     |
| created_by             | UUID       | Configuration manager                        |
---------------------------------------------------------------------------------------

**Standardized Value Lists:**

---------------------------------------------------------------------------------------
| Entity: AuditSeverity                                                               |
|---------------------------------------------------------------------------------------|
| Field                  | Type       | Description                                  |
|------------------------|------------|----------------------------------------------|
| id                     | UUID       | Primary key                                  |
| code                   | CharField  | "critical", "high", "medium", "low"          |
| name                   | CharField  | Display name                                 |
| description            | TextField  | Detailed description                         |
| color_code             | CharField  | UI color (hex)                               |
| sort_order             | Integer    | Display ordering                             |
| is_active              | Boolean    | Available for selection                      |
---------------------------------------------------------------------------------------

---------------------------------------------------------------------------------------
| Entity: FindingType                                                                 |
|---------------------------------------------------------------------------------------|
| Field                  | Type       | Description                                  |
|------------------------|------------|----------------------------------------------|
| id                     | UUID       | Primary key                                  |
| code                   | CharField  | "control_weakness", "non_compliance", etc.   |
| name                   | CharField  | Display name                                 |
| description            | TextField  | Type explanation                             |
| category               | CharField  | Grouping category                            |
| is_active              | Boolean    | Available for selection                      |
---------------------------------------------------------------------------------------

#### 3.1.2 Cross-Service Lookup Integration

**Organizational Structure (from Corporate Service):**

---------------------------------------------------------------------------------------
| Entity: Directorate (Cache/Sync from Corporate Service)                            |
|---------------------------------------------------------------------------------------|
| Field                  | Type       | Description                                  |
|------------------------|------------|----------------------------------------------|
| id                     | UUID       | Primary key (matches Corporate Service)      |
| external_id            | UUID       | Corporate Service reference                  |
| code                   | CharField  | Directorate code                             |
| name                   | CharField  | Directorate name                             |
| head_of_directorate    | UUID       | Director user ID                             |
| is_active              | Boolean    | Active status                                |
| last_sync              | DateTime   | Last sync from Corporate Service             |
---------------------------------------------------------------------------------------

---------------------------------------------------------------------------------------
| Entity: Unit (Cache/Sync from Corporate Service)                                   |
|---------------------------------------------------------------------------------------|
| Field                  | Type       | Description                                  |
|------------------------|------------|----------------------------------------------|
| id                     | UUID       | Primary key                                  |
| external_id            | UUID       | Corporate Service reference                  |
| directorate            | ForeignKey | Parent directorate                           |
| code                   | CharField  | Unit code                                    |
| name                   | CharField  | Unit name                                    |
| head_of_unit           | UUID       | Unit head user ID                            |
| is_active              | Boolean    | Active status                                |
| last_sync              | DateTime   | Last sync timestamp                          |
---------------------------------------------------------------------------------------

#### 3.1.3 Permission-Based Configuration Management

**Configuration Permissions (added to grc-service.json):**
- `grc_audit.manage_fiscal_years` - Create/edit fiscal years
- `grc_audit.manage_quarters` - Create/edit quarters  
- `grc_audit.manage_lookup_values` - Manage severity, finding types, etc.
- `grc_audit.sync_organizational_data` - Sync from Corporate Service
- `grc_audit.view_configurations` - View configuration values (for forms)

**Enhanced Role Definitions:**
```json
{
  "code": "grc_system_administrator", 
  "name": "GRC System Administrator",
  "description": "Can manage all GRC configuration settings",
  "permissions": [
    "grc_audit.manage_fiscal_years",
    "grc_audit.manage_quarters", 
    "grc_audit.manage_lookup_values",
    "grc_audit.sync_organizational_data",
    "grc_audit.view_configurations"
  ]
},
{
  "code": "chief_internal_auditor",
  "name": "Chief Internal Auditor", 
  "permissions": [
    "...existing permissions...",
    "grc_audit.manage_fiscal_years",
    "grc_audit.manage_quarters"
  ]
}
```

**On-the-Go Configuration UX Pattern:**
1. User encounters missing lookup value in form
2. System checks user permissions for configuration
3. If authorized, shows "+ Add New [Type]" option
4. Quick modal/dialog for adding new value
5. Value immediately available in current form
6. Background sync to other users

### 3.2 Core Audit Entities

Based on the SRS requirements, the following entities are identified:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           INTERNAL AUDIT DOMAIN MODEL                            │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐           │
│  │  AuditUniverse  │──1:N─│ AuditableEntity │──1:N─│ RiskAssessment  │           │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘           │
│           │                        │                        │                    │
│           │                        │                        │                    │
│           ▼                        ▼                        ▼                    │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐           │
│  │   AuditPlan     │──1:N─│ AuditEngagement │──1:N─│  AuditFinding   │           │
│  │   (RBIAP)       │      │                 │      │                 │           │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘           │
│           │                        │                        │                    │
│           │                        │                        │                    │
│           ▼                        ▼                        ▼                    │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────────┐       │
│  │  AuditProgram   │      │  AuditReport    │      │ AuditRecommendation │       │
│  └─────────────────┘      └─────────────────┘      └─────────────────────┘       │
│                                    │                        │                    │
│                                    ▼                        ▼                    │
│                           ┌─────────────────┐      ┌─────────────────┐           │
│                           │ QuarterlyReport │      │ Implementation  │           │
│                           │                 │      │  Monitoring     │           │
│                           └─────────────────┘      └─────────────────┘           │
│                                                                                  │
│  SUPPORTING ENTITIES:                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ AuditTeam   │  │ Meeting     │  │ WorkingPaper│  │RiskControl  │              │
│  │             │  │ (Entry/Exit)│  │             │  │  Matrix     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Entity Descriptions

#### 3.2.1 Audit Universe
Represents the complete scope of potential auditable activities within the organization.

------------------------------------------------------------------------------------------
| Field                  | Type       | Description                                      |
|------------------------|------------|--------------------------------------------------|
| id                     | UUID       | Primary key                                      |
| fiscal_year            | ForeignKey | Reference to FiscalYear lookup                   |
| description            | TextField  | Overall scope description                        |
| status                 | CharField  | draft, under_review, approved, archived          |
| created_by             | UUID       | Internal Auditor ID (from IAM)                   |
| reviewed_by            | UUID       | CIA ID who reviewed                              |
| approved_by            | UUID       | CIA ID who approved                              |
| approved_at            | DateTime   | Approval timestamp                               |
| orchestration_plan_id  | UUID       | Workflow reference                               |
------------------------------------------------------------------------------------------


#### 3.2.2 Auditable Entity
Individual units/departments that can be audited.

-------------------------------------------------------------------------------------------
| Field          | Type        | Description                                              |
|----------------|-------------|----------------------------------------------------------|
| id             | UUID        | Primary key                                              |
| audit_universe | ForeignKey  | Parent universe                                          |
| entity_type    | CharField   | directorate, unit, zone, process, system, project        |
| directorate    | ForeignKey  | Reference to Directorate (if applicable)                |
| unit           | ForeignKey  | Reference to Unit (if applicable)                       |
| name           | CharField   | Entity name                                              |
| code           | CharField   | Unique entity code                                       |
| description    | TextField   | Entity description                                       |
| head_of_entity | UUID        | Entity head user ID                                      |
| is_active      | Boolean     | Active status                                            |
| metadata       | JSONField   | Additional attributes                                    |
-------------------------------------------------------------------------------------------

#### 3.2.3 Risk Assessment
Risk evaluation for auditable entities.

-----------------------------------------------------------------------------------------------
| Field                       | Type        | Description                                     |
|-----------------------------|------------|--------------------------------------------------|
| id                          | UUID       | Primary key                                      |
| auditable_entity            | ForeignKey | Entity being assessed                            |
| assessment_period           | CharField  | Assessment period                                |
| inherent_risk_score         | Decimal    | Inherent risk rating                             |
| control_effectiveness_score | Decimal    | Control effectiveness                            |
| financial_exposure_score    | Decimal    | Financial risk rating                            |
| compliance_risk_score       | Decimal    | Compliance risk                                  |
| operational_impact_score    | Decimal    | Operational risk                                 |
| reputational_risk_score     | Decimal    | Reputation risk                                  |
| overall_risk_rating         | CharField  | high, medium, low                                |
| residual_risk_rating        | CharField  | Post-control risk                                |
| justification               | TextField  | Scoring rationale                                |
| evidence_attachments        | JSONField  | Supporting documents                             |
| assessed_by                 | UUID       | Assessor ID                                      |
| reviewed_by                 | UUID       | Reviewer ID                                      |
| status                      | CharField  | draft, submitted, reviewed, approved             |
-----------------------------------------------------------------------------------------------



#### 3.2.4 Audit Plan (RBIAP)
Risk-Based Internal Audit Annual Plan.

-----------------------------------------------------------------------------------------------------------------
| Field                    | Type       | Description                                                           |
|--------------------------|------------|-----------------------------------------------------------------------|
| id                       | UUID       | Primary key                                                           |
| reference_number         | CharField  | Unique plan reference                                                 |
| title                    | CharField  | Plan title                                                            |
| fiscal_year              | ForeignKey | Reference to FiscalYear lookup                                        |
| plan_type                | CharField  | annual, special, follow_up                                            |
| audit_universe           | ForeignKey | Associated universe                                                   |
| status                   | CharField  | draft, management_review, committee_review, approved, implementation  |
| priority_areas           | JSONField  | High-priority audit areas                                             |
| resource_allocation      | JSONField  | Auditor assignments                                                   |
| prepared_by              | UUID       | Preparing auditor                                                     |
| reviewed_by_cia          | UUID       | CIA reviewer                                                          |
| management_adopted_at    | DateTime   | Management adoption date                                              |
| management_comments      | TextField  | Management feedback                                                   |
| committee_approved_at    | DateTime   | Committee approval date                                               |
| committee_comments       | TextField  | Committee feedback                                                    |
| implementation_start_date| Date       | Plan start date                                                       |
| orchestration_plan_id    | UUID       | Workflow reference                                                    |
-----------------------------------------------------------------------------------------------------------------


#### 3.2.5 Audit Engagement
Individual audit assignment from the plan.

-----------------------------------------------------------------------------------------
| Field                     | Type       | Description                                  |
|---------------------------|------------|----------------------------------------------|
| id                        | UUID       | Primary key                                  |
| reference_number          | CharField  | Engagement reference                         |
| audit_plan                | ForeignKey | Parent plan                                  |
| auditable_entity          | ForeignKey | Entity to audit                              |
| title                     | CharField  | Engagement title                             |
| engagement_type           | CharField  | planned, ad_hoc, follow_up                   |
| status                    | CharField  | planning, fieldwork, reporting, completed    |
| lead_auditor              | UUID       | Lead auditor ID                              |
| audit_team                | JSONField  | Team member IDs                              |
| scope                     | TextField  | Audit scope                                  |
| objectives                | JSONField  | Audit objectives                             |
| methodology               | TextField  | Audit approach                               |
| planned_start_date        | Date       | Scheduled start                              |
| planned_end_date          | Date       | Scheduled completion                         |
| actual_start_date         | Date       | Actual start                                 |
| actual_end_date           | Date       | Actual completion                            |
| entry_meeting_date        | DateTime   | Entry meeting schedule                       |
| exit_meeting_date         | DateTime   | Exit meeting schedule                        |
| orchestration_plan_id     | UUID       | Workflow reference                           |
-----------------------------------------------------------------------------------------


#### 3.2.6 Audit Program
Detailed audit procedures and tests.

---------------------------------------------------------------------------------
| Field                  | Type       | Description                             |
|------------------------|------------|-----------------------------------------|
| id                     | UUID       | Primary key                             |
| engagement             | ForeignKey | Parent engagement                       |
| reference_number       | CharField  | Program reference                       |
| title                  | CharField  | Program title                           |
| status                 | CharField  | draft, approved, in_progress, completed |
| audit_scope            | TextField  | Defined scope                           |
| risk_control_matrix_id | UUID       | Associated RCM                          |
| prepared_by            | UUID       | Preparing auditor                       |
| approved_by            | UUID       | CIA approval                            |
| approved_at            | DateTime   | Approval timestamp                      |
---------------------------------------------------------------------------------


#### 3.2.7 Risk Control Matrix (RCM)
Maps risks to controls and test procedures.

--------------------------------------------------------------------------------------
| Field                         | Type       | Description                           |
|-------------------------------|------------|---------------------------------------|
| id                            | UUID       | Primary key                           |
| engagement                    | ForeignKey | Parent engagement                     |
| process_area                  | CharField  | Process being reviewed                |
| risk_description              | TextField  | Identified risk                       |
| risk_rating                   | CharField  | high, medium, low                     |
| control_description           | TextField  | Control in place                      |
| control_owner                 | UUID       | Control owner ID                      |
| control_type                  | CharField  | preventive, detective, corrective     |
| control_design_effectiveness  | CharField  | adequate, inadequate                  |
| test_procedure                | TextField  | Testing approach                      |
| test_results                  | TextField  | Test outcomes                         |
| created_by                    | UUID       | Creator ID                            |
--------------------------------------------------------------------------------------


#### 3.2.8 Working Paper
Audit evidence and documentation.

--------------------------------------------------------------------------------
| Field                 | Type       | Description                             |
|-----------------------|------------|-----------------------------------------|
| id                    | UUID       | Primary key                             |
| engagement            | ForeignKey | Parent engagement                       |
| reference_number      | CharField  | Paper reference                         |
| title                 | CharField  | Paper title                             |
| paper_type            | CharField  | planning, testing, findings, conclusion |
| content               | TextField  | Paper content                           |
| evidence_references   | JSONField  | Linked evidence                         |
| document_ids          | JSONField  | Document service refs                   |
| prepared_by           | UUID       | Preparer                                |
| reviewed_by           | UUID       | Reviewer                                |
| review_status         | CharField  | pending, reviewed, approved             |
| review_comments       | TextField  | Review notes                            |
--------------------------------------------------------------------------------


#### 3.2.9 Audit Finding
Issues identified during the audit.

------------------------------------------------------------------------------------------------------
| Field               | Type       | Description                                                     |
|---------------------|------------|-----------------------------------------------------------------|
| id                  | UUID       | Primary key                                                     |
| engagement          | ForeignKey | Parent engagement                                               |
| working_paper       | ForeignKey | Source working paper                                            |
| reference_number    | CharField  | Finding reference (e.g., "125 of Q2 2023/2024")                |
| fiscal_year         | ForeignKey | Reference to FiscalYear                                         |
| quarter             | ForeignKey | Reference to Quarter                                            |
| title               | CharField  | Finding title                                                   |
| finding_type        | ForeignKey | Reference to FindingType lookup                                 |
| severity            | ForeignKey | Reference to AuditSeverity lookup                               |
| condition           | TextField  | What was found                                                  |
| criteria            | TextField  | What should be                                                  |
| cause               | TextField  | Why it happened                                                 |
| effect              | TextField  | Impact/consequence                                              |
| risk_rating         | CharField  | Associated risk level                                           |
| auditee_response    | TextField  | Auditee feedback                                                |
| management_response | TextField  | Management response                                             |
| status              | CharField  | draft, discussed, final                                         |
------------------------------------------------------------------------------------------------------
 

#### 3.2.10 Audit Recommendation
Improvement suggestions from findings.

--------------------------------------------------------------------------------------
| Field             | Type       | Description                                       |
|-------------------|------------|---------------------------------------------------|
| id                | UUID       | Primary key                                       |
| finding           | ForeignKey | Parent finding                                    |
| reference_number  | CharField  | Recommendation ref                                |
| title             | CharField  | Recommendation title                              |
| description       | TextField  | Detailed recommendation                           |
| priority          | CharField  | high, medium, low                                 |
| responsible_party | UUID       | Responsible person                                |
| agreed_action     | TextField  | Agreed corrective action                          |
| target_date       | Date       | Implementation deadline                           |
| status            | CharField  | open, in_progress, implemented, verified, closed  |
--------------------------------------------------------------------------------------


#### 3.2.11 Implementation Monitoring
Tracks recommendation follow-up.

--------------------------------------------------------------------------------------
| Field             | Type       | Description                                       |
|-------------------|------------|---------------------------------------------------|
| id                | UUID       | Primary key                                       |
| finding           | ForeignKey | Parent finding                                    |
| reference_number  | CharField  | Recommendation ref                                |
| title             | CharField  | Recommendation title                              |
| description       | TextField  | Detailed recommendation                           |
| priority          | CharField  | high, medium, low                                 |
| responsible_party | UUID       | Responsible person                                |
| agreed_action     | TextField  | Agreed corrective action                          |
| target_date       | Date       | Implementation deadline                           |
| status            | CharField  | open, in_progress, implemented, verified, closed  |
--------------------------------------------------------------------------------------


#### 3.2.12 Audit Meeting
Entry and exit meeting records.

------------------------------------------------------------------------------------
| Field                   | Type       | Description                               |
|-------------------------|------------|-------------------------------------------|
| id                      | UUID       | Primary key                               |
| engagement              | ForeignKey | Parent engagement                         |
| meeting_type            | CharField  | entry, pre_exit, exit, team               |
| scheduled_date          | DateTime   | Scheduled time                            |
| actual_date             | DateTime   | Actual meeting time                       |
| location                | CharField  | Meeting venue                             |
| attendees               | JSONField  | Participant list                          |
| agenda                  | JSONField  | Meeting agenda                            |
| minutes                 | TextField  | Meeting minutes                           |
| action_items            | JSONField  | Follow-up actions                         |
| minutes_document_id     | UUID       | Document service ref                      |
| attendance_document_id  | UUID       | Attendance sheet ref                      |
| status                  | CharField  | scheduled, completed, cancelled           |
------------------------------------------------------------------------------------


#### 3.2.13 Audit Report
Final engagement reports.

------------------------------------------------------------------------------------------------
| Field                      | Type       | Description                                        |
|----------------------------|------------|----------------------------------------------------|
| id                         | UUID       | Primary key                                        |
| engagement                 | ForeignKey | Parent engagement                                  |
| reference_number           | CharField  | Report reference                                   |
| report_type                | CharField  | draft, final                                       |
| title                      | CharField  | Report title                                       |
| executive_summary          | TextField  | Summary                                            |
| scope_and_objectives       | TextField  | Scope description                                  |
| methodology                | TextField  | Approach used                                      |
| findings_summary           | JSONField  | Key findings                                       |
| recommendations_summary    | JSONField  | Key recommendations                                |
| conclusion                 | TextField  | Audit conclusion                                   |
| opinion                    | CharField  | satisfactory, needs_improvement, unsatisfactory    |
| status                     | CharField  | draft, under_review, approved, distributed         |
| prepared_by                | UUID       | Preparer                                           |
| reviewed_by                | UUID       | Reviewer                                           |
| approved_by                | UUID       | Approver (CIA)                                     |
| approval_date              | DateTime   | Approval timestamp                                 |
| distribution_list          | JSONField  | Recipients                                         |
| distributed_at             | DateTime   | Distribution date                                  |
| document_id                | UUID       | Generated document ref                             |
| orchestration_plan_id      | UUID       | Approval workflow                                  |
------------------------------------------------------------------------------------------------


#### 3.2.14 Quarterly Report
Consolidated quarterly audit reports.

-------------------------------------------------------------------------------------------------------------
| Field                      | Type       | Description                                                     |
|----------------------------|------------|-----------------------------------------------------------------|
| id                         | UUID       | Primary key                                                     |
| reference_number           | CharField  | Report reference                                                |
| fiscal_year                | CharField  | Fiscal year                                                     |
| quarter                    | CharField  | Q1, Q2, Q3, Q4                                                  |
| title                      | CharField  | Report title                                                    |
| period_start               | Date       | Period start                                                    |
| period_end                 | Date       | Period end                                                      |
| executive_summary          | TextField  | Summary                                                         |
| engagements_summary        | JSONField  | Included engagements                                            |
| findings_analysis          | JSONField  | Findings statistics                                             |
| recommendations_status     | JSONField  | Recommendations tracking                                        |
| implementation_rates       | JSONField  | Implementation metrics                                          |
| risk_trends                | JSONField  | Risk analysis                                                   |
| key_issues                 | JSONField  | Critical issues                                                 |
| status                     | CharField  | draft, management_review, committee_review, commission_approved |
| prepared_by                | UUID       | Preparer (PIA)                                                  |
| reviewed_by_cia            | UUID       | CIA reviewer                                                    |
| management_adopted_at      | DateTime   | Management adoption                                             |
| committee_reviewed_at      | DateTime   | Committee review                                                |
| commission_approved_at     | DateTime   | Commission approval                                             |
| document_id                | UUID       | Generated document ref                                          |
| orchestration_plan_id      | UUID       | Approval workflow                                               |
-------------------------------------------------------------------------------------------------------------


#### 3.2.15 Engagement Notification
Formal notification to auditees.

------------------------------------------------------------------------------------
| Field               | Type       | Description                                   |
|---------------------|------------|-----------------------------------------------|
| id                  | UUID       | Primary key                                   |
| engagement          | ForeignKey | Parent engagement                             |
| notification_type   | CharField  | engagement, entry_meeting, exit_meeting       |
| reference_number    | CharField  | Notification reference                        |
| recipient           | UUID       | Recipient ID                                  |
| recipient_email     | EmailField | Recipient email                               |
| subject             | CharField  | Notification subject                          |
| content             | TextField  | Notification body                             |
| attachments         | JSONField  | Attached documents                            |
| sent_at             | DateTime   | Send timestamp                                |
| read_at             | DateTime   | Read timestamp                                |
| status              | CharField  | draft, sent, delivered, read                  |
| signature           | TextField  | CIA signature data                            |
| qr_code             | TextField  | QR code data                                  |
| document_id         | UUID       | Generated document ref                        |
------------------------------------------------------------------------------------


#### 3.2.16 Independence Declaration
Auditor conflict of interest declarations.

-----------------------------------------------------------------------------
| Field                | Type       | Description                           |
|----------------------|------------|---------------------------------------|
| id                   | UUID       | Primary key                           |
| engagement           | ForeignKey | Parent engagement                     |
| auditor              | UUID       | Auditor ID                            |
| declaration_date     | DateTime   | Declaration timestamp                 |
| has_conflicts        | Boolean    | Conflict indicator                    |
| conflict_details     | TextField  | Conflict description                  |
| mitigation_measures  | TextField  | Mitigation approach                   |
| status               | CharField  | pending, declared, approved           |
| reviewed_by          | UUID       | Reviewer (CIA)                        |
| document_id          | UUID       | Signed document ref                   |
-----------------------------------------------------------------------------


---

## 4. Database Schema

### 4.1 PostgreSQL Tables

```sql
-- Core Audit Tables
CREATE TABLE audit_universe (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fiscal_year VARCHAR(20) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    created_by UUID NOT NULL,
    reviewed_by UUID,
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    orchestration_plan_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE auditable_entity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_universe_id UUID REFERENCES audit_universe(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    head_of_entity UUID,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE risk_assessment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auditable_entity_id UUID REFERENCES auditable_entity(id) ON DELETE CASCADE,
    assessment_period VARCHAR(50) NOT NULL,
    inherent_risk_score DECIMAL(5,2),
    control_effectiveness_score DECIMAL(5,2),
    financial_exposure_score DECIMAL(5,2),
    compliance_risk_score DECIMAL(5,2),
    operational_impact_score DECIMAL(5,2),
    reputational_risk_score DECIMAL(5,2),
    overall_risk_rating VARCHAR(20),
    residual_risk_rating VARCHAR(20),
    justification TEXT,
    evidence_attachments JSONB DEFAULT '[]',
    assessed_by UUID NOT NULL,
    reviewed_by UUID,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_plan (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_number VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    fiscal_year VARCHAR(20) NOT NULL,
    plan_type VARCHAR(50) DEFAULT 'annual',
    audit_universe_id UUID REFERENCES audit_universe(id),
    status VARCHAR(50) DEFAULT 'draft',
    priority_areas JSONB DEFAULT '[]',
    resource_allocation JSONB DEFAULT '{}',
    prepared_by UUID NOT NULL,
    reviewed_by_cia UUID,
    management_adopted_at TIMESTAMP WITH TIME ZONE,
    management_comments TEXT,
    committee_approved_at TIMESTAMP WITH TIME ZONE,
    committee_comments TEXT,
    implementation_start_date DATE,
    orchestration_plan_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_engagement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_number VARCHAR(100) UNIQUE NOT NULL,
    audit_plan_id UUID REFERENCES audit_plan(id),
    auditable_entity_id UUID REFERENCES auditable_entity(id),
    title VARCHAR(500) NOT NULL,
    engagement_type VARCHAR(50) DEFAULT 'planned',
    status VARCHAR(50) DEFAULT 'planning',
    lead_auditor UUID NOT NULL,
    audit_team JSONB DEFAULT '[]',
    scope TEXT,
    objectives JSONB DEFAULT '[]',
    methodology TEXT,
    planned_start_date DATE,
    planned_end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,
    entry_meeting_date TIMESTAMP WITH TIME ZONE,
    exit_meeting_date TIMESTAMP WITH TIME ZONE,
    orchestration_plan_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Additional tables following similar patterns...
-- (audit_program, risk_control_matrix, working_paper, audit_finding,
-- audit_recommendation, implementation_monitoring, audit_meeting,
-- audit_report, quarterly_report, engagement_notification, independence_declaration)

-- Indexes for performance
CREATE INDEX idx_audit_plan_status ON audit_plan(status);
CREATE INDEX idx_audit_plan_fiscal_year ON audit_plan(fiscal_year);
CREATE INDEX idx_audit_engagement_status ON audit_engagement(status);
CREATE INDEX idx_audit_engagement_lead_auditor ON audit_engagement(lead_auditor);
CREATE INDEX idx_audit_finding_severity ON audit_finding(severity);
CREATE INDEX idx_implementation_monitoring_status ON implementation_monitoring(implementation_status);
CREATE INDEX idx_risk_assessment_overall_rating ON risk_assessment(overall_risk_rating);
```

---

## 5. API Design

### 5.1 RESTful Endpoints

Base URL: `/api/v1/audit/`

#### 5.1.1 Audit Universe Management

```
GET    /universe/                          # List all universes
POST   /universe/                          # Create new universe
GET    /universe/{id}/                     # Get universe details
PUT    /universe/{id}/                     # Update universe
DELETE /universe/{id}/                     # Delete universe (draft only)
POST   /universe/{id}/submit-for-review/   # Submit to CIA
POST   /universe/{id}/approve/             # CIA approval
GET    /universe/{id}/entities/            # List entities in universe
POST   /universe/{id}/entities/            # Add entity to universe
```

#### 5.1.2 Auditable Entity Management

```
GET    /entities/                          # List all entities
POST   /entities/                          # Create entity
GET    /entities/{id}/                     # Get entity details
PUT    /entities/{id}/                     # Update entity
DELETE /entities/{id}/                     # Delete entity
GET    /entities/{id}/risk-assessments/    # Get entity risk assessments
POST   /entities/{id}/risk-assessments/    # Create risk assessment
```

#### 5.1.3 Risk Assessment

```
GET    /risk-assessments/                  # List all assessments
POST   /risk-assessments/                  # Create assessment
GET    /risk-assessments/{id}/             # Get assessment details
PUT    /risk-assessments/{id}/             # Update assessment
POST   /risk-assessments/{id}/submit/      # Submit for review
POST   /risk-assessments/{id}/approve/     # Approve assessment
GET    /risk-assessments/analytics/        # Risk analytics dashboard
```

#### 5.1.4 Audit Plan (RBIAP) Management

```
GET    /plans/                             # List all plans
POST   /plans/                             # Create new plan
GET    /plans/{id}/                        # Get plan details
PUT    /plans/{id}/                        # Update plan
DELETE /plans/{id}/                        # Delete plan (draft only)
POST   /plans/{id}/submit-to-management/   # Submit to management
POST   /plans/{id}/management-adopt/       # Management adoption
POST   /plans/{id}/submit-to-committee/    # Submit to audit committee
POST   /plans/{id}/committee-approve/      # Committee approval
POST   /plans/{id}/request-improvement/    # Request improvements
GET    /plans/{id}/engagements/            # List plan engagements
```

#### 5.1.5 Audit Engagement Management

```
GET    /engagements/                       # List all engagements
POST   /engagements/                       # Create engagement
GET    /engagements/{id}/                  # Get engagement details
PUT    /engagements/{id}/                  # Update engagement
DELETE /engagements/{id}/                  # Delete engagement

# Engagement Workflow
POST   /engagements/{id}/assign-team/      # Assign audit team
POST   /engagements/{id}/send-notification/ # Send engagement notification
GET    /engagements/{id}/declarations/     # Get independence declarations
POST   /engagements/{id}/declarations/     # Submit declaration

# Engagement Components
GET    /engagements/{id}/program/          # Get audit program
POST   /engagements/{id}/program/          # Create audit program
GET    /engagements/{id}/rcm/              # Get Risk Control Matrix
POST   /engagements/{id}/rcm/              # Create RCM entries
GET    /engagements/{id}/working-papers/   # List working papers
POST   /engagements/{id}/working-papers/   # Create working paper
GET    /engagements/{id}/findings/         # List findings
POST   /engagements/{id}/findings/         # Create finding
GET    /engagements/{id}/meetings/         # List meetings
POST   /engagements/{id}/meetings/         # Schedule meeting
```

#### 5.1.6 Configuration & Lookup Management

**Configuration Permissions Required:**
- `grc_audit.manage_fiscal_years`
- `grc_audit.manage_quarters` 
- `grc_audit.manage_lookup_values`
- `grc_audit.sync_organizational_data`

```
# Fiscal Year & Quarter Management
GET    /config/fiscal-years/              # List fiscal years
POST   /config/fiscal-years/              # Create fiscal year (permission required)
GET    /config/fiscal-years/{id}/         # Get fiscal year details
PUT    /config/fiscal-years/{id}/         # Update fiscal year
POST   /config/fiscal-years/{id}/activate/ # Set as active year

GET    /config/quarters/                  # List quarters
POST   /config/quarters/                  # Create quarter (permission required)
GET    /config/quarters/{id}/             # Get quarter details
PUT    /config/quarters/{id}/             # Update quarter
POST   /config/quarters/{id}/activate/    # Set as active quarter

# Lookup Value Management  
GET    /config/severities/               # List audit severities
POST   /config/severities/               # Create severity level
PUT    /config/severities/{id}/          # Update severity
DELETE /config/severities/{id}/          # Deactivate severity

GET    /config/finding-types/            # List finding types
POST   /config/finding-types/            # Create finding type
PUT    /config/finding-types/{id}/       # Update finding type
DELETE /config/finding-types/{id}/       # Deactivate finding type

# On-the-Go Configuration (for forms)
POST   /config/quick-add/               # Quick add lookup values
GET    /config/available-values/{type}/ # Get available values for forms

# Organizational Structure Sync
GET    /config/directorates/            # List directorates (cached from Corporate)
POST   /config/sync-organizational/     # Sync from Corporate Service
GET    /config/units/                   # List units (cached from Corporate)
GET    /config/sync-status/             # Check last sync status
```

#### 5.1.6 Audit Program

```
GET    /programs/                          # List all programs
GET    /programs/{id}/                     # Get program details
PUT    /programs/{id}/                     # Update program
POST   /programs/{id}/approve/             # Approve program
GET    /programs/{id}/tests/               # Get test procedures
POST   /programs/{id}/tests/               # Add test procedure
```

#### 5.1.7 Working Papers

```
GET    /working-papers/                    # List all working papers
GET    /working-papers/{id}/               # Get paper details
PUT    /working-papers/{id}/               # Update paper
POST   /working-papers/{id}/submit-review/ # Submit for review
POST   /working-papers/{id}/approve/       # Approve paper
POST   /working-papers/{id}/attach-evidence/ # Attach evidence
```

#### 5.1.8 Audit Findings

```
GET    /findings/                          # List all findings
GET    /findings/{id}/                     # Get finding details
PUT    /findings/{id}/                     # Update finding
POST   /findings/{id}/finalize/            # Finalize finding
GET    /findings/{id}/recommendations/     # Get recommendations
POST   /findings/{id}/recommendations/     # Create recommendation
```

#### 5.1.9 Recommendations & Monitoring

```
GET    /recommendations/                   # List all recommendations
GET    /recommendations/{id}/              # Get recommendation details
PUT    /recommendations/{id}/              # Update recommendation
POST   /recommendations/{id}/update-status/ # Update implementation status
GET    /recommendations/{id}/monitoring/   # Get monitoring history

# Monitoring
GET    /monitoring/                        # List all monitoring entries
POST   /monitoring/                        # Create monitoring entry
GET    /monitoring/{id}/                   # Get monitoring details
PUT    /monitoring/{id}/                   # Update monitoring
POST   /monitoring/{id}/verify/            # Verify implementation
GET    /monitoring/outstanding/            # List outstanding recommendations
POST   /monitoring/send-reminders/         # Send reminder notifications
GET    /monitoring/analytics/              # Monitoring analytics
```

#### 5.1.10 Audit Meetings

```
GET    /meetings/                          # List all meetings
GET    /meetings/{id}/                     # Get meeting details
PUT    /meetings/{id}/                     # Update meeting
POST   /meetings/{id}/complete/            # Mark as completed
POST   /meetings/{id}/upload-minutes/      # Upload meeting minutes
POST   /meetings/{id}/upload-attendance/   # Upload attendance sheet
POST   /meetings/{id}/send-notification/   # Send meeting notification
```

#### 5.1.11 Audit Reports

```
GET    /reports/engagements/               # List engagement reports
POST   /reports/engagements/               # Create engagement report
GET    /reports/engagements/{id}/          # Get report details
PUT    /reports/engagements/{id}/          # Update report
POST   /reports/engagements/{id}/submit-review/ # Submit for review
POST   /reports/engagements/{id}/approve/  # Approve report
POST   /reports/engagements/{id}/distribute/ # Distribute report

# Quarterly Reports
GET    /reports/quarterly/                 # List quarterly reports
POST   /reports/quarterly/                 # Create quarterly report
GET    /reports/quarterly/{id}/            # Get quarterly report
PUT    /reports/quarterly/{id}/            # Update quarterly report
POST   /reports/quarterly/{id}/submit-management/ # Submit to management
POST   /reports/quarterly/{id}/management-adopt/ # Management adoption
POST   /reports/quarterly/{id}/submit-committee/ # Submit to committee
POST   /reports/quarterly/{id}/committee-review/ # Committee review
POST   /reports/quarterly/{id}/submit-commission/ # Submit to commission
POST   /reports/quarterly/{id}/commission-approve/ # Commission approval
```

#### 5.1.12 Analytics & Dashboard

```
GET    /analytics/dashboard/               # Main audit dashboard
GET    /analytics/risk-summary/            # Risk assessment summary
GET    /analytics/plan-progress/           # Plan implementation progress
GET    /analytics/engagement-stats/        # Engagement statistics
GET    /analytics/finding-trends/          # Finding trends analysis
GET    /analytics/implementation-rates/    # Recommendation implementation rates
GET    /analytics/auditor-workload/        # Auditor workload analysis
```

### 5.2 Sample API Request/Response

#### Create Audit Plan Request

```json
POST /api/v1/audit/plans/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "title": "FY 2024/2025 Risk Based Internal Audit Plan",
    "fiscal_year": "2024/2025",
    "plan_type": "annual",
    "audit_universe_id": "uuid-of-approved-universe",
    "priority_areas": [
        {
            "area": "Procurement and Supply Chain",
            "risk_rating": "high",
            "planned_engagements": 3
        },
        {
            "area": "Financial Management",
            "risk_rating": "high",
            "planned_engagements": 2
        },
        {
            "area": "IT Systems and Security",
            "risk_rating": "medium",
            "planned_engagements": 2
        }
    ],
    "resource_allocation": {
        "total_audit_days": 180,
        "auditors_assigned": ["uuid-1", "uuid-2", "uuid-3"]
    }
}
```

#### Response

```json
{
    "id": "uuid-of-plan",
    "reference_number": "RBIAP-2024-001",
    "title": "FY 2024/2025 Risk Based Internal Audit Plan",
    "fiscal_year": "2024/2025",
    "plan_type": "annual",
    "status": "draft",
    "audit_universe": {
        "id": "uuid-of-universe",
        "fiscal_year": "2024/2025",
        "status": "approved"
    },
    "priority_areas": [...],
    "resource_allocation": {...},
    "prepared_by": {
        "id": "user-uuid",
        "name": "John Auditor",
        "email": "john@fcc.go.ke"
    },
    "orchestration_plan_id": null,
    "created_at": "2024-06-15T10:30:00Z",
    "updated_at": "2024-06-15T10:30:00Z",
    "workflow_status": null
}
```

---

## 6. Workflow Definitions

### 6.1 RBIAP Approval Workflow

```yaml
workflow_type: "rbiap_approval"
stages:
  - key: "cia_review"
    name: "CIA Review"
    order: 1
    assignees_type: "role"
    assignees_role: "CIA"
    actions:
      - type: "approve"
        next_stage: "management_review"
      - type: "return"
        next_stage: null
        status: "returned_to_auditor"

  - key: "management_review"
    name: "Management Review"
    order: 2
    assignees_type: "role"
    assignees_role: "Management"
    actions:
      - type: "adopt"
        next_stage: "committee_review"
      - type: "request_changes"
        next_stage: "cia_review"

  - key: "committee_review"
    name: "Audit Committee Review"
    order: 3
    assignees_type: "role"
    assignees_role: "AuditCommittee"
    actions:
      - type: "approve"
        next_stage: "commission_noting"
      - type: "request_improvement"
        next_stage: "cia_review"

  - key: "commission_noting"
    name: "Commission Noting"
    order: 4
    assignees_type: "role"
    assignees_role: "Commission"
    actions:
      - type: "note"
        next_stage: null
        status: "approved"
```

### 6.2 Audit Engagement Workflow

```yaml
workflow_type: "audit_engagement"
stages:
  - key: "planning"
    name: "Audit Planning"
    order: 1
    tasks:
      - "Familiarization with auditable area"
      - "Control assessment"
      - "Develop audit program"
      - "Prepare RCM"
    
  - key: "program_approval"
    name: "Program Approval"
    order: 2
    assignees_type: "role"
    assignees_role: "CIA"
    actions:
      - type: "approve"
        next_stage: "notification"
      - type: "return"
        next_stage: "planning"

  - key: "notification"
    name: "Engagement Notification"
    order: 3
    tasks:
      - "Prepare engagement notification"
      - "Send to auditee"
      - "Collect independence declarations"

  - key: "entry_meeting"
    name: "Entry Meeting"
    order: 4
    tasks:
      - "Schedule entry meeting"
      - "Conduct meeting"
      - "Document minutes"

  - key: "fieldwork"
    name: "Fieldwork"
    order: 5
    tasks:
      - "Execute audit tests"
      - "Collect evidence"
      - "Document working papers"
      - "Identify findings"

  - key: "working_paper_review"
    name: "Working Paper Review"
    order: 6
    assignees_type: "role"
    assignees_role: "CIA"
    
  - key: "pre_exit_meeting"
    name: "Pre-Exit Meeting"
    order: 7
    
  - key: "draft_report"
    name: "Draft Report Preparation"
    order: 8
    
  - key: "exit_meeting"
    name: "Exit Meeting"
    order: 9
    
  - key: "final_report"
    name: "Final Report"
    order: 10
    assignees_type: "role"
    assignees_role: "CIA"
    actions:
      - type: "approve"
        next_stage: "distribution"
      - type: "return"
        next_stage: "draft_report"

  - key: "distribution"
    name: "Report Distribution"
    order: 11
    status: "completed"
```

### 6.3 Quarterly Report Workflow

```yaml
workflow_type: "quarterly_report_approval"
stages:
  - key: "consolidation"
    name: "Report Consolidation"
    order: 1
    assignees_type: "role"
    assignees_role: "PrincipalInternalAuditor"
    
  - key: "cia_review"
    name: "CIA Review & Approval"
    order: 2
    assignees_type: "role"
    assignees_role: "CIA"
    
  - key: "management_deliberation"
    name: "Management Deliberation"
    order: 3
    assignees_type: "role"
    assignees_role: "Management"
    
  - key: "committee_review"
    name: "Audit Committee Review"
    order: 4
    assignees_type: "role"
    assignees_role: "AuditCommittee"
    actions:
      - type: "approve"
        next_stage: "commission_approval"
      - type: "request_improvement"
        next_stage: "cia_review"

  - key: "commission_approval"
    name: "Commission Approval"
    order: 5
    assignees_type: "role"
    assignees_role: "Commission"
    status: "approved"
```

---

## 7. Integration Patterns

### 7.1 IAM Service Integration

```python
# Authentication middleware
class IAMAuthenticationMiddleware:
    """
    Validates JWT tokens from IAM service and extracts user context.
    """
    
    def authenticate(self, request):
        token = self.extract_token(request)
        payload = self.validate_token(token)
        
        return {
            'user_id': payload['sub'],
            'email': payload['email'],
            'roles': payload['roles'],
            'permissions': payload['permissions'],
            'department': payload.get('department'),
            'is_superuser': payload.get('is_superuser', False)
        }

# Permission checking
class AuditPermissions:
    """
    Audit-specific permission classes.
    """
    
    PERMISSIONS = {
        'can_create_audit_plan': 'audit.create_plan',
        'can_approve_audit_plan': 'audit.approve_plan',
        'can_conduct_audit': 'audit.conduct_audit',
        'can_review_working_papers': 'audit.review_papers',
        'can_approve_reports': 'audit.approve_reports',
        'can_view_audit_dashboard': 'audit.view_dashboard',
    }
```

### 7.2 Document Records Service Integration

```python
# Document creation for audit artifacts
class DocumentServiceClient:
    """
    Client for Document Records Service API with audit-specific document types.
    """
    
    AUDIT_DOCUMENT_TYPES = {
        'AUDIT_PLAN': 'audit_plan',
        'ENGAGEMENT_NOTIFICATION': 'audit_notification', 
        'WORKING_PAPER': 'audit_working_paper',
        'FINDING_DOCUMENT': 'audit_finding',
        'AUDIT_REPORT': 'audit_report',
        'QUARTERLY_REPORT': 'quarterly_audit_report',
        'INDEPENDENCE_DECLARATION': 'independence_declaration'
    }
    
    def create_audit_document(self, doc_type, title, content, metadata=None):
        """Create document in Document Records Service."""
        payload = {
            'document_type': self.AUDIT_DOCUMENT_TYPES[doc_type],
            'title': title,
            'content': content,
            'metadata': {
                'source_service': 'grc-audit',
                'fiscal_year': metadata.get('fiscal_year'),
                'quarter': metadata.get('quarter'),
                'engagement_id': metadata.get('engagement_id'),
                **metadata or {}
            },
            'classification': 'internal',
            'retention_category': 'audit_records'
        }
        
        response = self.http_client.post('/api/v1/documents/', json=payload)
        return response.json()
```

### 7.3 Corporate Service Integration (Organizational Data)

```python
# Organizational structure synchronization
class CorporateServiceSync:
    """
    Synchronizes organizational structure from Corporate Service.
    """
    
    def sync_directorates(self):
        """Fetch and cache directorate data."""
        response = self.http_client.get('/api/v1/corporate/directorates/')
        directorates = response.json()['data']
        
        for dir_data in directorates:
            directorate, created = Directorate.objects.update_or_create(
                external_id=dir_data['id'],
                defaults={
                    'code': dir_data['code'],
                    'name': dir_data['name'],
                    'head_of_directorate': dir_data['director_id'],
                    'is_active': dir_data['is_active'],
                    'last_sync': timezone.now()
                }
            )
            
        # Sync units for each directorate
        self.sync_units()
    
    def sync_units(self):
        """Fetch and cache unit data."""
        response = self.http_client.get('/api/v1/corporate/units/')
        units = response.json()['data']
        
        for unit_data in units:
            Unit.objects.update_or_create(
                external_id=unit_data['id'],
                defaults={
                    'directorate_id': unit_data['directorate_id'],
                    'code': unit_data['code'], 
                    'name': unit_data['name'],
                    'head_of_unit': unit_data['head_id'],
                    'is_active': unit_data['is_active'],
                    'last_sync': timezone.now()
                }
            )

# Celery task for automated sync
@shared_task
def sync_organizational_data():
    """Background task to sync organizational data."""
    sync_service = CorporateServiceSync()
    sync_service.sync_directorates()
    
    # Publish sync completion event
    kafka_publisher = PermissionPublisher()
    kafka_publisher.publish_event('organizational_data_synced', {
        'service': 'grc-audit',
        'sync_timestamp': timezone.now().isoformat(),
        'synced_entities': ['directorates', 'units']
    })
```

### 7.4 Configuration Management Service Layer

```python
# Configuration management with permission checks
class ConfigurationManager:
    """
    Manages lookup tables and configuration with permission enforcement.
    """
    
    def create_fiscal_year(self, user_context, year_data):
        """Create new fiscal year with permission check."""
        if not self.has_permission(user_context, 'grc_audit.manage_fiscal_years'):
            raise PermissionDenied("Insufficient permissions to manage fiscal years")
            
        fiscal_year = FiscalYear.objects.create(
            year_code=year_data['year_code'],
            name=year_data['name'],
            start_date=year_data['start_date'],
            end_date=year_data['end_date'],
            created_by=user_context['user_id']
        )
        
        # Publish configuration change event
        self.publish_config_change('fiscal_year_created', fiscal_year.id)
        return fiscal_year
    
    def quick_add_lookup_value(self, user_context, value_type, value_data):
        """On-the-go lookup value creation for forms."""
        permission_map = {
            'severity': 'grc_audit.manage_lookup_values',
            'finding_type': 'grc_audit.manage_lookup_values',
            'fiscal_year': 'grc_audit.manage_fiscal_years',
            'quarter': 'grc_audit.manage_quarters'
        }
        
        required_permission = permission_map.get(value_type)
        if not self.has_permission(user_context, required_permission):
            raise PermissionDenied(f"Cannot create {value_type} values")
            
        # Create the value based on type
        model_map = {
            'severity': AuditSeverity,
            'finding_type': FindingType,
            'fiscal_year': FiscalYear,
            'quarter': Quarter
        }
        
        model_class = model_map[value_type]
        instance = model_class.objects.create(**value_data)
        
        # Real-time notification to other users
        self.broadcast_new_lookup_value(value_type, instance)
        return instance
    
    def broadcast_new_lookup_value(self, value_type, instance):
        """Broadcast new lookup value to active users."""
        kafka_publisher = PermissionPublisher()
        kafka_publisher.publish_event('lookup_value_added', {
            'type': value_type,
            'id': str(instance.id),
            'data': {
                'code': getattr(instance, 'code', None),
                'name': instance.name,
                'is_active': getattr(instance, 'is_active', True)
            }
        })
```
    
    BASE_URL = settings.DOCUMENT_SERVICE_URL
    
    async def create_document(self, document_data: dict) -> dict:
        """Create a new document in Document Records Service."""
        response = await self.client.post(
            f"{self.BASE_URL}/api/v1/documents/",
            json={
                "title": document_data['title'],
                "document_type": document_data['type'],
                "template_id": document_data.get('template_id'),
                "template_data": document_data.get('template_data'),
                "created_by": document_data['created_by'],
                "metadata": {
                    "source_service": "grc-service",
                    "audit_reference": document_data.get('audit_reference'),
                    "entity_type": document_data.get('entity_type'),
                    "entity_id": document_data.get('entity_id'),
                }
            }
        )
        return response.json()
    
    async def upload_file(self, document_id: str, file_data: bytes, filename: str):
        """Upload file content to existing document."""
        ...
    
    async def get_document(self, document_id: str) -> dict:
        """Retrieve document details."""
        ...
```

### 7.3 Work Orchestration Service Integration

```python
# Workflow management for audit processes
class WorkOrchestrationClient:
    """
    Client for Work Orchestration Service API.
    """
    
    BASE_URL = settings.WORK_ORCHESTRATION_URL
    
    async def create_workflow_plan(self, workflow_data: dict) -> dict:
        """Create a new workflow plan for audit process."""
        response = await self.client.post(
            f"{self.BASE_URL}/api/v1/workflow/plans/",
            json={
                "workflow_type": workflow_data['type'],
                "metadata": {
                    "source_service": "grc-service",
                    "entity_type": workflow_data['entity_type'],
                    "entity_id": workflow_data['entity_id'],
                    "reference_number": workflow_data['reference_number'],
                },
                "created_by": workflow_data['created_by'],
            }
        )
        return response.json()
    
    async def advance_stage(self, plan_id: str, stage_id: str, action: str, comments: str):
        """Advance workflow to next stage."""
        ...
    
    async def get_plan_status(self, plan_id: str) -> dict:
        """Get current workflow plan status."""
        ...
    
    async def create_task(self, task_data: dict) -> dict:
        """Create a standalone task for audit activities."""
        ...
```

### 7.4 Kafka Event Integration

```python
# Event publishing for cross-service communication
class AuditEventPublisher:
    """
    Publishes audit events to Kafka for consumption by other services.
    """
    
    TOPIC = "fims.audit.events"
    
    def publish_plan_approved(self, plan_id: str, approved_by: str):
        self.publish({
            "event_type": "audit.plan.approved",
            "payload": {
                "plan_id": plan_id,
                "approved_by": approved_by,
                "approved_at": datetime.utcnow().isoformat(),
            }
        })
    
    def publish_engagement_started(self, engagement_id: str, auditee_id: str):
        self.publish({
            "event_type": "audit.engagement.started",
            "payload": {
                "engagement_id": engagement_id,
                "auditee_id": auditee_id,
                "started_at": datetime.utcnow().isoformat(),
            }
        })
    
    def publish_finding_created(self, finding_id: str, severity: str):
        self.publish({
            "event_type": "audit.finding.created",
            "payload": {
                "finding_id": finding_id,
                "severity": severity,
                "created_at": datetime.utcnow().isoformat(),
            }
        })
    
    def publish_recommendation_due(self, recommendation_id: str, auditee_id: str):
        self.publish({
            "event_type": "audit.recommendation.due",
            "payload": {
                "recommendation_id": recommendation_id,
                "auditee_id": auditee_id,
            }
        })

# Event consumption
class AuditEventConsumer:
    """
    Consumes events from other services relevant to audit.
    """
    
    SUBSCRIBED_TOPICS = [
        "fims.iam.events",
        "fims.document.events",
        "fims.workflow.events",
    ]
    
    def handle_user_role_changed(self, payload):
        """Handle user role changes that may affect audit assignments."""
        ...
    
    def handle_document_approved(self, payload):
        """Handle document approval events for audit reports."""
        ...
    
    def handle_workflow_stage_completed(self, payload):
        """Handle workflow stage completion for audit workflows."""
        ...
```

---

## 8. Project Structure

### 8.1 Backend Service Structure

```
grc-service/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── docker-compose.prod-local.yml
├── manage.py
├── requirements.txt
├── env.example
├── README.md
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── authentication.py
│   │   ├── permissions.py
│   │   ├── permissions_jwt.py
│   │   │
│   │   ├── serializers/
│   │   │   ├── __init__.py
│   │   │   ├── audit_universe_serializers.py
│   │   │   ├── risk_assessment_serializers.py
│   │   │   ├── audit_plan_serializers.py
│   │   │   ├── audit_engagement_serializers.py
│   │   │   ├── audit_program_serializers.py
│   │   │   ├── working_paper_serializers.py
│   │   │   ├── audit_finding_serializers.py
│   │   │   ├── audit_report_serializers.py
│   │   │   ├── monitoring_serializers.py
│   │   │   └── analytics_serializers.py
│   │   │
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── health_view.py
│   │   │   ├── audit_universe_views.py
│   │   │   ├── risk_assessment_views.py
│   │   │   ├── audit_plan_views.py
│   │   │   ├── audit_engagement_views.py
│   │   │   ├── audit_program_views.py
│   │   │   ├── working_paper_views.py
│   │   │   ├── audit_finding_views.py
│   │   │   ├── audit_recommendation_views.py
│   │   │   ├── audit_report_views.py
│   │   │   ├── monitoring_views.py
│   │   │   ├── meeting_views.py
│   │   │   └── analytics_views.py
│   │   │
│   │   └── urls/
│   │       ├── __init__.py
│   │       ├── audit_universe.py
│   │       ├── risk_assessment.py
│   │       ├── audit_plan.py
│   │       ├── audit_engagement.py
│   │       ├── audit_report.py
│   │       ├── monitoring.py
│   │       └── analytics.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   │
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── audit_universe.py
│   │   │   ├── auditable_entity.py
│   │   │   ├── risk_assessment.py
│   │   │   ├── audit_plan.py
│   │   │   ├── audit_engagement.py
│   │   │   ├── audit_finding.py
│   │   │   └── audit_recommendation.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── iam_client.py
│   │   │   ├── document_client.py
│   │   │   ├── workflow_client.py
│   │   │   ├── notification_service.py
│   │   │   ├── report_generator.py
│   │   │   └── risk_calculator.py
│   │   │
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   ├── create_audit_plan.py
│   │   │   ├── approve_audit_plan.py
│   │   │   ├── create_engagement.py
│   │   │   ├── conduct_risk_assessment.py
│   │   │   ├── create_finding.py
│   │   │   ├── monitor_implementation.py
│   │   │   └── generate_quarterly_report.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── audit_plan_repository.py
│   │   │   ├── engagement_repository.py
│   │   │   ├── finding_repository.py
│   │   │   └── monitoring_repository.py
│   │   │
│   │   ├── permissions.py
│   │   ├── permissions_enforcement.py
│   │   ├── jwt_middleware.py
│   │   └── signals.py
│   │
│   └── infrastructure/
│       ├── __init__.py
│       │
│       ├── persistence/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── admin.py
│       │   └── migrations/
│       │
│       ├── messaging/
│       │   ├── __init__.py
│       │   ├── kafka_producer.py
│       │   ├── kafka_consumer.py
│       │   └── event_handlers.py
│       │
│       ├── external/
│       │   ├── __init__.py
│       │   ├── iam_adapter.py
│       │   ├── document_adapter.py
│       │   └── workflow_adapter.py
│       │
│       └── tasks/
│           ├── __init__.py
│           ├── celery_app.py
│           ├── monitoring_tasks.py
│           ├── notification_tasks.py
│           └── report_tasks.py
│
├── shared/
│   ├── __init__.py
│   ├── constants/
│   │   ├── __init__.py
│   │   ├── audit_status.py
│   │   └── risk_ratings.py
│   └── common/
│       ├── __init__.py
│       └── utils.py
│
├── templates/
│   ├── notifications/
│   │   ├── engagement_notification.html
│   │   ├── meeting_invitation.html
│   │   └── recommendation_reminder.html
│   └── reports/
│       ├── audit_report_template.html
│       └── quarterly_report_template.html
│
├── scripts/
│   ├── init-db/
│   │   └── init-postgres.sql
│   └── seed_data.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_audit_plan.py
│   ├── test_engagement.py
│   ├── test_findings.py
│   └── test_monitoring.py
│
├── logs/
├── media/
└── staticfiles/
```

### 8.2 Frontend Structure

```
frontend/apps/staff-portal/src/
├── pages/
│   └── grc/
│       ├── audit/
│       │   ├── AuditDashboardPage.tsx
│       │   ├── AuditUniversePage.tsx
│       │   ├── AuditUniverseDetailPage.tsx
│       │   ├── RiskAssessmentsPage.tsx
│       │   ├── RiskAssessmentDetailPage.tsx
│       │   ├── AuditPlansPage.tsx
│       │   ├── AuditPlanDetailPage.tsx
│       │   ├── EngagementsPage.tsx
│       │   ├── EngagementDetailPage.tsx
│       │   ├── AuditProgramPage.tsx
│       │   ├── WorkingPapersPage.tsx
│       │   ├── FindingsPage.tsx
│       │   ├── FindingDetailPage.tsx
│       │   ├── RecommendationsPage.tsx
│       │   ├── MonitoringPage.tsx
│       │   ├── MeetingsPage.tsx
│       │   ├── AuditReportsPage.tsx
│       │   ├── AuditReportDetailPage.tsx
│       │   ├── QuarterlyReportsPage.tsx
│       │   └── QuarterlyReportDetailPage.tsx
│       │
│       ├── risk/
│       │   └── (Phase 2 - Risk Management)
│       │
│       └── legal/
│           └── (Phase 3 - Legal Services)
│
└── components/
    └── grc/
        ├── audit/
        │   ├── dialogs/
        │   │   ├── CreateAuditUniverseDialog.tsx
        │   │   ├── CreateAuditableEntityDialog.tsx
        │   │   ├── CreateRiskAssessmentDialog.tsx
        │   │   ├── CreateAuditPlanDialog.tsx
        │   │   ├── CreateEngagementDialog.tsx
        │   │   ├── CreateAuditProgramDialog.tsx
        │   │   ├── CreateWorkingPaperDialog.tsx
        │   │   ├── CreateFindingDialog.tsx
        │   │   ├── CreateRecommendationDialog.tsx
        │   │   ├── CreateMeetingDialog.tsx
        │   │   ├── ScheduleMeetingDialog.tsx
        │   │   ├── UpdateMonitoringDialog.tsx
        │   │   └── IndependenceDeclarationDialog.tsx
        │   │
        │   ├── detail/
        │   │   ├── AuditUniverseDetail.tsx
        │   │   ├── AuditPlanDetail.tsx
        │   │   ├── EngagementDetail.tsx
        │   │   ├── FindingDetail.tsx
        │   │   ├── RecommendationDetail.tsx
        │   │   └── ReportDetail.tsx
        │   │
        │   ├── forms/
        │   │   ├── RiskAssessmentForm.tsx
        │   │   ├── RiskControlMatrixForm.tsx
        │   │   ├── WorkingPaperForm.tsx
        │   │   ├── FindingForm.tsx
        │   │   ├── MeetingMinutesForm.tsx
        │   │   └── MonitoringStatusForm.tsx
        │   │
        │   ├── tables/
        │   │   ├── AuditUniverseTable.tsx
        │   │   ├── RiskAssessmentTable.tsx
        │   │   ├── AuditPlanTable.tsx
        │   │   ├── EngagementTable.tsx
        │   │   ├── FindingsTable.tsx
        │   │   ├── RecommendationsTable.tsx
        │   │   └── MonitoringTable.tsx
        │   │
        │   ├── cards/
        │   │   ├── PlanSummaryCard.tsx
        │   │   ├── EngagementProgressCard.tsx
        │   │   ├── RiskSummaryCard.tsx
        │   │   ├── ImplementationRateCard.tsx
        │   │   └── AuditorWorkloadCard.tsx
        │   │
        │   ├── charts/
        │   │   ├── RiskDistributionChart.tsx
        │   │   ├── FindingsTrendChart.tsx
        │   │   ├── ImplementationProgressChart.tsx
        │   │   └── EngagementTimelineChart.tsx
        │   │
        │   └── workflows/
        │       ├── AuditPlanWorkflow.tsx
        │       ├── EngagementWorkflow.tsx
        │       ├── ReportApprovalWorkflow.tsx
        │       └── WorkflowStageIndicator.tsx
        │
        ├── risk/
        │   └── (Phase 2)
        │
        └── legal/
            └── (Phase 3)
```

---

## 9. Configuration Files

### 9.1 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres-grc-service:
    image: postgres:15-alpine
    container_name: postgres-grc-service
    environment:
      POSTGRES_DB: ${DB_NAME:-fims_grc}
      POSTGRES_USER: ${DB_USER:-grc_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-grc_password_2024}
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    ports:
      - "5437:5432"
    volumes:
      - postgres_grc_data:/var/lib/postgresql/data
      - ./scripts/init-db/init-postgres.sql:/docker-entrypoint-initdb.d/init-postgres.sql:ro
    networks:
      - fims-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-grc_user} -d ${DB_NAME:-fims_grc}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis-grc-service:
    image: redis:7-alpine
    container_name: redis-grc-service
    ports:
      - "${REDIS_PORT:-6384}:6379"
    volumes:
      - redis_grc_data:/data
    networks:
      - fims-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  grc-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fims-grc-service
    ports:
      - "${SERVICE_PORT:-8006}:8006"
    env_file:
      - .env
    volumes:
      - ./media:/app/media
      - ./staticfiles:/app/staticfiles
      - ./logs:/app/logs
    depends_on:
      postgres-grc-service:
        condition: service_healthy
      redis-grc-service:
        condition: service_healthy
    networks:
      - fims-network
    restart: unless-stopped
    command: >
      sh -c "
        echo 'Waiting for dependencies...' &&
        echo 'Running migrations...' &&
        python manage.py migrate &&
        echo 'Collecting static files...' &&
        python manage.py collectstatic --noinput &&
        echo 'Starting GRC service with gunicorn...' &&
        gunicorn config.wsgi:application --bind 0.0.0.0:8006 --workers 4 --timeout 120
      "
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8006/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  grc-celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fims-grc-celery-worker
    command: celery -A apps.infrastructure.tasks.celery_app worker -l info --concurrency=4
    env_file:
      - .env
    volumes:
      - ./media:/app/media
      - ./logs:/app/logs
    depends_on:
      postgres-grc-service:
        condition: service_healthy
      redis-grc-service:
        condition: service_healthy
    networks:
      - fims-network
    restart: unless-stopped

  grc-celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fims-grc-celery-beat
    command: celery -A apps.infrastructure.tasks.celery_app beat -l info
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    depends_on:
      postgres-grc-service:
        condition: service_healthy
      redis-grc-service:
        condition: service_healthy
    networks:
      - fims-network
    restart: unless-stopped

volumes:
  postgres_grc_data:
  redis_grc_data:

networks:
  fims-network:
    external: true
```



### 9.2 Requirements.txt

# Core platform
Django==4.2.7
djangorestframework==3.14.0
django-cors-headers==4.3.0
django-filter==23.3

# Messaging & async
celery[redis]==5.3.4
redis==4.6.0
kafka-python==2.0.2
confluent-kafka==2.3.0

# Persistence & utilities
psycopg2-binary==2.9.9
python-dotenv==1.0.0
requests==2.31.0

# API documentation
drf-spectacular==0.27.2
drf-spectacular-sidecar==2023.10.1

# Authentication
djangorestframework-simplejwt==5.3.0
PyJWT==2.8.0

# Report generation
reportlab==4.0.7
openpyxl==3.1.2
python-docx==0.8.11
weasyprint==60.1

# Email & Notifications
django-anymail==10.1

# Production Server
gunicorn==21.2.0
whitenoise==6.6.0

# Testing
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
factory-boy==3.3.0
faker==19.6.2

# Monitoring
django-structlog==4.0.0
structlog==23.1.0



### 9.3 Environment Variables

```bash
# env.example

# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,grc-service

# Database
DB_NAME=fims_grc
DB_USER=grc_user
DB_PASSWORD=grc_password_2024
DB_HOST=postgres-grc-service
DB_PORT=5432

# Redis
REDIS_URL=redis://redis-grc-service:6379/0
CELERY_BROKER_URL=redis://redis-grc-service:6379/1
CELERY_RESULT_BACKEND=redis://redis-grc-service:6379/2

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_GRC_TOPIC=fims.grc.events

# Service URLs
IAM_SERVICE_URL=http://iam-service:8000
DOCUMENT_SERVICE_URL=http://document-records-service:8002
WORK_ORCHESTRATION_URL=http://work-orchestration-service:8003

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440

# Service Configuration
SERVICE_NAME=grc-service
SERVICE_PORT=8006

# Email Configuration (for notifications)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=notifications@fcc.go.ke
EMAIL_HOST_PASSWORD=email-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=FCC GRC System <notifications@fcc.go.ke>

# External Domain
TUNNEL_DOMAIN=fcc.tunnel.ictpack.net
EXTERNAL_DOMAIN=fcc.tunnel.ictpack.net
```

---

## 10. Security Considerations

### 10.1 Authentication & Authorization

```python
# Permission definitions for GRC Audit module
AUDIT_PERMISSIONS = {
    # Universe Management
    'audit.universe.create': 'Create Audit Universe',
    'audit.universe.read': 'View Audit Universe',
    'audit.universe.update': 'Update Audit Universe',
    'audit.universe.delete': 'Delete Audit Universe',
    'audit.universe.approve': 'Approve Audit Universe',
    
    # Risk Assessment
    'audit.risk.create': 'Create Risk Assessment',
    'audit.risk.read': 'View Risk Assessment',
    'audit.risk.update': 'Update Risk Assessment',
    'audit.risk.approve': 'Approve Risk Assessment',
    
    # Audit Plan
    'audit.plan.create': 'Create Audit Plan',
    'audit.plan.read': 'View Audit Plan',
    'audit.plan.update': 'Update Audit Plan',
    'audit.plan.delete': 'Delete Audit Plan',
    'audit.plan.submit_management': 'Submit Plan to Management',
    'audit.plan.management_adopt': 'Adopt Plan (Management)',
    'audit.plan.submit_committee': 'Submit Plan to Committee',
    'audit.plan.committee_approve': 'Approve Plan (Committee)',
    
    # Audit Engagement
    'audit.engagement.create': 'Create Audit Engagement',
    'audit.engagement.read': 'View Audit Engagement',
    'audit.engagement.update': 'Update Audit Engagement',
    'audit.engagement.assign_team': 'Assign Audit Team',
    'audit.engagement.approve_program': 'Approve Audit Program',
    
    # Working Papers
    'audit.paper.create': 'Create Working Paper',
    'audit.paper.read': 'View Working Paper',
    'audit.paper.update': 'Update Working Paper',
    'audit.paper.review': 'Review Working Paper',
    'audit.paper.approve': 'Approve Working Paper',
    
    # Findings & Recommendations
    'audit.finding.create': 'Create Audit Finding',
    'audit.finding.read': 'View Audit Finding',
    'audit.finding.update': 'Update Audit Finding',
    'audit.recommendation.create': 'Create Recommendation',
    'audit.recommendation.update': 'Update Recommendation',
    
    # Reports
    'audit.report.create': 'Create Audit Report',
    'audit.report.read': 'View Audit Report',
    'audit.report.update': 'Update Audit Report',
    'audit.report.approve': 'Approve Audit Report',
    'audit.report.distribute': 'Distribute Audit Report',
    
    # Monitoring
    'audit.monitoring.read': 'View Implementation Monitoring',
    'audit.monitoring.update': 'Update Implementation Status',
    'audit.monitoring.verify': 'Verify Implementation',
    
    # Analytics
    'audit.analytics.view': 'View Audit Analytics',
}

# Role-based permission mapping
ROLE_PERMISSIONS = {
    'InternalAuditor': [
        'audit.universe.create', 'audit.universe.read', 'audit.universe.update',
        'audit.risk.create', 'audit.risk.read', 'audit.risk.update',
        'audit.plan.create', 'audit.plan.read', 'audit.plan.update',
        'audit.engagement.read', 'audit.engagement.update',
        'audit.paper.create', 'audit.paper.read', 'audit.paper.update',
        'audit.finding.create', 'audit.finding.read', 'audit.finding.update',
        'audit.recommendation.create', 'audit.recommendation.update',
        'audit.report.create', 'audit.report.read', 'audit.report.update',
        'audit.monitoring.read', 'audit.monitoring.update',
    ],
    
    'LeadAuditor': [
        # All Internal Auditor permissions plus:
        'audit.engagement.create', 'audit.engagement.assign_team',
        'audit.paper.review',
    ],
    
    'ChiefInternalAuditor': [
        # All Lead Auditor permissions plus:
        'audit.universe.approve', 'audit.universe.delete',
        'audit.risk.approve',
        'audit.plan.submit_management', 'audit.plan.delete',
        'audit.engagement.approve_program',
        'audit.paper.approve',
        'audit.report.approve', 'audit.report.distribute',
        'audit.monitoring.verify',
        'audit.analytics.view',
    ],
    
    'Management': [
        'audit.plan.read', 'audit.plan.management_adopt',
        'audit.report.read',
        'audit.monitoring.read',
        'audit.analytics.view',
    ],
    
    'AuditCommittee': [
        'audit.plan.read', 'audit.plan.committee_approve',
        'audit.report.read',
        'audit.monitoring.read',
        'audit.analytics.view',
    ],
    
    'Auditee': [
        'audit.engagement.read',
        'audit.finding.read',
        'audit.recommendation.read',
        'audit.monitoring.read', 'audit.monitoring.update',
    ],
}
```

### 10.2 Data Protection

- All sensitive audit data encrypted at rest
- Audit trails for all data modifications
- Role-based access control enforced at API level
- JWT tokens validated against IAM service
- Confidential audit findings protected with additional access controls

---

## 11. Testing Strategy

### 11.1 Test Categories

```python
# tests/conftest.py
import pytest
from rest_framework.test import APIClient
from apps.infrastructure.persistence.models import (
    AuditUniverse, AuditableEntity, RiskAssessment,
    AuditPlan, AuditEngagement, AuditFinding
)

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, mock_jwt_token):
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {mock_jwt_token}')
    return api_client

@pytest.fixture
def sample_audit_universe(db):
    return AuditUniverse.objects.create(
        fiscal_year='2024/2025',
        description='Test Audit Universe',
        status='approved',
        created_by='user-uuid-123'
    )

# tests/test_audit_plan.py
class TestAuditPlanAPI:
    
    def test_create_audit_plan(self, authenticated_client, sample_audit_universe):
        """Test creating a new audit plan."""
        response = authenticated_client.post('/api/v1/audit/plans/', {
            'title': 'FY 2024/2025 RBIAP',
            'fiscal_year': '2024/2025',
            'plan_type': 'annual',
            'audit_universe_id': str(sample_audit_universe.id),
        })
        assert response.status_code == 201
        assert response.data['reference_number'].startswith('RBIAP-')
    
    def test_submit_plan_to_management(self, authenticated_client, sample_audit_plan):
        """Test submitting plan for management review."""
        response = authenticated_client.post(
            f'/api/v1/audit/plans/{sample_audit_plan.id}/submit-to-management/'
        )
        assert response.status_code == 200
        assert response.data['status'] == 'management_review'
    
    def test_management_cannot_modify_plan(self, management_client, sample_audit_plan):
        """Test that management cannot modify audit plan content."""
        response = management_client.put(
            f'/api/v1/audit/plans/{sample_audit_plan.id}/',
            {'title': 'Modified Title'}
        )
        assert response.status_code == 403
```

---

## 12. Deployment Considerations

### 12.1 Service Discovery

The GRC Service will be registered with the API Gateway for routing:

```nginx
# API Gateway configuration addition
location /api/v1/audit/ {
    proxy_pass http://grc-service:8006/api/v1/audit/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /api/v1/risk/ {
    proxy_pass http://grc-service:8006/api/v1/risk/;
    # ... same headers
}

location /api/v1/legal/ {
    proxy_pass http://grc-service:8006/api/v1/legal/;
    # ... same headers
}
```

### 12.2 Database Migrations

```bash
# Initial migration commands
python manage.py makemigrations
python manage.py migrate

# Seed initial data
python manage.py loaddata initial_audit_data
```

### 12.3 Health Checks

```python
# Health check endpoint
@api_view(['GET'])
def health_check(request):
    checks = {
        'database': check_database(),
        'redis': check_redis(),
        'kafka': check_kafka(),
        'iam_service': check_iam_service(),
        'document_service': check_document_service(),
        'workflow_service': check_workflow_service(),
    }
    
    all_healthy = all(checks.values())
    
    return Response({
        'status': 'healthy' if all_healthy else 'degraded',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }, status=200 if all_healthy else 503)
```

---

## 13. Monitoring & Observability

### 13.1 Metrics to Track

- Audit plan creation and approval rates
- Average time to complete audit engagements
- Finding severity distribution
- Recommendation implementation rates
- Overdue monitoring items
- API response times
- Error rates by endpoint

### 13.2 Logging

```python
# Structured logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.dev.ConsoleRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/grc-service.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'apps.api': {'handlers': ['console', 'file'], 'level': 'INFO'},
        'apps.core': {'handlers': ['console', 'file'], 'level': 'INFO'},
        'apps.infrastructure': {'handlers': ['console', 'file'], 'level': 'INFO'},
    },
}
```

---

## 14. Future Phases

### Phase 2: Risk Management Module
- Risk Register Management
- Risk Identification & Assessment
- Risk Treatment Plans
- Risk Monitoring & Reporting
- Risk Dashboard & Analytics

### Phase 3: Legal Services Module
- Legal Opinions Management
- Court Applications (FCC Suing)
- Litigation Defense (FCC Sued)
- Commission Determinations
- Legal Document Management

---

## 15. Appendices

### Appendix A: Status Transition Diagrams

#### A.1 Audit Plan Status Flow
```
draft → under_cia_review → management_review → committee_review → approved → implementation
                ↓                    ↓                  ↓
           returned            request_changes    request_improvement
                ↓                    ↓                  ↓
              draft          under_cia_review    under_cia_review
```

#### A.2 Audit Engagement Status Flow
```
planning → program_approval → notification → entry_meeting → fieldwork 
    → working_paper_review → pre_exit_meeting → draft_report → exit_meeting 
    → final_report → distribution → completed
```

#### A.3 Recommendation Implementation Status Flow
```
open → in_progress → implemented → verified → closed
                ↓          ↓
            overdue    not_verified
                          ↓
                    in_progress
```

### Appendix B: Document Type Mappings

-----------------------------------------------------
| Audit Artifact           | Document Type Code     |
|--------------------------|------------------------|
| Audit Universe           | GRC-AUDIT-UNIVERSE     |
| Risk Assessment          | GRC-RISK-ASSESSMENT    |
| Audit Plan               | GRC-AUDIT-PLAN         |
| Engagement Notification  | GRC-ENG-NOTIFICATION   |
| Independence Declaration | GRC-IND-DECLARATION    |
| Audit Program            | GRC-AUDIT-PROGRAM      |
| Working Paper            | GRC-WORKING-PAPER      |
| Entry Meeting Minutes    | GRC-ENTRY-MINUTES      |
| Exit Meeting Minutes     | GRC-EXIT-MINUTES       |
| Draft Audit Report       | GRC-DRAFT-REPORT       |
| Final Audit Report       | GRC-FINAL-REPORT       |
| Quarterly Report         | GRC-QUARTERLY-REPORT   |
-----------------------------------------------------


### Appendix C: Kafka Event Types

--------------------------------------------------------------------------------
| Event Type                        | Description                              |
|-----------------------------------|------------------------------------------|
| audit.universe.created            | New audit universe created               |
| audit.universe.approved           | Audit universe approved                  |
| audit.plan.created                | New audit plan created                   |
| audit.plan.submitted              | Plan submitted for review                |
| audit.plan.approved               | Plan approved by committee               |
| audit.engagement.started          | Audit engagement initiated               |
| audit.engagement.completed        | Engagement fieldwork completed           |
| audit.finding.created             | New audit finding recorded               |
| audit.recommendation.created      | New recommendation created               |
| audit.recommendation.due          | Recommendation approaching deadline      |
| audit.recommendation.overdue      | Recommendation past deadline             |
| audit.report.approved             | Audit report approved                    |
| audit.report.distributed          | Report distributed to stakeholders       |
--------------------------------------------------------------------------------


---

## 16. Revision History

------------------------------------------------------------------------
| Version | Date       | Author           | Changes                    |
|---------|------------|------------------|----------------------------|
| 1.0     | 2024-XX-XX | System Architect | Initial design document    |
------------------------------------------------------------------------


---

**Document Status**: Draft  
**Review Required**: Technical Lead, Project Manager, Business Analyst  
**Next Review Date**: TBD

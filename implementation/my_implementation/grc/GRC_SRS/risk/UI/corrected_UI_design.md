# Risk Management & Quality Assurance Module — Corrected UI Design
*(100% aligned with SRS: RISK_MANAGEMENT.md & Risk_Management_Module_Core_Design.md)*

---

## SIDEBAR NAVIGATION STRUCTURE

```
🛡️  RISK MANAGEMENT & QUALITY ASSURANCE
│
├── Dashboard
├── Risk Settings
├── Risk Champions
├── Risk Assessment Sheets
├── Departmental Risk Registers
├── Institutional Risk Register
├── Risk Treatment Plan (RTAP)
├── Quarterly Performance Reports
└── Quality Assurance
      ├── Quality Auditors
      ├── QMS Audit Programs
      └── Non-Conformances
```


Risk Management

Risk Settings
Risk Champions
Departmental Risks
Institutional Risks
Risk Treatment Plans


Quality Assurance

Quality Auditors
Quality Audits

> NOTE: QMS Audit Plans are NOT in the sidebar — they are always accessed from a QMS Audit Program
> detail page. "Risk Rate" from the demo does NOT exist — the correct model is `RiskLevel`.
> Non-Conformances are raised from Audit Report pages but have a top-level list view for tracking.

---

### Route Definitions

```tsx
// All routes under ServiceProtectedRoute serviceKey="grc"
/service/grc/risk/                               → RiskDashboardPage
/service/grc/risk/settings                       → RiskSettingsPage
/service/grc/risk/champions                      → RiskChampionsPage
/service/grc/risk/champions/:id                  → RiskChampionDetailPage
/service/grc/risk/assessments                    → RiskAssessmentSheetsPage
/service/grc/risk/dept-registers                 → DeptRiskRegistersPage
/service/grc/risk/dept-registers/:id             → DeptRiskRegisterDetailPage
/service/grc/risk/institutional-register         → InstitutionalRiskRegisterPage
/service/grc/risk/institutional-register/:id     → InstitutionalRiskRegisterDetailPage
/service/grc/risk/rtap                           → RTAPPage
/service/grc/risk/rtap/:id                       → RTAPDetailPage
/service/grc/risk/quarterly-reports              → QuarterlyReportsPage
/service/grc/risk/quarterly-reports/:id          → QuarterlyReportDetailPage
/service/grc/risk/quality-auditors               → QualityAuditorsPage
/service/grc/risk/quality-auditors/:id           → QualityAuditorDetailPage
/service/grc/risk/qms-programs                   → QMSAuditProgramsPage
/service/grc/risk/qms-programs/:id               → QMSAuditProgramDetailPage
/service/grc/risk/qms-plans/:id                  → QMSAuditPlanDetailPage
/service/grc/risk/non-conformances               → NonConformancesPage
```

---

### Frontend File & Folder Structure

```
frontend/apps/staff/src/
│
├── pages/grc/risk/
│     ├── RiskDashboardPage.tsx
│     ├── RiskSettingsPage.tsx
│     ├── RiskChampionsPage.tsx
│     ├── RiskChampionDetailPage.tsx
│     ├── RiskAssessmentSheetsPage.tsx
│     ├── DeptRiskRegistersPage.tsx
│     ├── DeptRiskRegisterDetailPage.tsx
│     ├── InstitutionalRiskRegisterPage.tsx
│     ├── InstitutionalRiskRegisterDetailPage.tsx
│     ├── RTAPPage.tsx
│     ├── RTAPDetailPage.tsx
│     ├── QuarterlyReportsPage.tsx
│     ├── QuarterlyReportDetailPage.tsx
│     ├── QualityAuditorsPage.tsx
│     ├── QMSAuditProgramsPage.tsx
│     ├── QMSAuditProgramDetailPage.tsx
│     ├── QMSAuditPlanDetailPage.tsx
│     └── NonConformancesPage.tsx
│
├── components/grc/risk/
│     ├── CreateRiskChampionDialog.tsx
│     ├── CreateRiskAssessmentDialog.tsx
│     ├── EditRiskAssessmentDialog.tsx
│     ├── CreateDeptRegisterDialog.tsx
│     ├── CreateInstitutionalRegisterDialog.tsx
│     ├── AddInstitutionalEntryDialog.tsx
│     ├── CreateRTAPItemDialog.tsx
│     ├── RTAPItemStatusEditDialog.tsx
│     ├── SubmitQuarterlyUpdateDialog.tsx
│     ├── CreateQuarterlyReportDialog.tsx
│     ├── SubmitActivityReportDialog.tsx
│     ├── CreateQualityAuditorDialog.tsx
│     ├── RecordExamResultDialog.tsx
│     ├── CreateQMSProgramDialog.tsx
│     ├── CreateQMSPlanDialog.tsx
│     ├── AssignAuditorDialog.tsx
│     ├── LinkRiskAssessmentDialog.tsx
│     └── RaiseNonConformanceDialog.tsx
│
├── hooks/risk/
│     ├── useRiskPermissions.tsx
│     ├── useRiskSettings.ts
│     ├── useRiskChampions.ts
│     ├── useRiskAssessments.ts
│     ├── useDeptRiskRegisters.ts
│     ├── useInstitutionalRegisters.ts
│     ├── useRTAP.ts
│     ├── useQuarterlyRiskReports.ts
│     ├── useQualityAuditors.ts
│     ├── useQMSAudit.ts
│     ├── useNonConformances.ts
│     └── riskKeys.ts
│
├── services/
│     └── riskService.ts
│
└── types/
      └── risk.ts
```

---

### Permissions Hook — `useRiskPermissions.tsx`

```tsx
// Reads permissions_flat from JWT; returns boolean flags
export function useRiskPermissions() {
  const { permissions } = useAuth();
  return {
    canManageRiskSettings:    permissions.includes('grc:risk_settings:manage'),
    canViewChampions:         permissions.includes('grc:risk_champion:view'),
    canManageChampions:       permissions.includes('grc:risk_champion:manage'),
    canConductAssessments:    permissions.includes('grc:risk_assessment:conduct'),
    canReviewAssessments:     permissions.includes('grc:risk_assessment:review'),
    canManageDeptRegisters:   permissions.includes('grc:dept_risk_register:manage'),
    canApproveDeptRegisters:  permissions.includes('grc:dept_risk_register:approve'),
    canManageIRR:             permissions.includes('grc:institutional_risk_register:manage'),
    canApproveIRR:            permissions.includes('grc:institutional_risk_register:approve'),
    canManageRTAP:            permissions.includes('grc:rtap:manage'),
    canApproveRTAP:           permissions.includes('grc:rtap:approve'),
    canRespondRTAP:           permissions.includes('grc:rtap:respond'),
    canManageQuarterlyReport: permissions.includes('grc:quarterly_risk_report:manage'),
    canApproveQuarterlyReport:permissions.includes('grc:quarterly_risk_report:approve'),
    canManageQualityAuditors: permissions.includes('grc:quality_auditor:manage'),
    canManageQMSPrograms:     permissions.includes('grc:qms_audit_program:manage'),
    canApproveQMSPrograms:    permissions.includes('grc:qms_audit_program:approve'),
    canManageQMSPlans:        permissions.includes('grc:qms_audit_plan:manage'),
    canApproveQMSPlans:       permissions.includes('grc:qms_audit_plan:approve'),
    canManageChecklists:      permissions.includes('grc:qms_checklist:manage'),
    canManageAuditReports:    permissions.includes('grc:qms_audit_report:manage'),
    canSignAuditReports:      permissions.includes('grc:qms_audit_report:sign'),
    canManageNonConformances: permissions.includes('grc:non_conformance:manage'),
    canRespondNonConformances:permissions.includes('grc:non_conformance:respond'),
    canViewDashboard:         permissions.includes('grc:risk_dashboard:view'),
  };
}
```

---

### Status Badge Color Map

```tsx
// components/grc/risk/RiskStatusBadge.tsx
const STATUS_CLASSES: Record<string, string> = {
  draft:              'bg-gray-100 text-gray-800',
  submitted:          'bg-yellow-100 text-yellow-800',
  approved:           'bg-green-100 text-green-800',
  rejected:           'bg-red-100 text-red-800',
  signed:             'bg-blue-100 text-blue-800',
  rmqam_review:       'bg-purple-100 text-purple-800',
  management_review:  'bg-indigo-100 text-indigo-800',
  committee_review:   'bg-violet-100 text-violet-800',
  commission_review:  'bg-fuchsia-100 text-fuchsia-800',
  in_progress:        'bg-blue-100 text-blue-800',
  completed:          'bg-green-100 text-green-800',
  not_started:        'bg-gray-100 text-gray-800',
  raised:             'bg-red-100 text-red-800',
  acknowledged:       'bg-amber-100 text-amber-800',
  closed:             'bg-green-100 text-green-800',
  active:             'bg-green-100 text-green-800',
  inactive:           'bg-gray-100 text-gray-800',
  certified:          'bg-emerald-100 text-emerald-800',
  tl_signed:          'bg-blue-100 text-blue-800',
  auditee_acknowledged: 'bg-teal-100 text-teal-800',
  finalised:          'bg-green-100 text-green-800',
};

// RiskLevel badges use inline style:  style={{ backgroundColor: riskLevel.color_code, color: '#fff' }}
```

---

---

## 1. DASHBOARD
URL: /service/grc/risk/

Risk Management & Quality Assurance
Overview of all active risk control, treatment, and quality assurance activity

---
Summary Cards Row 1:
[Active Risk Champions: 6]   [Open Dept Registers: 3]   [IRR Status: Under Committee Review]   [Open NCs: 4]

Summary Cards Row 2:
[Overdue RTAP Items: 2]   [Upcoming Audit Plans: 1]   [Certified Quality Auditors: 5]   [Next QPR Due: Q2 FY 2025/26]

---
Quick Links:
[New Risk Assessment]  [View IRR]  [View RTAP]  [Record Non-Conformance]

---
Active Workflows Panel:
  ┌─────────────────────────────────────────────────────────────────┐
  │ ONGOING GOVERNANCE WORKFLOWS                                    │
  ├─────────────────────────────────────────────────────────────────┤
  │ IRR FY 2025/26           Committee Review    [View →]          │
  │ RTAP FY 2025/26          Management Review   [View →]          │
  │ QPR Q1 FY 2025/26        Approved ✓          [View →]          │
  │ QMS Audit Program FY…    Draft               [View →]          │
  └─────────────────────────────────────────────────────────────────┘

---
Risk Distribution Chart:
  Bar chart: Count of risk assessments by RiskLevel (colour-coded using RiskLevel.color_code)
  X-axis: Risk Level labels (Low / Medium / High / Critical)
  Y-axis: Number of risk assessments

---
Data: GET /api/v1/grc/risk/dashboard/
Component: RiskDashboardPage.tsx
Permission gate: canViewDashboard

---

---

## 2. RISK SETTINGS
URL: /service/grc/risk/settings

Risk Settings
Manage global lookup tables used across the Risk Management module

> PermissionGate: canManageRiskSettings
> Unauthorised users see a locked view with a "Contact RMQAM to modify settings" message.

---
Page Layout: Full-width with a tab strip across the top (8 tabs)

[ Risk Categories ] [ Likelihood ] [ Impact ] [ Risk Levels ] [ Sectors ] [ Strategic Objectives ] [ ISO Clauses ] [ NC Types ]

---
All tabs share the same layout pattern:
  [+ Add New]   [Search...]
  | Name / Code | Details | Actions |
  Showing X–Y of Z | Rows per page: 10

---

### TAB 1: Risk Categories
Component: RiskSettingsPage.tsx (tabbed)
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/categories/

| Name               | Description                                  | Actions        |
|--------------------|----------------------------------------------|----------------|
| Strategic          | Risks linked to strategic objectives.        | [Edit] [Delete] |
| Operational        | Day-to-day process and system failures.      | [Edit] [Delete] |
| Financial          | Budget, revenue, and expenditure risks.      | [Edit] [Delete] |
| Compliance         | Regulatory and legal compliance failures.    | [Edit] [Delete] |
| Reputational       | Risks to FCC's public image.                 | [Edit] [Delete] |

On [+ Add New]:

Add Risk Category

Name *
  [Enter category name                ]

Description
  [Enter description...               ]

[Cancel]  [Save]

> Delete is disabled if any RiskAssessmentSheet references this category.
> Show tooltip: "Cannot delete — in use by X risk assessments."

---

### TAB 2: Risk Likelihood
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/likelihoods/

| Label      | Numerical Value | Description                              | Actions        |
|------------|-----------------|------------------------------------------|----------------|
| Rare       | 1               | May occur only in exceptional circumstances | [Edit] [Delete] |
| Unlikely   | 2               | Could occur at some time.                | [Edit] [Delete] |
| Possible   | 3               | Might occur at some time.                | [Edit] [Delete] |
| Likely     | 4               | Will probably occur.                     | [Edit] [Delete] |
| Almost Certain | 5           | Expected to occur in most circumstances. | [Edit] [Delete] |

On [+ Add New]:

Add Risk Likelihood

Label *
  [Enter likelihood label             ]

Numerical Value *
  [Enter integer 1–10                 ]

Description
  [Enter description...               ]

[Cancel]  [Save]

---

### TAB 3: Risk Impact
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/impacts/

| Label        | Numerical Value | Description                                     | Actions        |
|--------------|-----------------|-------------------------------------------------|----------------|
| Insignificant | 1              | Negligible effect on operations.                | [Edit] [Delete] |
| Minor        | 2               | Minor disruption, managed within normal ops.    | [Edit] [Delete] |
| Moderate     | 3               | Significant disruption, recovery possible.      | [Edit] [Delete] |
| Major        | 4               | Significant impact on objectives.               | [Edit] [Delete] |
| Catastrophic | 5               | Severe, long-term impact on operations.         | [Edit] [Delete] |

On [+ Add New]:

Add Risk Impact

Label *
  [Enter impact label                 ]

Numerical Value *
  [Enter integer 1–10                 ]

Description
  [Enter description...               ]

[Cancel]  [Save]

---

### TAB 4: Risk Levels
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/levels/

> NOTE: This is "RiskLevel", NOT "Risk Rate". The demo UI's "Risk Rate" label is incorrect.

| Label    | Min Score | Max Score | Colour       | Actions        |
|----------|-----------|-----------|--------------|----------------|
| Low      | 1         | 5         | 🟢 #4CAF50   | [Edit] [Delete] |
| Medium   | 6         | 12        | 🟡 #FFC107   | [Edit] [Delete] |
| High     | 13        | 19        | 🟠 #FF9800   | [Edit] [Delete] |
| Critical | 20        | 25        | 🔴 #F44336   | [Edit] [Delete] |

Colour column renders a small swatch div + hex string.

On [+ Add New]:

Add Risk Level

Label *
  [Enter level label (e.g. "Critical") ]

Min Score *
  [Enter minimum risk score (inclusive)]

Max Score *
  [Enter maximum risk score (inclusive)]

Colour Code *
  [#RRGGBB colour picker               ]

[Cancel]  [Save]

> Validation: min_score < max_score; ranges must not overlap with existing levels.

---

### TAB 5: Risk Sectors
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/sectors/

| Label              | Description                        | Actions        |
|--------------------|------------------------------------|----------------|
| Financial Sector   | Banking and financial institutions | [Edit] [Delete] |
| Energy Sector      | Oil, gas, and utility providers    | [Edit] [Delete] |
| Telecommunications | Telecom operators                  | [Edit] [Delete] |

On [+ Add New]:

Add Risk Sector

Label *
  [Enter sector name                  ]

Description
  [Enter description...               ]

[Cancel]  [Save]

---

### TAB 6: Strategic Objectives
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/objectives/

| Code    | Description                                              | Actions        |
|---------|----------------------------------------------------------|----------------|
| SO-01   | Promote fair competition in all economic sectors.        | [Edit] [Delete] |
| SO-02   | Strengthen institutional capacity and governance.        | [Edit] [Delete] |
| SO-03   | Enhance stakeholder engagement and public awareness.     | [Edit] [Delete] |

On [+ Add New]:

Add Strategic Objective

Code *
  [e.g. SO-04                         ]

Description *
  [Enter strategic objective text     ]

[Cancel]  [Save]

---

### TAB 7: ISO Clauses
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/iso-clauses/

> Used by QMS Audit Checklists. Each checklist item is anchored to one ISO Clause.

| Clause Number | Title                                   | Actions        |
|---------------|-----------------------------------------|----------------|
| 4.1           | Understanding the organisation          | [Edit] [Delete] |
| 6.1           | Actions to address risks and opportunities | [Edit] [Delete] |
| 7.1           | Resources                               | [Edit] [Delete] |
| 8.1           | Operational planning and control        | [Edit] [Delete] |
| 9.1           | Monitoring, measurement, analysis       | [Edit] [Delete] |
| 10.2          | Nonconformity and corrective action     | [Edit] [Delete] |

On [+ Add New]:

Add ISO Clause

Clause Number *
  [e.g. 4.2                           ]

Title *
  [Enter clause title                 ]

[Cancel]  [Save]

---

### TAB 8: Non-Conformance Types
API: GET/POST/PATCH/DELETE /api/v1/grc/risk/settings/nc-types/

> Used to classify non-conformances raised from QMS Audit Reports.

| Label                      | Actions        |
|----------------------------|----------------|
| Minor Non-Conformance       | [Edit] [Delete] |
| Major Non-Conformance       | [Edit] [Delete] |
| Observation                | [Edit] [Delete] |

On [+ Add New]:

Add Non-Conformance Type

Label *
  [Enter NC type label                ]

[Cancel]  [Save]

---

---

## 3. RISK CHAMPIONS
URL: /service/grc/risk/champions
File: RiskChampionsPage.tsx

Risk Champions
Manage designated Risk Champions across organisational units

[+ Nominate Risk Champion]   [Search champions...]   [All Units ▼]   [All Statuses ▼]   [FY ▼]

---
Summary Cards:
[Total Champions: 8]   [Active: 6]   [Inactive: 2]   [Pending Appointment: 1]
---

| Name              | Org Unit               | Fiscal Year  | Status   | Appointment Letter  | Actions       |
|-------------------|------------------------|--------------|----------|---------------------|---------------|
| James Haule       | Research & Analysis    | FY 2025/26   | Active   | RCL/2025/001 ↗      | [View] [Edit] |
| Grace Mollel      | Finance & Admin        | FY 2025/26   | Active   | RCL/2025/002 ↗      | [View] [Edit] |
| Peter Ndunguru    | ICT Department         | FY 2025/26   | Inactive | RCL/2024/003 ↗      | [View]        |
| Mary Kimaro       | Legal Services         | FY 2025/26   | Active   | Pending...          | [View]        |

Showing 1–4 of 8 | Rows per page: 10 ▼   [ < 1 2 > ]

> PermissionGate canManageChampions: only RMQAM/Admin see [+ Nominate] and [Edit].
> "Appointment Letter" column links to the DRS document record (documentClient).

---

On clicking [+ Nominate Risk Champion]:
Component: CreateRiskChampionDialog.tsx

Nominate Risk Champion
FCC_SBP_RMQA_01: RC Nomination → Appointment → DG Signature

Champion *
  [SmartSelect — search IAM users by name/email ▼]   (resolves to UUID)

Organisational Unit *
  [Select from corporate org units ▼]   (GET /api/v1/organizational/units/)

Fiscal Year *
  [Select FY ▼]   (GET /api/v1/grc/risk/settings/fiscal-years/)

[Cancel]  [Save]

> On 409 from backend (duplicate active champion): toast.error("An active Risk Champion already exists
> for this organisational unit in the selected fiscal year.")
> On success: toast.success("Risk Champion nominated successfully.")
> Component creates RiskChampion record (status = active) and automatically initiates
> RiskChampionAppointment workflow (grc.risk_champion_appointment).

---

On clicking [View] for "James Haule":
URL: /service/grc/risk/champions/1

James Haule
Risk Champion — Research & Analysis

Status: [Active]   [Edit]   [Deactivate]

Organisational Unit:   Research & Analysis
Fiscal Year:           FY 2025/26
Appointment Letter:    RCL/2025/001  [Open in DRS ↗]
Created:               January 15, 2025

---
CHAMPION DETAIL TABS:
[ Profile ] [ Appointments ] [ Activity Log ]
---

### TAB 1: Profile

Champion:          James Haule  (synced from IAM — read-only)
Email:             james.haule@fcc.go.tz
Org Unit:          Research & Analysis
Status:            Active
Fiscal Year:       FY 2025/26

[Edit]  (opens EditRiskChampionDialog — can change OrgUnit, FiscalYear only)

---

### TAB 2: Appointments

Appointment Records for this Risk Champion.

[+ Initiate Appointment Process]   (visible only if no in-progress appointment)

| Appointment Ref | Status           | Initiated Date | Signed Date  | Actions |
|-----------------|------------------|----------------|--------------|---------|
| RCA/2025/001    | Signed           | 2025-01-15     | 2025-01-28   | [View]  |

Workflow Template: `grc.risk_champion_appointment`
Stages: Draft → Submitted → Approved → Signed  (rejected → back to Draft)

On clicking [View] for RCA/2025/001:

RCA/2025/001
Risk Champion Appointment
Status: [Signed]

Champion:         James Haule
Org Unit:         Research & Analysis
Initiated By:     RMQAM Office
Signed By:        DG

Appointment Letter (DRS):
  [RCL/2025/001 — View Letter ↗]

EmbeddedWorkflowConsole
  workflowKey="grc.risk_champion_appointment"
  entityId={appointmentId}
  (Standard console — shows current stage, advance/recall/cancel buttons per role)

---

### TAB 3: Activity Log

Standard audit log table:
| Timestamp           | User            | Action        | Notes        |
|---------------------|-----------------|---------------|--------------|
| 2025-01-15 09:31    | RMQAM Officer   | Created       | —            |
| 2025-01-28 14:10    | DG              | Signed        | Letter filed |

---

---

## 4. RISK ASSESSMENT SHEETS
URL: /service/grc/risk/assessments
File: RiskAssessmentSheetsPage.tsx

Risk Assessment Sheets
Individual risk identification and scoring by Risk Champions

[+ New Assessment]   [Search risks...]   [All Categories ▼]   [All Levels ▼]   [All Units ▼]   [FY ▼]

---
Summary Cards:
[Total Assessments: 42]   [High Risk: 8]   [Critical Risk: 2]   [Unassigned to Register: 5]
---

| Risk ID    | Risk Description                      | Category    | Likelihood   | Impact   | Score | Level    | Org Unit         | FY        | Actions       |
|------------|---------------------------------------|-------------|--------------|----------|-------|----------|------------------|-----------|---------------|
| RAS/001    | Inadequate ICT infrastructure backup  | Operational | Likely (4)   | Major (4)| 16    | [High]   | ICT Department   | FY 2025/26 | [View] [Edit] |
| RAS/002    | Staff corruption risk                 | Compliance  | Possible (3) | Critical (5)| 15 | [High]   | Internal Audit   | FY 2025/26 | [View] [Edit] |
| RAS/003    | Budget overrun on capital projects    | Financial   | Unlikely (2) | Minor (2)| 4    | [Low]    | Finance & Admin  | FY 2025/26 | [View] [Edit] |

> Risk Level badge uses style={{ backgroundColor: riskLevel.color_code, color: '#fff' }}
> "Score" = inherent_risk_score computed by backend (likelihood.numerical_value × impact.numerical_value)
> PermissionGate canConductAssessments: only RC / assessors see [+ New Assessment].
> PermissionGate canReviewAssessments: reviewers see [Review] action on submitted assessments.

Showing 1–3 of 42 | Rows per page: 10 ▼

---

On clicking [+ New Assessment]:
Component: CreateRiskAssessmentDialog.tsx

New Risk Assessment Sheet
(Process: FCC_SBP_RMQA_03 Step 2 — RC identifies and assesses risks in dept meeting)

Risk Description *
  [Describe the risk clearly...        ]

Risk Category *
  [Select category ▼]

Likelihood *
  [Select likelihood level ▼]   → shows label + numerical value

Impact *
  [Select impact level ▼]       → shows label + numerical value

Inherent Risk Score  (read-only, auto-computed)
  [Displayed immediately on Likelihood/Impact selection: score = L × I]
  Example: "4 × 4 = 16 → High"

Risk Level  (read-only, auto-resolved from score)
  [Resolved badge: ████ High]

Root Cause *
  [Describe root cause...              ]

Existing Controls
  [Describe existing controls in place ]

Residual Likelihood *
  [Select residual likelihood ▼]

Residual Impact *
  [Select residual impact ▼]

Residual Risk Score  (read-only, auto-computed)
  [Displayed: residual_L × residual_I = score → level]

Strategic Objective
  [Select strategic objective ▼]   (optional link)

Risk Owner *
  [SmartSelect IAM user ▼]   (UUID ref — NOT free-text name)

Organisational Unit *
  [Select org unit ▼]

Fiscal Year *
  [Select FY ▼]

[Cancel]  [Save]

> Score fields are computed client-side (mirroring backend formula) for instant feedback,
> then confirmed from the server response after save.
> On success: toast.success("Risk assessment saved.")
> All numeric score inputs are read-only <span> elements, NOT <input> fields.

---

On clicking [View] for RAS/001:
URL: (modal or drawer, no separate route needed)

RAS/001 — Inadequate ICT infrastructure backup
Risk Assessment Sheet   [Edit]  (if canConductAssessments)

Category:             Operational
Likelihood:           Likely (4)
Impact:               Major (4)
Inherent Risk Score:  16
Risk Level:           ████ High
Residual Likelihood:  Possible (3)
Residual Impact:      Moderate (3)
Residual Risk Score:  9
Residual Risk Level:  ████ Medium
Root Cause:           Aging hardware and no offsite backup policy.
Existing Controls:    Daily local backup, backup testing quarterly.
Strategic Objective:  SO-02 — Strengthen institutional capacity.
Risk Owner:           Grace Mollel
Org Unit:             ICT Department
Fiscal Year:          FY 2025/26
Created:              2025-01-20
Created By:           James Haule (RC — ICT)

Departmental Register:  DRR/ICT/2025/001  [View →]
Institutional Entry:    IRR/2025/006       (if threshold exceeded)

---

---

## 5. DEPARTMENTAL RISK REGISTERS
URL: /service/grc/risk/dept-registers
File: DeptRiskRegistersPage.tsx

Departmental Risk Registers
Annual risk registers maintained by each Risk Champion per organisational unit

[+ Create Register]   [Search registers...]   [All Units ▼]   [All Statuses ▼]   [FY ▼]

---
Summary Cards:
[Total Registers: 6]   [Draft: 2]   [Submitted: 1]   [Approved: 3]
---

| Register Ref       | Org Unit            | Fiscal Year  | RC             | Risk Entries | Status      | Actions |
|--------------------|---------------------|--------------|----------------|--------------|-------------|---------|
| DRR/RA/2025/001    | Research & Analysis | FY 2025/26   | James Haule    | 5 risks      | [Approved]  | [View]  |
| DRR/FA/2025/001    | Finance & Admin     | FY 2025/26   | Grace Mollel   | 3 risks      | [Submitted] | [View]  |
| DRR/ICT/2025/001   | ICT Department      | FY 2025/26   | (none)         | 0 risks      | [Draft]     | [View]  |

Showing 1–3 of 6 | Rows per page: 10 ▼

> Each org unit has at most ONE register per fiscal year (409 enforced by backend).
> PermissionGate canManageDeptRegisters: RC and RMQAM see [+ Create Register].

---

On clicking [+ Create Register]:
Component: CreateDeptRegisterDialog.tsx

Create Departmental Risk Register
One register per organisational unit per fiscal year.

Organisational Unit *
  [Select from corporate org units ▼]

Fiscal Year *
  [Select FY ▼]

[Cancel]  [Save]

> On 409: toast.error("A register already exists for this unit and fiscal year.")
> On success: redirects to the new register's detail page.

---

On clicking [View] for DRR/RA/2025/001:
URL: /service/grc/risk/dept-registers/1
File: DeptRiskRegisterDetailPage.tsx

DRR/RA/2025/001
Departmental Risk Register — Research & Analysis

Status: [Approved]

Org Unit:     Research & Analysis
Fiscal Year:  FY 2025/26
Risk Champion: James Haule
Created:       January 20, 2025
Approved By:   RMQAM Officer (2025-02-05)

[Submit for Approval]  (visible when status=draft, canManageDeptRegisters, entries > 0)
[Recall]               (visible when status=submitted, canManageDeptRegisters)

---
REGISTER DETAIL TABS:
[ Risk Entries ] [ Workflow ] [ Audit Log ]
---

### TAB 1: Risk Entries

[+ Link Assessment]   (visible when status=draft, canManageDeptRegisters)

| # | Risk ID  | Risk Description                       | Score | Level    | Likelihood | Impact | Actions          |
|---|----------|----------------------------------------|-------|----------|------------|--------|------------------|
| 1 | RAS/001  | Inadequate ICT infrastructure backup  | 16    | [High]   | Likely (4) | Major (4) | [View] [Unlink] |
| 2 | RAS/008  | Staff fraud risk                       | 12    | [Medium] | Possible(3)| Major (4) | [View] [Unlink] |

[+ Link Assessment] → opens LinkRiskAssessmentDialog.tsx

LinkRiskAssessmentDialog:
Select Risk Assessment *
  [Searchable table of existing RiskAssessmentSheets for this org unit + FY, not yet in any register]

[Cancel]  [Link Selected]

> [Unlink] is disabled if register status ≠ draft.
> If entries list is empty and user clicks [Submit for Approval]:
>   Show Alert (warning): "Cannot submit — this register has no linked risk assessments.
>   Please link at least one assessment before submitting."
>   [Submit for Approval] button is also disabled client-side when entries = 0.

---

### TAB 2: Workflow

EmbeddedWorkflowConsole
  workflowKey="grc.dept_risk_register_approval"
  entityId={registerId}

Workflow: Draft → Submitted → Approved
         Approved ← Rejected (returns to draft)
Actors:
  - Risk Champion: submits
  - Head of Department: endorses (intermediate step)
  - RMQAM: approves

---

### TAB 3: Audit Log

| Timestamp           | User            | Action     | Notes                    |
|---------------------|-----------------|------------|--------------------------|
| 2025-01-20 10:00    | James Haule     | Created    | —                        |
| 2025-01-20 10:30    | James Haule     | Linked RAS | RAS/001, RAS/008         |
| 2025-02-01 09:00    | James Haule     | Submitted  | Submitted for approval   |
| 2025-02-05 11:00    | RMQAM Officer   | Approved   | —                        |

---

---

## 6. INSTITUTIONAL RISK REGISTER (IRR)
URL: /service/grc/risk/institutional-register
File: InstitutionalRiskRegisterPage.tsx

Institutional Risk Register
Organisation-wide consolidated register of risks exceeding the institutional risk appetite

[+ Create IRR]   [Search IRR...]   [All Statuses ▼]   [FY ▼]

---
Summary Cards:
[IRR Count: 2]   [Active IRR: 1]   [Total Entries: 18]   [Under Commission Review: 1]
---

| Register Ref    | Fiscal Year  | Entry Count | Status                      | RTAP Created | Actions |
|-----------------|--------------|-------------|-----------------------------|--------------|---------|
| IRR/2025/001    | FY 2025/26   | 12 risks    | [Committee Review]          | Yes ↗         | [View]  |
| IRR/2024/001    | FY 2024/25   | 8 risks     | [Approved]                  | Yes ↗         | [View]  |

> One IRR per fiscal year. Backend enforces uniqueness (409 if duplicate FY).
> PermissionGate canManageIRR: RMQAM see [+ Create IRR].
> When IRR is Approved, backend automatically creates the linked RTAP (status=draft).

---

On clicking [+ Create IRR]:
Component: CreateInstitutionalRegisterDialog.tsx

Create Institutional Risk Register
One register per fiscal year. Risks are drawn from approved departmental registers.

Fiscal Year *
  [Select FY ▼]

Institutional Risk Appetite Threshold
  [Displayed from system settings — read-only. Example: "Score ≥ 13 qualifies for IRR"]

[Cancel]  [Save]

> On 409: toast.error("An Institutional Risk Register already exists for this fiscal year.")

---

On clicking [View] for IRR/2025/001:
URL: /service/grc/risk/institutional-register/1
File: InstitutionalRiskRegisterDetailPage.tsx

IRR/2025/001
Institutional Risk Register — FY 2025/26

Status: [Committee Review]

Fiscal Year:       FY 2025/26
Total Entries:     12 risks
Linked RTAP:       RTAP/2025/001  [View →]
Created By:        RMQAM Officer
Created:           February 10, 2025

[Add Risk Entry]     (visible when status=draft, canManageIRR)
[Submit for Review]  (visible when status=draft, canManageIRR, entries > 0)
[Recall]             (visible when status=rmqam_review, canManageIRR)

---
IRR DETAIL TABS:
[ Risk Entries ] [ Activity Reports ] [ Workflow ] [ Audit Log ]
---

### TAB 1: Risk Entries

[+ Add from Departmental]   (visible when status=draft, canManageIRR)

| # | Risk ID  | Risk Description                         | Score | Level      | Source Dept              | Risk Owner   | Actions          |
|---|----------|------------------------------------------|-------|------------|--------------------------|--------------|------------------|
| 1 | RAS/001  | Inadequate ICT infrastructure backup    | 16    | [High]     | ICT Department           | Grace Mollel | [View] [Remove]  |
| 2 | RAS/012  | Regulatory capture risk                 | 20    | [Critical] | Research & Analysis      | James Haule  | [View] [Remove]  |

AddInstitutionalEntryDialog:
> Shows ONLY risk assessments from APPROVED departmental registers that meet or exceed
> the institutional risk appetite threshold.
> Assessments already included in this IRR are excluded.

Add Risk Entries to IRR
Showing risks from approved departmental registers exceeding the threshold (Score ≥ 13).

[ ] RAS/003 — Staff corruption risk — Score: 15 — Finance & Admin
[ ] RAS/011 — Regulatory capture risk — Score: 20 — Research & Analysis
[ ] RAS/017 — Procurement irregularities — Score: 14 — Procurement

[Cancel]  [Add Selected]

> [Remove] is disabled if IRR status ≠ draft.

---

### TAB 2: Activity Reports

Quarterly activity reports submitted by Risk Champions linked to this IRR.

[+ Submit Activity Report]   (visible to Risk Champions canManageIRR)

| RC           | Quarter | Fiscal Year | Submission Date | Status    | Actions |
|--------------|---------|-------------|-----------------|-----------|---------|
| James Haule  | Q1      | FY 2025/26  | 2025-07-15      | Submitted | [View]  |
| Grace Mollel | Q1      | FY 2025/26  | 2025-07-18      | Submitted | [View]  |

SubmitActivityReportDialog:
Quarter *     [Select Q1/Q2/Q3/Q4 ▼]
Fiscal Year * [Select FY ▼]
Report *      [Textarea — RC's quarterly activity narrative]
Attachments   [Upload file]

[Cancel]  [Submit]

---

### TAB 3: Workflow

EmbeddedWorkflowConsole
  workflowKey="grc.institutional_risk_register_approval"
  entityId={irrId}

4-Stage Workflow:
  Draft → RMQAM Review → Management Review → Committee Review → Commission Review → Approved
                                                                (rejected → Draft)
Actors:
  RMQAM: initiates review
  Senior Management: management review
  Risk & Governance Committee: committee review
  Commission: final approval

---

### TAB 4: Audit Log

Standard table: Timestamp | User | Action | Notes

---

---

## 7. RISK TREATMENT ACTION PLAN (RTAP)
URL: /service/grc/risk/rtap
File: RTAPPage.tsx

Risk Treatment Action Plans
Quarterly implementation tracking for approved institutional risk mitigations

> IMPORTANT: RTAPs are auto-created by the system when an IRR is approved.
> There is NO [+ Create] button on this page. Users can only [View] existing RTAPs.

[Search RTAPs...]   [All Statuses ▼]   [FY ▼]

---
Summary Cards:
[Total RTAPs: 2]   [In Progress: 1]   [Approved: 1]   [Overdue Items: 2]
---

| RTAP Ref       | Fiscal Year  | Linked IRR   | Items | Completion % | Status             | Actions |
|----------------|--------------|--------------|-------|--------------|--------------------|---------|
| RTAP/2025/001  | FY 2025/26   | IRR/2025/001 | 12    | 42%          | [Management Review]| [View]  |
| RTAP/2024/001  | FY 2024/25   | IRR/2024/001 | 8     | 100%         | [Approved]         | [View]  |

> Completion % = count(RTAPItems where status=completed) / total RTAPItems × 100
> Auto-created with IRR approval: no manual creation allowed.

---

On clicking [View] for RTAP/2025/001:
URL: /service/grc/risk/rtap/1
File: RTAPDetailPage.tsx

RTAP/2025/001
Risk Treatment Action Plan — FY 2025/26

Status: [Management Review]

Linked IRR:      IRR/2025/001  [View →]
Fiscal Year:     FY 2025/26
Total Items:     12
Completed Items: 5
Completion:      42%
Created:         Auto-created on IRR approval (2025-03-01)

[Submit for Review]   (visible when status=draft, canManageRTAP)
[Recall]              (visible when status=rmqam_review, canManageRTAP)

---
RTAP DETAIL TABS:
[ Treatment Items ] [ Quarterly Updates ] [ Workflow ] [ Audit Log ]
---

### TAB 1: Treatment Items

Each RTAPItem corresponds to one InstitutionalRiskEntry in the linked IRR.

[+ Add Treatment Item]   (visible when status=draft, canManageRTAP)

| # | Risk ID  | Risk Description                   | Treatment Action         | Responsible    | Target Date   | Status           | Actions               |
|---|----------|------------------------------------|--------------------------|----------------|---------------|------------------|-----------------------|
| 1 | RAS/001  | Inadequate ICT infrastructure backup | Procure offsite backup solution | Grace Mollel | 2025-06-30 | [In Progress]  | [Edit] [Updates]      |
| 2 | RAS/012  | Regulatory capture risk            | Staff training on ethics | James Haule    | 2025-09-30    | [Not Started]    | [Edit] [Updates]      |

CreateRTAPItemDialog:
Risk Entry *      [Select from IRR entries not yet assigned an RTAP item ▼]
Treatment Action * [Describe the mitigation action                        ]
Responsible *     [SmartSelect IAM user ▼]
Target Date *     [mm/dd/yyyy]

[Cancel]  [Save]

RTAPItemStatusEditDialog:
> Updates the status of a single RTAPItem (not_started / in_progress / completed).

Update Treatment Item Status

Risk:              RAS/001 — Inadequate ICT infrastructure backup
Current Status:    [In Progress]

New Status *       [Select ▼: Not Started | In Progress | Completed]
Remarks *          [Explain the update...                           ]

[Cancel]  [Update]

---

### TAB 2: Quarterly Updates

Quarterly progress updates submitted per RTAPItem.

[+ Submit Quarterly Update]   (visible to canRespondRTAP or canManageRTAP)

| Item # | Risk          | Quarter | Fiscal Year | Progress Notes    | Status Update  | Submitted By  | Date       | Actions |
|--------|---------------|---------|-------------|-------------------|----------------|---------------|------------|---------|
| 1      | RAS/001       | Q1      | FY 2025/26  | Vendor shortlisted | In Progress   | Grace Mollel  | 2025-07-10 | [View]  |
| 2      | RAS/012       | Q1      | FY 2025/26  | Training scheduled | Not Started   | James Haule   | 2025-07-12 | [View]  |

SubmitQuarterlyUpdateDialog:
RTAP Item *      [Select RTAPItem ▼]
Quarter *        [Q1 / Q2 / Q3 / Q4 ▼]
Fiscal Year *    [FY ▼]
Progress Notes * [Describe progress this quarter...  ]
Status Update *  [Not Started / In Progress / Completed ▼]
Attachments      [Upload supporting evidence]

[Cancel]  [Submit]

> On submit: RTAPItem.status is updated to match the submitted status update.
> If all items = completed: backend auto-flags RTAP as ready for completion.

---

### TAB 3: Workflow

EmbeddedWorkflowConsole
  workflowKey="grc.rtap_approval"
  entityId={rtapId}

5-Stage Workflow:
  Draft → RMQAM Review → LSM Submission → Management Review → Committee Review → Commission Submission → Approved
                                                                          (rejected → Draft)
Actors:
  RMQAM: prepares and initiates
  Legal Services Manager: submits to management
  Senior Management: reviews
  Risk & Governance Committee: reviews
  Commission: final approval

---

### TAB 4: Audit Log

Standard table: Timestamp | User | Action | Notes

---

---

## 8. QUARTERLY PERFORMANCE REPORTS (QPR)
URL: /service/grc/risk/quarterly-reports
File: QuarterlyReportsPage.tsx

Quarterly Performance Reports
Consolidated quarterly risk management performance reporting to senior governance

[+ Create QPR]   [Search QPRs...]   [All Statuses ▼]   [FY ▼]   [Quarter ▼]

---
Summary Cards:
[Total QPRs: 4]   [Draft: 1]   [Approved: 2]   [In Review: 1]
---

| QPR Ref       | Fiscal Year  | Quarter | Status                    | Created By     | Date       | Actions |
|---------------|--------------|---------|---------------------------|----------------|------------|---------|
| QPR/2025/Q1   | FY 2025/26   | Q1      | [Approved]                | RMQAM Officer  | 2025-07-20 | [View]  |
| QPR/2025/Q2   | FY 2025/26   | Q2      | [Management Review]       | RMQAM Officer  | 2025-10-18 | [View]  |
| QPR/2025/Q3   | FY 2025/26   | Q3      | [Draft]                   | RMQAM Officer  | 2026-01-05 | [View]  |

> One QPR per FY + Quarter (backend enforces 409 on duplicate).
> PermissionGate canManageQuarterlyReport: RMQAM see [+ Create QPR].

---

On clicking [+ Create QPR]:
Component: CreateQuarterlyReportDialog.tsx

Create Quarterly Performance Report

Fiscal Year *    [Select FY ▼]
Quarter *        [Q1 / Q2 / Q3 / Q4 ▼]
Summary *        [Executive summary of quarterly risk performance...]
Attachments      [Upload QPR draft document from DRS]

[Cancel]  [Save as Draft]

> On 409: toast.error("A QPR already exists for this fiscal year and quarter.")

---

On clicking [View] for QPR/2025/Q2:
URL: /service/grc/risk/quarterly-reports/2
File: QuarterlyReportDetailPage.tsx

QPR/2025/Q2
Quarterly Performance Report — Q2 FY 2025/26

Status: [Management Review]

Fiscal Year:  FY 2025/26
Quarter:      Q2
Created By:   RMQAM Officer
Created:      2025-10-18

[Edit]       (visible when status=draft, canManageQuarterlyReport)
[Submit for Review]  (visible when status=draft, canManageQuarterlyReport)
[Recall]     (visible when status=rmqam_prepare, canManageQuarterlyReport)

---
QPR DETAIL TABS:
[ Summary ] [ Activity Reports ] [ Workflow ] [ Audit Log ]
---

### TAB 1: Summary

Executive Summary
[Textarea — editable when status=draft, read-only otherwise]

Attachments:
  [QPR Q2 FY 2025/26 Draft.pdf ↗]   [Upload Additional]

Key Metrics This Quarter:
  RTAP Completion:      42% (5 of 12 items)
  New Risks Identified: 3
  Risks Closed:         1
  Active Risk Champions: 6

> Metrics sourced from GET /api/v1/grc/risk/dashboard/ quarterly breakdown.

---

### TAB 2: Activity Reports

Quarterly activity reports submitted by Risk Champions this quarter.

| RC           | Org Unit        | Submission Date | Status    | Actions |
|--------------|-----------------|-----------------|-----------|---------|
| James Haule  | Research & Anal | 2025-10-15      | Submitted | [View]  |
| Grace Mollel | Finance & Admin | 2025-10-18      | Submitted | [View]  |

> Read-only in this context. Activity Reports are created from the IRR detail page.

---

### TAB 3: Workflow

EmbeddedWorkflowConsole
  workflowKey="grc.quarterly_risk_report_approval"
  entityId={qprId}

5-Stage Workflow:
  Draft → RMQAM Prepare → LSM Submit → Management Review → Committee Review → Commission Submit → Approved
                                                                       (rejected → Draft)
Actors:
  RMQAM: prepares
  Legal Services Manager: submits
  Senior Management: reviews
  Risk & Governance Committee: reviews
  Commission: approves

---

### TAB 4: Audit Log

Standard table: Timestamp | User | Action | Notes

---

---

## 9. QUALITY AUDITORS
URL: /service/grc/risk/quality-auditors
File: QualityAuditorsPage.tsx

Quality Auditors
Manage ISO-certified internal quality auditors for QMS audit activity

[+ Register Auditor]   [Search auditors...]   [All Units ▼]   [Certified Only ▼]   [All Statuses ▼]

---
Summary Cards:
[Total Auditors: 8]   [Certified: 5]   [In Training: 2]   [Max Attempts Reached: 1]
---

| Name              | Org Unit          | Exam Score | Is Certified | Attempts | Status   | Actions       |
|-------------------|-------------------|------------|--------------|----------|----------|---------------|
| Anna Kimaro       | Research & Anal   | 82%        | Yes ✓        | 1        | [Active] | [View] [Edit] |
| Paul Mwita        | Finance & Admin   | 68%        | No ✗         | 1        | [Active] | [View] [Edit] |
| Rehema Minja      | ICT Department    | 55%        | No ✗         | 2        | [Active] | [View]        |
| David Sanga       | Legal Services    | 91%        | Yes ✓        | 1        | [Active] | [View] [Edit] |

> "Certified" = is_certified = true (exam_score ≥ 75).
> "Attempts" = attempt_count (max 2).
> PermissionGate canManageQualityAuditors: only RMQAM see [+ Register Auditor] and [Edit].

---

On clicking [+ Register Auditor]:
Component: CreateQualityAuditorDialog.tsx

Register Quality Auditor
FCC_SBP_RMQA_06: Nomination → ISO Training → Examination → DG Appointment

Auditor *
  [SmartSelect IAM user ▼]   (UUID — NOT free-text name)

Organisational Unit *
  [Select org unit ▼]

Notes
  [Optional notes on nomination context...]

[Cancel]  [Save]

> On success: QualityAuditor created. is_certified = false. attempt_count = 0.
> Auditor must sit ISO 9001 Lead Auditor exam before appointment can proceed.

---

On clicking [View] for "Paul Mwita":
URL: /service/grc/risk/quality-auditors/2
File: QualityAuditorDetailPage.tsx

Paul Mwita
Quality Auditor — Finance & Admin

> EXAM STATUS BANNER (conditional rendering):

When attempt_count = 0:
  ┌─────────────────────────────────────────────────────────────────┐
  │ ℹ  ISO 9001 Lead Auditor examination not yet sat.              │
  │    [Record Exam Result]                                        │
  └─────────────────────────────────────────────────────────────────┘

When attempt_count = 1 AND is_certified = false (failed first attempt):
  ┌─────────────────────────────────────────────────────────────────┐
  │ ⚠  Exam not passed (Score: 68%). One re-sit attempt allowed.   │
  │    Arrange re-sit examination.  [Record Re-sit Result]         │
  └─────────────────────────────────────────────────────────────────┘

When attempt_count = 2 AND is_certified = false (failed both attempts):
  ┌─────────────────────────────────────────────────────────────────┐
  │ ✕  Maximum exam attempts reached (2/2). This auditor cannot be │
  │    appointed. A replacement nomination is required.            │
  │    [Nominate Replacement]  (canManageQualityAuditors only)     │
  └─────────────────────────────────────────────────────────────────┘
  NOTE: [Initiate Appointment] button is DISABLED when attempt_count = 2 AND is_certified = false.
  NOTE: [Record Exam Result] button is also HIDDEN in this state.

When is_certified = true:
  ┌─────────────────────────────────────────────────────────────────┐
  │ ✓  ISO 9001 Certified. Exam Score: 82%. Eligible for           │
  │    appointment.  [Initiate Appointment]                        │
  └─────────────────────────────────────────────────────────────────┘

---

AUDITOR DETAIL TABS:
[ Profile ] [ Exam Results ] [ Appointments ] [ Audit History ] [ Activity Log ]
---

### TAB 1: Profile

Auditor:          Paul Mwita  (synced from IAM)
Email:            paul.mwita@fcc.go.tz
Org Unit:         Finance & Admin
Is Certified:     No
Exam Score:       68%
Attempt Count:    1 / 2
Status:           Active

[Edit]   (canManageQualityAuditors only; can change Org Unit and Notes)

---

### TAB 2: Exam Results

| Attempt # | Exam Date   | Score | Pass / Fail | Recorded By       | Actions |
|-----------|-------------|-------|-------------|-------------------|---------|
| 1         | 2025-02-10  | 68%   | Fail        | RMQAM Officer     | [View]  |

RecordExamResultDialog:
Attempt Number   (auto: current attempt_count + 1 — read-only display)
Exam Date *      [mm/dd/yyyy]
Score (%) *      [Enter score 0–100]
Notes            [Optional remarks]
Supporting Document  [Upload exam certificate/result sheet to DRS]

[Cancel]  [Save]

> If score ≥ 75: is_certified set to true. "Certified" badge appears.
> If score < 75 AND attempt_count already = 1: attempt_count = 2. Max attempts banner shown.
> If attempt_count would exceed 2: backend returns 400; toast.error("Maximum exam attempts (2) already reached.")

---

### TAB 3: Appointments

| Appointment Ref | Status    | Signed Date  | Actions |
|-----------------|-----------|--------------|---------|
| QAA/2025/001    | Signed    | 2025-03-01   | [View]  |

Workflow: `grc.qa_appointment`
Stages: Draft → Submitted → Approved → Signed
Actors: RMQAM submits → Head approves → DG signs

[+ Initiate Appointment]   (visible only if is_certified = true AND no in-progress appointment AND attempt_count < 2 OR is_certified = true)

---

### TAB 4: Audit History

| Audit Plan Ref   | Auditee Unit     | Program    | Role         | Date       | Report Status | Actions |
|------------------|------------------|------------|--------------|------------|---------------|---------|
| QAP/2025/001/ICT | ICT Department   | QMSP/2025  | Lead Auditor | 2025-04-10 | Finalised     | [View]  |

---

### TAB 5: Activity Log

Standard table: Timestamp | User | Action | Notes

---

---

## 10. QMS AUDIT PROGRAMS
URL: /service/grc/risk/qms-programs
File: QMSAuditProgramsPage.tsx

QMS Audit Programs
Annual audit programmes defining the scope of internal quality audits

[+ Create Program]   [Search programs...]   [All Statuses ▼]   [FY ▼]

---
Summary Cards:
[Total Programs: 2]   [Active (Approved): 1]   [In Planning: 1]   [Total Plans Under Active: 3]
---

| Program Ref   | Fiscal Year  | Description                  | Plans | Status      | Actions |
|---------------|--------------|------------------------------|-------|-------------|---------|
| QMSP/2026/001 | FY 2025/26   | Annual Internal QMS Audit    | 3     | [Approved]  | [View]  |
| QMSP/2027/001 | FY 2026/27   | Annual Internal QMS Audit    | 0     | [Draft]     | [View]  |

> One program per fiscal year (backend enforces 409 on duplicate FY).
> PermissionGate canManageQMSPrograms: RMQAM see [+ Create Program].

---

On clicking [+ Create Program]:
Component: CreateQMSProgramDialog.tsx

Create QMS Audit Program

Fiscal Year *    [Select FY ▼]
Description *    [Describe the annual audit program scope...]
Objectives       [List key audit objectives...]
Scope            [Describe activities/units in scope...]

[Cancel]  [Save as Draft]

> On 409: toast.error("A QMS Audit Program already exists for this fiscal year.")

---

On clicking [View] for QMSP/2026/001:
URL: /service/grc/risk/qms-programs/1
File: QMSAuditProgramDetailPage.tsx

QMSP/2026/001
QMS Audit Program — FY 2025/26

Status: [Approved]

Fiscal Year:   FY 2025/26
Description:   Annual Internal QMS Audit
Created By:    RMQAM Officer
Created:       2025-03-01

[Edit]          (visible when status=draft, canManageQMSPrograms)
[Submit for Approval]  (visible when status=draft, canManageQMSPrograms)
[Recall]        (visible when status=submitted, canManageQMSPrograms)
[+ Create Audit Plan]  (visible when status=approved, canManageQMSPlans)

---
PROGRAM DETAIL TABS:
[ Audit Plans ] [ Workflow ] [ Audit Log ]
---

### TAB 1: Audit Plans

[+ Create Audit Plan]   (visible when program status=approved, canManageQMSPlans)

| Plan Ref          | Auditee Unit       | Audit Dates           | Team Lead    | Status           | Actions |
|-------------------|--------------------|-----------------------|--------------|------------------|---------|
| QAP/2025/001/ICT  | ICT Department     | 2025-04-10 → 04-12   | Anna Kimaro  | [Completed]      | [View]  |
| QAP/2025/002/FA   | Finance & Admin    | 2025-05-01 → 05-03   | David Sanga  | [In Progress]    | [View]  |
| QAP/2025/003/RA   | Research & Anal    | 2025-06-10 → 06-12   | (unassigned) | [Draft]          | [View]  |

CreateQMSPlanDialog:
Auditee Organisational Unit *
  [Select org unit ▼]

Audit Start Date *
  [mm/dd/yyyy]

Audit End Date *
  [mm/dd/yyyy]

Notification Date *
  [mm/dd/yyyy]
  ⚠  INFO: "Notification must be sent at least 10 working days before the audit start date."
  Zod validation:  .refine(d => differenceInBusinessDays(auditStart, d) >= 10,
                    "Notification date must be at least 10 working days before audit start.")

Audit Scope *
  [Describe specific scope for this unit...]

[Cancel]  [Save]

> On save: backend creates QMSAuditPlan with status=draft, sends notification email to auditee Head.
> On Zod error (< 10 days): field-level error shown below Notification Date field
>   — "Notification must be at least 10 working days before audit start."
>   [Save] button remains disabled until resolved.

---

### TAB 2: Workflow

EmbeddedWorkflowConsole
  workflowKey="grc.qms_audit_program_approval"
  entityId={programId}

Workflow: Draft → Submitted → Approved  (rejected → Draft)
Actors:
  RMQAM: submits
  Head / Management: approves

---

### TAB 3: Audit Log

Standard table: Timestamp | User | Action | Notes

---

---

## 11. QMS AUDIT PLAN DETAIL
URL: /service/grc/risk/qms-plans/:id
File: QMSAuditPlanDetailPage.tsx

> QMS Audit Plans do NOT have a list page in the sidebar.
> They are always accessed via [View] from a Program's Audit Plans tab.

---

QAP/2025/002/FA
QMS Audit Plan — Finance & Admin

Status: [In Progress]

Parent Program:      QMSP/2026/001  [View →]
Auditee Unit:        Finance & Admin
Audit Start:         2025-05-01
Audit End:           2025-05-03
Notification Date:   2025-04-15
Scope:               Review of procurement QMS compliance, budget controls, financial reporting.
Lead Auditor:        David Sanga
Audit Team:          [See Team tab]

[Edit]          (visible when status=draft, canManageQMSPlans)
[Submit for Approval]  (visible when status=draft, canManageQMSPlans)
[Recall]        (visible when status=submitted, canManageQMSPlans)
[Start Audit]   (visible when status=approved, canManageQMSPlans)
[Complete Audit] (visible when status=in_progress, all checklists filled, report=finalised)

---
AUDIT PLAN DETAIL TABS:
[ Team ] [ Checklists ] [ Audit Report ] [ Non-Conformances ] [ Workflow ] [ Audit Log ]
---

### TAB 1: Team

> Conflict rule: a Quality Auditor CANNOT be assigned to audit their own organisational unit.
> AssignAuditorDialog shows a warning Alert if a conflict is detected.

[+ Assign Auditor]   (visible when status=draft/approved, canManageQMSPlans)

| Name          | Org Unit        | Role         | Is Certified | Actions   |
|---------------|-----------------|--------------|--------------|-----------|
| David Sanga   | Legal Services  | Lead Auditor | Yes ✓        | [Remove]  |
| Anna Kimaro   | Research & Anal | Team Member  | Yes ✓        | [Remove]  |

AssignAuditorDialog:
Auditor *    [Select from certified Quality Auditors (is_certified=true) ▼]
Role *       [Lead Auditor / Team Member ▼]

⚠  CONFLICT CHECK (rendered on auditor selection):
   If selected auditor's org_unit = plan's auditee_org_unit:
   ┌────────────────────────────────────────────────────────────────┐
   │ ⚠  Conflict of Interest: This auditor belongs to the same     │
   │    unit being audited (Finance & Admin). Per ISO 9001 and FCC  │
   │    policy, the same-unit auditor cannot audit their own unit.  │
   │    Please select a different auditor.                         │
   └────────────────────────────────────────────────────────────────┘
   [Assign] button is DISABLED when conflict detected.

[Cancel]  [Assign]

---

### TAB 2: Checklists

Each checklist item corresponds to one ISO Clause + one assigned Quality Auditor.
[+ Add Checklist Item]   (visible when status=in_progress, canManageChecklists)

| # | ISO Clause | Clause Title                       | Auditor       | Conformity         | Notes    | Actions        |
|---|------------|------------------------------------|---------------|--------------------|----------|----------------|
| 1 | 4.1        | Understanding the organisation      | David Sanga   | [Conforming]       |          | [Edit]         |
| 2 | 6.1        | Actions to address risks            | Anna Kimaro   | [Minor NC]         | Staff unaware of risk register process | [Edit] |
| 3 | 7.1        | Resources                           | David Sanga   | [Conforming]       |          | [Edit]         |
| 4 | 10.2       | Nonconformity and corrective action | Anna Kimaro   | [Major NC]         | No corrective action log maintained    | [Edit] |

Conformity options (badge colours):
  [Conforming]  → bg-green-100  text-green-800
  [Minor NC]    → bg-yellow-100 text-yellow-800
  [Major NC]    → bg-red-100    text-red-800
  [Observation] → bg-blue-100   text-blue-800
  [N/A]         → bg-gray-100   text-gray-800

On [Edit] AuditChecklist:

Edit Checklist Item

ISO Clause *     [Select ISO clause ▼]
Auditor *        [Select team member ▼]
Conformity *     [Conforming / Minor NC / Major NC / Observation / N/A ▼]
Notes            [Describe findings...                                 ]
Evidence         [Upload supporting evidence to DRS]

[Cancel]  [Save]

> When conformity = Minor NC or Major NC:
>   After saving checklist item, system prompts:
>   "A non-conformance has been detected. Raise a Non-Conformance record now?"
>   [Yes — Raise NC]  [No — Skip]
>   [Yes] opens RaiseNonConformanceDialog pre-filled with ISO Clause and Audit Plan.

---

### TAB 3: Audit Report

Each QMSAuditPlan has exactly ONE QMSAuditReport (auto-created when audit starts).

Report Ref: ARP/2025/002/FA
Status: [Draft]

Summary of Findings *        [Textarea — editable when status=draft, read-only otherwise]
Positive Observations        [Textarea]
Areas for Improvement        [Textarea]
Conclusion *                 [Textarea]

NC Summary:
  Minor NCs: 1   |  Major NCs: 1   |  Total NCs: 2

[Submit Report]       (visible when status=draft, canManageAuditReports — all checklist items must be filled)
[Sign Report (TL)]    (visible when status=draft, canSignAuditReports — Team Lead signature)
[Acknowledge (Auditee)] (visible when status=tl_signed — auditee's Head acknowledges)
[Finalise]            (visible when status=auditee_acknowledged, canManageAuditReports)

> Report Status flow:
>   draft → tl_signed → auditee_acknowledged → finalised
> Once finalised: report is READ-ONLY. NC records can still have status updates.

---

### TAB 4: Non-Conformances

Non-conformances raised from this audit plan's checklist findings.

[+ Raise NC]   (visible when status=in_progress/completed, canManageNonConformances)

| NC Ref        | Type   | ISO Clause | Status         | Assigned To   | Due Date   | Actions   |
|---------------|--------|------------|----------------|---------------|------------|-----------|
| NC/2025/001   | Major  | 10.2       | [In Progress]  | Grace Mollel  | 2025-07-01 | [View]    |
| NC/2025/002   | Minor  | 6.1        | [Raised]       | Paul Mwita    | 2025-07-15 | [View]    |

> New NCs can also be raised directly from the [+ Raise NC] button here.

RaiseNonConformanceDialog:
NC Type *           [Select NC Type ▼]  (from NonConformanceType settings)
ISO Clause *        [Select ISO Clause ▼]
Audit Plan *        [Auto-filled — read-only]
Description *       [Describe the non-conformance clearly...]
Assigned To *       [SmartSelect IAM user ▼]
Due Date *          [mm/dd/yyyy]
Evidence            [Upload from DRS]

[Cancel]  [Raise NC]

---

### TAB 5: Workflow

EmbeddedWorkflowConsole
  workflowKey="grc.qms_audit_plan_approval"
  entityId={planId}

Workflow: Draft → Submitted → Approved → In Progress → Completed
         (rejected → Draft)
Actors:
  RMQAM: submits
  Head: approves
  RMQAM / QA Team: in_progress (active audit)
  RMQAM: completes on finalised report + all NCs closed

---

### TAB 6: Audit Log

Standard table: Timestamp | User | Action | Notes

---

---

## 12. NON-CONFORMANCES
URL: /service/grc/risk/non-conformances
File: NonConformancesPage.tsx

Non-Conformances
Track and resolve non-conformances identified during QMS audits

> [+ Raise NC] is only available from inside an Audit Plan's Non-Conformances tab.
> This page is READ + RESPOND only. Bulk action: [Export to CSV].

[Search NCs...]   [All Types ▼]   [All Statuses ▼]   [All Audit Plans ▼]   [All Assignees ▼]

---
Summary Cards:
[Total NCs: 7]   [Raised: 2]   [In Progress: 3]   [Closed: 2]   [Overdue: 1]
---

| NC Ref       | Type        | ISO Clause | Audit Plan            | Auditee Unit     | Status         | Assigned To   | Due Date   | Actions        |
|--------------|-------------|------------|-----------------------|------------------|----------------|---------------|------------|----------------|
| NC/2025/001  | Major NC    | 10.2       | QAP/2025/002/FA       | Finance & Admin  | [In Progress]  | Grace Mollel  | 2025-07-01 | [View] [Update]|
| NC/2025/002  | Minor NC    | 6.1        | QAP/2025/002/FA       | Finance & Admin  | [Raised]       | Paul Mwita    | 2025-07-15 | [View] [Update]|
| NC/2025/003  | Major NC    | 8.1        | QAP/2025/001/ICT      | ICT Department   | [Closed]       | Grace Mollel  | 2025-04-30 | [View]         |
| NC/2025/004  | Observation | 7.1        | QAP/2025/001/ICT      | ICT Department   | [Closed]       | David Sanga   | 2025-04-30 | [View]         |

> Overdue = status ≠ closed AND due_date < today → row highlighted bg-red-50.
> PermissionGate canRespondNonConformances: assigned staff see [Update] button.
> PermissionGate canManageNonConformances: RMQAM see [Update] + can reassign.

---

On clicking [View] for NC/2025/001:
(opens as a side drawer or modal — no separate route needed)

NC/2025/001 — Major Non-Conformance
Status: [In Progress]

Type:            Major NC
ISO Clause:      10.2 — Nonconformity and corrective action
Audit Plan:      QAP/2025/002/FA  [View →]
Auditee Unit:    Finance & Admin
Description:     No corrective action log maintained. Findings from previous audits not tracked.
Raised By:       Anna Kimaro
Raised Date:     2025-05-03
Assigned To:     Grace Mollel
Due Date:        2025-07-01
Evidence:        [NCE/2025/001.pdf ↗]

Progress Notes:
  2025-05-15  Grace Mollel: "Corrective action log template created and shared with team."
  2025-06-01  Grace Mollel: "Log populated with historical findings. Training session scheduled."

[Log Progress Update]  (visible canRespondNonConformances or canManageNonConformances)
[Mark as Closed]       (visible when status=in_progress, canManageNonConformances, all evidence uploaded)

---

On clicking [Update] / [Log Progress Update]:

Update Non-Conformance

NC:                NC/2025/001 — 10.2 (Finance & Admin)
Current Status:    [In Progress]

Progress Notes *   [Describe corrective action taken this period...]
New Status *       [No Change / In Progress / Closed ▼]
Evidence           [Upload corrective action evidence to DRS]

[Cancel]  [Save Update]

> On status → closed: toast.success("Non-conformance closed successfully.")
> If all NCs for an Audit Plan are closed: audit plan status CAN be completed.
>   System shows informational toast: "All NCs closed. You may now complete the Audit Plan."

---

---

## CROSS-CUTTING NOTES (apply to entire module)

---

### A. API Client Pattern

```ts
// services/riskService.ts
import { grcClient } from '@shared/api/gateway';
import { unwrap, mapPaginatedResponse } from '@shared/api/utils';

export const riskService = {
  // Settings
  getCategories:      (params?) => grcClient.get('/risk/settings/categories/', { params }).then(mapPaginatedResponse),
  getLikelihoods:     (params?) => grcClient.get('/risk/settings/likelihoods/', { params }).then(mapPaginatedResponse),
  getImpacts:         (params?) => grcClient.get('/risk/settings/impacts/', { params }).then(mapPaginatedResponse),
  getRiskLevels:      (params?) => grcClient.get('/risk/settings/levels/', { params }).then(mapPaginatedResponse),
  getIsoClauses:      (params?) => grcClient.get('/risk/settings/iso-clauses/', { params }).then(mapPaginatedResponse),
  getNcTypes:         (params?) => grcClient.get('/risk/settings/nc-types/', { params }).then(mapPaginatedResponse),

  // Champions
  getChampions:       (params?) => grcClient.get('/risk/champions/', { params }).then(mapPaginatedResponse),
  getChampion:        (id)      => grcClient.get(`/risk/champions/${id}/`).then(unwrap),
  createChampion:     (data)    => grcClient.post('/risk/champions/', data).then(unwrap),
  updateChampion:     (id, data)=> grcClient.patch(`/risk/champions/${id}/`, data).then(unwrap),

  // Appointments
  getAppointments:    (params?) => grcClient.get('/risk/champion-appointments/', { params }).then(mapPaginatedResponse),

  // Assessments
  getAssessments:     (params?) => grcClient.get('/risk/assessments/', { params }).then(mapPaginatedResponse),
  getAssessment:      (id)      => grcClient.get(`/risk/assessments/${id}/`).then(unwrap),
  createAssessment:   (data)    => grcClient.post('/risk/assessments/', data).then(unwrap),
  updateAssessment:   (id, data)=> grcClient.patch(`/risk/assessments/${id}/`, data).then(unwrap),

  // Dept Registers
  getDeptRegisters:   (params?) => grcClient.get('/risk/dept-registers/', { params }).then(mapPaginatedResponse),
  getDeptRegister:    (id)      => grcClient.get(`/risk/dept-registers/${id}/`).then(unwrap),
  createDeptRegister: (data)    => grcClient.post('/risk/dept-registers/', data).then(unwrap),

  // IRR
  getIRRs:            (params?) => grcClient.get('/risk/institutional-registers/', { params }).then(mapPaginatedResponse),
  getIRR:             (id)      => grcClient.get(`/risk/institutional-registers/${id}/`).then(unwrap),
  createIRR:          (data)    => grcClient.post('/risk/institutional-registers/', data).then(unwrap),

  // RTAP
  getRTAPs:           (params?) => grcClient.get('/risk/rtap/', { params }).then(mapPaginatedResponse),
  getRTAP:            (id)      => grcClient.get(`/risk/rtap/${id}/`).then(unwrap),
  getRTAPItems:       (rtapId)  => grcClient.get('/risk/rtap-items/', { params: { rtap: rtapId } }).then(mapPaginatedResponse),
  createRTAPItem:     (data)    => grcClient.post('/risk/rtap-items/', data).then(unwrap),
  updateRTAPItem:     (id, data)=> grcClient.patch(`/risk/rtap-items/${id}/`, data).then(unwrap),
  submitQtrUpdate:    (data)    => grcClient.post('/risk/rtap-quarterly-updates/', data).then(unwrap),

  // QPR
  getQPRs:            (params?) => grcClient.get('/risk/quarterly-reports/', { params }).then(mapPaginatedResponse),
  getQPR:             (id)      => grcClient.get(`/risk/quarterly-reports/${id}/`).then(unwrap),
  createQPR:          (data)    => grcClient.post('/risk/quarterly-reports/', data).then(unwrap),

  // Quality Auditors
  getAuditors:        (params?) => grcClient.get('/risk/quality-auditors/', { params }).then(mapPaginatedResponse),
  getAuditor:         (id)      => grcClient.get(`/risk/quality-auditors/${id}/`).then(unwrap),
  createAuditor:      (data)    => grcClient.post('/risk/quality-auditors/', data).then(unwrap),
  recordExamResult:   (id, data)=> grcClient.post(`/risk/quality-auditors/${id}/exam/`, data).then(unwrap),

  // QA Appointments
  getQAAppointments:  (params?) => grcClient.get('/risk/qa-appointments/', { params }).then(mapPaginatedResponse),

  // QMS Programs
  getQMSPrograms:     (params?) => grcClient.get('/risk/qms-programs/', { params }).then(mapPaginatedResponse),
  getQMSProgram:      (id)      => grcClient.get(`/risk/qms-programs/${id}/`).then(unwrap),
  createQMSProgram:   (data)    => grcClient.post('/risk/qms-programs/', data).then(unwrap),

  // QMS Plans
  getQMSPlan:         (id)      => grcClient.get(`/risk/qms-plans/${id}/`).then(unwrap),
  createQMSPlan:      (data)    => grcClient.post('/risk/qms-plans/', data).then(unwrap),
  assignAuditor:      (planId, data) => grcClient.post(`/risk/qms-plans/${planId}/assign-auditor/`, data).then(unwrap),

  // Checklists
  getChecklists:      (planId)  => grcClient.get('/risk/qms-checklists/', { params: { plan: planId } }).then(mapPaginatedResponse),
  updateChecklist:    (id, data)=> grcClient.patch(`/risk/qms-checklists/${id}/`, data).then(unwrap),

  // Audit Reports
  getAuditReport:     (planId)  => grcClient.get('/risk/qms-reports/', { params: { plan: planId } }).then(mapPaginatedResponse),
  updateAuditReport:  (id, data)=> grcClient.patch(`/risk/qms-reports/${id}/`, data).then(unwrap),

  // Non-Conformances
  getNonConformances: (params?) => grcClient.get('/risk/non-conformances/', { params }).then(mapPaginatedResponse),
  getNonConformance:  (id)      => grcClient.get(`/risk/non-conformances/${id}/`).then(unwrap),
  createNC:           (data)    => grcClient.post('/risk/non-conformances/', data).then(unwrap),
  updateNC:           (id, data)=> grcClient.patch(`/risk/non-conformances/${id}/`, data).then(unwrap),

  // Workflow (standard 5 endpoints per entity)
  workflowStart:    (entityType, id) => grcClient.post(`/risk/${entityType}/${id}/workflow/start/`).then(unwrap),
  workflowStatus:   (entityType, id) => grcClient.get(`/risk/${entityType}/${id}/workflow/status/`).then(unwrap),
  workflowAdvance:  (entityType, id, data) => grcClient.post(`/risk/${entityType}/${id}/workflow/advance/`, data).then(unwrap),
  workflowCancel:   (entityType, id) => grcClient.post(`/risk/${entityType}/${id}/workflow/cancel/`).then(unwrap),
  workflowRecall:   (entityType, id) => grcClient.post(`/risk/${entityType}/${id}/workflow/recall/`).then(unwrap),

  // Dashboard
  getDashboard:     () => grcClient.get('/risk/dashboard/').then(unwrap),
};
```

---

### B. TanStack Query — Hook Pattern

```ts
// hooks/risk/riskKeys.ts
export const riskKeys = {
  all: ['risk'] as const,
  dashboard:       () => [...riskKeys.all, 'dashboard'] as const,
  champions:       (p?) => [...riskKeys.all, 'champions', p] as const,
  champion:        (id) => [...riskKeys.all, 'champion', id] as const,
  assessments:     (p?) => [...riskKeys.all, 'assessments', p] as const,
  deptRegisters:   (p?) => [...riskKeys.all, 'dept-registers', p] as const,
  deptRegister:    (id) => [...riskKeys.all, 'dept-register', id] as const,
  irrs:            (p?) => [...riskKeys.all, 'irrs', p] as const,
  irr:             (id) => [...riskKeys.all, 'irr', id] as const,
  rtaps:           (p?) => [...riskKeys.all, 'rtaps', p] as const,
  rtap:            (id) => [...riskKeys.all, 'rtap', id] as const,
  rtapItems:       (rtapId) => [...riskKeys.all, 'rtap-items', rtapId] as const,
  qprs:            (p?) => [...riskKeys.all, 'qprs', p] as const,
  auditors:        (p?) => [...riskKeys.all, 'auditors', p] as const,
  auditor:         (id) => [...riskKeys.all, 'auditor', id] as const,
  qmsPrograms:     (p?) => [...riskKeys.all, 'qms-programs', p] as const,
  qmsProgram:      (id) => [...riskKeys.all, 'qms-program', id] as const,
  qmsPlan:         (id) => [...riskKeys.all, 'qms-plan', id] as const,
  checklists:      (planId) => [...riskKeys.all, 'checklists', planId] as const,
  nonConformances: (p?) => [...riskKeys.all, 'non-conformances', p] as const,
  riskSettings:    (tab) => [...riskKeys.all, 'settings', tab] as const,
};
```

```ts
// Example hook — hooks/risk/useRiskChampions.ts
export function useRiskChampions(params?: RiskChampionParams) {
  return useQuery({
    queryKey: riskKeys.champions(params),
    queryFn:  () => riskService.getChampions(params),
  });
}

export function useCreateRiskChampion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: riskService.createChampion,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: riskKeys.champions() });
      toast.success('Risk Champion nominated successfully.');
    },
    onError: (err: AxiosError) => {
      if (err.response?.status === 409)
        toast.error('An active Risk Champion already exists for this unit and fiscal year.');
      else
        toast.error('Failed to create Risk Champion. Please try again.');
    },
  });
}
```

---

### C. Workflow Console Integration

```tsx
// All workflow-bearing entities use EmbeddedWorkflowConsole — NO inline stage fallback.
// If Work Orchestration Service is unavailable, show Alert "Workflow service unavailable."

import { EmbeddedWorkflowConsole } from '@shared/components/workflow';

// Usage in any detail page:
<EmbeddedWorkflowConsole
  workflowKey="grc.risk_champion_appointment"
  entityId={appointmentId}
  onStatusChange={() => queryClient.invalidateQueries({ queryKey: riskKeys.champion(championId) })}
/>
```

Workflow template keys (for reference):
| Entity                          | Workflow Key                             |
|---------------------------------|------------------------------------------|
| RiskChampionAppointment         | `grc.risk_champion_appointment`          |
| DepartmentalRiskRegister        | `grc.dept_risk_register_approval`        |
| InstitutionalRiskRegister       | `grc.institutional_risk_register_approval` |
| RiskTreatmentActionPlan         | `grc.rtap_approval`                      |
| QuarterlyPerformanceReport      | `grc.quarterly_risk_report_approval`     |
| QualityAuditorAppointment       | `grc.qa_appointment`                     |
| QMSAuditProgram                 | `grc.qms_audit_program_approval`         |
| QMSAuditPlan                    | `grc.qms_audit_plan_approval`            |

---

### D. Realtime / Notification Patterns

Kafka Events consumed by frontend (via SSE / WebSocket on notification service):

| Event                               | Toast / Notification                                          |
|-------------------------------------|---------------------------------------------------------------|
| `risk.champion.appointment.signed`  | "Risk Champion appointment letter has been signed."          |
| `risk.dept_register.approved`       | "Departmental Risk Register has been approved."              |
| `risk.irr.approved`                 | "Institutional Risk Register approved. RTAP auto-created."   |
| `risk.rtap.created`                 | "Risk Treatment Action Plan is ready for population."        |
| `risk.qpr.approved`                 | "Quarterly Performance Report approved."                     |
| `risk.qms_plan.notification_sent`   | "Audit notification sent to auditee unit."                   |
| `risk.nc.raised`                    | "New non-conformance raised: {ncRef}"                        |

---

### E. Document Repository (DRS) Integration

Documents stored in DRS are referenced via `documentClient`:

| Document Type                  | Entity                  | DRS Link Pattern                           |
|--------------------------------|-------------------------|--------------------------------------------|
| RC Appointment Letter          | RiskChampionAppointment | `document_ref` on appointment record       |
| QA Appointment Letter          | QualityAuditorAppointment | `document_ref` on appointment record    |
| QPR Document                   | QuarterlyPerformanceReport | `attachment_ref`                        |
| Audit Plan Notification        | QMSAuditPlan            | auto-generated on notification send        |
| QMS Audit Report               | QMSAuditReport          | `report_document_ref`                      |
| NC Evidence                    | NonConformance          | `evidence_ref`                             |
| RTAP Quarterly Update Evidence | RTAPQuarterlyUpdate     | `evidence_ref`                             |

```tsx
// Pattern for opening DRS document
import { documentClient } from '@shared/api/gateway';

const openDocumentInDRS = (documentRef: string) => {
  window.open(documentClient.getDocumentUrl(documentRef), '_blank');
};

// Rendered as:
<Button variant="link" onClick={() => openDocumentInDRS(appointment.document_ref)}>
  {appointment.document_ref}  ↗
</Button>
```

---

### F. SmartSelect (IAM User Picker) Pattern

All user references (Risk Owner, Champion, Auditor, Assigned To) MUST use IAM SmartSelect — NOT free-text name inputs.

```tsx
// Used in all dialogs that reference IAM users
import { IAMUserSmartSelect } from '@shared/components/iam';

<IAMUserSmartSelect
  name="champion_uuid"
  label="Champion *"
  onSelect={(user) => form.setValue('champion_uuid', user.uuid)}
  required
/>
// Stores UUID, displays full name + email. Resolves on display from IAM cache.
```

---

### G. Pagination, Filtering, and Sorting

All list pages implement:
- **Pagination:** Page selector + rows per page (10/25/50). Uses `page` + `page_size` query params.
- **Filtering:** Each filter dropdown updates URL query params; filters are preserved on back navigation.
- **Search:** Debounced 300ms search input → `search=` param against backend.
- **Sorting:** Clickable column headers → `ordering=field` or `ordering=-field` for descending.

```tsx
// Standard filter state pattern:
const [filters, setFilters] = useState({ search: '', status: '', org_unit: '', fiscal_year: '', page: 1 });
// Synced to URL via useSearchParams()
```

---

### H. Loading, Error, and Empty States

```tsx
// Standard loading skeleton (table rows):
if (isLoading) return <TableSkeleton rows={5} cols={7} />;

// Error state:
if (isError)  return <Alert variant="destructive">Failed to load data. Please refresh.</Alert>;

// Empty state:
if (data?.count === 0) return (
  <EmptyState
    icon={<ShieldIcon />}
    title="No records found"
    message="No items match the current filters."
    action={canManage && <Button onClick={() => setCreateOpen(true)}>+ Create</Button>}
  />
);
```

---

### I. Business Rules Summary (Hard Constraints)

| Rule | Entity | Enforcement |
|------|--------|-------------|
| One active RC per org unit per FY | RiskChampion | Backend 409 → `toast.error(...)` |
| QA exam ≥75% required for certification | QualityAuditor | Server-side; UI disables appointment when is_certified=false |
| Max 2 exam attempts | QualityAuditor | attempt_count ≤ 2; "Max attempts" banner; [Record Exam] hidden |
| QA cannot audit own org unit | QMSAuditTeamAssignment | Conflict Alert in AssignAuditorDialog; [Assign] disabled |
| Notification ≥10 working days before audit start | QMSAuditPlan | Zod `.refine()` in CreateQMSPlanDialog |
| IRR entries from threshold-exceeding risks only | InstitutionalRiskEntry | AddInstitutionalEntryDialog filters by score ≥ threshold |
| Dept Register cannot be submitted without entries | DeptRiskRegister | [Submit] disabled client-side; Alert shown |
| RTAP auto-created with IRR approval — no manual create | RTAP | No [+ Create] on RTAPPage; [View] only |
| One Dept Register per org unit per FY | DeptRiskRegister | Backend 409 → `toast.error(...)` |
| One IRR per FY | InstitutionalRiskRegister | Backend 409 → `toast.error(...)` |
| One QPR per FY + Quarter | QuarterlyPerformanceReport | Backend 409 → `toast.error(...)` |
| One QMS Program per FY | QMSAuditProgram | Backend 409 → `toast.error(...)` |
| Audit Report: all checklist items must be filled before TL sign | QMSAuditReport | [Sign Report] disabled until all checklist rows have a conformity value |

---

### J. PermissionGate Usage Reference

```tsx
import { PermissionGate } from '@shared/components/auth';

// Wraps any button/action that requires a specific permission
<PermissionGate permission="grc:risk_champion:manage">
  <Button onClick={() => setCreateOpen(true)}>+ Nominate Risk Champion</Button>
</PermissionGate>

// Multi-permission (ANY of):
<PermissionGate anyOf={['grc:rtap:manage', 'grc:rtap:respond']}>
  <Button>Submit Quarterly Update</Button>
</PermissionGate>
```

---

### K. Risk Score Auto-Computation (Client-Side Preview)

The backend computes `inherent_risk_score = likelihood.numerical_value × impact.numerical_value` on save.
The frontend MUST preview this computation client-side within the dialog BEFORE save:

```tsx
// Inside CreateRiskAssessmentDialog
const score = (selectedLikelihood?.numerical_value ?? 0) * (selectedImpact?.numerical_value ?? 0);
const riskLevel = riskLevels.find(l => score >= l.min_score && score <= l.max_score);

// Rendered immediately on selection change — NOT an <input>:
<div className="flex items-center gap-2">
  <span className="font-mono text-lg">{score}</span>
  {riskLevel && (
    <span className="px-2 py-1 rounded text-white text-sm font-medium"
          style={{ backgroundColor: riskLevel.color_code }}>
      {riskLevel.label}
    </span>
  )}
</div>
```

---

*End of Corrected UI Design Document*
*(SRS Reference: RISK_MANAGEMENT.md — 100% coverage)*
*(Models Reference: Risk_Management_Module_Core_Design.md — all 20 models covered)*

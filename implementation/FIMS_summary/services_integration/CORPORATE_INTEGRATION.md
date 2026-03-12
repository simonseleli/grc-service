# Corporate Service Implementation Summary

**Version**: 3.2  
**Last Updated**: March 10, 2026  
**Status**: Production Ready

This document provides a comprehensive summary of the Corporate Service implementation for both backend and frontend. It serves as a reference for understanding what has been built, how it works, and how to extend it.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Backend Implementation](#3-backend-implementation)
4. [Frontend Implementation](#4-frontend-implementation)
5. [Data Models](#5-data-models)
6. [Inter-Service Communication](#6-inter-service-communication)
7. [Workflow Integration](#7-workflow-integration)
8. [Background Tasks & Scheduling](#8-background-tasks--scheduling)
9. [API Reference](#9-api-reference)
10. [Development Patterns](#10-development-patterns)
11. [Hybrid Permission System](#11-hybrid-permission-system)
12. [UI/UX Enhancements](#12-uiux-enhancements)
13. [Deployment](#13-deployment)
14. [Extending the Service](#14-extending-the-service)
15. [Changelog](#15-changelog)

---

## 1. Overview

### 1.1 Purpose

The Corporate Service is the central microservice handling all corporate operations for the organization, including:

- **Human Resources (HR)**: Staff management, organization structure, leave, training, safari, fleet, allowances, benefits
- **Finance**: Budget management, internal payments, imprest, petty cash, fees, revenue, billing, GePG integration
- **Procurement**: Annual plans, requisitions, vendors, purchase orders, contracts, store management, inventory
- **Asset Management**: Asset register, assignments, maintenance, depreciation, disposal, valuation, custodian management, property loss reports

### 1.2 Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 5.x, Django REST Framework, PostgreSQL |
| **Frontend** | React 18, TypeScript, TanStack Query (React Query), Radix UI/Shadcn, Tailwind CSS |
| **Messaging** | Apache Kafka |
| **Caching** | Redis |
| **Task Queue** | Celery with Celery Beat |
| **Authentication** | JWT (shared with IAM Service) |
| **API Documentation** | drf-spectacular (OpenAPI/Swagger) |
| **Containerization** | Docker, Docker Compose |

### 1.3 Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        API Gateway (Nginx :8080)                         │
│    /api/v1/corporate/* → Corporate Service                              │
│    /api/v1/auth/*      → IAM Service                                    │
│    /api/v1/workflow/*  → Work Orchestration Service                     │
│    /api/v1/documents/* → Document Records Service                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│   IAM Service   │      │ Work Orchestration  │      │    Document     │
│     :8000       │◄────►│    Service :8004    │◄────►│  Service :8002  │
└─────────────────┘      └─────────────────────┘      └─────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │     Corporate Service :8008   │
                    │  ┌─────────────────────────┐  │
                    │  │      HR Module          │  │
                    │  │  (Staff, Leave, Fleet)  │  │
                    │  ├─────────────────────────┤  │
                    │  │    Finance Module       │  │
                    │  │  (Budget, Imprest, PC)  │  │
                    │  ├─────────────────────────┤  │
                    │  │  Procurement Module     │  │
                    │  │  (Plans, Vendors, PO)   │  │
                    │  ├─────────────────────────┤  │
                    │  │    Assets Module        │  │
                    │  │  (Register, Deprec.)    │  │
                    │  └─────────────────────────┘  │
                    └───────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ PostgreSQL│   │   Redis   │   │   Kafka   │
            │  :5432    │   │   :6379   │   │   :9092   │
            └───────────┘   └───────────┘   └───────────┘
```

---

## 2. Architecture

### 2.1 Clean Architecture (Hexagonal Architecture)

The Corporate Service implements Clean Architecture with clear separation of concerns:

```
corporate-service/
├── config/                         # Django configuration
│   ├── settings.py                 # Django settings
│   ├── celery.py                   # Celery app + beat schedule
│   ├── urls.py                     # Root URL routing
│   └── permissions/                # Permission JSON definitions
│       └── corporate-service.json
│
├── apps/
│   ├── api/                        # Interface Layer (REST API)
│   │   ├── authentication.py       # JWT authentication
│   │   ├── mixins/
│   │   │   └── workflow_viewset_mixin.py
│   │   ├── serializers/
│   │   │   ├── asset_serializers.py
│   │   │   ├── config_serializers.py
│   │   │   ├── finance_serializers.py
│   │   │   ├── hr_serializers.py
│   │   │   └── procurement_serializers.py
│   │   ├── urls/
│   │   │   ├── api_urls.py         # Main REST routes
│   │   │   └── health_urls.py
│   │   └── views/
│   │       ├── asset_views.py
│   │       ├── config_views.py
│   │       ├── finance_views.py
│   │       ├── hr_config_views.py
│   │       ├── hr_leave_views.py
│   │       ├── hr_organization_views.py
│   │       ├── hr_staff_views.py
│   │       ├── hr_training_safari_fleet_allowances_views.py
│   │       ├── organization_hierarchy_views.py
│   │       └── procurement_views.py
│   │
│   ├── core/                       # Domain Layer
│   │   ├── entities/               # Domain entities (dataclasses)
│   │   ├── repositories/           # Repository interfaces (ABC)
│   │   ├── mixins/
│   │   │   └── workflow_mixin.py   # Model workflow mixin
│   │   ├── workflows/
│   │   │   └── workflows.yaml      # Workflow template definitions
│   │   ├── templates/
│   │   │   ├── notifications.yaml  # Notification templates (registered with Work Orchestration Service)
│   │   │   └── registry.py
│   │   ├── consumers/
│   │   │   └── workflow_event_consumer.py
│   │   ├── kafka_permission_publisher.py
│   │   ├── permission_middleware.py
│   │   └── permissions.py
│   │
│   ├── infrastructure/             # Infrastructure Layer
│   │   ├── persistence/
│   │   │   ├── models.py           # All Django ORM models (94+)
│   │   │   ├── repositories/       # Repository implementations
│   │   │   └── depreciation_service.py
│   │   ├── external/               # HTTP clients (core services ONLY: IAM, Document, Orchestration)
│   │   │   ├── iam_client.py
│   │   │   ├── orchestration_client.py   # Also handles notification dispatch (notifications are built into orchestration)
│   │   │   └── document_client.py
│   │   └── messaging/
│   │       └── kafka_producer.py
│   │
│   ├── hr/                         # HR Module
│   │   ├── services/
│   │   └── tasks/
│   │       └── leave_tasks.py
│   ├── finance/                    # Finance Module
│   │   └── services/
│   ├── procurement/                # Procurement Module
│   │   └── services/
│   ├── fleet/                      # Fleet Module
│   │   └── services/
│   └── assets/                     # Assets Module
│       └── tasks/
│           └── depreciation_tasks.py
│
└── [docs, logs, media, scripts, staticfiles]
```

### 2.2 Layer Responsibilities

| Layer | Responsibility | Dependencies |
|-------|----------------|--------------|
| **Domain (core)** | Business logic, entities, repository interfaces, workflow definitions | None (framework-independent) |
| **Infrastructure** | Data persistence, external services, messaging, Kafka | Domain |
| **API** | HTTP request/response handling, serialization, authentication | Domain, Infrastructure |
| **Module Services** | Business logic orchestration | Domain, Infrastructure |

### 2.3 Design Patterns Used

1. **Repository Pattern**: Interface defined in `core/repositories/`, implementation in `infrastructure/persistence/repositories/`
2. **Service Layer Pattern**: Business logic in module-specific services (`hr/services/`, `finance/services/`, etc.)
3. **Domain Entity Pattern**: Core entities are Python dataclasses separate from ORM models
4. **Dependency Inversion**: Domain depends on abstractions (repository interfaces), not implementations
5. **Workflow Mixin Pattern**: `WorkflowViewSetMixin` provides standardized workflow REST actions
6. **Model Mixin Pattern**: `WorkflowMixin` adds workflow fields and methods to models
7. **Event-Driven Pattern**: Kafka consumers react to workflow events to update entity state
8. **Partial Update ViewSet**: Custom base ViewSet supporting list, retrieve, create, partial_update operations
9. **Ownership Filter Pattern**: `OwnershipFilterMixin` automatically filters querysets based on user identity and permissions
10. **Status Display Pattern**: `StatusDisplayMixin` adds human-readable status labels to API responses
11. **Smart Navigation Pattern**: `PermissionLink` component resolves navigation paths based on user permissions

---

## 3. Backend Implementation

### 3.1 ViewSets by Domain

#### Configuration ViewSets (`config_views.py`, `hr_config_views.py`)

| ViewSet | Purpose |
|---------|---------|
| `LookupCategoryViewSet` | Lookup categories (gender, marital_status, etc.) |
| `LookupValueViewSet` | Lookup values within categories |
| `SalaryGradeViewSet` | Salary grade configuration |
| `DesignationViewSet` | Staff designations |
| `RankViewSet` | Staff ranks |
| `BankViewSet` | Banks |
| `BankBranchViewSet` | Bank branches |
| `PerDiemRateViewSet` | Per diem rate configuration |
| `FuelStationProviderViewSet` | Fuel station providers |
| `ExtraDutyRateConfigViewSet` | Extra duty rate configuration |
| `BenefitTypeViewSet` | Employee benefit types |
| `StaffBenefitViewSet` | Staff benefits (with remove, suspend, reactivate, summary actions) |

#### HR ViewSets

| File | ViewSets |
|------|----------|
| `hr_organization_views.py` | `DepartmentViewSet` |
| `organization_hierarchy_views.py` | `OrganizationHierarchyViewSet` (read-only hierarchy) |
| `hr_staff_views.py` | `StaffProfileViewSet`, `StaffDependantViewSet`, `StaffQualificationViewSet`, `StaffEmploymentHistoryViewSet` |
| `hr_leave_views.py` | `LeaveTypeViewSet`, `LeaveRosterViewSet`, `LeaveRosterEntryViewSet`, `LeaveBalanceViewSet`, `LeaveApplicationViewSet`, `LeavePaymentViewSet`, `LeaveAllowanceConfigViewSet`, `LeaveReportViewSet`, `LeaveAllowanceRequestViewSet` |
| `hr_training_safari_fleet_allowances_views.py` | `TrainingProgramViewSet`, `TrainingRequestViewSet`, `TrainingSessionViewSet`, `TrainingSessionAttendeeViewSet`, `TrainingResourceViewSet`, `SafariApplicationViewSet`, `VehicleViewSet`, `FuelWalletViewSet`, `FuelRequestViewSet`, `VehicleScheduleViewSet`, `VehicleMaintenanceRequestViewSet`, `VehicleMaintenanceItemViewSet`, `SalaryAdvanceRequestViewSet`, `ExtraDutyClaimViewSet`, `ExtraDutyClaimItemViewSet` |

#### Finance ViewSets (`finance_views.py`)

| ViewSet | Purpose |
|---------|---------|
| `CostCenterViewSet` | Cost center management |
| `BudgetAllocationViewSet` | Budget allocations |
| `BudgetVerificationViewSet` | Budget verification |
| `BudgetTransferViewSet` | Budget transfers (workflow-enabled) |
| `InternalMemoViewSet` | Internal memos (workflow-enabled) |
| `InternalPaymentViewSet` | Internal payments |
| `InternalPaymentItemViewSet` | Payment line items |
| `ImprestRequestViewSet` | Imprest requests |
| `ImprestRetirementViewSet` | Imprest retirements (workflow-enabled) |
| `ImprestRetirementItemViewSet` | Retirement line items |
| `PettyCashRequisitionViewSet` | Petty cash requisitions (workflow-enabled) |
| `PettyCashLineItemViewSet` | Petty cash line items |
| `PettyCashFloatViewSet` | Petty cash floats |
| `PettyCashFloatReplenishmentViewSet` | Float replenishments |
| `FeeCategoryViewSet` | Fee categories |
| `FeeItemViewSet` | Fee items |
| `RevenueSourceViewSet` | Revenue sources |
| `RevenueSourceTypeViewSet` | Revenue source types |
| `BillViewSet` | GePG bills |
| `GepgTransactionViewSet` | GePG transactions |
| `VendorInvoiceViewSet` | Vendor invoices |
| `ExternalPaymentRequestViewSet` | External payment requests |

#### Procurement ViewSets (`procurement_views.py`)

| ViewSet | Purpose |
|---------|---------|
| `TenderCategoryViewSet` | Tender categories |
| `BudgetPurposeViewSet` | Budget purposes |
| `FundingSourceViewSet` | Funding sources |
| `ProcurementMethodViewSet` | Procurement methods |
| `ProcurementMethodCategoryViewSet` | Procurement method categories |
| `SelectionMethodViewSet` | Selection methods |
| `ContractTypeViewSet` | Contract types |
| `TenderNumberSequenceViewSet` | Tender number sequences |
| `AnnualProcurementPlanViewSet` | Annual procurement plans (workflow-enabled) |
| `ProcurementPlanItemViewSet` | Plan items |
| `ProcurementPlanItemHistoryViewSet` | Plan item history |
| `DepartmentalRequestViewSet` | Departmental requests |
| `RequisitionViewSet` | Requisitions (workflow-enabled) |
| `RequisitionItemViewSet` | Requisition items |
| `VendorViewSet` | Vendor management |
| `VendorCategoryViewSet` | Vendor categories |
| `VendorRatingViewSet` | Vendor ratings |
| `PurchaseOrderViewSet` | Purchase orders |
| `ContractViewSet` | Contracts (workflow-enabled) |
| `ContractPaymentViewSet` | Contract payments |
| `GoodsDeliveryViewSet` | Goods deliveries (workflow-enabled) |
| `InventoryItemViewSet` | Inventory items |
| `GoodsRequestViewSet` | Goods requests |
| `GoodsIssueVoucherViewSet` | Goods issue vouchers (workflow-enabled) |
| `StoreReceiptVoucherViewSet` | Store receipt vouchers |
| `StockMovementViewSet` | Stock movements |
| `StockAdjustmentViewSet` | Stock adjustments |

#### Asset ViewSets (`asset_views.py`)

| ViewSet | Purpose | Custom Actions |
|---------|---------|----------------|
| `AssetCategoryViewSet` | Asset categories | |
| `AssetViewSet` | Asset register | |
| `AssetAssignmentViewSet` | Asset assignments | |
| `AssetMaintenanceViewSet` | Asset maintenance | submit, approve, start, complete, reject, advance |
| `DepreciationRunViewSet` | Depreciation runs | execute, catch-up |
| `AssetDepreciationRecordViewSet` | Depreciation records | |
| `AssetDisposalViewSet` | Asset disposals | submit, valuate, committee-review, notify-treasury, approve, complete, reject, return, advance |
| `AssetDeploymentViewSet` | Asset deployments | relocate, return, history, by-location |
| `AssetValuationViewSet` | Asset valuations | bulk-revalue, report, history |
| `CustodianDepartmentViewSet` | Custodian departments | configure, config, assets |
| `CustodianConfigurationViewSet` | Custodian configurations | category/set, asset/set, asset/reset |
| `PropertyLossReportViewSet` | Property loss reports | submit, advance |
| `PropertyLossReportConfigViewSet` | Loss report config | |

### 3.2 Workflow-Enabled ViewSets

ViewSets that integrate with the Work Orchestration Service inherit `WorkflowViewSetMixin` and provide these standard actions:

| Action | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| `start_workflow` | POST | `/{id}/start-workflow/` | Start workflow |
| `workflow_action` | POST | `/{id}/workflow-action/` | Perform workflow action (approve/reject/return) |
| `workflow_status` | GET | `/{id}/workflow-status/` | Get workflow status |
| `workflow_history` | GET | `/{id}/workflow-history/` | Get workflow activity history |
| `cancel_workflow` | POST | `/{id}/cancel-workflow/` | Cancel workflow |

### 3.3 Custom ViewSet Actions by Entity

| Entity | Custom Actions |
|--------|----------------|
| **LeaveApplicationViewSet** | submit, hram-approve, hod-approve, director-approve, finance-verify, final-approve, reject, return |
| **LeaveBalanceViewSet** | bulk_initialize, year_end_rollover |
| **LeaveReportViewSet** | staff_leave_plans, leave_utilization, carry_over_report |
| **TrainingSessionViewSet** | publish, start, complete, cancel, attendees, invitations |
| **StaffBenefitViewSet** | remove, suspend, reactivate, summary |
| **AssetMaintenanceViewSet** | submit, approve, start, complete, reject |
| **AssetDisposalViewSet** | submit, valuate, committee-review, notify-treasury, approve, complete, reject, return |
| **AssetValuationViewSet** | bulk-revalue, report, history |
| **AssetDeploymentViewSet** | relocate, return, history, by-location |
| **DepreciationRunViewSet** | execute, catch-up |

### 3.4 Code Generation Patterns

Auto-generated codes follow consistent patterns:

| Entity | Prefix | Pattern | Example |
|--------|--------|---------|---------|
| Leave Application | `APP-` | `APP-{uuid8}` | `APP-A1B2C3D4` |
| Leave Allowance Request | `LAR-` | `LAR-{year}-{seq:04d}` | `LAR-2026-0001` |
| Training Request | `TR-` | `TR-{uuid8}` | `TR-A1B2C3D4` |
| Training Session | `TS-` | `TS-{year}-{count:04d}` | `TS-2026-0001` |
| Safari Application | `SA-` | `SA-{uuid8}` | `SA-A1B2C3D4` |
| Fuel Request | `FR-` | `FR-{uuid8}` | `FR-A1B2C3D4` |
| Vehicle Maintenance | `MR-` | `MR-{uuid8}` | `MR-A1B2C3D4` |
| Salary Advance | `SAR-` | `SAR-{uuid8}` | `SAR-A1B2C3D4` |
| Extra Duty Claim | `EDC-` | `EDC-{uuid8}` | `EDC-A1B2C3D4` |
| Internal Memo | `MEMO-` | `MEMO-{uuid8}` | `MEMO-A1B2C3D4` |
| Imprest Request | `IM-` | `IM-{uuid8}` | `IM-A1B2C3D4` |
| Requisition | `REQ-` | `REQ-{uuid8}` | `REQ-A1B2C3D4` |
| Purchase Order | `PO-` | `PO-{uuid8}` | `PO-A1B2C3D4` |
| Annual Procurement Plan | `APP-` | `APP-{year}-{uuid6}` | `APP-2026-A1B2C3` |
| Procurement Plan Item | | `{org}/{fy}/{cat}/{seq:02d}` | `FCC/2025-26/G/01` |
| Goods Delivery | `GD-` | `GD-{uuid8}` | `GD-A1B2C3D4` |
| Goods Issue Voucher | `GIV-` | `GIV-{uuid8}` | `GIV-A1B2C3D4` |
| Store Receipt Voucher | `SRV-` | `SRV-{uuid8}` | `SRV-A1B2C3D4` |
| Stock Movement | `SM-` | `SM-{uuid8}` | `SM-A1B2C3D4` |
| Asset | `AST-` | `AST-{uuid8}` | `AST-A1B2C3D4` |
| Depreciation Run | `DRUN-` | `DRUN-{uuid8}` | `DRUN-A1B2C3D4` |
| Asset Disposal | `DSP-` | `DSP-{uuid8}` | `DSP-A1B2C3D4` |
| Property Loss Report | `PL-` | `PL-{year}-{count:04d}` | `PL-2026-0001` |

---

## 4. Frontend Implementation

### 4.1 Directory Structure

```
frontend/apps/staff-portal/src/
├── pages/corporate/              # ~95 page components
├── components/
│   ├── corporate/                # ~85 dialog/form components
│   │   ├── organization-hierarchy/  # Hierarchy visualizations
│   │   └── staff-detail/         # Staff profile tab components
│   └── dashboards/
│       └── CorporateServicesDashboard.tsx
├── services/
│   └── corporateService.ts       # Centralized API client (~6.8k lines)
├── hooks/
│   └── useCorporateWorkflows.ts  # Workflow mutation hooks
└── routes/
    └── (defined in App.tsx)

frontend/packages/shared/src/
├── hooks/
│   └── useResourcePermission.ts  # Permission scope resolution hook
├── components/
│   └── PermissionLink.tsx        # Smart navigation based on permissions
└── utils/
    └── tokenUtils.ts             # JWT token parsing utilities
```

### 4.2 Pages by Category

| Category | Pages |
|----------|-------|
| **HR - Staff** | StaffListingPage, StaffDetailPage, StaffPositionsPage, OrganizationStructurePage |
| **HR - Leave** | LeaveApplicationPage, LeaveApplicationDetailPage, LeaveRosterPage, LeaveRosterDetailPage, MyLeaveRosterPage, MyLeaveRosterDetailPage, LeaveTypesPage, LeavePaymentsPage, LeavePaymentDetailPage, LeaveAllowanceRequestsPage, LeaveAllowanceConfigsPage, LeaveReportsPage |
| **HR - Fleet** | FleetManagementPage, VehicleViewPage, FuelRequestPage, FuelRequestDetailPage, FuelWalletsPage, FuelStationsPage, FuelTransactionPage, VehicleSchedulingPage, VehicleSchedulingDetailPage, VehicleMaintenancePage, VehicleMaintenanceDetailPage, VehicleDisposalPage, VehicleCalendarPage |
| **HR - Training** | StaffTrainingPage, TrainingRequestDetailPage, TrainingApplicationPage, TrainingSessionsPage, TrainingSessionDetailPage, TrainingProgramsPage, TrainingCalendarPage |
| **HR - Allowances** | EmployeeBenefitsPage, SafariApplicationPage, SafariApplicationDetailPage, ExtraDutyPage, ExtraDutyDetailPage, SalaryAdvancesPage, SalaryAdvanceDetailPage |
| **Finance** | InternalPaymentPage, InternalMemoPage, InternalMemoDetailPage, ImprestRequestPage, ImprestRetirementPage, ImprestRetirementDetailPage, BudgetAllocationPage, BudgetVerificationPage, BudgetTransferPage, BudgetTransferDetailPage, PettyCashPage, PettyCashDetailPage, PettyCashFloatPage, CostCentersPage, FeeManagementPage, ExternalPaymentPage, VendorInvoicePage |
| **Finance - Revenue** | RevenueCollectionPage, RevenueFinesPage, RevenueSourcesPage, GePGBillsPage, GePGPaymentsPage |
| **Procurement - Plans** | AcquisitionApprovalPage, DepartmentalPlanPage, SubmissionAnnualPlanPage, ApprovedAnnualPlanPage, AnnualProcurementPlanDetailPage, ProcurementPlanPage, ProcurementPlanViewPage |
| **Procurement - Orders** | RequisitionViewPage, PurchaseOrderPage, PurchaseOrderViewPage, VendorPage |
| **Procurement - Delivery** | GoodsDeliveryPage, GoodsDeliveryDetailPage, GoodsDeliveryViewPage |
| **Procurement - Store** | GeneralStorePage, GoodsRequestPage, GoodsIssueVoucherPage, GoodsIssueVoucherDetailPage, StoreReceiptVoucherPage, StockMovementPage, StockAdjustmentPage |
| **Contracts** | ContractManagementPage, ContractDetailPage, ContractViewPage, ContractPaymentsPage |
| **Assets** | AssetRegisterPage, AssetViewPage, AssetCategoryPage, AssetAssignedPage, AssetMaintenancePage, AssetMaintenanceDetailPage, AssetDisposalPage, AssetDisposalDetailPage, AssetDisposalViewPage, AssetCustodianPage, AssetDeploymentPage, AssetValuationPage, PropertyLossPage, PropertyLossReportDetailPage, DepreciationRunsPage |
| **Configuration** | DepartmentsPage, LookupCategoriesPage, RanksPage, SalaryGradesPage, BanksPage, BankBranchesPage, TenderCategoriesPage, ProcurementMethodsPage, PerDiemRatesPage, ExtraDutyRateConfigsPage |

### 4.3 API Client (`corporateService.ts`)

The centralized API client provides type-safe access to all corporate endpoints:

```typescript
// Path constants
const PATHS = {
  // Config
  lookupCategories: "config/lookup-categories",
  lookupValues: "config/lookup-values",
  salaryGrades: "config/salary-grades",
  
  // HR - Organization
  departments: "hr/organization/departments",
  staffProfiles: "hr/organization/staff-profiles",
  
  // HR - Leave
  leaveTypes: "hr/leave/types",
  leaveRosters: "hr/leave/roster",
  leaveBalances: "hr/leave/balances",
  leaveApplications: "hr/leave/applications",
  
  // Finance
  costCenters: "finance/cost-centers",
  budgetAllocations: "finance/budget/allocations",
  internalMemos: "finance/payments/internal-memos",
  imprestRequests: "finance/imprest/requests",
  
  // Procurement
  requisitions: "procurement/requisitions",
  purchaseOrders: "procurement/orders",
  vendors: "procurement/vendors",
  goodsIssueVouchers: "procurement/store/issue-vouchers",
  
  // Assets
  assets: "assets/register",
  assetCategories: "assets/categories",
  assetMaintenance: "assets/maintenance",
  assetDisposals: "assets/disposals",
} as const;

// Generic CRUD helpers
export function corporateList<T>(path: string, params?: Record<string, any>) {
  return corporateClient.get<PaginatedResponse<T>>(`/${path}/`, { params });
}

export function corporateGet<T>(path: string, id: string) {
  return corporateClient.get<T>(`/${path}/${id}/`);
}

export function corporateCreate<T>(path: string, data: Partial<T>) {
  return corporateClient.post<T>(`/${path}/`, data);
}

export function corporateUpdate<T>(path: string, id: string, data: Partial<T>) {
  return corporateClient.patch<T>(`/${path}/${id}/`, data);
}

export function corporateDelete(path: string, id: string) {
  return corporateClient.delete(`/${path}/${id}/`);
}
```

### 4.4 State Management with React Query

**Query Pattern:**

```typescript
const { data, isLoading, isError, refetch } = useQuery({
  queryKey: ["corporate", "leave-applications", { myOnly, status, page }],
  queryFn: () => listLeaveApplications({ 
    limit: 20, 
    offset: (page - 1) * 20,
    applicant: myOnly ? currentStaffId : undefined,
    status 
  }),
});
```

**Mutation Pattern:**

```typescript
const createMutation = useMutation({
  mutationFn: (payload: CreateLeaveApplicationPayload) => 
    createLeaveApplication(payload),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["corporate", "leave-applications"] });
    toast.success("Leave application created successfully");
    setDialogOpen(false);
  },
  onError: (error: Error) => {
    toast.error(error.message || "Failed to create application");
  },
});
```

**Query Key Convention:**

```typescript
["corporate", <resource>]                          // All items
["corporate", <resource>, { filters }]             // Filtered list
["corporate", <resource>, id]                      // Single item
["corporate", "staff-profile-by-user", userId]     // User's staff profile
```

### 4.5 Workflow Hooks (`useCorporateWorkflows.ts`)

Provides reusable hooks for workflow operations:

```typescript
// Status and history queries
const { data: status } = useCorporateWorkflowStatus("leave-application", id);
const { data: history } = useCorporateWorkflowHistory("leave-application", id);

// Mutation hooks by entity
const submitMutation = useSubmitLeaveApplication();
const approveMutation = useApproveLeaveApplication();
const rejectMutation = useRejectLeaveApplication();

// Generic advance hook
const advanceMutation = useAdvanceRequisition();
```

### 4.6 Common UI Patterns

**GenericListPage Component:**

```typescript
<GenericListPage
  title="Leave Applications"
  items={mappedItems}
  columns={columns}
  userRole={userRole}
  onView={(item) => navigate(`/service/corporate/leave-applications/${item.id}`)}
  onEdit={handleEdit}
  onDelete={handleDelete}
  onCreateNew={() => setDialogOpen(true)}
  showCreateButton={true}
  pagination={{ page, totalPages, onPageChange }}
/>
```

**List Page + Dialog Pattern:**

1. `useQuery` for list data
2. `useMutation` for create/update/delete
3. `GenericListPage` for layout with columns definition
4. Create/Edit dialog (e.g., `CreateLeaveApplicationDialog`) controlled by `open` and `editData`
5. `mapToListItem` function to convert API models to list item shape
6. `myOnly` prop for personal workspace filtering

**Form Validation with Zod:**

```typescript
const formSchema = z.object({
  leave_type: z.string().min(1, "Leave type is required"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().min(1, "End date is required"),
  days_requested: z.number().min(1, "At least 1 day required"),
  reason: z.string().min(10, "Please provide a detailed reason"),
});

const { register, handleSubmit, control, formState: { errors } } = useForm({
  resolver: zodResolver(formSchema),
});
```

### 4.7 Dashboard Implementation

The Corporate Services Dashboard (`CorporateServicesDashboard.tsx`) provides:

- **Summary Cards**: Quick stats for each module
- **Charts**: Revenue vs expenses (line), department spending (pie), leave status (bar), fleet utilization (bar)
- **Tabbed Sections**: My Workspace, Procurement, Finance, Human Resource
- **Quick Links**: Direct navigation to common tasks

---

## 5. Data Models

### 5.1 Base Model

All models extend a common base:

```python
class BaseModel(models.Model):
    """Abstract base model with common fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

### 5.2 Model Categories

#### Configuration Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `LookupCategory` | lookup_categories | code, name, is_system |
| `LookupValue` | lookup_values | category (FK), code, name, sort_order, is_active |
| `SalaryGrade` | salary_grades | code, name, level, min_salary, max_salary |
| `Designation` | designations | code, name, salary_grade (FK) |
| `Rank` | ranks | code, name, level |
| `Bank` | banks | code, name, swift_code |
| `BankBranch` | bank_branches | bank (FK), code, name, location |

#### Organization Model

```python
class Department(BaseModel):
    UNIT_TYPE_CHOICES = [
        ('commission', 'Commission'),
        ('directorate', 'Directorate'),
        ('section', 'Section'),
        ('unit', 'Unit'),
        ('zonal_office', 'Zonal Office'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    unit_type = models.CharField(max_length=30, choices=UNIT_TYPE_CHOICES)
    parent = models.ForeignKey('self', null=True, related_name='children')
    level = models.PositiveSmallIntegerField(default=0)
    head_id = models.UUIDField(null=True)  # Reference to StaffProfile
    is_active = models.BooleanField(default=True)
```

#### HR Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `StaffProfile` | staff_profiles | user_id, pf_number, first_name, last_name, department, designation, rank, line_manager |
| `StaffDependant` | staff_dependants | staff (FK), relationship (LookupValue) |
| `StaffQualification` | staff_qualifications | staff (FK), qualification_type (LookupValue), institution |
| `StaffEmploymentHistory` | staff_employment_history | staff (FK), organization, department |
| `StaffBenefit` | staff_benefits | staff (FK), benefit_type (FK) |
| `LeaveType` | leave_types | code, name, max_days_per_year, allow_carry_forward, max_carry_forward_days |
| `LeaveRoster` | leave_rosters | fiscal_year, status, created_by_id |
| `LeaveRosterEntry` | leave_roster_entries | roster (FK), staff (FK), planned_dates (JSON) |
| `LeaveBalance` | leave_balances | staff (FK), leave_type (FK), fiscal_year, opening_balance, earned_days, used_days, carried_forward, closing_balance |
| `LeaveApplication` | leave_applications | application_number, applicant (FK), leave_type (FK), start_date, end_date, workflow_plan_id |
| `LeavePayment` | leave_payments | leave_application (FK), payment_type, amount, status |
| `LeaveAllowanceRequest` | leave_allowance_requests | request_number (LAR-), staff (FK), leave_application (FK) |

#### Fleet Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `Vehicle` | vehicles | registration_number, make, model, fuel_type, department |
| `FuelWallet` | fuel_wallets | department (FK), fiscal_year, allocated_amount, utilized_amount |
| `FuelRequest` | fuel_requests | request_number (FR-), vehicle (FK), driver (FK), workflow_plan_id |
| `VehicleSchedule` | vehicle_schedules | vehicle (FK), scheduled dates, workflow_plan_id |
| `VehicleMaintenanceRequest` | vehicle_maintenance_requests | request_number (MR-), vehicle (FK), workflow_plan_id |

#### Training & Allowance Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `TrainingProgram` | training_programs | name, description, duration |
| `TrainingRequest` | training_requests | request_number (TR-), staff (FK), program (FK), workflow_plan_id |
| `TrainingSession` | training_sessions | session_number (TS-), program (FK), status |
| `SafariApplication` | safari_applications | application_number (SA-), applicant (FK), destination, workflow_plan_id |
| `SalaryAdvanceRequest` | salary_advance_requests | request_number (SAR-), staff (FK), amount, workflow_plan_id |
| `ExtraDutyClaim` | extra_duty_claims | claim_number (EDC-), claimant (FK), department, workflow_plan_id |

#### Finance Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `CostCenter` | cost_centers | department (FK), code, name |
| `BudgetAllocation` | budget_allocations | department (FK), fiscal_year, amounts |
| `BudgetTransfer` | budget_transfers | transfer_number, from_allocation (FK), to_allocation (FK), workflow_plan_id |
| `InternalMemo` | internal_memos | memo_number (MEMO-), officer (FK), department (FK), amount_requested, workflow_plan_id |
| `InternalPayment` | internal_payments | payment_number, memo (FK), status |
| `ImprestRequest` | imprest_requests | imprest_number (IM-), holder (FK), amount, workflow_plan_id |
| `ImprestRetirement` | imprest_retirements | retirement_number, imprest_request (FK), workflow_plan_id |
| `PettyCashRequisition` | petty_cash_requisitions | requisition_number, user_department (FK), workflow_plan_id |
| `PettyCashFloat` | petty_cash_floats | department (FK), custodian (FK), amount |
| `VendorInvoice` | vendor_invoices | invoice_number, vendor (FK) |
| `ExternalPaymentRequest` | external_payment_requests | request_number, vendor (FK) |

#### Procurement Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `AnnualProcurementPlan` | annual_procurement_plans | plan_number (APP-), fiscal_year, status, workflow_plan_id |
| `ProcurementPlanItem` | procurement_plan_items | tender_number, plan (FK), department (FK) |
| `DepartmentalRequest` | departmental_requests | request_number, department (FK) |
| `Requisition` | requisitions | requisition_number (REQ-), requester (FK), department (FK), workflow_plan_id |
| `Vendor` | vendors | name, registration_number |
| `PurchaseOrder` | purchase_orders | po_number (PO-), requisition (FK), vendor (FK) |
| `Contract` | contracts | contract_number, vendor (FK), workflow_plan_id |
| `GoodsDelivery` | goods_deliveries | delivery_number, po (FK), workflow_plan_id |
| `InventoryItem` | inventory_items | item_code, name, category (FK), quantity_on_hand |
| `GoodsRequest` | goods_requests | request_number, requester (FK), department (FK) |
| `GoodsIssueVoucher` | goods_issue_vouchers | voucher_number (GIV-), goods_request (FK), workflow_plan_id |
| `StoreReceiptVoucher` | store_receipt_vouchers | receipt_number (SRV-), goods_delivery (FK) |
| `StockMovement` | stock_movements | movement_number (SM-), inventory_item (FK), movement_type |

#### Asset Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `AssetCategory` | asset_categories | code, name, custodian_department (FK), depreciation_method, useful_life_years |
| `Asset` | assets | asset_tag (AST-), category (FK), acquisition_cost, status (LookupValue), custodian_department |
| `AssetAssignment` | asset_assignments | asset (FK), assigned_to (FK), department (FK), assigned_at, returned_at |
| `AssetMaintenance` | asset_maintenance | asset (FK), request_type, status, workflow_plan_id |
| `AssetDeployment` | asset_deployments | asset (FK), location_type, department (FK), status |
| `AssetValuation` | asset_valuations | asset (FK), valuation_date, market_value |
| `CustodianConfiguration` | custodian_configurations | department (FK), capabilities |
| `DepreciationRun` | depreciation_runs | run_number (DRUN-), fiscal_year, period_number, status |
| `AssetDepreciationRecord` | asset_depreciation_records | asset (FK), depreciation_run (FK), amount |
| `AssetDisposal` | asset_disposals | disposal_number (DSP-), asset (FK), disposal_method, workflow_plan_id |
| `PropertyLossReport` | property_loss_reports | report_number (PL-), asset (FK), reporting_department (FK), workflow_plan_id |
| `PropertyLossReportConfig` | property_loss_report_config | max_report_days, high_value_threshold |

---

## 6. Inter-Service Communication

### 6.1 Communication Methods

| Method | Services | Use Case |
|--------|----------|----------|
| **HTTP (direct)** | IAM, Work Orchestration | User management, workflow operations |
| **Kafka (async)** | IAM, Work Orchestration | Permissions, templates, workflow events |
| **API Gateway** | All services | Client requests, route proxying |

### 6.2 IAM Service Client

**Location**: `apps/infrastructure/external/iam_client.py`

```python
class IAMClient:
    """Client for IAM Service communication."""
    
    def __init__(self):
        self.base_url = settings.IAM_SERVICE_URL  # http://fims-iam-service:8000
        self.admin_token = settings.IAM_SERVICE_TOKEN
    
    def create_user(self, user_data: dict) -> Optional[dict]:
        """Create a new user in IAM Service."""
        response = requests.post(
            f"{self.base_url}/api/v1/iam/users/",
            json=user_data,
            headers=self._get_headers(),
        )
        return response.json()
    
    def assign_role(self, user_id: str, role_code: str) -> bool:
        """Assign a role to a user."""
        response = requests.post(
            f"{self.base_url}/api/v1/iam/rbac/assign/",
            json={'user_id': user_id, 'role_code': role_code},
            headers=self._get_headers(),
        )
        return response.status_code == 200
    
    def check_user_exists(self, email: str) -> bool:
        """Check if user exists by email."""
        response = requests.get(
            f"{self.base_url}/api/v1/iam/users/lookup/email/{email}/",
            headers=self._get_headers(),
        )
        return response.status_code == 200
```

**Used by**: `StaffOnboardingService` for creating IAM users when onboarding staff.

### 6.3 Work Orchestration Client

**Location**: `apps/infrastructure/external/orchestration_client.py`

```python
class OrchestrationClient:
    """Client for Work Orchestration Service."""
    
    def __init__(self):
        self.base_url = settings.WORK_ORCHESTRATION_SERVICE_URL
        self.service_token = settings.SERVICE_TO_SERVICE_TOKEN
    
    def start_workflow(
        self,
        template_code: str,
        context: dict,
        initiator_id: str,
    ) -> Optional[dict]:
        """Start a new workflow from a template."""
        response = requests.post(
            f"{self.base_url}/api/v1/workflow/plans/",
            json={
                'template_code': template_code,
                'context': context,
                'initiated_by': initiator_id,
            },
            headers=self._get_headers(),
        )
        return response.json()
    
    def advance_stage(
        self,
        plan_id: str,
        action_code: str,
        actor_id: str,
        comments: str = '',
    ) -> Optional[dict]:
        """Execute a workflow action (approve/reject/return)."""
        response = requests.post(
            f"{self.base_url}/api/v1/workflow/plans/{plan_id}/advance/",
            json={
                'action_code': action_code,
                'actor_id': actor_id,
                'comments': comments,
            },
            headers=self._get_headers(actor_id),
        )
        return response.json()
    
    def get_plan(self, plan_id: str) -> Optional[dict]:
        """Get workflow plan details."""
        response = requests.get(
            f"{self.base_url}/api/v1/workflow/plans/{plan_id}/",
            headers=self._get_headers(),
        )
        return response.json()
    
    def get_plan_activity(self, plan_id: str) -> List[dict]:
        """Get workflow activity history."""
        response = requests.get(
            f"{self.base_url}/api/v1/workflow/plans/{plan_id}/activity/",
            headers=self._get_headers(),
        )
        return response.json()
    
    def _get_headers(self, actor_id: str = None):
        headers = {
            'X-Service-Token': self.service_token,
            'Content-Type': 'application/json',
        }
        if actor_id:
            headers['X-Actor-ID'] = actor_id
        return headers
```

### 6.4 Kafka Integration

**Location**: `apps/infrastructure/messaging/kafka_producer.py`

**Topics:**

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `service.permission.registry` | Publish | Register permissions with IAM |
| `workflow-templates` | Publish | Register workflow templates |
| `notification-templates` | Publish | Register notification templates with Work Orchestration Service (notifications are a built-in function of orchestration) |
| `workflow-events` | Consume | Receive workflow stage/completion events |

**Workflow Event Consumer** (`apps/core/consumers/workflow_event_consumer.py`):

- Runs as separate container: `corporate-kafka-consumer`
- Command: `python manage.py consume_workflow_events`
- Consumer group: `corporate-service-workflow-consumer`
- Handles: `WorkflowStageUpdated`, `WorkflowCompleted` events

**Entity handlers in consumer:**

- Leave application, training request, extra duty claim, safari application
- Salary advance, fuel request, vehicle scheduling/maintenance
- Asset maintenance/disposal, property loss report
- Internal memo, imprest retirement, budget transfer, petty cash requisition
- Requisition, goods issue voucher, annual procurement plan, goods delivery, contract

---

## 7. Workflow Integration

### 7.1 Workflow Template Registration

**Template Definition** (`apps/core/workflows/workflows.yaml`):

```yaml
templates:
  - code: corporate.leave_application
    name: Leave Application Workflow
    description: Standard leave application approval workflow
    version: "1.0"
    module: hr
    entity_type: leave_application
    stages:
      - code: submission
        name: Submission
        order: 1
        actions:
          - code: submit
            name: Submit for Approval
            next_stage: hod_approval
            
      - code: hod_approval
        name: HOD Approval
        order: 2
        approver_type: supervisor
        actions:
          - code: approve
            name: Approve
            next_stage: hr_verification
          - code: reject
            name: Reject
            next_stage: rejected
          - code: return
            name: Return for Revision
            next_stage: submission
            
      - code: hr_verification
        name: HR Verification
        order: 3
        approver_role: hr_officer
        actions:
          - code: verify
            name: Verify
            next_stage: completed
          - code: reject
            name: Reject
            next_stage: rejected
            
      - code: completed
        name: Completed
        order: 4
        is_terminal: true
        
      - code: rejected
        name: Rejected
        order: 5
        is_terminal: true
```

**Template codes:**

| Module | Templates |
|--------|-----------|
| **HR** | `corporate.leave_application`, `corporate.training_request`, `corporate.safari_application`, `corporate.salary_advance_request`, `corporate.extra_duty_claim`, `corporate.leave_allowance_request` |
| **Fleet** | `corporate.fuel_request`, `corporate.vehicle_scheduling`, `corporate.vehicle_maintenance` |
| **Finance** | `corporate.internal_memo`, `corporate.imprest_retirement`, `corporate.budget_transfer`, `corporate.petty_cash_requisition` |
| **Procurement** | `corporate.requisition`, `corporate.goods_issue_voucher`, `corporate.annual_procurement_plan`, `corporate.goods_delivery`, `corporate.contract` |
| **Assets** | `corporate.asset_maintenance`, `corporate.asset_disposal`, `corporate.property_loss_report` |

### 7.2 WorkflowViewSetMixin

**Location**: `apps/api/mixins/workflow_viewset_mixin.py`

Provides REST actions for workflow-enabled ViewSets:

```python
class WorkflowViewSetMixin:
    """Mixin providing workflow actions for ViewSets."""
    
    workflow_template_code: str = None  # Override in subclass
    orchestration_client = OrchestrationClient()
    
    @action(detail=True, methods=['post'])
    def start_workflow(self, request, pk=None):
        """Start a workflow for this entity."""
        instance = self.get_object()
        context = self.get_workflow_context(instance)
        metadata = self.get_workflow_metadata(instance)
        
        result = self.orchestration_client.start_workflow(
            template_code=self.workflow_template_code,
            context={**context, 'metadata': metadata},
            initiator_id=str(request.user.id),
        )
        
        if result:
            instance.workflow_plan_id = result.get('id')
            instance.workflow_stage = result.get('current_stage', {}).get('code')
            instance.save()
            return Response({'workflow_plan_id': result.get('id')})
        return Response({'error': 'Failed to start workflow'}, status=400)
    
    @action(detail=True, methods=['post'])
    def workflow_action(self, request, pk=None):
        """Perform a workflow action."""
        instance = self.get_object()
        action_code = request.data.get('action')
        comments = request.data.get('comments', '')
        
        result = self.orchestration_client.advance_stage(
            plan_id=instance.workflow_plan_id,
            action_code=action_code,
            actor_id=str(request.user.id),
            comments=comments,
        )
        
        if result:
            instance.workflow_stage = result.get('current_stage', {}).get('code')
            instance.save()
            return Response(result)
        return Response({'error': 'Action failed'}, status=400)
    
    @action(detail=True, methods=['get'])
    def workflow_status(self, request, pk=None):
        """Get current workflow status."""
        instance = self.get_object()
        if not instance.workflow_plan_id:
            return Response({'error': 'No workflow'}, status=404)
        
        plan = self.orchestration_client.get_plan(instance.workflow_plan_id)
        return Response(plan)
    
    @action(detail=True, methods=['get'])
    def workflow_history(self, request, pk=None):
        """Get workflow activity history."""
        instance = self.get_object()
        if not instance.workflow_plan_id:
            return Response({'error': 'No workflow'}, status=404)
        
        activities = self.orchestration_client.get_plan_activity(
            instance.workflow_plan_id
        )
        return Response(activities)
```

### 7.3 WorkflowMixin for Models

**Location**: `apps/core/mixins/workflow_mixin.py`

Adds workflow fields and methods to models:

```python
class WorkflowMixin(models.Model):
    """Mixin for workflow-enabled models."""
    
    workflow_plan_id = models.UUIDField(null=True, blank=True, db_index=True)
    workflow_stage = models.CharField(max_length=50, blank=True, null=True)
    workflow_stage_id = models.UUIDField(null=True, blank=True)
    workflow_started_at = models.DateTimeField(null=True, blank=True)
    workflow_completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def start_workflow(self, plan_id: str, stage: str):
        self.workflow_plan_id = plan_id
        self.workflow_stage = stage
        self.workflow_started_at = timezone.now()
        self.save()
    
    def update_workflow_stage(self, stage: str, stage_id: str = None):
        self.workflow_stage = stage
        self.workflow_stage_id = stage_id
        self.save()
    
    def complete_workflow(self):
        self.workflow_completed_at = timezone.now()
        self.save()
```

### 7.4 Workflow Template Reference

This section provides a detailed reference for all workflow templates, including their input context, stages, actions, and final output status.

---

#### HR WORKFLOWS

##### 1. Leave Application (`corporate.leave_application`)

| Property | Value |
|----------|-------|
| **Description** | Complete leave application workflow from submission to payment processing |
| **SLA** | 4,320 minutes (3 days) |
| **Module** | HR / Leave |
| **Integrations** | IAM, MUSE |

**Input Context:**
- `entity_type`: "leave_application"
- `entity_id`: UUID of the leave application
- `line_manager_id`: Staff's direct supervisor
- `director_id`: Director for approval
- `is_paid_leave`: Boolean for conditional DG approval

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Head/Manager Approval | `{{line_manager_id}}` | approve → next, reject → rejected, return → pending | `hod_approved` |
| 2 | HR Verification | `role:hr_officer` | verify → next, reject → rejected | `hr_verified` |
| 3 | HRAM Review | `role:hr_admin_manager` | approve → next, reject → rejected | `hram_approved` |
| 4 | Director/DCS Approval | `{{director_id}}`, `role:director_corporate_services` | approve → next, reject → rejected | `director_approved` |
| 5 | DG Approval *(conditional)* | `role:director_general` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 2. Training Request (`corporate.training_request`)

| Property | Value |
|----------|-------|
| **Description** | Training request workflow with supervisor and HR approval |
| **SLA** | 7,200 minutes (5 days) |
| **Module** | HR / Training |

**Input Context:**
- `entity_type`: "training_request"
- `entity_id`: UUID of the training request
- `supervisor_id`: Staff's supervisor

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Supervisor Approval | `{{supervisor_id}}` | approve → next, reject → rejected | `supervisor_approved` |
| 2 | HR Verification | `role:hr_officer` | verify → next, reject → rejected | `hr_verified` |
| 3 | HRAM Confirmation | `role:hr_admin_manager` | confirm → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 3. Extra Duty Claim (`corporate.extra_duty_claim`)

| Property | Value |
|----------|-------|
| **Description** | Extra duty hours claim workflow |
| **SLA** | 4,320 minutes (3 days) |
| **Module** | HR / Claims |

**Input Context:**
- `entity_type`: "extra_duty_claim"
- `entity_id`: UUID of the claim
- `hod_id`: Head of Department

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | HOD Approval | `{{hod_id}}` | approve → next, reject → rejected | `hod_approved` |
| 2 | HR Verification | `role:hr_officer` | verify → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 4. Safari Application (`corporate.safari_application`)

| Property | Value |
|----------|-------|
| **Description** | Official safari/travel application with allowance calculation |
| **SLA** | 4,320 minutes (3 days) |
| **Module** | HR / Safari |
| **Integrations** | MUSE |

**Input Context:**
- `entity_type`: "safari_application"
- `entity_id`: UUID of the application
- `hod_id`: Head of Department

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | HOD Approval | `{{hod_id}}` | approve → next, reject → rejected, return → pending | `hod_approved` |
| 2 | HR Verification | `role:hr_officer` | verify → next, reject → rejected | `hr_verified` |
| 3 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 4 | Payment Processing | `role:finance_officer` | process → completed | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 5. Salary Advance Request (`corporate.salary_advance`)

| Property | Value |
|----------|-------|
| **Description** | Salary advance request with deduction scheduling |
| **SLA** | 2,880 minutes (2 days) |
| **Module** | HR / Advance |

**Input Context:**
- `entity_type`: "salary_advance_request"
- `entity_id`: UUID of the request
- `hod_id`: Head of Department

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | HOD Approval | `{{hod_id}}` | approve → next, reject → rejected | `hod_approved` |
| 2 | HR Verification | `role:hr_officer` | verify → next, reject → rejected | `hr_verified` |
| 3 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 4 | Disbursement | `role:finance_officer` | disburse → completed | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 6. Imprest Application (`corporate.imprest_application`)

| Property | Value |
|----------|-------|
| **Description** | Imprest application for travel and activity advances |
| **SLA** | 2,880 minutes (2 days) |
| **Module** | HR / Imprest |

**Input Context:**
- `entity_type`: "imprest_request"
- `entity_id`: UUID of the request
- `hod_id`: Head of Department

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | HOD Approval | `{{hod_id}}` | approve → next, reject → rejected | `hod_approved` |
| 2 | Finance Verification | `role:finance_officer` | verify → next, reject → rejected | `finance_verified` |
| 3 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 4 | Disbursement | `role:finance_officer` | disburse → completed | `approved` |

**Final Status:** `approved` (or `rejected`)

---

#### FINANCE WORKFLOWS

##### 7. Internal Payment Request (`corporate.internal_payment`)

| Property | Value |
|----------|-------|
| **Description** | Internal payment request with multi-level approval |
| **SLA** | 2,880 minutes (2 days) |
| **Module** | Finance / Payment |

**Input Context:**
- `entity_type`: "internal_payment"
- `entity_id`: UUID of the payment
- `first_approver_id`: HOD or Director

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | HOD/Director Approval | `{{first_approver_id}}` | approve → next, reject → rejected | `hod_approved` |
| 2 | Finance Verification | `role:finance_officer` | verify → next, reject → rejected | `finance_verified` |
| 3 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 4 | Disbursement | `role:finance_officer` | disburse → completed | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 8. Imprest Retirement (`corporate.imprest_retirement`)

| Property | Value |
|----------|-------|
| **Description** | Imprest/payment retirement workflow |
| **SLA** | 4,320 minutes (3 days) |
| **Module** | Finance / Retirement |

**Input Context:**
- `entity_type`: "imprest_retirement"
- `entity_id`: UUID of the retirement

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Finance Verification | `role:finance_officer` | verify → next, return → pending, reject → rejected | `finance_verified` |
| 2 | FAM Approval | `role:finance_accounts_manager` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 9. Budget Transfer Request (`corporate.budget_transfer`)

| Property | Value |
|----------|-------|
| **Description** | Budget transfer between allocations |
| **SLA** | 2,880 minutes (2 days) |
| **Module** | Finance / Budget |

**Input Context:**
- `entity_type`: "budget_transfer"
- `entity_id`: UUID of the transfer

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 2 | DCS Approval | `role:director_corporate_services` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 10. Petty Cash Requisition (`corporate.petty_cash_requisition`)

| Property | Value |
|----------|-------|
| **Description** | Petty cash request workflow |
| **SLA** | 480 minutes (8 hours) |
| **Module** | Finance / Petty Cash |

**Input Context:**
- `entity_type`: "petty_cash_requisition"
- `entity_id`: UUID of the requisition
- `custodian_id`: Petty cash custodian

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Custodian Approval | `{{custodian_id}}` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 11. External Payment (`corporate.external_payment`)

| Property | Value |
|----------|-------|
| **Description** | External payment workflow for vendor invoices |
| **SLA** | 5,760 minutes (4 days) |
| **Module** | Finance / External Payment |
| **Integrations** | MUSE |

**Input Context:**
- `entity_type`: "external_payment_request"
- `entity_id`: UUID of the request
- `assigned_officer_id`: Processing officer
- `hod_id`: Head of Department

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Reception & Assignment | `role:reception_officer` | assign → next, reject → rejected | `assigned` |
| 2 | Payment Request Creation | `{{assigned_officer_id}}` | submit → next, return → pending | `processing` |
| 3 | HOD Approval | `{{hod_id}}` | approve → next, reject → rejected | `hod_approved` |
| 4 | FAM Review | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 5 | DCS Approval | `role:director_corporate_services` | approve → next, reject → rejected | `dcs_approved` |
| 6 | Payment Disbursement | `role:finance_officer` | process → completed | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 12. Revenue Collection (`corporate.revenue_collection`)

| Property | Value |
|----------|-------|
| **Description** | Revenue collection workflow with GePG integration |
| **SLA** | 2,880 minutes (2 days) |
| **Module** | Finance / Revenue |
| **Integrations** | GePG |

**Input Context:**
- `entity_type`: "revenue_collection"
- `entity_id`: UUID of the collection

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Create Collection Request | `role:finance_officer` | submit → next | `pending_approval` |
| 2 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `awaiting_payment` |
| 3 | Payment Confirmation | `role:finance_officer` | confirm → completed | `approved` |

**Final Status:** `approved` (or `rejected`)

---

#### PROCUREMENT WORKFLOWS

##### 13. Requisition Approval (`corporate.requisition_approval`)

| Property | Value |
|----------|-------|
| **Description** | Purchase requisition approval workflow |
| **SLA** | 4,320 minutes (3 days) |
| **Module** | Procurement / Requisition |

**Input Context:**
- `entity_type`: "requisition"
- `entity_id`: UUID of the requisition
- `hod_id`: Head of Department

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | HOD Approval | `{{hod_id}}` | approve → next, reject → rejected | `hod_approved` |
| 2 | PMU Review | `role:procurement_officer` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 14. Goods Issue Voucher (`corporate.goods_issue`)

| Property | Value |
|----------|-------|
| **Description** | Goods issue from store workflow |
| **SLA** | 480 minutes (8 hours) |
| **Module** | Procurement / Stores |

**Input Context:**
- `entity_type`: "goods_issue_voucher"
- `entity_id`: UUID of the voucher

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Stores Approval | `role:stores_officer` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 15. Annual Procurement Plan (`corporate.annual_procurement_plan`)

| Property | Value |
|----------|-------|
| **Description** | Annual procurement plan approval workflow |
| **SLA** | 10,080 minutes (7 days) |
| **Module** | Procurement / Planning |

**Input Context:**
- `entity_type`: "annual_procurement_plan"
- `entity_id`: UUID of the plan

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | PMU Review | `role:procurement_officer` | recommend → next, return → pending | `pmu_recommended` |
| 2 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 3 | DCS Approval | `role:director_corporate_services` | approve → next, reject → rejected | `dcs_approved` |
| 4 | DG Approval | `role:director_general` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 16. Goods Delivery & Inspection (`corporate.goods_delivery`)

| Property | Value |
|----------|-------|
| **Description** | Goods delivery inspection and acceptance workflow |
| **SLA** | 2,880 minutes (2 days) |
| **Module** | Procurement / Delivery |

**Input Context:**
- `entity_type`: "goods_delivery"
- `entity_id`: UUID of the delivery

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Inspection Committee Review | `role:inspection_committee` | accept → next, partial_accept → next, reject → rejected | `inspected` |
| 2 | Stores Receipt | `role:stores_officer` | receive → completed | `received` |

**Final Status:** `received` (or `rejected`)

---

##### 17. Contract Approval (`corporate.contract_approval`)

| Property | Value |
|----------|-------|
| **Description** | Contract approval and management workflow |
| **SLA** | 7,200 minutes (5 days) |
| **Module** | Procurement / Contracts |

**Input Context:**
- `entity_type`: "contract"
- `entity_id`: UUID of the contract

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | PMU Review | `role:procurement_officer` | recommend → next, return → pending | `pmu_reviewed` |
| 2 | Legal Review | `role:legal_officer` | clear → next, return → pending | `legal_cleared` |
| 3 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 4 | Accounting Officer Approval | `role:director_general` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

#### ASSET WORKFLOWS

##### 18. Asset Disposal (`corporate.asset_disposal`)

| Property | Value |
|----------|-------|
| **Description** | Asset disposal workflow with multi-level approval |
| **SLA** | 10,080 minutes (7 days) |
| **Module** | Asset / Disposal |

**Input Context:**
- `entity_type`: "asset_disposal"
- `entity_id`: UUID of the disposal

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Asset Manager Review | `role:asset_manager` | recommend → next, reject → rejected | `asset_manager_approved` |
| 2 | FAM Approval | `role:finance_accounts_manager` | approve → next, reject → rejected | `fam_approved` |
| 3 | DCS Approval | `role:director_corporate_services` | approve → next, reject → rejected | `dcs_approved` |
| 4 | Disposal Execution | `role:asset_officer` | execute → completed | `completed` |

**Final Status:** `completed` (or `rejected`)

---

##### 19. Asset Maintenance Request (`corporate.asset_maintenance`)

| Property | Value |
|----------|-------|
| **Description** | Asset maintenance request workflow |
| **SLA** | 2,880 minutes (2 days) |
| **Module** | Asset / Maintenance |

**Input Context:**
- `entity_type`: "asset_maintenance"
- `entity_id`: UUID of the maintenance request

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Asset Manager Review | `role:asset_manager` | approve → next, reject → rejected | `approved` |
| 2 | Maintenance Execution | `role:asset_officer` | complete → completed | `completed` |

**Final Status:** `completed` (or `rejected`)

---

##### 20. Property Loss Report (`corporate.property_loss_report`)

| Property | Value |
|----------|-------|
| **Description** | Property loss/damage reporting and investigation workflow |
| **SLA** | 10,080 minutes (7 days) |
| **Module** | Asset / Loss |

**Input Context:**
- `entity_type`: "property_loss_report"
- `entity_id`: UUID of the report
- `hod_id`: Head of Department

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | HOD Acknowledgment | `{{hod_id}}` | acknowledge → next, return → pending | `hod_acknowledged` |
| 2 | Asset Manager Review | `role:asset_manager` | recommend_investigation → next, recommend_write_off → next | `asset_manager_reviewed` |
| 3 | DCS Decision | `role:director_corporate_services` | approve_investigation → next, approve_write_off → next, charge_responsible → next | `dcs_decided` |
| 4 | Resolution | `role:asset_officer` | close → completed | `resolved` |

**Final Status:** `resolved`

---

#### FLEET WORKFLOWS

##### 21. Fuel Request (`corporate.fuel_request`)

| Property | Value |
|----------|-------|
| **Description** | Vehicle fuel request workflow |
| **SLA** | 240 minutes (4 hours) |
| **Module** | Fleet / Fuel |

**Input Context:**
- `entity_type`: "fuel_request"
- `entity_id`: UUID of the request

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Fleet Manager Approval | `role:fleet_manager` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

##### 22. Vehicle Maintenance Request (`corporate.vehicle_maintenance`)

| Property | Value |
|----------|-------|
| **Description** | Vehicle maintenance request workflow |
| **SLA** | 4,320 minutes (3 days) |
| **Module** | Fleet / Maintenance |

**Input Context:**
- `entity_type`: "vehicle_maintenance_request"
- `entity_id`: UUID of the request

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Fleet Manager Review | `role:fleet_manager` | approve → next, reject → rejected | `fleet_approved` |
| 2 | Maintenance Execution | `role:fleet_officer` | complete → completed | `completed` |

**Final Status:** `completed` (or `rejected`)

---

##### 23. Vehicle Scheduling (`corporate.vehicle_scheduling`)

| Property | Value |
|----------|-------|
| **Description** | Vehicle booking and scheduling approval workflow |
| **SLA** | 240 minutes (4 hours) |
| **Module** | Fleet / Scheduling |

**Input Context:**
- `entity_type`: "vehicle_schedule"
- `entity_id`: UUID of the schedule

**Stages:**

| # | Stage | Assignees | Actions | Status on Complete |
|---|-------|-----------|---------|-------------------|
| 1 | Fleet Manager Approval | `role:fleet_manager` | approve → completed, reject → rejected | `approved` |

**Final Status:** `approved` (or `rejected`)

---

#### WORKFLOW SUMMARY TABLE

| # | Workflow | Stages | SLA | Final Status |
|---|----------|--------|-----|--------------|
| 1 | Leave Application | 5 | 3 days | approved |
| 2 | Training Request | 3 | 5 days | approved |
| 3 | Extra Duty Claim | 2 | 3 days | approved |
| 4 | Safari Application | 4 | 3 days | approved |
| 5 | Salary Advance | 4 | 2 days | approved |
| 6 | Imprest Application | 4 | 2 days | approved |
| 7 | Internal Payment | 4 | 2 days | approved |
| 8 | Imprest Retirement | 2 | 3 days | approved |
| 9 | Budget Transfer | 2 | 2 days | approved |
| 10 | Petty Cash | 1 | 8 hours | approved |
| 11 | External Payment | 6 | 4 days | approved |
| 12 | Revenue Collection | 3 | 2 days | approved |
| 13 | Requisition | 2 | 3 days | approved |
| 14 | Goods Issue | 1 | 8 hours | approved |
| 15 | Annual Procurement Plan | 4 | 7 days | approved |
| 16 | Goods Delivery | 2 | 2 days | received |
| 17 | Contract Approval | 4 | 5 days | approved |
| 18 | Asset Disposal | 4 | 7 days | completed |
| 19 | Asset Maintenance | 2 | 2 days | completed |
| 20 | Property Loss Report | 4 | 7 days | resolved |
| 21 | Fuel Request | 1 | 4 hours | approved |
| 22 | Vehicle Maintenance | 2 | 3 days | completed |
| 23 | Vehicle Scheduling | 1 | 4 hours | approved |

---

### 7.5 Workflow Event Processing

The Kafka consumer processes workflow events to update entity status:

```python
class WorkflowEventConsumer:
    ENTITY_HANDLERS = {
        'leave_application': LeaveApplicationHandler,
        'training_request': TrainingRequestHandler,
        'internal_memo': InternalMemoHandler,
        'asset_disposal': AssetDisposalHandler,
        # ... more handlers
    }
    
    def handle_stage_updated(self, event: dict):
        entity_type = event.get('entity_type')
        entity_id = event.get('entity_id')
        new_stage = event.get('stage_code')
        
        handler = self.ENTITY_HANDLERS.get(entity_type)
        if handler:
            handler.on_stage_updated(entity_id, new_stage, event)
    
    def handle_workflow_completed(self, event: dict):
        entity_type = event.get('entity_type')
        entity_id = event.get('entity_id')
        final_stage = event.get('final_stage')
        
        handler = self.ENTITY_HANDLERS.get(entity_type)
        if handler:
            handler.on_completed(entity_id, final_stage, event)
```

---

### 7.6 Workflow Return and Resubmission (March 2026)

The Corporate Service implements a comprehensive return and resubmission workflow that allows documents to be sent back for amendment while preserving the complete workflow history.

#### 7.6.1 Return Action Handling

When an approver returns a document for clarification/amendment:

1. **Stage status** is set to `'returned'` (not completed)
2. **Entity status** is set to `'returned'`
3. **Document becomes editable** by the applicant
4. **All comments and activities** are preserved

**Workflow YAML Configuration:**

```yaml
stages:
  - key: hr_verification
    name: "HR Verification"
    actions:
      - name: "approve"
        nextState: "completed"
      - name: "return"
        label: "Return for Amendment"
        nextState: "returned"  # Stage status set to 'returned'
```

#### 7.6.2 Resubmission Logic

When a user resubmits a returned document, the system finds and re-activates the **same stage** that returned it:

**Location**: All workflow service files (e.g., `leave_application_service.py`)

```python
def _resubmit_application(self, application, submitter_id=None):
    """Resubmit a returned application by re-activating the returning stage."""
    
    if application.workflow_plan_id:
        plan = self.workflow_client.get_plan(str(application.workflow_plan_id))
        if plan and plan.stages:
            # Find the stage that returned the document (status = 'returned')
            returning_stage = None
            for stage in plan.stages:
                if stage.get('status') == 'returned':
                    returning_stage = stage
                    break
            
            if returning_stage:
                # Re-activate the returning stage with revision increment
                self.workflow_client.activate_stage(
                    str(application.workflow_plan_id),
                    returning_stage.get('id'),
                    increment_revision=True
                )
                application.status = 'resubmitted'
                application.save()
                return application
            else:
                # Fallback: activate first pending stage
                for stage in plan.stages:
                    if stage.get('status') == 'pending':
                        self.workflow_client.activate_stage(
                            str(application.workflow_plan_id),
                            stage.get('id'),
                            increment_revision=True
                        )
                        break
    
    application.status = 'pending'
    application.save()
    return application
```

**Key Behavior:**
- Resubmission returns to the **same stage** that returned it (not the next stage)
- If HR Verification returns a document, resubmission goes back to HR Verification
- The workflow continues from the returning stage, not from the beginning

#### 7.6.3 Revision Tracking

To support the "already acted" check after resubmission, the Work Orchestration Service implements revision tracking:

**Database Schema:**

```python
# WorkflowStageModel
class WorkflowStageModel(models.Model):
    revision = models.IntegerField(default=1)  # Incremented on resubmission
    # ... other fields

# WorkflowActivityModel  
class WorkflowActivityModel(models.Model):
    stage_revision = models.IntegerField(default=1)  # Links activity to stage revision
    # ... other fields
```

**"Already Acted" Check:**

The permission check now filters by the current stage revision:

```python
def _enrich_plan_with_permissions(plan, user_id, ...):
    current_stage = plan.current_stage
    current_revision = getattr(current_stage, 'revision', 1) or 1
    
    # Only check activities from the CURRENT revision
    stage_activities = repo.list_activity(
        plan_id=plan.plan_id,
        stage_id=current_stage.external_id,
        stage_revision=current_revision  # Filter by revision
    )
    
    user_already_acted = any(
        activity.get('actor_id') == user_id and 
        activity.get('event_type') in ['approve', 'reject', 'return']
        for activity in stage_activities
    )
```

**Benefits:**
- Users can re-approve/reject after a document is resubmitted
- Previous revision activities are preserved for audit trail
- No "You have already acted on this stage" errors after resubmission

#### 7.6.4 Activate Stage API

**Endpoint**: `POST /api/v1/workflow/plans/{plan_id}/stages/{stage_id}/activate/`

**Request Body:**
```json
{
  "increment_revision": true
}
```

**Response:**
```json
{
  "status": "success",
  "stage_id": "uuid",
  "stage_name": "HR Verification",
  "new_status": "in_progress",
  "revision": 2
}
```

**OrchestrationClient Method:**

```python
def activate_stage(self, plan_id: str, stage_id: str, increment_revision: bool = False):
    """
    Activate a specific stage in a workflow plan.
    
    Args:
        plan_id: The workflow plan ID
        stage_id: The stage ID to activate
        increment_revision: If True, increments the stage revision counter
    """
    response = self._make_request(
        'POST',
        f'/plans/{plan_id}/stages/{stage_id}/activate/',
        data={'increment_revision': increment_revision}
    )
    return response
```

#### 7.6.5 Services with Resubmission Support

All workflow-enabled services now support return and resubmission:

| Module | Services |
|--------|----------|
| **HR** | `leave_application_service.py`, `safari_application_workflow_service.py`, `training_request_service.py`, `salary_advance_workflow_service.py`, `extra_duty_claim_service.py`, `property_loss_report_service.py`, `fuel_request_service.py`, `asset_disposal_service.py`, `asset_maintenance_service.py`, `vehicle_maintenance_service.py` |
| **Finance** | `internal_memo_service.py`, `imprest_retirement_service.py`, `petty_cash_workflow_service.py`, `petty_cash_service.py`, `budget_transfer_service.py` |
| **Procurement** | `requisition_service.py`, `annual_procurement_plan_workflow_service.py`, `contract_workflow_service.py`, `giv_workflow_service.py`, `goods_delivery_workflow_service.py` |
| **Fleet** | `fuel_request_workflow_service.py`, `vehicle_scheduling_workflow_service.py` |

#### 7.6.6 Workflow State Transitions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Return and Resubmission Flow                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. Initial Submit:
   ┌──────────┐    submit    ┌───────────────┐   approve   ┌─────────────────┐
   │  Draft   │ ──────────► │ HOD Approval  │ ─────────► │ HR Verification │
   └──────────┘              │ (in_progress) │             │  (in_progress)  │
                             └───────────────┘             └─────────────────┘
                                                                    │
                                                              return │
                                                                    ▼
2. Return:                                                  ┌─────────────────┐
                                                            │ HR Verification │
   Entity Status: 'returned'                                │   (returned)    │
   Document: Editable                                       └─────────────────┘
                                                                    │
                                                           resubmit │
                                                                    ▼
3. Resubmit:                                               ┌─────────────────┐
                                                           │ HR Verification │
   Same stage re-activated with revision++                 │  (in_progress)  │
   Entity Status: 'resubmitted'                            │   revision=2    │
   Approver can act again                                  └─────────────────┘
```

---

## 8. Background Tasks & Scheduling

### 8.1 Celery Configuration

**Location**: `config/celery.py`

```python
app = Celery('corporate')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat schedule
app.conf.beat_schedule = {
    'auto-create-leave-roster': {
        'task': 'apps.hr.tasks.leave_tasks.auto_create_annual_leave_roster',
        'schedule': crontab(month_of_year=1, day_of_month=1, hour=0, minute=5),
    },
    'auto-close-leave-roster': {
        'task': 'apps.hr.tasks.leave_tasks.auto_close_leave_roster_year_end',
        'schedule': crontab(month_of_year=12, day_of_month=31, hour=23, minute=55),
    },
    'process-leave-carry-forward': {
        'task': 'apps.hr.tasks.leave_tasks.process_leave_carry_forward',
        'schedule': crontab(month_of_year=1, day_of_month=2, hour=1, minute=0),
    },
    'run-monthly-depreciation': {
        'task': 'apps.assets.tasks.depreciation_tasks.run_monthly_depreciation',
        'schedule': crontab(day_of_month='last', hour=23, minute=0),
    },
}
```

### 8.2 Leave Tasks

**Location**: `apps/hr/tasks/leave_tasks.py`

| Task | Schedule | Purpose |
|------|----------|---------|
| `auto_create_annual_leave_roster` | Jan 1, 00:05 | Create new year roster, initialize balances with carry-forward |
| `auto_close_leave_roster_year_end` | Dec 31, 23:55 | Close roster, recalculate closing balances |
| `process_leave_carry_forward` | Jan 2, 01:00 | Backup carry-forward processing |

### 8.3 Depreciation Tasks

**Location**: `apps/assets/tasks/depreciation_tasks.py`

| Task | Schedule | Purpose |
|------|----------|---------|
| `run_monthly_depreciation` | Last day of month, 23:00 | Run monthly depreciation for all active assets |
| `catch_up_depreciation` | Manual (via API) | Backfill missed depreciation periods |

---

## 9. API Reference

### 9.1 Base URL

```
Production: https://api.example.com/api/v1/corporate/
Development: http://localhost:8080/api/v1/corporate/
```

### 9.2 Authentication

All endpoints require JWT authentication:

```http
Authorization: Bearer <jwt_token>
```

### 9.3 Endpoint Categories

| Category | Base Path | Description |
|----------|-----------|-------------|
| **Config** | `/config/` | Lookup categories, values, salary grades, etc. |
| **HR** | `/hr/` | Organization, staff, leave, training, fleet, allowances |
| **Finance** | `/finance/` | Budget, payments, imprest, petty cash, fees, revenue |
| **Procurement** | `/procurement/` | Plans, requisitions, vendors, orders, contracts, store |
| **Assets** | `/assets/` | Register, categories, maintenance, depreciation, disposal |

### 9.4 Common Endpoint Patterns

For each resource (e.g., `leave-applications`):

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/{resource}/` | List all (paginated) |
| `POST` | `/{resource}/` | Create new |
| `GET` | `/{resource}/{id}/` | Get single |
| `PATCH` | `/{resource}/{id}/` | Partial update |
| `DELETE` | `/{resource}/{id}/` | Delete |
| `POST` | `/{resource}/{id}/start-workflow/` | Start workflow |
| `POST` | `/{resource}/{id}/workflow-action/` | Perform workflow action |
| `GET` | `/{resource}/{id}/workflow-status/` | Get workflow status |
| `GET` | `/{resource}/{id}/workflow-history/` | Get workflow history |

### 9.5 Pagination

```json
{
  "count": 150,
  "next": "http://api.example.com/api/v1/corporate/hr/leave/applications/?page=2",
  "previous": null,
  "results": [...]
}
```

Query parameters:
- `limit`: Items per page (default: 20)
- `offset`: Number of items to skip
- Or: `page`: Page number (when using PageNumberPagination)

### 9.6 Filtering

Most list endpoints support filtering:

```http
GET /api/v1/corporate/hr/leave/applications/?status=pending&applicant={uuid}&leave_type={uuid}
GET /api/v1/corporate/assets/register/?category={uuid}&department={uuid}&status={uuid}
```

---

## 10. Development Patterns

### 10.1 Adding a New Entity

1. **Define Django Model** (`apps/infrastructure/persistence/models.py`):

```python
class NewEntity(BaseModel, WorkflowMixin):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='draft')
    
    class Meta:
        db_table = 'new_entities'
```

2. **Create Serializer** (`apps/api/serializers/`):

```python
class NewEntitySerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()
    
    class Meta:
        model = NewEntity
        fields = '__all__'
    
    def get_department_name(self, obj):
        return obj.department.name if obj.department else None
```

3. **Create ViewSet** (`apps/api/views/`):

```python
class NewEntityViewSet(WorkflowViewSetMixin, ModelViewSet):
    queryset = NewEntity.objects.all()
    serializer_class = NewEntitySerializer
    workflow_template_code = 'corporate.new_entity'
    filterset_fields = ['department', 'status']
    
    def get_workflow_context(self, instance):
        return {
            'entity_type': 'new_entity',
            'entity_id': str(instance.id),
            'code': instance.code,
        }
```

4. **Register URL** (`apps/api/urls/api_urls.py`):

```python
router.register(r'module/new-entities', NewEntityViewSet)
```

5. **Add Workflow Template** (`apps/core/workflows/workflows.yaml`):

```yaml
- code: corporate.new_entity
  name: New Entity Workflow
  entity_type: new_entity
  stages:
    # Define stages...
```

### 10.2 Frontend Pattern for New Entity

1. **Add API Functions** (`services/corporateService.ts`):

```typescript
export interface NewEntityItem {
  id: string;
  code: string;
  name: string;
  department: string;
  department_name?: string;
  status: string;
}

export function listNewEntities(params?: ListParams) {
  return corporateList<NewEntityItem>(PATHS.newEntities, params);
}

export function createNewEntity(data: Partial<NewEntityItem>) {
  return corporateCreate<NewEntityItem>(PATHS.newEntities, data);
}

export function submitNewEntityWorkflow(id: string) {
  return corporateClient.post(`/${PATHS.newEntities}/${id}/start-workflow/`);
}
```

2. **Create Page Component**:

```typescript
function NewEntityPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  
  const { data, isLoading } = useQuery({
    queryKey: ["corporate", "new-entities"],
    queryFn: () => listNewEntities(),
  });
  
  const createMutation = useMutation({
    mutationFn: createNewEntity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["corporate", "new-entities"] });
      toast.success("Created successfully");
      setDialogOpen(false);
    },
  });
  
  return (
    <>
      <GenericListPage
        title="New Entities"
        items={data?.results?.map(mapToListItem) ?? []}
        columns={columns}
        onCreateNew={() => setDialogOpen(true)}
      />
      <CreateNewEntityDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={(data) => createMutation.mutate(data)}
      />
    </>
  );
}
```

3. **Add Route** (`App.tsx`):

```typescript
<Route path="new-entities" element={<NewEntityPage />} />
```

---

## 11. Hybrid Permission System

The Corporate Service implements a comprehensive ownership-based access control system that ensures users only see records they are authorized to access. This hybrid approach combines backend queryset filtering with frontend route guards.

### 11.1 Access Scopes

The system defines four levels of data access:

| Scope | Description | Use Case |
|-------|-------------|----------|
| **OWN** | User sees only their own records | Default for all regular users |
| **SUBORDINATES** | User sees their own records plus direct/recursive reports | Supervisors and line managers |
| **DEPARTMENT** | User sees all records within their department | Department-level roles |
| **ALL** | User sees all records across the organization | Superusers, admins, and users with `view_all` permission |

### 11.2 Backend Implementation

**Location**: `apps/core/ownership.py`

#### AccessScope Enum

```python
from enum import Enum

class AccessScope(Enum):
    OWN = "own"
    SUBORDINATES = "subordinates"
    DEPARTMENT = "department"
    ALL = "all"
```

#### Subordinate Resolution

The `get_subordinate_staff_ids()` function recursively traverses the `line_manager_id` relationship to build a complete list of a supervisor's direct and indirect reports:

```python
def get_subordinate_staff_ids(staff_id, recursive=True):
    """
    Get staff IDs of subordinates via line_manager relationship.
    Returns list of StaffProfile.id values (not user_ids).
    """
    direct_ids = list(
        StaffProfile.objects.filter(
            line_manager_id=staff_id, is_active=True
        ).values_list('id', flat=True)
    )

    if not recursive or not direct_ids:
        return direct_ids

    all_ids = list(direct_ids)
    for sub_id in direct_ids:
        all_ids.extend(get_subordinate_staff_ids(sub_id, recursive=True))
    return all_ids
```

#### Access Scope Resolution

The `resolve_access_scope()` function determines a user's access level based on their permissions:

```python
def resolve_access_scope(request, permission_resource=None):
    """
    Determine what access scope the current user has.

    Checks in order:
    1. Superuser / wildcard → ALL
    2. Has view_all or manage permission for resource → ALL
    3. Has view_subordinates permission + ?scope=subordinates → SUBORDINATES
    4. Default → OWN
    """
    if getattr(request, 'is_superuser', False):
        return AccessScope.ALL

    perms = getattr(request, 'user_permissions_flat', [])
    if '*' in perms:
        return AccessScope.ALL

    if permission_resource:
        view_all_codes = {
            f'{permission_resource}.view_all',
            f'{permission_resource}.manage',
        }
        if view_all_codes & set(perms):
            return AccessScope.ALL

        scope_param = request.GET.get('scope', '')
        if scope_param == 'subordinates':
            view_sub_code = f'{permission_resource}.view_subordinates'
            if view_sub_code in perms:
                return AccessScope.SUBORDINATES

    return AccessScope.OWN
```

#### OwnershipFilterMixin

A reusable DRF ViewSet mixin that automatically filters querysets based on ownership:

```python
class OwnershipFilterMixin:
    """
    DRF ModelViewSet mixin that auto-filters querysets by ownership.

    Usage:
        class MyViewSet(OwnershipFilterMixin, viewsets.ModelViewSet):
            owner_field = 'requester_id'      # FK field on the model
            permission_resource = 'finance.internal_payment'
    """
    owner_field = None
    permission_resource = None

    def get_queryset(self):
        qs = super().get_queryset()

        if self.owner_field is None:
            return qs

        allowed_ids = get_allowed_owner_ids(self.request, self.permission_resource)

        if allowed_ids is None:
            return qs  # User can see all
        if not allowed_ids:
            return qs.none()  # No staff profile found

        return qs.filter(**{f'{self.owner_field}__in': allowed_ids})
```

### 11.3 Owner Field Mapping

Each entity has a designated owner field that determines record ownership:

| Entity | Owner Field | Description |
|--------|-------------|-------------|
| `LeaveApplication` | `applicant_id` | The staff member applying for leave |
| `SafariApplication` | `applicant_id` | The staff member traveling |
| `ExtraDutyClaim` | `claimant_id` | The staff member claiming extra duty |
| `SalaryAdvanceRequest` | `staff_id` | The staff member requesting advance |
| `InternalMemo` | `officer_id` | The officer initiating the memo |
| `InternalPayment` | `requester_id` | The staff requesting payment |
| `ImprestRequest` | `holder_id` | The imprest holder |
| `FuelRequest` | `driver_id` | The requesting driver |
| `TrainingRequest` | `staff_id` | The staff requesting training |
| `LeaveAllowanceRequest` | `staff_id` | The staff requesting allowance |

### 11.4 Frontend Implementation

#### useResourcePermission Hook

**Location**: `frontend/packages/shared/src/hooks/useResourcePermission.ts`

A React hook that checks the current user's permission scope for a given resource:

```typescript
export interface ResourcePermission {
  canViewAll: boolean;
  canViewSubordinates: boolean;
  canViewOwn: boolean;
}

export const useResourcePermission = (
  permissionResource: string
): ResourcePermission => {
  const { user } = useAuth();
  const permissions = getPermissionsFromToken();

  return useMemo(() => {
    if (!user) {
      return { canViewAll: false, canViewSubordinates: false, canViewOwn: false };
    }

    if (user.is_superuser || permissions.includes("*")) {
      return { canViewAll: true, canViewSubordinates: true, canViewOwn: true };
    }

    const canViewAll =
      permissions.includes(`${permissionResource}.view_all`) ||
      permissions.includes(`${permissionResource}.manage`);

    const canViewSubordinates = permissions.includes(
      `${permissionResource}.view_subordinates`
    );

    return {
      canViewAll,
      canViewSubordinates,
      canViewOwn: true,
    };
  }, [user, permissions, permissionResource]);
};
```

#### PermissionLink Component

**Location**: `frontend/packages/shared/src/components/PermissionLink.tsx`

A smart navigation component that automatically routes users to the appropriate page based on their permissions:

```typescript
interface PermissionLinkProps extends Omit<LinkProps, "to"> {
  permissionResource: string;  // e.g., "finance.internal_payment"
  allPath: string;             // Path for users with view_all permission
  myPath: string;              // Path for regular users (own records)
  children: React.ReactNode;
}

export const PermissionLink: React.FC<PermissionLinkProps> = ({
  permissionResource,
  allPath,
  myPath,
  children,
  ...rest
}) => {
  const { canViewAll } = useResourcePermission(permissionResource);

  return (
    <Link to={canViewAll ? allPath : myPath} {...rest}>
      {children}
    </Link>
  );
};
```

**Usage Example:**

```tsx
<PermissionLink
  permissionResource="finance.internal_payment"
  allPath="/service/corporate/internal-payments"
  myPath="/service/corporate/my-payments"
>
  View Payments
</PermissionLink>
```

### 11.5 Security Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Permission Check Flow                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────────┐
                        │    User Makes API Request    │
                        └─────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  JWT Middleware Extracts User Info  │
                    │  - staff_id, is_superuser           │
                    │  - user_permissions_flat            │
                    └─────────────────────────────────────┘
                                      │
                                      ▼
                  ┌─────────────────────────────────────────┐
                  │     OwnershipFilterMixin.get_queryset   │
                  └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌───────────┐     ┌───────────────┐    ┌───────────┐
            │ Superuser │     │ view_all perm │    │  Default  │
            │  or '*'   │     │   or manage   │    │  (OWN)    │
            └───────────┘     └───────────────┘    └───────────┘
                    │                 │                 │
                    ▼                 ▼                 ▼
              ┌───────────┐     ┌───────────┐    ┌───────────────┐
              │ Return    │     │ Return    │    │ Filter by     │
              │ ALL       │     │ ALL       │    │ owner_field   │
              │ records   │     │ records   │    │ = staff_id    │
              └───────────┘     └───────────┘    └───────────────┘
```

### 11.6 Implementation Checklist for New Entities

When adding a new entity that requires ownership-based access:

1. **Backend:**
   - Identify the owner field (e.g., `applicant_id`, `requester_id`)
   - Add `OwnershipFilterMixin` to the ViewSet
   - Set `owner_field` and `permission_resource` attributes
   - For `PartialUpdateViewSet` (non-ModelViewSet), manually apply filter in `list()` method

2. **Frontend:**
   - Create both "all" and "my" routes (e.g., `/leave-applications` and `/my-leave-applications`)
   - Use `useResourcePermission` hook to conditionally show UI elements
   - Use `PermissionLink` for navigation links that should respect permissions
   - Set `myOnly` prop on list pages to filter to current user's records

3. **Permissions:**
   - Add `{resource}.view_all` permission for full access
   - Add `{resource}.view_subordinates` permission for supervisor access
   - Update `config/permissions/corporate-service.json`

### 11.7 Permission-Based Menu Visibility (March 2026)

The frontend navigation system dynamically shows/hides menu items based on user permissions, ensuring users only see menus for features they can access.

#### Menu Configuration with Permissions

**Location**: `frontend/apps/fims/src/config/servicesConfig.ts`

Each menu item can specify required permissions:

```typescript
interface MenuItem {
  label: string;
  path: string;
  icon?: IconType;
  permissions?: string[];      // Required permissions (ANY match grants access)
  requireAll?: boolean;        // If true, ALL permissions required
  hideForRoles?: string[];     // Hide for specific roles
  showForRoles?: string[];     // Only show for specific roles
}

// Example configuration
const hrMenuItems: MenuItem[] = [
  {
    label: "Leave Applications",
    path: "/service/corporate/leave-applications",
    permissions: ["hr.leave_application.view_all", "hr.leave_application.manage"],
  },
  {
    label: "My Leave",
    path: "/service/corporate/my-leave-applications",
    // No permissions = visible to all authenticated users
  },
  {
    label: "Staff Management",
    path: "/service/corporate/staff",
    permissions: ["hr.staff.view_all", "hr.staff.manage"],
  },
];
```

#### useMenuVisibility Hook

**Location**: `frontend/packages/shared/src/hooks/useMenuVisibility.ts`

```typescript
export const useMenuVisibility = (menuItems: MenuItem[]) => {
  const { user, permissions } = useAuth();
  
  return useMemo(() => {
    return menuItems.filter(item => {
      // No permission requirement = always visible
      if (!item.permissions || item.permissions.length === 0) {
        return true;
      }
      
      // Superusers see everything
      if (user?.is_superuser) {
        return true;
      }
      
      // Check if user has wildcard permission
      if (permissions.includes('*')) {
        return true;
      }
      
      // Check required permissions
      if (item.requireAll) {
        return item.permissions.every(p => permissions.includes(p));
      } else {
        return item.permissions.some(p => permissions.includes(p));
      }
    });
  }, [menuItems, user, permissions]);
};
```

#### Dynamic Sidebar Rendering

```tsx
const CorporateSidebar: React.FC = () => {
  const visibleHRItems = useMenuVisibility(hrMenuItems);
  const visibleFinanceItems = useMenuVisibility(financeMenuItems);
  const visibleProcurementItems = useMenuVisibility(procurementMenuItems);
  
  return (
    <Sidebar>
      {visibleHRItems.length > 0 && (
        <MenuSection title="Human Resources">
          {visibleHRItems.map(item => (
            <MenuItem key={item.path} {...item} />
          ))}
        </MenuSection>
      )}
      {visibleFinanceItems.length > 0 && (
        <MenuSection title="Finance">
          {visibleFinanceItems.map(item => (
            <MenuItem key={item.path} {...item} />
          ))}
        </MenuSection>
      )}
      {/* ... more sections */}
    </Sidebar>
  );
};
```

#### Menu Visibility Rules

| User Type | Visible Menus |
|-----------|--------------|
| **Superuser** | All menus |
| **Admin with `*`** | All menus |
| **HR Manager** | HR menus (based on `hr.*` permissions) + personal menus |
| **Finance Officer** | Finance menus (based on `finance.*` permissions) + personal menus |
| **Regular Staff** | Only "My" personal menus (My Leave, My Safari, etc.) |

#### "My" vs "All" Menu Pattern

For each entity, two menu items are typically provided:

| Menu Item | Path | Permissions | Audience |
|-----------|------|-------------|----------|
| Leave Applications | `/leave-applications` | `hr.leave_application.view_all` | HR staff, managers |
| My Leave | `/my-leave-applications` | *(none)* | All staff |
| Internal Payments | `/internal-payments` | `finance.internal_payment.view_all` | Finance staff |
| My Payments | `/my-payments` | *(none)* | All staff |

This ensures:
- All users can access their own records
- Only authorized users see the "all records" view
- Menu clutter is reduced for regular users

---

## 12. UI/UX Enhancements

### 12.1 Status Display Utilities

To provide consistent, human-readable status labels across the application, we implemented automatic status formatting utilities.

#### format_status_label Function

**Location**: `apps/core/utils.py`

Converts snake_case status codes to properly formatted display labels, handling common acronyms:

```python
def format_status_label(status: str) -> str:
    """
    Convert status code to human-readable label.
    
    Examples:
        finance_verified → Finance Verified
        hod_approved → HOD Approved
        under_review → Under Review
        fam_approved → FAM Approved
        hr_verified → HR Verified
        dcs_approval → DCS Approval
    """
    if not status:
        return ''
    
    ACRONYMS = {
        'hod', 'fam', 'hr', 'dcs', 'hram', 'pmu', 'tb', 'ao', 
        'giv', 'lpo', 'grn', 'rfq', 'po', 'pr', 'it', 'ict',
        'ceo', 'cfo', 'coo', 'md', 'gm', 'agm', 'sm', 'am',
    }
    
    words = status.replace('_', ' ').split()
    result = []
    
    for word in words:
        if word.lower() in ACRONYMS:
            result.append(word.upper())
        else:
            result.append(word.capitalize())
    
    return ' '.join(result)
```

#### StatusDisplayMixin

**Location**: `apps/api/serializers/base.py`

A serializer mixin that automatically adds a `status_display` field to API responses:

```python
class StatusDisplayMixin:
    """
    Mixin that adds a `status_display` field to serializers.
    
    Usage:
        class MySerializer(StatusDisplayMixin, serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = ['id', 'status', ...]  # No need to add 'status_display'
    """
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        status = getattr(instance, 'status', None)
        if status:
            rep['status_display'] = format_status_label(status)
        else:
            rep['status_display'] = ''
        return rep
```

### 12.2 My Workspace Pages Pattern

"My" pages provide a filtered view showing only the current user's records. Several enhancements were made to improve the user experience:

#### Auto-Selection of Current Staff

For pages like "My Leave Applications", "My Safari", "My Extra Duty", and "My Salary Advance", the applicant/staff field is:
- Automatically pre-filled with the current user's staff profile
- Disabled to prevent changes (since it's their own request)

**Implementation Pattern:**

```typescript
// In the create/edit dialog component
interface CreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: FormData) => void;
  currentStaff?: StaffProfile | null;  // New prop
}

// In the dialog, conditionally render the field:
{currentStaff ? (
  <Input
    disabled
    value={`${currentStaff.first_name} ${currentStaff.last_name}`}
  />
) : (
  <Select {...register("applicant_id")}>
    {staffList.map((staff) => (
      <SelectItem key={staff.id} value={staff.id}>
        {staff.first_name} {staff.last_name}
      </SelectItem>
    ))}
  </Select>
)}

// In the list page, pass currentStaff when myOnly is true:
<CreateDialog
  currentStaff={myOnly ? currentStaffProfile : null}
  onSubmit={handleCreate}
/>
```

#### Page/Route Pattern

| Admin Page | My Page | URL Pattern |
|------------|---------|-------------|
| Leave Applications | My Leave Applications | `/my-leave-applications` |
| Leave Roster | My Leave Roster | `/my-leave-roster` |
| Leave Allowance | My Leave Allowance | `/my-leave-allowance-requests` |
| Safari Applications | My Safari | `/my-safari` |
| Extra Duty Claims | My Extra Duty | `/my-extra-duty` |
| Salary Advances | My Salary Advance | `/my-salary-advance` |
| Internal Payments | My Payments | `/my-payments` |

### 12.3 My Leave Roster Enhancement

The "My Leave Roster" menu was enhanced to replace a simple popup dialog with a full dedicated page featuring:

- **Calendar View**: Visual display of leave entries on a calendar grid
- **Table View**: Sortable list of all leave entries
- **Summary Cards**: Quick stats showing days allocated, used, and remaining
- **Add Entry Dialog**: Simplified entry creation for the current user only

**Files Created/Modified:**
- `MyLeaveRosterDetailPage.tsx` - New full page component with calendar/table views
- `MyLeaveRosterPage.tsx` - Updated to navigate to detail page instead of showing popup
- `App.tsx` - Added route `/my-leave-roster/:id` for the detail page

### 12.4 Leave Allowance Request Improvements

Several enhancements were made to the leave allowance request workflow:

#### Fiscal Year Dropdown

The fiscal year field now uses a dropdown populated from existing leave rosters instead of a free-text input:

```typescript
// Fetch rosters and extract unique fiscal years
const { data: rostersData } = useQuery({
  queryKey: ["corporate", "leave-rosters"],
  queryFn: () => listLeaveRosters(),
  enabled: open,
});

const fiscalYears = useMemo(() => {
  const years = new Set(rostersData?.results?.map(r => r.fiscal_year) ?? []);
  return Array.from(years).sort().reverse();
}, [rostersData]);
```

#### View and Delete Actions

The leave allowance request list page now supports:
- **View**: Opens a detailed dialog showing calculation breakdown (eligible days, used days, allowance amount)
- **Delete**: Available only for requests in "draft" status

Backend support was added via a `destroy` method in `LeaveAllowanceRequestViewSet`:

```python
def destroy(self, request, pk=None):
    instance = self.get_object()
    if instance.status != 'draft':
        return Response(
            {'error': 'Only draft requests can be deleted'},
            status=status.HTTP_400_BAD_REQUEST
        )
    instance.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
```

#### Backend Bug Fixes

1. **Field Name Correction**: Changed `staff_id` to `applicant_id` in leave application queries (LeaveApplication uses `applicant_id`)
2. **Import Scope Fix**: Moved `from django.db import models` to method scope for `models.Q` usage
3. **Fiscal Year Parsing**: Fixed logic to correctly handle both formats:
   - `YYYY/YYYY+1` (e.g., "2025/2026") → July 1 to June 30
   - `YYYY` (e.g., "2026") → January 1 to December 31

### 12.5 Extra Duty Claim Improvements

Enhanced the Extra Duty detail page with conditional UI based on claim status:

| Feature | Draft Status | Submitted/Other Status |
|---------|--------------|------------------------|
| Submit button | Visible (if work entries exist) | Hidden |
| Add Work Entry button | Visible | Hidden |
| Edit/Delete buttons on entries | Visible | Hidden |
| Actions column in table | Visible | Hidden |

**Implementation:**

```typescript
// Conditional Submit based on work entries
<EmbeddedWorkflowConsole
  onSubmit={items.length > 0 ? handleSubmit : undefined}
/>

// Conditional Add button
{claim.status === "draft" && (
  <Button onClick={() => setIsAddOpen(true)}>
    Add Work Entry
  </Button>
)}

// Conditional table actions column
{claim.status === "draft" && (
  <TableHead className="text-right">Actions</TableHead>
)}
```

### 12.6 Safari Application Enhancement

Added `applicant_name` field to the Safari Application serializer for display purposes:

```python
class SafariApplicationSerializer(StatusDisplayMixin, serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField(read_only=True)
    
    def get_applicant_name(self, obj):
        try:
            staff = StaffProfile.objects.get(id=obj.applicant_id)
            return f"{staff.first_name} {staff.last_name}"
        except StaffProfile.DoesNotExist:
            return None
```

### 12.7 Naming Consistency

Updated menu items and page titles for better clarity:

| Before | After |
|--------|-------|
| My Leave Allowance Requests | My Leave Allowance |
| My Imprest Requests | My Payments |

Files updated: `servicesConfig.ts`, `CorporateServicesDashboard.tsx`, page components

---

## 13. Deployment

### 13.1 Docker Compose Services

```yaml
services:
  corporate-service:
    build: ./microservices/corporate-service
    ports:
      - "8008:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres-corporate-service:5432/fims_corporate
      - REDIS_URL=redis://redis-corporate-service:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=fims-kafka:9092
      - IAM_SERVICE_URL=http://fims-iam-service:8000
      - WORK_ORCHESTRATION_SERVICE_URL=http://fims-work-orchestration-service:8004
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - postgres-corporate-service
      - redis-corporate-service
      - fims-kafka
    networks:
      - fims-network

  corporate-celery:
    build: ./microservices/corporate-service
    command: celery -A config worker -l info
    environment:
      # Same as corporate-service
    depends_on:
      - corporate-service
      - redis-corporate-service

  corporate-celery-beat:
    build: ./microservices/corporate-service
    command: celery -A config beat -l info
    environment:
      # Same as corporate-service
    depends_on:
      - corporate-celery

  corporate-kafka-consumer:
    build: ./microservices/corporate-service
    command: python manage.py consume_workflow_events
    environment:
      # Same as corporate-service
    depends_on:
      - corporate-service
      - fims-kafka
```

### 13.2 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://host:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | `kafka:9092` |
| `IAM_SERVICE_URL` | IAM service endpoint | `http://fims-iam-service:8000` |
| `WORK_ORCHESTRATION_SERVICE_URL` | Orchestration endpoint | `http://fims-work-orchestration-service:8004` |
| `JWT_SECRET_KEY` | Shared JWT secret | `your-secret-key` |
| `SERVICE_TO_SERVICE_TOKEN` | Service auth token | `your-service-token` |
| `CELERY_BROKER_URL` | Celery broker | `redis://host:6379/1` |

### 13.3 Management Commands

| Command | Description |
|---------|-------------|
| `python manage.py migrate` | Run database migrations |
| `python manage.py register_permissions_kafka` | Register permissions with IAM |
| `python manage.py register_workflow_templates` | Register workflow templates |
| `python manage.py register_notification_templates` | Register notification templates with Work Orchestration Service |
| `python manage.py consume_workflow_events` | Start Kafka consumer |
| `python manage.py seed_org_structure` | Seed organization structure |
| `python manage.py seed_hr_config` | Seed HR configuration |
| `python manage.py seed_staff_data` | Seed sample staff data |

---

## 14. Extending the Service

### 14.1 Adding a New Module

1. Create module directory: `apps/{module_name}/`
2. Add `services/` subdirectory for business logic
3. Add `tasks/` subdirectory for Celery tasks (if needed)
4. Add models to `apps/infrastructure/persistence/models.py`
5. Add serializers to `apps/api/serializers/{module}_serializers.py`
6. Add views to `apps/api/views/{module}_views.py`
7. Register URLs in `apps/api/urls/api_urls.py`
8. Add workflow templates to `apps/core/workflows/workflows.yaml`
9. Update permissions in `config/permissions/corporate-service.json`

### 14.2 Adding a New External Service Integration

1. Create client in `apps/infrastructure/external/{service}_client.py`
2. Add configuration to `config/settings.py`
3. Add environment variables to docker-compose and deployment configs
4. Document the API contract and authentication method

### 14.3 Best Practices

1. **Domain Logic**: Keep business logic in services, not views
2. **Repository Pattern**: Use repositories for complex data access
3. **Error Handling**: Return structured error responses with field-level validation
4. **Logging**: Log important operations and errors
5. **Workflow Integration**: Use `WorkflowViewSetMixin` for workflow-enabled entities
6. **Kafka Events**: Handle workflow events in the consumer for status updates
7. **Code Generation**: Use consistent prefix patterns for entity codes
8. **Frontend State**: Use React Query with proper cache invalidation
9. **Form Validation**: Use Zod schemas for frontend validation
10. **Type Safety**: Maintain TypeScript interfaces in sync with API responses
11. **Ownership Filtering**: Use `OwnershipFilterMixin` for entities that should be filtered by owner
12. **Permission-Aware Navigation**: Use `PermissionLink` for links that should adapt based on user permissions
13. **Status Display**: Use `StatusDisplayMixin` for consistent human-readable status labels
14. **My Page Pattern**: Create separate "My" pages with `myOnly` prop for personal workspace views

---

## 15. Changelog

### Version 3.2 (March 10, 2026)

#### Workflow Return/Resubmission Fixes

**Bug Fix: Resubmission Now Returns to Correct Stage**

Previously, when resubmitting a returned document, the system would advance to the next pending stage instead of returning to the stage that initiated the return. This has been fixed across all 22 workflow-enabled services.

| Before (Bug) | After (Fixed) |
|-------------|---------------|
| HR returns document → User resubmits → Goes to HRAM Review | HR returns document → User resubmits → Goes back to HR |
| Return stage was skipped | Return stage is re-activated |

**Technical Changes:**

1. **`_resubmit_*` methods updated** across all services to:
   - First look for a stage with `status == 'returned'`
   - Re-activate that specific stage (not the next pending stage)
   - Only fall back to first pending stage if no returned stage is found

2. **Services Updated (22 total):**

   | Module | Services |
   |--------|----------|
   | HR | `leave_application_service.py`, `safari_application_workflow_service.py`, `training_request_service.py`, `salary_advance_workflow_service.py`, `extra_duty_claim_service.py`, `property_loss_report_service.py`, `fuel_request_service.py`, `asset_disposal_service.py`, `asset_maintenance_service.py`, `vehicle_maintenance_service.py` |
   | Finance | `internal_memo_service.py`, `imprest_retirement_service.py`, `petty_cash_workflow_service.py`, `petty_cash_service.py`, `budget_transfer_service.py` |
   | Procurement | `requisition_service.py`, `annual_procurement_plan_workflow_service.py`, `contract_workflow_service.py`, `giv_workflow_service.py`, `goods_delivery_workflow_service.py` |
   | Fleet | `fuel_request_workflow_service.py`, `vehicle_scheduling_workflow_service.py` |

3. **Workflow YAML Cleanup (Leave Application):**
   - Removed problematic inline "revision stages" from `corporate.leave_application` workflow
   - All return actions now correctly use `nextState: "returned"`
   - Simplified stage flow from 7 stages to 5 sequential stages

#### Revision Tracking Enhancements

**Stage Revision Filtering for "Already Acted" Check**

The `_enrich_plan_with_permissions` function in Work Orchestration Service now correctly filters activities by the current stage revision:

```python
# Before: Checked ALL activities (blocked resubmission approvals)
user_already_acted = any(
    activity.get('actor_id') == user_id and 
    activity.get('stage_id') == current_stage.external_id
    for activity in all_activities
)

# After: Only checks activities from CURRENT revision
current_revision = getattr(current_stage, 'revision', 1) or 1
stage_activities = repo.list_activity(
    plan_id=plan.plan_id,
    stage_id=current_stage.external_id,
    stage_revision=current_revision  # Filter by revision
)
```

**Benefits:**
- Approvers can now properly act on resubmitted documents
- No more "You have already acted on this stage" errors after resubmission
- Previous revision activities preserved for audit trail

### Version 3.1 (March 2026)

#### Workflow Integration Improvements

- Added comprehensive return and resubmission support
- Implemented revision tracking in Work Orchestration Service
- Added `activate_stage` API endpoint for explicit stage activation
- Updated all workflow services with `_resubmit_*` methods

#### Permission-Based Menu Visibility

- Implemented dynamic menu filtering based on user permissions
- Added `useMenuVisibility` hook for frontend navigation
- Created "My" vs "All" menu pattern for personal workspace
- Menus auto-hide for users without required permissions

#### Access Control Enhancements

- Hybrid permission system with scope-based access (own, department, all)
- Owner field mapping for automatic scope filtering
- Backend `AccessScopeFilterMixin` for ViewSets
- Frontend `useAccessControl` hook for UI permission checks

### Version 3.0 (March 2026)

- Initial comprehensive implementation
- All HR, Finance, Procurement, and Asset modules
- Workflow integration with Work Orchestration Service
- React Query state management
- Clean architecture patterns

---

## Related Documentation

- [Workflow Integration Guide](./workflow-integration-guide.md)
- [Workflow Actions Reference](./workflow-actions-reference.md)
- [Workflow Implementation Gaps](./workflow-implementation-gaps.md)
- [Corporate Service System Design](./corporate-service-system-design.md)
- [Finance Module SRS](./finance_srs.md)
- [HR Module SRS](./humanresource_srs.md)
- [Procurement Module SRS](./procurement_srs.md)
- [Seed Data Guide](../../docs/seed-data-guide.md)
- [Access Control Implementation](#11-hybrid-permission-system) (See Section 11)

---

*This document should be updated as the service evolves. Version 3.2 - March 2026*
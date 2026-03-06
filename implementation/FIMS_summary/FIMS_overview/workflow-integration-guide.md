# Workflow Integration Guide

> **Purpose:** This document provides a complete guide for integrating a business process (e.g., Leave Application, Imprest Retirement, Asset Disposal) with the Work Orchestration Service. It covers template definition, registration, service integration, and unified UI.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Step 1: Define the Workflow Template](#step-1-define-the-workflow-template)
3. [Step 2: Register the Template](#step-2-register-the-template)
4. [Step 3: Add Entity Detail Path (Frontend Link)](#step-3-add-entity-detail-path-frontend-link)
5. [Step 4: Create the Service Layer](#step-4-create-the-service-layer)
6. [Step 5: Frontend Integration](#step-5-frontend-integration)
7. [Step 6: Testing the Integration](#step-6-testing-the-integration)
8. [Step 7: Action Handling in Work Orchestration](#step-7-action-handling-in-work-orchestration)
9. [Troubleshooting](#troubleshooting)
10. [Appendix: Complete Leave Application Example](#appendix-complete-leave-application-example)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Staff Portal)                        │
│  ┌─────────────────────┐    ┌─────────────────────────────────────────────┐ │
│  │ Entity Detail Page  │    │  Embedded Workflow Console (iframe)         │ │
│  │ (LeaveDetailPage)   │───▶│  - Shows workflow stages                    │ │
│  │                     │    │  - Action buttons (Approve, Reject, etc.)   │ │
│  │                     │    │  - Activity history                         │ │
│  └─────────────────────┘    └─────────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ API Requests
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY (Nginx)                            │
│  /api/v1/corporate/* ──▶ Corporate Service                                  │
│  /api/v1/workflow/*  ──▶ Work Orchestration Service                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
              ┌────────────────────────┴────────────────────────┐
              │                                                 │
              ▼                                                  ▼
┌──────────────────────────────┐          ┌──────────────────────────────────┐
│     CORPORATE SERVICE        │          │   WORK ORCHESTRATION SERVICE     │
│                              │          │                                  │
│  - Entity Models             │  HTTP    │  - Workflow Plans (instances)    │
│  - Business Logic            │─────────▶│  - Stage Management              │
│  - OrchestrationClient       │          │  - Action Execution              │
│                              │          │  - Activity Logging              │
│  - Workflow Templates (YAML) │  Kafka   │  - Generic Console UI            │
│  - Template Registry         │─────────▶│  - Template Storage              │
└──────────────────────────────┘          └──────────────────────────────────┘
```

### Key Concepts

------------------------------------------------------------------------------------------------------------------------------------
| Concept                | Description                                                                                             |
|------------------------|---------------------------------------------------------------------------------------------------------|
| **Workflow Template**  | A YAML definition of the workflow stages, actions, and assignees. Published to Orchestration via Kafka. |
| **Workflow Plan**      | An instance of a workflow template for a specific entity (e.g., a specific leave application).          |
| **Stage**              | A step in the workflow (e.g., "Manager Approval", "HR Verification").                                   |
| **Action**             | An operation a user can perform on a stage (e.g., "approve", "reject", "return").                       |
| **Context**            | Variables passed when starting a workflow, used to resolve assignees (e.g., `{{applicant_id}}`).        |
| **Metadata**           | Additional data stored with the plan for display in the UI (e.g., dates, amounts, entity details).      |
------------------------------------------------------------------------------------------------------------------------------------

---

## Step 1: Define the Workflow Template

Create or update the workflow template in `apps/core/workflows/workflows.yaml`.

### Template Structure

```yaml
templates:
  - code: "corporate.your_entity_workflow"    # Unique identifier
    name: "Your Entity Workflow"               # Human-readable name
    workflow_type: "corporate_hr"              # Category (hr, finance, procurement, etc.)
    version: 1                                 # Increment when making changes
    definition:
      description: "Description of the workflow"
      sla:
        targetMinutes: 4320                    # Overall SLA in minutes
        breachStrategy: "escalate"             # What happens on breach
      metadata:
        module: "hr"                           # Module category
        category: "leave"                      # Subcategory
        requires_payment: true                 # Custom flags
      stages:
        - definitionKey: "stage_key_1"         # Unique key within this template
          name: "Stage Display Name"           # Shown in UI
          order: 1                             # Stage sequence (1, 2, 3...)
          assignees: ["{{variable_id}}"]       # Who can act on this stage
          actions:
            - name: "submit"                   # Action identifier
              label: "Submit Application"      # Button label in UI
              nextState: "completed"           # "completed" moves to next stage
            - name: "save_draft"
              label: "Save Draft"
              nextState: "pending"             # "pending" stays at current stage
          sla:
            durationMinutes: 1440              # Stage-specific SLA
            breachStrategy: "notify"
```

### Assignee Types

| Type | Example | Description |
|------|---------|-------------|
| **Context Variable** | `{{applicant_id}}` | Resolved from context passed when starting workflow |
| **Role-based** | `role:hr_officer` | Any user with the specified role |
| **Multiple** | `["{{hod_id}}", "role:director"]` | Either the specific user OR anyone with the role |

### Action Next States

| Value | Behavior |
|-------|----------|
| `completed` | Stage is marked complete, workflow advances to next stage |
| `pending` | Stage remains in progress (e.g., save draft) |
| `rejected` | Stage is marked rejected, workflow may end or trigger special handling |

### Example: Leave Application Template

```yaml
- code: "corporate.leave_application"
  name: "Leave Application Process"
  workflow_type: "corporate_hr"
  version: 1
  definition:
    description: "Complete leave application workflow"
    sla:
      targetMinutes: 4320
      breachStrategy: "escalate"
    metadata:
      module: "hr"
      category: "leave"
      requires_payment: true
    stages:
      - definitionKey: "leave_draft"
        name: "Application Draft"
        order: 1
        assignees: ["{{applicant_id}}"]
        actions:
          - name: "submit"
            label: "Submit Application"
            nextState: "completed"
          - name: "save_draft"
            label: "Save Draft"
            nextState: "pending"
      
      - definitionKey: "leave_head_approval"
        name: "Head/Manager Approval"
        order: 2
        assignees: ["{{line_manager_id}}"]
        actions:
          - name: "approve"
            label: "Approve"
            nextState: "completed"
          - name: "reject"
            label: "Reject"
            nextState: "rejected"
          - name: "return"
            label: "Return for Amendment"
            nextState: "pending"
        sla:
          durationMinutes: 1440
          breachStrategy: "notify"
      
      - definitionKey: "leave_hr_verification"
        name: "HR Verification"
        order: 3
        assignees: ["role:hr_officer"]
        actions:
          - name: "verify"
            label: "Verify & Forward"
            nextState: "completed"
          - name: "reject"
            label: "Reject"
            nextState: "rejected"
        sla:
          durationMinutes: 480
      
      # ... more stages ...
      
      - definitionKey: "leave_completed"
        name: "Completed"
        order: 7
        actions: []  # Final stage has no actions
```

---

## Step 2: Register the Template

Templates are published to Work Orchestration via Kafka. This happens automatically on service startup or can be triggered manually.

### Automatic Registration (on service startup)

In `apps/core/apps.py`:

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        # Register workflow templates when Django starts
        from apps.core.workflows.registry import WorkflowTemplateRegistry
        
        registry = WorkflowTemplateRegistry()
        count = registry.load_templates()
        if count > 0:
            published = registry.publish_all()
            print(f"Published {published} workflow templates to Kafka")
```

### Manual Registration (management command)

```bash
# From the service container
python manage.py register_workflow_templates

# With verbose output
python manage.py register_workflow_templates --verbosity=2

# Register specific module only
python manage.py register_workflow_templates --module=hr
```

### How Registration Works

1. **Load templates** from `workflows.yaml`
2. **Generate hash** of template content for change detection
3. **Publish to Kafka** topic `workflow-templates`
4. **Work Orchestration** consumes the message and stores/updates the template

```python
# apps/core/workflows/registry.py (simplified)
class WorkflowTemplateRegistry:
    def publish_template(self, template: Dict[str, Any]) -> bool:
        producer = self._get_producer()
        if not producer:
            return False
        
        message = {
            'action': 'register',
            'service': self.SERVICE_NAME,
            'timestamp': datetime.utcnow().isoformat(),
            'template': {
                'code': template['code'],
                'name': template['name'],
                'workflow_type': template.get('workflow_type', 'approval'),
                'version': template.get('version', 1),
                'is_active': True,
                'definition': template.get('definition', {}),
            }
        }
        
        producer.produce(
            self._topic,
            key=template['code'].encode('utf-8'),
            value=json.dumps(message).encode('utf-8'),
            callback=self._delivery_callback
        )
        producer.flush()
        return True
```

---

## Step 3: Add Entity Detail Path (Frontend Link)

To enable the "View full details" link in the Orchestration console, register the frontend path for your entity.

### Update `apps/core/workflow_entity_paths.py`

```python
# entity_type (from workflow metadata) -> staff portal path
ENTITY_DETAIL_PATHS = {
    'leave_application': '/service/corporate/leave-applications',
    # Add your entity here:
    'your_entity': '/service/corporate/your-entity-list',
}
```

The path should match the route in the frontend `App.tsx`:
```tsx
<Route path="your-entity-list/:id" element={<YourEntityDetailPage />} />
```

---

## Step 4: Create the Service Layer

The service layer handles business logic and communicates with Work Orchestration.

### 4.1 Model Setup

Ensure your model has workflow fields (use the mixin or add manually):

```python
# apps/infrastructure/persistence/models.py

from apps.core.mixins.workflow_mixin import WorkflowMixin

class YourEntity(WorkflowMixin, BaseModel):
    """Your entity with workflow support."""
    
    # Your entity fields
    reference_number = models.CharField(max_length=50, unique=True)
    applicant = models.ForeignKey('Staff', on_delete=models.PROTECT)
    department = models.ForeignKey('Department', on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default='draft')
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    # ... other fields ...
    
    # WorkflowMixin provides:
    # - workflow_plan_id (UUID)
    # - workflow_stage (CharField)
    # - workflow_stage_id (UUID)
    # - workflow_started_at (DateTimeField)
    # - workflow_completed_at (DateTimeField)
    
    def get_workflow_context(self) -> dict:
        """Context variables for assignee resolution."""
        context = {
            'entity_type': 'your_entity',
            'entity_id': str(self.id),
            'applicant_id': str(self.applicant_id),
            'department_id': str(self.department_id) if self.department_id else None,
        }
        
        # Add HOD if available
        if self.department and hasattr(self.department, 'head_id'):
            context['hod_id'] = str(self.department.head_id)
        
        return context
    
    def get_workflow_metadata(self) -> dict:
        """Metadata stored with the workflow plan (displayed in UI)."""
        from apps.core.workflow_entity_paths import add_entity_detail_path_to_metadata
        
        meta = {
            'entity_type': 'your_entity',
            'entity_id': str(self.id),
            'reference_number': self.reference_number,
            'applicant_id': str(self.applicant_id),
            'amount': str(self.amount) if self.amount else None,
            # Add fields you want visible in the workflow console
        }
        
        # This adds the frontend link for "View full details"
        return add_entity_detail_path_to_metadata(meta, 'your_entity')
```

### 4.2 Service Class

Create a service class to handle workflow operations:

```python
# apps/your_module/services/your_entity_service.py

import logging
from django.db import transaction
from django.utils import timezone

from apps.core.workflow_entity_paths import get_entity_detail_path
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class YourEntityService:
    """Service for managing YourEntity with workflow integration."""
    
    WORKFLOW_TEMPLATE_CODE = "corporate.your_entity_workflow"
    
    def __init__(self):
        self.workflow_client = OrchestrationClient()
    
    @transaction.atomic
    def submit_for_approval(self, entity_id: str, submitter_id: str):
        """Submit entity to start the workflow."""
        from apps.infrastructure.persistence.models import YourEntity
        
        entity = YourEntity.objects.select_related(
            'applicant', 'department'
        ).get(id=entity_id)
        
        if entity.status != 'draft':
            raise ValueError(f"Cannot submit entity with status '{entity.status}'")
        
        # 1. Build workflow context (for assignee resolution)
        context = entity.get_workflow_context()
        
        # 2. Build metadata (for UI display)
        metadata = entity.get_workflow_metadata()
        
        # 3. Add entity_detail_path for "View full details" link
        detail_path = get_entity_detail_path('your_entity')
        if detail_path:
            metadata['entity_detail_path'] = detail_path
        
        # 4. Start the workflow
        workflow_result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=submitter_id,
            subject_ref=str(entity.id),
            metadata=metadata,
        )
        
        # 5. Update entity with workflow info
        entity.status = 'submitted'
        
        if workflow_result:
            entity.workflow_plan_id = workflow_result.plan_id
            entity.workflow_stage = workflow_result.current_stage_name or ''
            entity.workflow_stage_id = workflow_result.current_stage_id
            entity.workflow_started_at = timezone.now()
            
            logger.info(
                "Started workflow for %s: plan_id=%s, stage=%s",
                entity.reference_number,
                workflow_result.plan_id,
                workflow_result.current_stage_name,
            )
        else:
            logger.warning(
                "Failed to start workflow for %s",
                entity.reference_number
            )
        
        entity.save()
        return entity
```

### 4.3 OrchestrationClient

The `OrchestrationClient` handles HTTP communication with Work Orchestration:

```python
# apps/infrastructure/external/orchestration_client.py (key methods)

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class WorkflowPlanResult:
    plan_id: str
    status: str
    current_stage_id: Optional[str]
    current_stage_name: Optional[str]
    stages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: Optional[str] = None


class OrchestrationClient:
    """Client for Work Orchestration Service API."""
    
    def __init__(self):
        self.base_url = settings.WORK_ORCHESTRATION_SERVICE_URL  # e.g., "http://work-orchestration-service:8004/api/v1/workflow"
        self.service_token = settings.SERVICE_TO_SERVICE_TOKEN
    
    def start_workflow(
        self,
        template_code: str,
        context: Dict[str, Any],
        initiator_id: str,
        subject_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkflowPlanResult]:
        """
        Start a workflow instance from a registered template.
        
        Args:
            template_code: Template code (e.g., 'corporate.leave_application')
            context: Variables for assignee resolution (e.g., applicant_id, hod_id)
            initiator_id: User ID starting the workflow
            subject_ref: Reference to the entity (usually entity ID)
            metadata: Additional data for UI display
        
        Returns:
            WorkflowPlanResult with plan ID and stage info
        """
        # Look up template by code
        template_id = self._get_template_id_by_code(template_code)
        if not template_id:
            return None
        
        payload = {
            'template_id': template_id,
            'workflow_type': template_code.split('.')[0],
            'created_by': initiator_id,
            'metadata': {
                **(metadata or {}),
                'context': context,
                'subject_ref': subject_ref,
                'template_code': template_code,
            },
        }
        
        response = self._make_request('POST', '/plans/', data=payload)
        # ... parse response and return WorkflowPlanResult
```

### 4.4 API ViewSet

Expose the submit action via API:

```python
# apps/api/views/your_entity_views.py

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.your_module.services.your_entity_service import YourEntityService


class YourEntityViewSet(ModelViewSet):
    """API ViewSet for YourEntity."""
    
    # ... standard CRUD methods ...
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit entity for workflow approval."""
        service = YourEntityService()
        
        try:
            entity = service.submit_for_approval(
                entity_id=pk,
                submitter_id=str(request.user.id),
            )
            
            return Response({
                'id': str(entity.id),
                'status': entity.status,
                'workflow_plan_id': str(entity.workflow_plan_id) if entity.workflow_plan_id else None,
                'workflow_stage': entity.workflow_stage,
                'message': 'Submitted successfully',
            })
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to submit'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='workflow-status')
    def workflow_status(self, request, pk=None):
        """Get current workflow status."""
        entity = self.get_object()
        
        if not entity.workflow_plan_id:
            return Response({
                'has_workflow': False,
                'status': entity.status,
            })
        
        return Response({
            'has_workflow': True,
            'plan_id': str(entity.workflow_plan_id),
            'stage': entity.workflow_stage,
            'status': entity.status,
        })
```

---

## Step 5: Frontend Integration

### 5.1 Service Functions

Add API functions in `corporateService.ts`:

```typescript
// services/corporateService.ts

export interface YourEntityItem {
  id: string;
  reference_number: string;
  status: string;
  workflow_plan_id?: string;
  workflow_stage?: string;
  // ... other fields
}

export interface WorkflowStatusResponse {
  has_workflow: boolean;
  plan_id?: string;
  stage?: string;
  status: string;
}

// List entities
export function listYourEntities(params?: { limit?: number; offset?: number; status?: string }) {
  return corporateList<YourEntityItem>(PATHS.yourEntities, params);
}

// Get single entity
export function getYourEntity(id: string) {
  return corporateGet<YourEntityItem>(PATHS.yourEntities, id);
}

// Submit for approval
export async function submitYourEntity(entityId: string): Promise<YourEntityItem> {
  const resp = await corporateClient.post<YourEntityItem>(
    `${PATHS.yourEntities}/${entityId}/submit/`
  );
  return resp.data;
}

// Get workflow status
export async function getYourEntityWorkflowStatus(entityId: string): Promise<WorkflowStatusResponse> {
  const resp = await corporateClient.get<WorkflowStatusResponse>(
    `${PATHS.yourEntities}/${entityId}/workflow-status/`
  );
  return resp.data;
}
```

### 5.2 Detail Page with Embedded Workflow Console

```tsx
// pages/corporate/YourEntityDetailPage.tsx

import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { EmbeddedWorkflowConsole } from '@staff/components/workflow/EmbeddedWorkflowConsole';
import {
  getYourEntity,
  submitYourEntity,
  getYourEntityWorkflowStatus,
} from '@/services/corporateService';

export function YourEntityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // Fetch entity data
  const { data: entity, isLoading } = useQuery({
    queryKey: ['your-entity', id],
    queryFn: () => getYourEntity(id!),
    enabled: !!id,
  });
  
  // Fetch workflow status
  const { data: workflowStatus } = useQuery({
    queryKey: ['your-entity-workflow', id],
    queryFn: () => getYourEntityWorkflowStatus(id!),
    enabled: !!id,
  });
  
  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: () => submitYourEntity(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['your-entity', id] });
      queryClient.invalidateQueries({ queryKey: ['your-entity-workflow', id] });
    },
  });
  
  if (isLoading || !entity) {
    return <div>Loading...</div>;
  }
  
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
      {/* Left Column: Entity Details */}
      <div className="lg:col-span-2 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Entity Details</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Display your entity fields */}
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-muted-foreground">Reference</dt>
                <dd className="font-medium">{entity.reference_number}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Status</dt>
                <dd className="font-medium">{entity.status}</dd>
              </div>
              {/* ... more fields ... */}
            </dl>
          </CardContent>
        </Card>
      </div>
      
      {/* Right Column: Workflow Console */}
      <div>
        <EmbeddedWorkflowConsole
          entityType="your-entity"  // Must match key in useCorporateWorkflows
          entityId={id!}
          entityTitle="Your Entity"
          entityReference={entity.reference_number}
          entityStatus={entity.status}
          hasWorkflow={workflowStatus?.has_workflow ?? false}
          workflowPlanId={workflowStatus?.plan_id}
          onSubmit={async () => {
            await submitMutation.mutateAsync();
          }}
        />
      </div>
    </div>
  );
}
```

### 5.3 Add Route in App.tsx

```tsx
// App.tsx

import { YourEntityPage } from "@staff/pages/corporate/YourEntityPage";
import { YourEntityDetailPage } from "@staff/pages/corporate/YourEntityDetailPage";

// Inside corporate routes:
<Route path="your-entities" element={<YourEntityPage />} />
<Route path="your-entities/:id" element={<YourEntityDetailPage />} />
```

### 5.4 Register Workflow Status Hook

Update `useCorporateWorkflows.ts` to include your entity:

```typescript
// hooks/useCorporateWorkflows.ts

import * as corporateService from '@staff/services/corporateService';

// Step 1: Add your entity type to the union
export type CorporateWorkflowEntity = 
  | 'leave-application'
  | 'imprest-retirement'
  | 'your-entity'  // Add your entity
  // ... other entities

// Step 2: Add workflow status function mapping
const workflowStatusFunctions: Record<CorporateWorkflowEntity, (id: string) => Promise<WorkflowStatusResponse>> = {
  'leave-application': corporateService.getLeaveApplicationWorkflowStatus,
  'imprest-retirement': corporateService.getImprestRetirementWorkflowStatus,
  'your-entity': corporateService.getYourEntityWorkflowStatus,  // Add your fetcher
  // ... other entities
};

// Step 3: Add workflow history function mapping
const workflowHistoryFunctions: Record<CorporateWorkflowEntity, (id: string) => Promise<WorkflowHistoryResponse>> = {
  'leave-application': corporateService.getLeaveApplicationWorkflowHistory,
  'imprest-retirement': corporateService.getImprestRetirementWorkflowHistory,
  'your-entity': corporateService.getYourEntityWorkflowHistory,  // Add your fetcher
  // ... other entities
};
```

### 5.5 EmbeddedWorkflowConsole Props Reference

The `EmbeddedWorkflowConsole` component accepts the following props:

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `entityType` | `CorporateWorkflowEntity` | Yes | Entity type key (must be registered in hooks) |
| `entityId` | `string` | Yes | UUID of the entity |
| `entityTitle` | `string` | Yes | Display title (e.g., "Leave Application") |
| `entityReference` | `string` | No | Reference number for display |
| `entityStatus` | `string` | No | Current entity status |
| `hasWorkflow` | `boolean` | No | Whether entity has a workflow (default: true) |
| `workflowPlanId` | `string` | No | Direct plan ID if already known |
| `onSubmit` | `() => Promise<void>` | No | Callback for draft submission |
| `height` | `string` | No | iframe height (default: '600px') |
| `className` | `string` | No | Additional CSS classes |

### 5.6 How the Embedded Console Works

The `EmbeddedWorkflowConsole` component:

1. **Fetches workflow status** using `useCorporateWorkflowStatus(entityType, entityId)`
2. **Builds iframe URL** to Work Orchestration's generic console:
   ```
   /api/v1/workflow/console/{plan_id}/?token={jwt}&app_base_url={origin}
   ```
3. **Passes JWT token** via URL parameter (Work Orchestration's middleware reads it)
4. **Passes app_base_url** so the generic console can build "View full details" links
5. **Shows loading/error states** while iframe loads
6. **Falls back to submit button** for draft entities without a workflow yet

---

## Step 6: Testing the Integration

### 6.1 Verify Template Registration

```bash
# Check if template is registered in Work Orchestration
docker exec -it fims-work-orchestration-service python manage.py shell

>>> from apps.infrastructure.persistence.models import WorkflowTemplateModel
>>> WorkflowTemplateModel.objects.filter(code='corporate.your_entity_workflow').exists()
True
>>> template = WorkflowTemplateModel.objects.get(code='corporate.your_entity_workflow')
>>> print(template.name, template.version)
```

### 6.2 Test Workflow Creation

1. Create a draft entity in the frontend
2. Click "Submit for Approval"
3. Check the entity now has `workflow_plan_id`
4. Verify the workflow appears in Work Orchestration dashboard

### 6.3 Test Stage Actions

1. Log in as the assignee for the current stage
2. Open the workflow console
3. Click an action button (e.g., "Approve")
4. Verify the workflow advances to the next stage

### 6.4 Test "View Full Details" Link

1. Open a workflow in the Work Orchestration console
2. Click "View full details" in the header
3. Verify it opens the entity detail page in Corporate

---

## Step 7: Action Handling in Work Orchestration

When a user clicks an action button (e.g., "Approve") in the embedded workflow console, the action is handled entirely by the Work Orchestration Service.

### How Actions Work

1. **User clicks action button** in the generic console
2. **JavaScript sends POST** to `/api/v1/workflow/stages/{stage_id}/execute-action/`
3. **Work Orchestration** validates the action:
   - Is the stage in_progress?
   - Is the user an assignee for this stage?
   - Is this action valid for this stage?
4. **Action is executed**:
   - Stage status updated (completed, rejected, pending)
   - Activity logged with actor details
   - Next stage activated if applicable
5. **Response returned** with updated plan data
6. **UI refreshes** to show new state

### Activity Logging

Each action is logged with:
- `action` - The action name (approve, reject, verify, etc.)
- `actor_id` - User who performed the action
- `actor_name` - Display name (fetched from IAM)
- `timestamp` - When the action occurred
- `stage_name` - Stage where action was performed
- `remarks` - Optional comments

### Handling Actions in Corporate Service (Optional)

If you need to perform additional business logic when an action is taken (e.g., update entity status, send notifications), you can:

1. **Poll for changes** in the frontend and update entity status
2. **Listen to Kafka events** published by Work Orchestration
3. **Use webhooks** if configured

Example of polling approach in frontend:
```typescript
// In your detail page, refetch entity when workflow changes
const { data: entity } = useQuery({
  queryKey: ['your-entity', id],
  queryFn: () => getYourEntity(id!),
  refetchInterval: 10000, // Refetch every 10 seconds
});
```

---

## Troubleshooting

### Template Not Found

**Error:** `Workflow template not found: corporate.your_entity_workflow`

**Solutions:**
1. Check template is defined in `workflows.yaml`
2. Run registration command:
   ```bash
   docker exec -it fims-corporate-service python manage.py register_workflow_templates
   ```
3. Verify template in Work Orchestration DB:
   ```bash
   docker exec -it fims-work-orchestration-service python manage.py shell
   >>> from apps.infrastructure.persistence.models import WorkflowTemplateModel
   >>> WorkflowTemplateModel.objects.filter(code__contains='your_entity').values('code', 'is_active')
   ```

### Iframe Refused to Connect

**Error:** `localhost refused to connect` or blank iframe

**Causes:**
1. X-Frame-Options blocking the embed
2. Work Orchestration service not running
3. Wrong URL being used

**Solutions:**
1. Verify `@xframe_options_exempt` decorator on `WorkflowConsoleView`
2. Check service health: `curl http://localhost:8004/health/`
3. Check browser console for actual error

### Authorization Header Missing

**Error:** `{"error": "Authorization header missing or invalid"}`

**Cause:** JWT not being passed correctly to iframe

**Solutions:**
1. Verify `jwt_middleware.py` reads token from query param:
   ```python
   token = request.GET.get('token') or auth_header.replace('Bearer ', '')
   ```
2. Verify frontend is passing token in URL:
   ```typescript
   const url = `${baseUrl}/console/${planId}/?token=${token}`
   ```

### Assignee Resolution Failed

**Error:** Stage has no assignees or wrong assignees

**Causes:**
1. Context variables not passed correctly
2. Template assignee syntax incorrect
3. Role not found in IAM

**Debug:**
1. Check workflow metadata contains context:
   ```python
   plan.metadata.get('context')  # Should have applicant_id, hod_id, etc.
   ```
2. Verify template assignee format: `["{{variable_name}}"]` or `["role:role_name"]`

### "View Full Details" Link Not Working

**Error:** Link missing or goes to wrong page

**Causes:**
1. `entity_detail_path` not in metadata
2. `app_base_url` not passed to iframe
3. Path doesn't match frontend route

**Solutions:**
1. Add entity to `workflow_entity_paths.py`
2. Verify `add_entity_detail_path_to_metadata()` called in model
3. Check frontend route matches the path

---

## Appendix: Complete Leave Application Example

### Files Modified/Created

| File | Purpose |
|------|---------|
| `apps/core/workflows/workflows.yaml` | Template definition |
| `apps/core/workflow_entity_paths.py` | Frontend path mapping |
| `apps/infrastructure/persistence/models.py` | LeaveApplication model with workflow fields |
| `apps/hr/services/leave_application_service.py` | Business logic + workflow start |
| `apps/api/views/leave_views.py` | API endpoints |
| `frontend/.../LeaveApplicationDetailPage.tsx` | Detail page with embedded console |
| `frontend/.../corporateService.ts` | API functions |
| `frontend/.../useCorporateWorkflows.ts` | Workflow hooks |

### Complete Service Implementation

```python
# apps/hr/services/leave_application_service.py

import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone

from apps.core.workflow_entity_paths import get_entity_detail_path
from apps.infrastructure.external.orchestration_client import OrchestrationClient

logger = logging.getLogger(__name__)


class LeaveApplicationService:
    """Leave application management service with workflow integration."""

    WORKFLOW_TEMPLATE_CODE = 'corporate.leave_application'

    def __init__(self):
        self._workflow_client = None

    @property
    def workflow_client(self) -> OrchestrationClient:
        """Lazy-load the OrchestrationClient."""
        if self._workflow_client is None:
            self._workflow_client = OrchestrationClient()
        return self._workflow_client

    @transaction.atomic
    def submit_application(
        self,
        application_id: str,
        submitter_id: Optional[str] = None,
    ):
        """
        Submit leave application for approval.
        Creates a workflow plan in Work Orchestration Service.
        """
        from apps.infrastructure.persistence.models import LeaveApplication

        application = LeaveApplication.objects.select_related(
            'applicant', 'department', 'leave_type'
        ).get(id=application_id)

        if application.status != 'draft':
            raise ValueError(f"Cannot submit application with status '{application.status}'")

        # Step 1: Build workflow context (for assignee resolution)
        context = {
            'entity_type': 'leave_application',
            'entity_id': str(application.id),
            'applicant_id': str(application.applicant_id),
            'department_id': str(application.department_id) if application.department_id else None,
            'leave_type': application.leave_type.code if application.leave_type else None,
            'days_requested': application.days_requested,
            'is_paid_leave': application.is_paid,
        }

        # Add HOD/Director info if available
        if application.department:
            if hasattr(application.department, 'head_id') and application.department.head_id:
                context['hod_id'] = str(application.department.head_id)
            if hasattr(application.department, 'directorate') and application.department.directorate:
                if hasattr(application.department.directorate, 'director_id'):
                    context['director_id'] = str(application.department.directorate.director_id)

        # Step 2: Build metadata (for UI display)
        metadata = {
            'entity_type': 'leave_application',
            'entity_id': str(application.id),
            'application_number': application.application_number,
            'applicant_id': str(application.applicant_id),
            'leave_type': application.leave_type.name if application.leave_type else None,
            'start_date': str(application.start_date),
            'end_date': str(application.end_date),
            'days_requested': application.days_requested,
        }

        # Step 3: Add entity_detail_path for "View full details" link
        detail_path = get_entity_detail_path('leave_application')
        if detail_path:
            metadata['entity_detail_path'] = detail_path

        # Step 4: Start workflow
        initiator_id = submitter_id or str(application.applicant_id)

        workflow_result = self.workflow_client.start_workflow(
            template_code=self.WORKFLOW_TEMPLATE_CODE,
            context=context,
            initiator_id=initiator_id,
            subject_ref=str(application.id),
            metadata=metadata,
        )

        # Step 5: Update application with workflow info
        application.status = 'submitted'

        if workflow_result:
            application.workflow_plan_id = workflow_result.plan_id
            application.workflow_stage = workflow_result.current_stage_name or ''
            application.workflow_stage_id = workflow_result.current_stage_id
            application.workflow_started_at = timezone.now()
            logger.info(
                "Started workflow for leave application %s: plan_id=%s, stage=%s",
                application.application_number,
                workflow_result.plan_id,
                workflow_result.current_stage_name,
            )
        else:
            logger.warning(
                "Failed to start workflow for leave application %s",
                application.application_number,
            )

        application.save()
        return application

    def get_workflow_status(self, application_id: str) -> Optional[dict]:
        """Get the current workflow status for an application."""
        from apps.infrastructure.persistence.models import LeaveApplication

        application = LeaveApplication.objects.get(id=application_id)

        if not application.workflow_plan_id:
            return None

        plan = self.workflow_client.get_plan(str(application.workflow_plan_id))
        if not plan:
            return {
                'has_workflow': True,
                'workflow_plan_id': str(application.workflow_plan_id),
                'status': 'unknown',
                'error': 'Could not fetch workflow status',
            }

        return {
            'has_workflow': True,
            'workflow_plan_id': plan.plan_id,
            'status': plan.status,
            'current_stage': plan.current_stage_name,
            'current_stage_id': plan.current_stage_id,
            'stages': plan.stages,
            'is_completed': plan.status in ('completed', 'cancelled'),
        }

    def get_workflow_history(self, application_id: str) -> List[dict]:
        """Get workflow activity history for an application."""
        from apps.infrastructure.persistence.models import LeaveApplication

        application = LeaveApplication.objects.get(id=application_id)

        if not application.workflow_plan_id:
            return []

        return self.workflow_client.get_plan_activity(str(application.workflow_plan_id))
```

### Workflow Data Flow

```
1. User creates Leave Application (status: draft)
                    │
                    ▼
2. User clicks "Submit for Approval"
                    │
                    ▼
3. LeaveApplicationService.submit_application()
   ├── Build context: { applicant_id, department_id, hod_id, ... }
   ├── Build metadata: { entity_type, entity_id, application_number, dates, ... }
   ├── Add entity_detail_path for UI link
   └── Call workflow_client.start_workflow()
                    │
                    ▼
4. OrchestrationClient makes HTTP POST to Work Orchestration
   POST /api/v1/workflow/plans/
   {
     "template_id": "...",
     "workflow_type": "corporate",
     "created_by": "user-uuid",
     "metadata": {
       "entity_type": "leave_application",
       "entity_id": "leave-uuid",
       "entity_detail_path": "/service/corporate/leave-applications",
       "application_number": "LV-A6AD223B",
       "applicant_id": "staff-uuid",
       "leave_type": "Annual Leave",
       "start_date": "2026-06-15",
       "end_date": "2026-06-30",
       "days_requested": 16,
       "context": { applicant_id, hod_id, ... }
     }
   }
                    │
                    ▼
5. Work Orchestration creates Plan with Stages
   - Creates WorkflowPlan instance
   - Creates WorkflowStage instances from template
   - Sets first stage to "in_progress"
   - Returns plan_id and stage info
                    │
                    ▼
6. LeaveApplication updated:
   - status = "submitted"
   - workflow_plan_id = plan_id
   - workflow_stage = "Application Draft"
   - workflow_started_at = now()
                    │
                    ▼
7. Frontend displays Embedded Workflow Console
   - Shows current stage and actions
   - User with permission can Approve/Reject/Return
                    │
                    ▼
8. Action executed → stage advances → repeat until completed
```

### Entity Path Registry

```python
# apps/core/workflow_entity_paths.py

from typing import Optional

ENTITY_DETAIL_PATHS = {
    'leave_application': '/service/corporate/leave-applications',
    'imprest_retirement': '/service/corporate/imprest-retirement',
    'internal_memo': '/service/corporate/internal-memos',
    'petty_cash_requisition': '/service/corporate/petty-cash',
    'budget_transfer': '/service/corporate/budget-transfers',
    'requisition': '/service/corporate/requisitions',
    'goods_issue_voucher': '/service/corporate/giv',
    'vehicle_maintenance': '/service/corporate/vehicle-maintenance',
    'asset_maintenance': '/service/corporate/asset-maintenance',
    'asset_disposal': '/service/corporate/asset-disposal',
    'training_request': '/service/corporate/staff-training',
    'extra_duty_claim': '/service/corporate/extra-duty',
    'fuel_request': '/service/corporate/fuel-request',
    'external_payment': '/service/corporate/external-payment',
}


def get_entity_detail_path(entity_type: str) -> Optional[str]:
    """Return the staff portal detail path for the entity type, or None."""
    return ENTITY_DETAIL_PATHS.get(entity_type)


def add_entity_detail_path_to_metadata(metadata: dict, entity_type: str) -> dict:
    """Add entity_detail_path to metadata if we have a path for this entity_type."""
    path = get_entity_detail_path(entity_type)
    if path:
        metadata = {**metadata, 'entity_detail_path': path}
    return metadata
```

---

## Quick Reference: Adding a New Workflow

### Checklist

- [ ] **Step 1:** Add template to `apps/core/workflows/workflows.yaml`
- [ ] **Step 2:** Add entity path to `apps/core/workflow_entity_paths.py`
- [ ] **Step 3:** Add `get_workflow_metadata()` to model (use `add_entity_detail_path_to_metadata`)
- [ ] **Step 4:** Create service with `submit_for_approval()` method
- [ ] **Step 5:** Add API endpoint with `@action(detail=True, methods=['post'])` for submit
- [ ] **Step 6:** Add workflow status endpoint: `@action(detail=True, methods=['get'], url_path='workflow-status')`
- [ ] **Step 7:** Add workflow history endpoint: `@action(detail=True, methods=['get'], url_path='workflow-history')`
- [ ] **Step 8:** Add entity type to `CorporateWorkflowEntity` union in `useCorporateWorkflows.ts`
- [ ] **Step 9:** Add status/history functions to mapping objects in `useCorporateWorkflows.ts`
- [ ] **Step 10:** Create detail page with `<EmbeddedWorkflowConsole />`
- [ ] **Step 11:** Register template and rebuild services

### Commands

```bash
# Register templates (from corporate service container)
docker exec -it fims-corporate-service python manage.py register_workflow_templates

# Rebuild services after code changes
docker compose build corporate-service work-orchestration-service
docker compose up -d corporate-service work-orchestration-service

# Verify template registered
docker exec -it fims-work-orchestration-service python manage.py shell -c "
from apps.infrastructure.persistence.models import WorkflowTemplateModel
print(list(WorkflowTemplateModel.objects.filter(code__startswith='corporate.').values_list('code', flat=True)))
"

# Check workflow for specific entity
docker exec -it fims-corporate-service python manage.py shell -c "
from apps.infrastructure.persistence.models import LeaveApplication
app = LeaveApplication.objects.filter(workflow_plan_id__isnull=False).first()
if app:
    print(f'App: {app.application_number}')
    print(f'Plan ID: {app.workflow_plan_id}')
    print(f'Stage: {app.workflow_stage}')
"
```

---

*Last updated: February 2026*

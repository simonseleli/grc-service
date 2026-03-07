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

## Step 8: React to Workflow Events (Kafka — Your Service Consumes)

The workflow-integration-guide above shows how to **start** a workflow. This section covers how your service **reacts** to what WO publishes back — the closing half of the integration loop.

### 8.1 What WO Publishes

Every time a stage action is executed or a workflow completes, WO publishes to the Kafka topic `workflow-events`.

Your service must subscribe to this topic and filter by `event_type`:

| `event_type` | When | Key Fields |
|---|---|---|
| `WorkflowStageUpdated` | Every stage action (approve/reject/return/etc.) | `planId`, `stageId`, `action`, `actorId`, `newStatus`, `form_data` |
| `WorkflowCompleted` | Simple completion event (all stages terminal) | `planId`, `workflowType` |
| `{workflow_type}.workflow.completed` | Full completion event | `plan_id`, `final_decision`, `result_data`, `metadata` |
| `{workflow_type}.stage.completed` | **GRC engagement only** — individual stage completes | `plan_id`, `stage_key`, `action_name`, `metadata` |

> `{workflow_type}.workflow.completed` is the event your service waits for to finalize an entity (set status to `approved`, `rejected`, `cancelled`). The `WorkflowCompleted` event fires at the same time but carries less data.

### 8.2 Full Completion Event Payload

```json
{
  "event_type": "grc.workflow.completed",
  "event_version": "1.0",
  "timestamp": "2026-03-07T10:30:00Z",
  "source_service": "work-orchestration-service",
  "plan_id": "plan-uuid",
  "workflow_type": "grc",
  "final_status": "completed",
  "final_decision": "approved",
  "metadata": {
    "entity_id": "your-entity-uuid",
    "entity_type": "audit_plan",
    "reference_number": "RBIAP-001",
    "template_code": "grc.audit_plan_approval"
  },
  "result_data": {
    "disposal_method": "shredding",
    "certificate_number": "CERT-001"
  },
  "completed_at": "2026-03-07T10:30:00Z"
}
```

**`final_decision` values:**

| Value | Meaning |
|---|---|
| `approved` | All stages completed with no rejection |
| `rejected` | At least one stage was rejected |
| `cancelled` | Workflow was cancelled before completion |

**`result_data`** contains form fields submitted during stage actions (e.g., dropdowns, text fields in the WO console). Your service reads these to extract final decisions that were recorded in the console.

### 8.3 Stage Completion Event (GRC Engagement Lifecycle Only)

For `grc.engagement_notification` workflows, WO publishes a **stage event** after each individual stage completes, letting GRC update the engagement's current phase before the full workflow ends:

```json
{
  "event_type": "grc.stage.completed",
  "source_service": "work-orchestration-service",
  "plan_id": "plan-uuid",
  "workflow_type": "grc",
  "final_decision": "",
  "metadata": {
    "template_code": "grc.engagement_notification",
    "entity_id": "engagement-uuid",
    "stage_key": "planning",
    "action_name": "start_fieldwork"
  }
}
```

`stage_key` values are the `key` field from your workflow template stage definition (e.g., `planning`, `fieldwork`, `reporting`).

> This event only fires when `metadata.template_code == 'grc.engagement_notification'`. For all other workflow types, only the final `{type}.workflow.completed` event is published.

### 8.4 How to Consume — Kafka Consumer Pattern

Your service subscribes to `workflow-events` topic and processes events based on `event_type`:

```python
# apps/core/workflows/consumers/workflow_event_consumer.py

import json
import logging
from kafka import KafkaConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


class WorkflowEventConsumer:
    """Consumes workflow-events topic from Work Orchestration."""

    TOPIC = 'workflow-events'

    def __init__(self):
        self.consumer = KafkaConsumer(
            self.TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            group_id='grc-service-workflow-consumer',  # use YOUR service prefix
            auto_offset_reset='earliest',
            enable_auto_commit=True,
        )

    def process_event(self, event: dict) -> bool:
        event_type = event.get('event_type', '')

        # Only process GRC workflow events
        if not event_type.startswith('grc.'):
            return True  # Ignore other services' events

        if event_type == 'grc.workflow.completed':
            return self._handle_workflow_completed(event)

        if event_type == 'grc.stage.completed':
            return self._handle_stage_completed(event)

        logger.debug("Unhandled GRC event type: %s", event_type)
        return True

    def _handle_workflow_completed(self, event: dict) -> bool:
        """Update entity status based on workflow final decision."""
        metadata = event.get('metadata', {})
        entity_id = metadata.get('entity_id')
        entity_type = metadata.get('entity_type')
        final_decision = event.get('final_decision')  # 'approved', 'rejected', 'cancelled'
        result_data = event.get('result_data', {})

        if not entity_id or not entity_type:
            logger.warning("Workflow completed event missing entity_id or entity_type: %s", event)
            return False

        # Route to correct handler based on entity_type
        try:
            if entity_type == 'audit_plan':
                self._finalize_audit_plan(entity_id, final_decision, result_data, metadata)
            elif entity_type == 'engagement':
                self._finalize_engagement(entity_id, final_decision, result_data, metadata)
            # ... add other entity types
            return True
        except Exception as e:
            logger.error("Failed to finalize %s %s: %s", entity_type, entity_id, e, exc_info=True)
            return False

    def _handle_stage_completed(self, event: dict) -> bool:
        """Update engagement stage/phase based on intermediate stage completion."""
        metadata = event.get('metadata', {})
        entity_id = metadata.get('entity_id')
        stage_key = metadata.get('stage_key')
        action_name = metadata.get('action_name')

        if not entity_id or not stage_key:
            return False

        logger.info("Engagement %s: stage '%s' completed via action '%s'", entity_id, stage_key, action_name)
        # e.g., update engagement.current_phase = 'fieldwork' when stage_key='fieldwork'
        return True

    def _finalize_audit_plan(self, entity_id, decision, result_data, metadata):
        """Apply workflow outcome to audit plan."""
        from apps.core.models import AuditPlan
        plan = AuditPlan.objects.get(id=entity_id)
        if decision == 'approved':
            plan.status = 'approved'
        elif decision == 'rejected':
            plan.status = 'returned'
        plan.save(update_fields=['status'])
        logger.info("Audit plan %s finalized: %s", entity_id, decision)
```

#### Celery Beat Task to Drive the Consumer

```python
# In grc-service apps/core/tasks.py

@shared_task(bind=True, ignore_result=True)
def process_workflow_events(self) -> int:
    """Poll workflow-events Kafka topic and apply outcomes to GRC entities."""
    consumer = get_workflow_event_consumer()
    processed = 0
    try:
        for _ in range(20):  # max 20 per run
            count = consumer.poll_and_process(timeout=0.5)
            if count == 0:
                break
            processed += count
        if processed > 0:
            logger.info("Processed %d workflow event(s)", processed)
    except Exception as e:
        logger.error("Error processing workflow events: %s", e, exc_info=True)
    return processed
```

```python
# In settings.py
CELERY_BEAT_SCHEDULE = {
    # ... existing tasks ...
    'process-workflow-events': {
        'task': 'apps.core.tasks.process_workflow_events',
        'schedule': 10.0,  # Every 10 seconds
    },
}
```

### 8.5 Consumer Group Naming Convention

```
{service-name}-workflow-consumer
```

Examples:
- `grc-service-workflow-consumer`
- `document-records-service-workflow-consumer`
- `corporate-service-workflow-consumer`

Each service has its own consumer group so every service independently reads the same events (Kafka fan-out).

---

## Step 9: Tasks Integration (HTTP REST)

WO has a full task management subsystem. Your service can create, assign, and track tasks — either linked to a workflow plan or completely standalone.

### 9.1 Task Types

| Type | Description |
|---|---|
| **Plan-linked tasks** | Assigned to a specific workflow stage; lifecycle tied to the plan |
| **Standalone tasks** | Independent tasks with no workflow plan; tracked separately |

### 9.2 Task Endpoints

All endpoints are under `/api/v1/work-orchestration/`:

| Method | Path | What it does |
|---|---|---|
| `GET` | `tasks/` | List all plan-linked tasks (filter by `status`, `assignee`, `queue`, `due_before`) |
| `POST` | `tasks/` | Create a plan-linked task |
| `GET/PATCH` | `plans/{plan_id}/tasks/{task_id}/` | Get or update a plan task |
| `GET` | `standalone-tasks/` | List standalone tasks |
| `POST` | `standalone-tasks/` | Create a standalone task |
| `GET/PATCH` | `standalone-tasks/{task_id}/` | Get or update a standalone task |
| `GET/POST` | `tasks/{task_id}/comments/` | Thread comments on a task |
| `GET/DELETE` | `tasks/{task_id}/comments/{comment_id}/` | Manage individual comment |
| `GET/POST` | `tasks/{task_id}/collaborators/` | Add/list collaborators |
| `GET` | `invitations/` | User's pending task invitations |
| `GET/POST` | `task-types/` | Manage task type definitions |
| `GET/POST` | `task-queues/` | Manage task queue definitions |

### 9.3 Create Task Request Body

```json
POST /api/v1/work-orchestration/tasks/
{
  "title": "Prepare risk assessment matrix",
  "description": "Identify and rate all risks for FY2025/26 audit",
  "task_type": "audit",
  "assignee": "user-uuid",
  "created_by": "user-uuid",
  "plan_id": "optional-plan-uuid",
  "stage_id": "optional-stage-uuid",
  "due_at": "2026-03-14T17:00:00Z",
  "priority": "high",
  "queue": "audit-fieldwork",
  "estimated_hours": 8.0,
  "related_entity": {
    "type": "engagement",
    "id": "engagement-uuid"
  },
  "context": {}
}
```

**Task status values:** `pending`, `assigned`, `in_progress`, `completed`, `cancelled`

**Task priority values:** `low`, `normal`, `high`, `urgent`

### 9.4 Task Response Shape

```json
{
  "id": "task-uuid",
  "title": "Prepare risk assessment matrix",
  "description": "...",
  "task_type": "audit",
  "status": "assigned",
  "priority": "high",
  "assignee": "user-uuid",
  "created_by": "user-uuid",
  "plan_id": "plan-uuid",
  "stage_id": "stage-uuid",
  "queue": "audit-fieldwork",
  "due_at": "2026-03-14T17:00:00Z",
  "estimated_hours": 8.0,
  "actual_hours": null,
  "related_entity": {"type": "engagement", "id": "..."},
  "created_at": "2026-03-07T10:00:00Z",
  "updated_at": "2026-03-07T10:00:00Z"
}
```

### 9.5 Automatic Task Notifications

WO **automatically sends notifications** when tasks change — you do not need to publish notification events for these:

| Event | Notification Sent |
|---|---|
| Task created | `work_orchestration.task.assigned` → assignee |
| `assignee` field updated | `work_orchestration.task.assigned` → new assignee |
| `status` set to `completed` | `work_orchestration.task.completed` → task creator |
| Other field update | `work_orchestration.task.updated` → assignee |

### 9.6 Timesheet Logging

Users log time against tasks:

```json
POST /api/v1/work-orchestration/plans/{plan_id}/tasks/{task_id}/timesheets/
{
  "user_id": "user-uuid",
  "started_at": "2026-03-07T08:00:00Z",
  "ended_at": "2026-03-07T12:00:00Z",
  "hours": 4.0,
  "notes": "Reviewed working papers"
}
```

For standalone tasks, replace the path with `standalone-tasks/{task_id}/timesheets/`.

---

## Step 10: Reminders Integration (HTTP REST)

Your service can schedule reminders through WO's reminder engine. WO delivers then via configured channels (in_app, email, SMS, webhook) with retry and escalation support.

WO's Celery Beat processes due reminders every **60 seconds**.

### 10.1 Schedule a Reminder

```json
POST /api/v1/work-orchestration/reminders/
{
  "title": "Audit Plan Review Due",
  "message": "The audit plan review deadline is today. Please take action.",
  "due_at": "2026-03-10T09:00:00Z",
  "plan_id": "optional-plan-uuid",
  "task_id": "optional-task-uuid",
  "channel": "email",
  "target_user_id": "user-uuid",
  "metadata": {
    "entity_type": "audit_plan",
    "entity_id": "plan-uuid",
    "link": "https://staff.fcc.go.tz/grc/audit/plans/plan-uuid"
  },
  "max_retries": 3,
  "recurrence": {},
  "escalation_policy": {}
}
```

**`channel` values:** `in_app`, `email`, `sms`, `webhook`

### 10.2 List Reminders

```
GET /api/v1/work-orchestration/reminders/?status=pending&plan_id={uuid}&due_before=2026-03-10T00:00:00Z
```

### 10.3 Recurrence Configuration

```json
"recurrence": {
  "frequency": "daily",
  "interval": 1,
  "end_date": "2026-03-20T00:00:00Z"
}
```

### 10.4 Escalation Policy

```json
"escalation_policy": {
  "escalate_after_minutes": 120,
  "escalate_to_user_id": "supervisor-uuid",
  "escalate_channel": "email"
}
```

### 10.5 Automation-Triggered Reminders

You can also trigger reminders automatically via the workflow template's `automation.escalationReminder` config (see Step 12) — this requires no code in your service, only YAML configuration.

---

## Step 11: Analytics & Reports (HTTP REST)

WO exposes read-only analytics and report generation across all workflow and task data. All endpoints require JWT auth + `CanViewAnalytics` permission.

### 11.1 Analytics Endpoints

| Endpoint | Returns |
|---|---|
| `GET /analytics/stats/` | Total plans by status/type, total tasks, completion rates, avg duration |
| `GET /analytics/tasks/overdue/?limit=100` | List of all overdue tasks platform-wide |
| `GET /analytics/queues/?queue_name=audit-fieldwork` | Queue depth, pending count, avg task age |
| `GET /analytics/stages/?limit=10` | Stage performance — avg duration, bottleneck detection, slowest stages |

### 11.2 Stats Response (example)

```json
{
  "data": {
    "total_plans": 142,
    "plans_by_status": {"completed": 98, "in_progress": 31, "cancelled": 13},
    "plans_by_type": {"grc": 67, "corporate_hr": 45, "document": 30},
    "total_tasks": 520,
    "tasks_by_status": {"completed": 310, "in_progress": 145, "pending": 65},
    "avg_completion_days": 4.2
  }
}
```

### 11.3 Vetting Report

Generates a cross-workflow vetting/audit report:

```
GET /api/v1/work-orchestration/reports/vetting/
  ?workflow_type=grc
  &start_date=2026-01-01
  &end_date=2026-03-31
  &status=completed
  &format=json
```

**Supported formats:** `json`, `pdf`, `excel`, `csv`

PDF and Excel output are returned as file downloads (`Content-Disposition: attachment`):

```
GET /reports/vetting/?format=pdf   → application/pdf download
GET /reports/vetting/?format=excel → .xlsx download
GET /reports/vetting/?format=csv   → .csv download
```

### 11.4 Task Report

```
GET /api/v1/work-orchestration/reports/tasks/
  ?assignee={user-uuid}
  &status=overdue
  &queue=audit-fieldwork
  &format=json
```

---

## Step 12: Automation Engine (Template YAML Metadata)

WO evaluates automation rules embedded directly in your **workflow template stage metadata** every 30 seconds. This lets you configure automated behavior without writing any service-side code.

### 12.1 How It Works

When WO receives a `WorkflowStageUpdated` event on `workflow-events`, it:

1. Loads the plan and stage
2. Reads `stage.metadata.automation` config
3. Executes any matching automation rules

### 12.2 Available Automation Rules

Add an `automation` key to any stage's `metadata` in your `workflows.yaml`:

```yaml
templates:
  - code: "grc.audit_plan_approval"
    name: "Audit Plan Approval"
    workflow_type: "grc"
    version: 1
    definition:
      stages:
        - key: "cia_review"
          name: "CIA Review"
          order: 1
          assignees: ["{{cia_id}}"]
          actions:
            - name: "approve"
              next_state: "completed"
            - name: "return"
              next_state: "rejected"
          metadata:
            automation:
              # Rule 1 — Auto-advance to a specific target when approved
              autoAdvance:
                onStatuses: ["completed"]
                action: "activate"
                targetStage: "director_endorsement"
                actorId: "automation-bot"
                comment: "Automatically forwarded after CIA approval"

              # Rule 2 — Schedule an escalation reminder if stage goes blocked/pending
              escalationReminder:
                onStatuses: ["blocked", "pending"]
                offsetMinutes: 60
                channel: "email"
                title: "Audit Plan Review Outstanding"
                message: "The audit plan review requires your attention."
                maxRetries: 3
                escalationPolicy:
                  escalate_after_minutes: 120
                  escalate_to_user_id: "{{cia_id}}"

              # Rule 3 — POST to your service when stage updates
              webhooks:
                - url: "https://grc-service:8002/internal/hooks/stage-update/"
                  events: ["WorkflowStageUpdated"]
                  headers:
                    X-Internal-Token: "shared-secret-token"
```

### 12.3 Automation Rule Reference

#### `autoAdvance`

Automatically executes a stage action when a stage reaches a target status.

| Field | Type | Required | Description |
|---|---|---|---|
| `onStatuses` | `List[str]` | YES | Status values that trigger this rule (e.g., `["completed"]`) |
| `action` | `string` | YES | Action name to execute (must be defined in stage actions) |
| `targetStage` | `string` | NO | Key of the target stage to activate (defaults to next sequential stage) |
| `actorId` | `string` | NO | Actor to attribute the automated action to (defaults to `automation-bot`) |
| `comment` | `string` | NO | Comment appended to activity log |
| `metadataPatch` | `object` | NO | Key-value pairs to merge into stage metadata |

#### `escalationReminder`

Schedules a reminder delivery when a stage enters a blocked/pending state.

| Field | Type | Required | Description |
|---|---|---|---|
| `onStatuses` | `List[str]` | YES | Trigger statuses (e.g., `["blocked", "pending"]`) |
| `offsetMinutes` | `int` | YES | Minutes from trigger to reminder delivery |
| `channel` | `string` | YES | Delivery channel: `email`, `in_app`, `sms`, `webhook` |
| `title` | `string` | YES | Reminder title |
| `message` | `string` | NO | Reminder body |
| `targetUserId` | `string` | NO | User to remind (defaults to first assignee of stage) |
| `maxRetries` | `int` | NO | Max delivery retries (default: 3) |
| `recurrence` | `object` | NO | Recurrence configuration |
| `escalationPolicy` | `object` | NO | Escalation after N minutes to another user |

#### `webhooks`

HTTP POST to one or more URLs when specified events fire.

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | `string` | YES | Full URL to POST to |
| `events` | `List[str]` | YES | Event type filter (e.g., `["WorkflowStageUpdated"]`) |
| `headers` | `object` | NO | HTTP headers to include (e.g., auth token) |

**Webhook payload sent to your URL:**

```json
{
  "eventType": "WorkflowStageUpdated",
  "planId": "plan-uuid",
  "stageDefinitionKey": "cia_review",
  "newStatus": "completed",
  "actorId": "user-uuid",
  "action": "approve",
  "timestamp": "2026-03-07T10:30:00Z",
  "metadata": { ...stage metadata... }
}
```

### 12.4 Automation Polling Schedule

WO's Celery Beat runs `process_workflow_events` every **30 seconds**. The automation engine processes the `WorkflowStageUpdated` event from the `workflow-events` Kafka topic and evaluates all matching rules.

---

## Complete Integration Summary

This table shows every integration point WO offers and which step covers it:

| Integration | Method | Direction | Guide Section |
|---|---|---|---|
| **Register workflow template** | Kafka `workflow-templates` | Your service → WO | Step 2 |
| **Start a workflow plan** | HTTP POST `/plans/` | Your service → WO | Step 4 |
| **Embedded workflow console UI** | iframe → `/plans/{id}/console/` | Frontend → WO | Step 5 |
| **React to stage actions** | Kafka `workflow-events` consumer | WO → Your service | Step 8 |
| **React to workflow completion** | Kafka `workflow-events` consumer | WO → Your service | Step 8 |
| **Create / manage tasks** | HTTP REST `/tasks/` & `/standalone-tasks/` | Your service → WO | Step 9 |
| **Log time against tasks** | HTTP REST `/tasks/{id}/timesheets/` | Your service → WO | Step 9 |
| **Schedule reminders** | HTTP REST `/reminders/` | Your service → WO | Step 10 |
| **Dashboard analytics** | HTTP GET `/analytics/stats/` | Your service → WO | Step 11 |
| **Vetting / task reports** | HTTP GET `/reports/vetting/` (json/pdf/excel/csv) | Your service → WO | Step 11 |
| **Auto-advance stages** | Template YAML `metadata.automation.autoAdvance` | Config only | Step 12 |
| **Escalation reminders** | Template YAML `metadata.automation.escalationReminder` | Config only | Step 12 |
| **Webhooks on stage events** | Template YAML `metadata.automation.webhooks` | WO → Your service | Step 12 |
| **Register notification templates** | Kafka `notification-templates` | Your service → WO | See `WORK_ORCHESTRATION_NOTIFICATIONS.md` |
| **Send notifications via WO** | Kafka `notifications-{priority}` | Your service → WO | See `WORK_ORCHESTRATION_NOTIFICATIONS.md` |

---

*Last updated: March 2026*

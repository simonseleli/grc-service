# Frontend Core Patterns — Internal Audit Module (GRC)

> **Scope:** Global rules for all GRC/Internal Audit frontend pages in the Staff Portal.  
> **Does NOT cover:** Workflow-enabled Detail Pages — those follow [NEW_DETAIL_PAGE_REFERENCE.md](./NEW_DETAIL_PAGE_REFERENCE.md).  
> **Stack:** React 18, TypeScript, TanStack Query v5, Tailwind CSS, shadcn/ui, sonner, lucide-react.  
> **Verified against:** Actual source files in `frontend/apps/staff-portal/src/pages/grc/` and supporting hooks/services — March 2026.

---

## 0. Path Aliases

All imports in staff-portal use these Vite/TypeScript path aliases (defined in `vite.config.ts`):

| Alias | Resolves to |
|---|---|
| `@staff` | `apps/staff-portal/src/` |
| `@shared` | `packages/shared/src/` |
| `@ui` | `packages/shared/src/ui/` |

Examples:
```ts
import { useGRCPermissions } from '@staff/hooks/useGRCPermissions';
import { Button } from '@ui/button';
import { GenericListPage } from '@shared/components/GenericListPage';
import type { AuditPlan } from '@staff/types/grc';
```

---

## 0a. Important: Two Styles of List Pages

Two different layout conventions exist across GRC list pages. **New Internal Audit pages must follow Style B** (the canonical pattern confirmed in `AuditPlansPage.tsx`, `AuditableEntitiesPage.tsx`, `AuditMemosPage.tsx`).

| | Style A (old — avoid) | Style B (canonical — use this) |
|---|---|---|
| Wrapper | `<div className="space-y-6">` | `<div className="space-y-4">` |
| Title | `text-3xl font-bold tracking-tight` | `text-2xl font-bold` |
| Subtitle text | `<p className="text-muted-foreground">...` under h1 | Not used — icon + h1 only |
| Padding | No outer padding (relies on service shell) | No outer `p-4` on list pages — only on detail pages |
| Button guard | `<ProtectedComponent service="grc" resource="...">` | `{canManagePlans && <Button>}` (from `useGRCPermissions`) |

**`AuditUniversePage.tsx` and `ConfigurationManagementPage.tsx` use Style A — do not copy them.** Style B is consistent across all newer pages.

---

## 1. Pagination Patterns

### 1.1 State Management

Every list page owns its own pagination state locally:

```tsx
const [page, setPage] = useState(1);
const [pageSize, setPageSize] = useState(20);
```

- Default `pageSize` is **20**.
- `page` is 1-indexed. Never use 0-based page numbers in API calls.

### 1.2 Hook Signature

All per-entity list hooks follow this signature:

```tsx
const { data, isLoading, error } = useAuditPlans(page, pageSize, filters?);
//                                   useAuditUniverses(page, pageSize, filters?)
//                                   useAuditFindings(page, pageSize, filters?)
```

- `filters` is an optional `Record<string, unknown>` — serialised into the query key via `serializeFilters(filters)` from `@staff/hooks/grcKeys`.
- The hook passes `{ page, page_size: pageSize, ...filters }` to the service function via `GRCListParams`.

### 1.3 GRCListParams Type

```ts
// From @staff/types/grc
export interface GRCListParams {
  page?: number;
  page_size?: number;
  ordering?: string;
  search?: string;
  [key: string]: string | number | boolean | undefined;  // additional filters
}
```

### 1.4 Response Shape

All paginated list endpoints return `AuditCollectionResult<T>` (defined in `@staff/types/grc`):

```ts
export interface AuditCollectionResult<T> {
  results: T[];
  count: number;      // total matching records
  page: number;
  page_size: number;
  // NOTE: total_pages is NOT in the type definition.
  // Compute it manually: Math.ceil(count / page_size)
}
```

Access in component:
```tsx
const items = (data?.results ?? []).filter(item => item.is_active !== false);
const totalCount = data?.count ?? 0;
const totalPages = Math.ceil(totalCount / pageSize);
```

**Always filter soft-deleted items** after fetching: `.filter(item => item.is_active !== false)`. The backend may return `is_active: false` records in list responses.

### 1.5 GenericListPage Integration

Use `<GenericListPage>` from `@shared/components/GenericListPage` for standard entity list pages:

```tsx
import { GenericListPage } from '@shared/components/GenericListPage';

<GenericListPage
  title="Risk-Based Audit Plans"
  items={transformedItems}          // must match ListItem shape (id, title, status, createdAt, updatedAt)
  columns={columns}                 // Array<{ key: string; label: string; sortable?: boolean; render?: fn }>
  enableServerPagination
  currentPage={page}
  pageSize={pageSize}
  totalCount={data?.count ?? 0}
  onPageChange={setPage}
  onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
  pagination={{
    page,
    page_size: pageSize,
    total_pages: Math.ceil((data?.count ?? 0) / pageSize),
  }}
  onView={handleView}
  onEdit={canManagePlans ? handleEdit : undefined}
  onDelete={canManagePlans ? handleDelete : undefined}
  userRole={user?.role ?? 'staff'}  // required prop
  itemType="audit plan"             // used in empty state messages
  showCreateButton={false}          // use manual header button instead
/>
```

- Always reset `page` to `1` when `pageSize` changes or when a new search filter is applied.
- `pageSizeOptions` defaults are `[10, 20, 50, 100]` inside `GenericListPage`.
- Pass `onEdit={undefined}` and `onDelete={undefined}` (not just omit) when the user lacks permission — this hides those action buttons in the table rows.

### 1.6 Data Transform Pattern

Every list page defines a local `transform<Entity>ForList` function that maps the API type to the `ListItem` shape `GenericListPage` expects:

```tsx
function transformAuditPlanForList(plan: AuditPlan) {
  return {
    id: plan.id,
    title: plan.title,                                // required by ListItem
    reference_number: plan.reference_number,          // extra columns
    fiscalYear: plan.fiscal_year?.year_code || 'N/A',
    planType: plan.plan_type.charAt(0).toUpperCase() + plan.plan_type.slice(1),
    status: plan.status,                              // required by ListItem
    createdAt: new Date(plan.created_at).toLocaleDateString(),   // required by ListItem
    updatedAt: new Date(plan.updated_at || plan.created_at).toLocaleDateString(), // required
    _original: plan as any,  // keep reference for action handlers
  };
}

// In component:
const items = (data?.results ?? []).filter(item => item.is_active !== false);
const transformedItems = items.map(transformAuditPlanForList);
```

- `_original` stores the raw API object so action handlers can access full entity data via `items.find(e => e.id === id)`.
- Required `ListItem` keys: `id`, `title`, `status`, `createdAt`, `updatedAt`.

### 1.7 Loading States in List Pages

While `isLoading` is true, render a full-width dashed loading banner (verified against `AuditPlansPage.tsx`, `AuditableEntitiesPage.tsx`, `AuditUniversePage.tsx`):

```tsx
{isLoading && (
  <div className="mb-4 flex items-center rounded-md border border-dashed bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    Loading...
  </div>
)}
```

- Never block the entire page with a full-screen spinner for list pages.
- On Detail Pages, use a centered spinner (see §5.12 for the exact verified pattern).

---

## 2. API Calling Patterns

### 2.1 Architecture

```
Page/Component
  └── Custom hook (useAuditPlans, useCreateAuditPlan, ...)
        └── grcService.ts functions
              └── grcClient (Axios instance from @shared/api/gateway)
                    └── API Gateway → GRC Service
```

- **Never** call `grcService` or `axios` directly from a page component.
- **Never** put `useQuery` / `useMutation` inline in a page — always use a named hook from the hooks layer.

### 2.2 Service Layer — grcService.ts

All GRC API calls live in `frontend/apps/staff-portal/src/services/grcService.ts`.

- Import the `grcClient` Axios instance from `@shared/api/gateway`.
- Authentication: the Axios request interceptor automatically injects `Authorization: Bearer <accessToken>` from `localStorage`.
- FormData uploads: the interceptor removes the `Content-Type` header so the browser sets the correct multipart boundary.

**FIMS Envelope shape:**

```ts
type Envelope<T> = {
  success: boolean;
  data: T;
  meta?: {
    page?: number;
    page_size?: number;
    total?: number;
    total_pages?: number;
  };
};
```

**Unwrap helper — use for single-object endpoints:**

```ts
const unwrap = <T>(response: { data: any }): T => {
  const payload = response.data as Envelope<T> | T;
  if ((payload as Envelope<T>)?.success !== undefined && (payload as Envelope<T>).data !== undefined) {
    return (payload as Envelope<T>).data;
  }
  return payload as T;
};
```

**`mapPaginatedResponse` — use for list endpoints:**

```ts
const result = mapPaginatedResponse<AuditPlan>(response);
// Returns: AuditCollectionResult<AuditPlan>
```

### 2.3 React Query — Hook Conventions

**Global QueryClient defaults** (set in `App.tsx`):

```ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,         // 30 seconds
      gcTime: 5 * 60 * 1000,        // 5 minutes
      refetchOnWindowFocus: true,
      refetchOnMount: true,
      retry: 1,
    },
  },
});
```

**Per-entity override (applied in each hook):**

```ts
// List, detail, and lookup hooks (GRC entity data)
staleTime: 5 * 60 * 1000   // 5 minutes — audit data changes infrequently

// Config hooks (fiscal years, severities, etc.)
staleTime: 5 * 60 * 1000

// Workflow status/history hooks
staleTime: 30_000           // 30 seconds — workflow state needs freshness
retry: 1
```

**Lazy fetching (dialog-only queries):**

For dropdowns and selects that only appear inside a dialog, pass the dialog-open state as the `enabled` flag:

```tsx
// In the page component:
const [isGenerateOpen, setIsGenerateOpen] = useState(false);

// These hooks only fire when the dialog is actually open:
const { data: fiscalYearsData } = useFiscalYears(isGenerateOpen);
const { data: universesData } = useAuditUniversesLookup(isGenerateOpen);
```

All config hooks in `useGRCConfig.ts` accept an `enabled: boolean` parameter for this purpose.

### 2.4 Query Key Factory Pattern

Every entity file exports a query key factory:

```ts
export const auditPlanKeys = {
  all: ['audit-plans'] as const,
  lists: () => [...auditPlanKeys.all, 'list'] as const,
  list: (page: number, pageSize: number, filterKey: string) =>
    [...auditPlanKeys.lists(), page, pageSize, filterKey] as const,
  details: () => [...auditPlanKeys.all, 'detail'] as const,
  detail: (id: string) => [...auditPlanKeys.details(), id] as const,
};
```

- Use `serializeFilters(filters)` from `grcKeys.ts` to produce a stable `filterKey` string for the filter dimension.
- After a successful mutation, invalidate `auditPlanKeys.lists()` (not the full `all` key) to avoid busting detail caches unnecessarily.

### 2.5 Error Handling

**In mutations — extract error message consistently (verified pattern from all GRC hooks):**

```ts
onError: (error: any) => {
  toast.error('Failed to create audit plan', {
    description: error.response?.data?.error || error.message,
  });
}
```

- `error.response?.data?.error` — the GRC service wraps validation/business errors here.
- Fall back to `error.message` for network-level errors.
- Never surface raw stack traces or full response objects to the user.

**Config hooks use a slightly different error format (verified in `useGRCConfig.ts`):**

```ts
onError: (error: any) => {
  toast.error(error.response?.data?.error?.message || 'Failed to create fiscal year');
  // Note: config errors use error.response?.data?.error?.message (nested .message)
}
```

**In components — persistent error display:**

```tsx
{error && (
  <Alert variant="destructive">
    <AlertTitle>Unable to load audit plans</AlertTitle>
    <AlertDescription className="mb-3">
      {error instanceof Error ? error.message : 'Failed to load data'}
    </AlertDescription>
  </Alert>
)}
```

### 2.6 Mutation Pattern

```ts
const createMutation = useCreateAuditPlan();
const deleteMutation = useDeleteAuditPlan();

// Create — close dialog on success:
createmutation.mutate(formData, {
  onSuccess: () => setIsCreateOpen(false),  // close dialog
});

// After create, optionally navigate to the new record's detail page:
createmutation.mutate(formData, {
  onSuccess: (newPlan) => {
    navigate(`/service/grc/audit-plans/${newPlan.id}`);
  },
});

// Delete — close confirm dialog on either success or error:
deleteMutation.mutate(deletingItem.id, {
  onSettled: () => setDeletingItem(null),  // always close
});

// Update — close edit dialog on success:
updateMutation.mutate({ id: editingItem.id, data: formData }, {
  onSuccess: () => setEditingItem(null),
});
```

**Rules:**
- `onSuccess` toast is always fired **inside the hook** (not in the component).
- The component's `.mutate(data, { onSuccess })` callback handles **only UI side-effects** (close dialogs, reset form state, navigate).
- Use `onSettled` (not `onSuccess`) for delete confirmations — it fires on both success and error, ensuring the dialog always closes.
- Disable submit/action buttons while `isPending`:

```tsx
<Button disabled={createMutation.isPending}>
  {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
  Save
</Button>
```

---

## 3. RBAC Patterns

### 3.1 Permission System

Permissions are read from the JWT access token (`permissions_flat` claim). No API call is needed.

- **Superuser**: `permissions_flat: ['*']` — all permissions granted.
- **Regular users**: array of specific permission codes.

**Permission code format:** `grc:<resource>:<action>`  
Examples: `grc:audit_plan:manage`, `grc:audit_plan:approve`, `grc:audit_universe:view`

### 3.2 useGRCPermissions Hook

```tsx
import { useGRCPermissions } from '@staff/hooks/useGRCPermissions';

const {
  hasPermission,
  hasAnyPermission,
  canManagePlans,
  canApprovePlans,
  canViewReports,
  canManageEngagements,
  // ...
} = useGRCPermissions();
```

- Call this hook **once per page** at the top of the component, destructure what you need.
- `hasPermission('grc:audit_plan:manage')` — direct code check.
- `hasAnyPermission(['grc:audit_plan:manage', 'grc:audit_plan:approve'])` — OR check.

### 3.3 Composite Role Logic

Derive functional role booleans from raw permission booleans:

```ts
const { canManagePlans, canApprovePlans } = useGRCPermissions();

// SRS §1.8.1: IA drafts (Req 2), CIA reviews/improves (Req 3, 7)
const canDraftPlans   = canManagePlans && !canApprovePlans;  // IA only
const canImprovePlans = canManagePlans && canApprovePlans;   // CIA only (Step 8)
```

Do this at the page level — do not scatter conditional permission logic deep in child components.

### 3.3a Full Convenience Boolean Reference

All booleans returned by `useGRCPermissions()` (verified from source):

```ts
// Audit Universe
canViewAuditUniverse, canManageAuditUniverse, canApproveAuditUniverse
// Risk Assessment
canConductRiskAssessment, canReviewRiskAssessment
// Audit Plan
canViewPlans, canManagePlans, canApprovePlans
// Engagement
canManageEngagements
// Working Papers
canManageWorkingPapers, canReviewWorkingPapers
// Findings
canManageFindings, canRespondToFindings
// Reports
canViewReports, canApproveReports
// Monitoring
canUpdateMonitoring
// Dashboard
canViewDashboard
// Config
canManageConfig, canManageFiscalYears, canManageSeverities, canManageFindingTypes, canManageRiskRatings
// Audit Memo
canViewMemos, canManageMemos, canApproveMemos
// Declaration of Independence
canManageDeclarations, canSignDeclarations
// Preliminary Survey
canManageSurveys
// RCM
canManageRCM, canApproveRCM
// Audit Program
canManageAuditPrograms
// Engagement Notification
canManageEngagementNotifications, canApproveEngagementNotifications
// Quarterly Report
canManageQuarterlyReports, canApproveQuarterlyReports
// Meetings
canManageMeetings, canViewMeetings
```

### 3.4 Two Approaches to Permission-Gated Rendering

**Approach A — Inline conditional (preferred for new pages):**

Used in `AuditPlansPage.tsx`, `AuditableEntitiesPage.tsx`, and all newer GRC pages:

```tsx
const { canManagePlans, canApprovePlans } = useGRCPermissions();

{canManagePlans && (
  <Button onClick={() => setIsCreateOpen(true)}>
    <Plus className="mr-2 h-4 w-4" />
    Create Plan
  </Button>
)}
```

**Approach B — `<ProtectedComponent>` wrapper (legacy — only in `AuditUniversePage`):**

```tsx
import { ProtectedComponent } from '@staff/components/ProtectedComponent';

<ProtectedComponent service="grc" resource="audit_universe" action="manage">
  <Button onClick={() => setIsCreateOpen(true)}>Create Universe</Button>
</ProtectedComponent>
```

`ProtectedComponent` reads from `usePermissions()` (not `useGRCPermissions()`). Its props are `service`, `resource`, `action`, `fallback?`, `showAccessDenied?`.

**Use Approach A (inline conditional from `useGRCPermissions`) for all new pages.**

**Rules for both approaches:**
- **Never** render a button and then disable it based on permission — hide it entirely.
- A button may be disabled for business/state reasons (wrong status, pending mutation), but visibility is always permission-driven.

### 3.5 Permission-Gated Business Logic

Status-gated edit (verified in `AuditPlansPage.tsx`):

```tsx
const handleEdit = (id: string) => {
  const item = items.find((p) => p.id === id);
  if (!item) return;
  // Gate on both permission AND entity status:
  const canEdit = (canDraftPlans && item.status === 'draft')  // IA edits drafts
               || (canImprovePlans && item.status !== 'draft'); // CIA edits post-return
  if (canEdit) setEditingItem(item);
};
```

For table column actions, pass `onEdit`/`onDelete` as `undefined` when not permitted:

```tsx
onEdit={canManagePlans ? handleEdit : undefined}
onDelete={canManagePlans ? handleDelete : undefined}
```

For submit triggers, gate on BOTH permission AND status:

```tsx
const isDraft = item.status === 'draft';
const workflowPlanId = workflowStatus?.workflow_plan_id;

{canDraftPlans && isDraft && !workflowPlanId && (
  <Button onClick={handleSubmit} disabled={submitMutation.isPending}>
    Submit for Approval
  </Button>
)}
```

### 3.6 Route-Level Protection

Service-level access is enforced by `<ServiceProtectedRoute serviceKey="grc" ...>` in `App.tsx`.  
Do not re-implement service-level guards inside page components — rely on route protection.

---

## 4. Notification Patterns

### 4.1 Toast Library

Use **`sonner`** exclusively:

```ts
import { toast } from 'sonner';
```

Do NOT use shadcn `useToast` / `@ui/use-toast` in GRC pages or hooks.  
Both `<Toaster />` (shadcn) and `<Sonner />` (sonner) are mounted in `App.tsx` — only sonner is used for GRC.

### 4.2 Success Notifications

```ts
// Simple — no description needed
toast.success('Audit universe deleted successfully');

// With description
toast.success('Audit universe created successfully', {
  description: `Fiscal Year: ${newUniverse.fiscal_year?.year_code}`,
});

// Workflow submission
toast.success('Audit plan submitted for approval via Work Orchestration');
```

### 4.3 Error Notifications

```ts
// Mutation failure
toast.error('Failed to create audit plan', {
  description: error.response?.data?.error || error.message,
});

// Business rule violation (soft — not a network error)
toast.error('Cannot delete this audit plan', {
  description: 'Plans with active engagements cannot be deleted.',
});
```

### 4.4 Warning Notifications

Use `toast.warning` for soft guards where the action is not proceeding but no crash has occurred:

```ts
toast.warning('No fiscal year selected', {
  description: 'Please select a fiscal year before generating a plan.',
});
```

### 4.5 Where Toasts Are Fired

| Location | Rule |
|---|---|
| Mutation hooks (`onSuccess`, `onError`) | **Always** — this is the canonical place |
| Page components | Only for local UX events not tied to a mutation (e.g., business-rule block before calling mutate, copy to clipboard) |
| Service functions | **Never** — services are UI-agnostic |

Example of a page-level toast (business guard, not a mutation failure — verified in `AuditPlansPage.tsx`):

```tsx
const handleDelete = (id: string) => {
  const item = items.find((p) => p.id === id);
  if (!item) return;
  if (item.status === 'active' || item.status === 'completed') {
    toast.error('Cannot delete this audit plan', {
      description: `Plans in '${item.status}' status have linked engagements and cannot be deleted.`,
    });
    return;  // Do NOT call the mutation at all
  }
  setDeletingItem(item);  // Proceed to confirm dialog
};
```

### 4.6 Alert Components (In-Page)

For persistent errors (e.g., data failed to load), use the shadcn `<Alert>` component inline:

```tsx
import { Alert, AlertDescription, AlertTitle } from '@ui/alert';

{error && (
  <Alert variant="destructive">
    <AlertTitle>Error loading data</AlertTitle>
    <AlertDescription>{(error as any).message}</AlertDescription>
  </Alert>
)}
```

- Use `<Alert>` for errors that should persist until the user takes action or refreshes.
- Use `toast` for transient feedback on user actions (create, update, delete, submit).

### 4.7 Confirm Dialogs (Destructive Actions)

Use `<AlertDialog>` from `@ui/alert-dialog` for irreversible actions (delete). Full verified pattern:

```tsx
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@ui/alert-dialog';

<AlertDialog open={!!deletingItem} onOpenChange={(open) => !open && setDeletingItem(null)}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Delete Audit Plan?</AlertDialogTitle>
      <AlertDialogDescription>
        This action cannot be undone.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
      <AlertDialogAction
        onClick={confirmDelete}
        disabled={deleteMutation.isPending}
        className="bg-destructive hover:bg-destructive/90"
      >
        {deleteMutation.isPending ? (
          <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Deleting...</>
        ) : (
          'Delete'
        )}
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

`confirmDelete` calls `deleteMutation.mutate(id, { onSettled: () => setDeletingItem(null) })`.

---

## 5. Layout System

### 5.1 Service Shell

All GRC pages render inside `<ServiceLayout serviceType="grc" ...>` defined in `App.tsx`.  
This provides the sidebar navigation and top header bar automatically — pages must NOT add their own app header or sidebar.

Route definition pattern:

```tsx
<Route
  path="/service/grc"
  element={
    <ServiceProtectedRoute serviceKey="grc" serviceName="Governance, Risk & Compliance (GRC)">
      <ServiceLayout serviceType="grc" serviceName="Governance, Risk & Compliance (GRC)" servicePath="grc" />
    </ServiceProtectedRoute>
  }
>
  <Route index element={<GRCDashboard />} />
  <Route path="audit-plans" element={<AuditPlansPage />} />
  {/* ... */}
</Route>
```

### 5.2 Page Wrapper — List Pages

**Canonical list page wrapper** (verified in `AuditPlansPage.tsx`, `AuditableEntitiesPage.tsx`):

```tsx
<>
  <div className="space-y-4">
    {/* header row */}
    {/* optional info Alert */}
    {/* error Alert */}
    {/* isLoading banner */}
    {/* GenericListPage or table */}
  </div>

  {/* dialogs and confirm modals outside the div */}
  <CreateAuditPlanDialog ... />
  <AlertDialog ... />
</>
```

- List pages: **`space-y-4`**, no outer `p-4`.
- All dialogs and `<AlertDialog>` are siblings of the main `<div>`, rendered inside a fragment `<>...</>`.

### 5.2a Page Wrapper — Detail Pages

**Canonical detail page wrapper** (verified in `AuditPlanDetailPage.tsx`, `WorkingPaperDetailPage.tsx`, `EngagementDetailPage.tsx`):

```tsx
<div className="space-y-4 p-4">
  {/* header row */}
  {/* data cards */}
  {/* EmbeddedWorkflowConsole at bottom */}
</div>
```

- Detail pages: **`space-y-4 p-4`** — 16px padding all sides.
- **Do NOT use** `p-6 space-y-6` on any GRC page.
- `RCMDetailPage.tsx` uses `space-y-6 p-6` — it is **not** the canonical pattern.

### 5.3 Page Header — List Pages

Verified canonical pattern from `AuditPlansPage.tsx` and `AuditableEntitiesPage.tsx`:

```tsx
<div className="flex items-center justify-between">
  <div className="flex items-center gap-2">
    <ClipboardList className="h-6 w-6 text-primary" />
    <h1 className="text-2xl font-bold">Risk-Based Audit Plans</h1>
  </div>
  <div className="flex items-center gap-2">
    {canManagePlans && (
      <Button onClick={() => setIsCreateOpen(true)}>
        <Plus className="mr-2 h-4 w-4" />
        Create Plan
      </Button>
    )}
    {/* Multiple actions: extra buttons inline here */}
    {canManagePlans && (
      <Button variant="outline" onClick={() => setIsGenerateOpen(true)}>
        <Sparkles className="mr-2 h-4 w-4" />
        Generate Draft
      </Button>
    )}
  </div>
</div>
```

- Icon: `h-6 w-6 text-primary` always paired with the page heading.
- Action buttons: right-aligned inside `flex items-center gap-2`.
- Title: `text-2xl font-bold` — no icon inside the `<h1>` itself.
- Multiple action buttons stack horizontally in the right container.

### 5.4 Page Header — Detail Pages

Verified canonical pattern from `AuditPlanDetailPage.tsx` and `WorkingPaperDetailPage.tsx`:

```tsx
<div className="flex items-center gap-4">
  {/* Back button — icon ChevronLeft (NOT ArrowLeft) */}
  <Button variant="ghost" size="icon" onClick={handleBack} aria-label="Back">
    <ChevronLeft className="h-4 w-4" />
  </Button>

  {/* Title block — fills remaining space */}
  <div className="flex-1">
    <h1 className="text-2xl font-semibold">{plan.title}</h1>
    {/* Optional subtitle — reference number, fiscal year, etc. */}
    <p className="text-sm text-muted-foreground">
      Ref: <span className="font-mono">{plan.reference_number}</span>
    </p>
  </div>

  {/* Right side: CTAs then status badge */}
  {canDraftPlans && isDraft && !workflowPlanId && (
    <Button onClick={handleSubmit} disabled={submitMutation.isPending}>
      {submitMutation.isPending
        ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        : <Send className="mr-2 h-4 w-4" />}
      Submit for Approval
    </Button>
  )}
  <Badge className={statusColors[plan.status] ?? 'bg-gray-100 text-gray-800'}>
    {statusLabel}
  </Badge>
</div>
```

**Critical verified details:**
- Back icon is `<ChevronLeft>` (from `lucide-react`), NOT `<ArrowLeft>`.
- Always include `aria-label="Back"` on the icon button.
- Title div uses `flex-1` — it pushes CTAs and badge to the right.
- Status badge uses `<Badge className={...}>` with custom Tailwind classes.
- `handleBack` navigates to the list URL (not `navigate(-1}`): `navigate('/service/grc/audit-plans')`.

### 5.5 Cards

```tsx
<Card>
  <CardHeader className="pb-2">
    <CardTitle className="text-base flex items-center gap-2">
      <FileText className="h-4 w-4 text-muted-foreground" />
      Plan Details
    </CardTitle>
  </CardHeader>
  <CardContent>
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <p className="text-sm text-muted-foreground">Fiscal Year</p>
        <p className="font-medium">{plan.fiscal_year?.year_code ?? '—'}</p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">Status</p>
        <p className="font-medium">{statusLabel}</p>
      </div>
    </div>
  </CardContent>
</Card>
```

Rules:
- `<CardHeader className="pb-2">` — reduce bottom padding.
- `<CardTitle className="text-base flex items-center gap-2">` — small title with lucide icon.
- Do NOT use `<CardDescription>`.
- Do NOT use `<Separator>` inside cards — use separate cards per logical section instead.
- One card per logical section (Details, Review Info, People, Description, etc.).
- If a section has no data, do **not** render the card at all (conditional rendering).

### 5.6 Grid Layouts

| Use Case | Class |
|---|---|
| Standard 2-col detail grid | `grid gap-4 md:grid-cols-2` |
| People/roles 4-col grid | `grid gap-4 lg:grid-cols-4` |
| Single column | no grid — default block flow |

### 5.7 Status Badges

**Verified pattern:** Use the shadcn `<Badge>` component with a `className` override — do NOT use `variant` prop:

```tsx
import { Badge } from '@ui/badge';

<Badge className={statusColors[item.status] ?? 'bg-gray-100 text-gray-800'}>
  {statusLabel}
</Badge>
```

Do NOT use `<Badge variant="default">` / `<Badge variant="outline">` for status — those don't map to audit statuses.

**Standard status colors (verified across all GRC entities):**

```ts
const statusColors: Record<string, string> = {
  // Universal
  draft:             'bg-gray-100 text-gray-800',
  approved:          'bg-green-100 text-green-800',
  rejected:          'bg-red-100 text-red-800',
  archived:          'bg-gray-100 text-gray-500',
  // Audit Universe
  under_review:      'bg-yellow-100 text-yellow-800',
  // Audit Plan
  management_review: 'bg-yellow-100 text-yellow-800',
  committee_review:  'bg-blue-100 text-blue-800',
  implementation:    'bg-purple-100 text-purple-800',
  // Working Paper
  pending:           'bg-yellow-100 text-yellow-800',
  // Findings
  discussed:         'bg-blue-100 text-blue-800',
  final:             'bg-green-100 text-green-800',
  // General
  active:            'bg-green-100 text-green-800',
  completed:         'bg-purple-100 text-purple-800',
  submitted:         'bg-blue-100 text-blue-800',
};
```

Fallback: `'bg-gray-100 text-gray-800'` for any unrecognised status.

**Compute `statusLabel` — verified pattern from `AuditPlanDetailPage.tsx`:**

```ts
// Detail pages use this exact form:
const statusLabel =
  (plan.status?.charAt(0).toUpperCase() ?? '') +
  (plan.status?.slice(1).replace(/_/g, ' ') ?? 'Draft');
// 'management_review' → 'Management review'

// Alternative (Title Case all words):
const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
// 'management_review' → 'Management Review'
```

Both forms are in use. Either is acceptable, but be consistent within a page.

### 5.8 Typography

| Element | Class | Notes |
|---|---|---|
| Page title (list) | `text-2xl font-bold` | Canonical (Style B) |
| Page title (detail) | `text-2xl font-semibold` | Inside `<div className="flex-1">` |
| Page subtitle (detail) | `text-sm text-muted-foreground` | Under h1 in the flex-1 div |
| Reference/code inline | `font-mono` | Inside subtitle `<span>` |
| Card section title | `text-base` | Inside `<CardTitle>` component |
| Field label | `text-sm text-muted-foreground` | Above the value |
| Field value | `font-medium` | Below the label |
| Helper / secondary text | `text-sm text-muted-foreground` | General secondary |

### 5.9 Icons

Source: `lucide-react` exclusively.

| Context | Icon | Size |
|---|---|---|
| Page header | Entity-specific (e.g., `ClipboardList`, `Globe`, `Database`) | `h-6 w-6 text-primary` |
| Card section title | Section-specific (e.g., `FileText`, `Users`, `AlignLeft`) | `h-4 w-4 text-muted-foreground` |
| Button internal (with text) | Action-specific | `h-4 w-4 mr-2` |
| Back button (icon-only) | `ChevronLeft` (NOT ArrowLeft) | `h-4 w-4` (no margin) |
| Submit/send action | `Send` | `h-4 w-4 mr-2` |
| Loading spinner | `Loader2` | `h-4 w-4 animate-spin` (large: `h-6 w-6`) |
| Error state | `AlertCircle` | `h-4 w-4` |
| Info alert | Entity icon | `h-4 w-4` |

### 5.10 Buttons

| Variant | Use |
|---|---|
| `default` (solid) | Primary action (Create, Submit, Save) |
| `outline` | Secondary action (Edit, Export) |
| `ghost` | Tertiary / icon-only (Back, Close) |
| `destructive` | Inside confirm dialogs only |

- Icon + text buttons: `<Icon className="mr-2 h-4 w-4" />` before the text.
- Icon-only buttons: `size="icon"` prop, no text, no margin on icon.
- Disable buttons (not hide) when a pending mutation is in progress.

### 5.11 Tables

GenericListPage renders its own table internally. For custom tables (e.g., sub-tables inside detail pages):

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table';

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Code</TableHead>
      <TableHead>Name</TableHead>
      <TableHead>Status</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {items.map((item) => (
      <TableRow key={item.id}>
        <TableCell className="font-medium">{item.code}</TableCell>
        <TableCell>{item.name}</TableCell>
        <TableCell>
          <Badge className={getStatusColor(item.status)}>{item.status}</Badge>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

- First identifying column: `className="font-medium"`.
- All other data columns: no extra className unless needed.
- Status column: inline `<Badge className={getStatusColor(status)}>` (local function or map).

### 5.12 Detail Page Loading and Error States

Verified pattern from `AuditPlanDetailPage.tsx` and `WorkingPaperDetailPage.tsx`:

```tsx
// Loading: centered spinner, minimum height
if (isLoading) {
  return (
    <div className="flex items-center justify-center min-h-[300px]">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}

// Error / not found:
if (isError || !data) {
  return (
    <div className="p-4">
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load. It may not exist or you may not have access.
        </AlertDescription>
      </Alert>
    </div>
  );
}

// Normal render:
return (
  <div className="space-y-4 p-4">
    {/* ... */}
  </div>
);
```

Do these checks in that order — loading first, then error, then normal render.

---

## 6. Workflow UI Rules (General)

> Detail pages for workflow-enabled entities have their own canonical file.  
> This section covers list pages and non-detail UI only.

### 6.1 Status Display on List Pages

- List pages show the current workflow stage as a status badge (§5.7) in a `Status` column.
- The badge reflects `item.status` — the backend normalises workflow stages into a status string on every entity.
- Do not call `useGRCWorkflowStatus` from list-page components — only detail pages fetch workflow status.

### 6.2 Submit / Trigger Workflow Buttons on List Pages

Some entities allow workflow submission directly from the list view (e.g., Audit Universes submit button):

```tsx
{canManageAuditUniverse && item.status === 'draft' && (
  <Button
    size="sm"
    variant="outline"
    onClick={() => submitMutation.mutate(item.id)}
    disabled={submitMutation.isPending}
  >
    Submit for Approval
  </Button>
)}
```

Rules:
- Only show submission triggers to users with `manage` permission — not `approve`.
- Only show when the item is in a submittable status (always gate on `item.status`).
- Use `size="sm"` for inline table-row buttons.

### 6.3 Workflow Status Hook Usage

Only used on detail pages and in `EmbeddedWorkflowConsole`. Never call from list pages.

```ts
// Detail page only:
const { data: workflowStatus } = useGRCWorkflowStatus('audit-plan', planId);
const { data: workflowHistory } = useGRCWorkflowHistory('audit-plan', planId);
```

Available entity types for `useGRCWorkflowStatus` / `useGRCWorkflowHistory`:
- `'audit-universe'`
- `'audit-plan'`
- `'audit-engagement'`
- `'working-paper'`
- `'audit-program'`

### 6.4 EmbeddedWorkflowConsole Placement

On workflow-enabled Detail Pages:
- Always placed at the **bottom** of the page, after all data cards.
- Full-width — NOT in a side column or inside a card.
- Props are never modified when restructuring a detail page layout.

On pages that are NOT detail pages (list pages, configuration pages):
- Do not render `EmbeddedWorkflowConsole`.

### 6.5 Inline vs Non-Inline Patterns

| Pattern | When to Use |
|---|---|
| Inline edit (row-level) | **Never** in GRC — always use a Dialog |
| Dialog | All create and edit forms |
| Full-page form | Not used in GRC — all forms are dialogs |
| Confirmation AlertDialog | All destructive actions (delete, reject, archive) |
| Detail Page navigation | `useNavigate()` to `/service/grc/<entity>/:id` for viewing full detail |

**Dialog component pattern (verified from all GRC Create*Dialog components):**

```tsx
<CreateAuditPlanDialog
  open={isCreateOpen}
  onOpenChange={setIsCreateOpen}
  onSuccess={(newPlan) => {
    setIsCreateOpen(false);
    navigate(`/service/grc/audit-plans/${newPlan.id}`);
  }}
  isSubmitting={createMutation.isPending}
/>

{/* Edit dialog: */}
{editingItem && (
  <CreateAuditPlanDialog
    open={!!editingItem}
    onOpenChange={(open) => !open && setEditingItem(null)}
    mode="edit"
    plan={editingItem}
    onSuccess={() => setEditingItem(null)}
    isSubmitting={updateMutation.isPending}
  />
)}
```

**Standard Dialog props (in all grc Create*Dialog components):**

| Prop | Type | Purpose |
|---|---|---|
| `open` | `boolean` | Controls visibility |
| `onOpenChange` | `(open: boolean) => void` | Close handler |
| `mode` | `'create' \| 'edit'` | Form mode |
| `onSuccess` | `(result?) => void` | Called after mutation succeeds |
| `isSubmitting?` | `boolean` | Disables submit button |

- Dialog open state is owned by the page: `const [isCreateOpen, setIsCreateOpen] = useState(false)`.
- `isSubmitting={mutation.isPending}` disables the submit button inside the dialog form.

### 6.6 Workflow-Related Page States

On detail pages only, handle these states in order:

```tsx
if (isLoading) {
  return (
    <div className="flex items-center justify-center min-h-[300px]">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}

if (isError || !data) {
  return (
    <div className="p-4">
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load. It may not exist or you may not have access.
        </AlertDescription>
      </Alert>
    </div>
  );
}
```

Never render partial data — wait for the full record before rendering the detail layout.

---

## 7. Navigation Patterns

### 7.1 List → Detail

```tsx
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

// View handler on list page:
const handleView = (id: string) => {
  navigate(`/service/grc/audit-plans/${id}`);
};
```

### 7.2 Detail → List (Back)

```tsx
// Navigate to specific list route — NOT navigate(-1)
const handleBack = () => {
  navigate('/service/grc/audit-plans');
};
```

Do NOT use `navigate(-1)` on detail pages — the back destination should be deterministic.

### 7.3 After Create

```tsx
// Option A: Navigate to new record immediately
createmutation.mutate(formData, {
  onSuccess: (newPlan) => {
    navigate(`/service/grc/audit-plans/${newPlan.id}`);
  },
});

// Option B: Stay on list, close dialog (most entities)
createmutation.mutate(formData, {
  onSuccess: () => setIsCreateOpen(false),
});
```

Audit Plans currently use Option A (navigate to new detail). Most other entities use Option B.

### 7.4 Established GRC Route Paths

| Entity | List Route | Detail Route |
|---|---|---|
| Audit Universe | `/service/grc/audit-universe` | `/service/grc/audit-universe/:id` |
| Audit Plan | `/service/grc/audit-plans` | `/service/grc/audit-plans/:id` |
| Engagement | `/service/grc/engagements` | `/service/grc/engagements/:id` |
| Working Paper | _(via engagement detail)_ | _(via engagement detail)_ |
| RCM | `/service/grc/rcm` | `/service/grc/rcm/:id` |

---

## 8. Config and Lookup Hooks

All config hooks are in `@staff/hooks/useGRCConfig`. Import individually:

```ts
import { useFiscalYears, useAuditSeverities, useRiskRatings } from '@staff/hooks/useGRCConfig';
import { useGRCUsersByRole } from '@staff/hooks/useGRCConfig';
```

All accept an `enabled: boolean` parameter — pass `isDialogOpen` to lazy-load:

```tsx
const { data: fiscalYearsData } = useFiscalYears(isCreateOpen);
const auditors = await useGRCUsersByRole('AUDIT_TEAM_MEMBER', isCreateOpen);
```

Access results: `fiscalYearsData?.results ?? []`.

---

## 9. Info Alerts on List Pages

Some list pages show a blue/default info `<Alert>` with contextual guidance. This is optional but follow the pattern when used:

```tsx
<Alert>  {/* no variant — uses default border style */}
  <Globe className="h-4 w-4" />
  <AlertDescription>
    Contextual guidance about this entity and its purpose.
  </AlertDescription>
</Alert>
```

Place immediately after the header row, before the error Alert and loading banner.

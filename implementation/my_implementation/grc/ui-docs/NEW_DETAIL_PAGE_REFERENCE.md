# UI Documentation — Audit Universe Detail Page

---

> ## ⚠️ REFERENCE UI PATTERN — READ THIS BEFORE MODIFYING ANY DETAIL PAGE
>
> This file documents the **canonical UI design** for all GRC detail pages in the Staff Portal.
> When converting another detail page to match this design, follow these rules strictly.
>
> ### ✅ WHAT TO CHANGE (UI only)
> - Page wrapper: use `<div className="space-y-4 p-4">` — NOT `p-6 space-y-6`
> - Header row: use `flex items-center gap-4` with a ghost **icon-only** back button (`size="icon"`), NOT a stacked layout with text back button above the title
> - Title: `text-2xl font-semibold` — NOT `font-bold`, no icon inside the `<h1>`
> - Status badge: use custom Tailwind classes (`bg-gray-100 text-gray-800`, etc.) — NOT shadcn `variant=` props
> - Status label text: Title-Case with underscores replaced by spaces (e.g. `under_review` → `Under Review`)
> - Cards: one card per logical section (Details, Review Info, Resource, Description, etc.) — NOT one big card with `<Separator>` dividers inside
> - Card header: `<CardHeader className="pb-2">` + `<CardTitle className="text-base flex items-center gap-2">` with a small icon — NOT `CardDescription` subtitle
> - Card content grids: use `grid gap-4 md:grid-cols-2` for details, `lg:grid-cols-4` for people fields
> - Label/value pairs: `<p className="text-sm text-muted-foreground">` label, `<p className="font-medium">` value
> - Conditional cards: if a section has no data, do NOT render the card at all
> - Workflow console: always at the **bottom**, full-width — NOT in a side column
> - Remove `<Separator>` dividers, `<CardDescription>`, sidebar grid layouts, and inline workflow Plan ID cards
>
> ### ❌ WHAT NOT TO CHANGE
> - All hooks (`useQuery`, `useMutation`, custom hooks like `useGRCPermissions`, `useGRCWorkflowStatus`)
> - All permission logic (`canDraftPlans`, `canImprovePlans`, `<ProtectedComponent>`, etc.)
> - All conditional rendering logic (which button is shown, to whom, under what status)
> - All data fields displayed — just move them into the new card structure
> - `handleSubmit`, `handleBack`, and any other event handlers
> - `EmbeddedWorkflowConsole` props — all props stay exactly the same
> - Error and loading states — keep the same logic, just use `p-4` instead of `p-6`
>
> ### 🔁 CONVERSION CHECKLIST
> 1. Replace imports: remove `Separator`, `CardDescription`. Add lucide icons for each card section.
> 2. Replace `statusColors` with the Tailwind-class map (see Section 3 below).
> 3. Add `statusLabel` computation string (Title-Case + replace underscores).
> 4. Rewrite the header row using the `flex items-center gap-4` pattern.
> 5. Split the single details card into separate cards per section.
> 6. Move `EmbeddedWorkflowConsole` to the bottom as a standalone full-width block.
> 7. Do not add any new logic — only restructure the JSX.


**THE REFERENCE FILES ARE:**
1. frontend/apps/staff-portal/src/pages/grc/AuditPlanDetailPage.tsx
2. frontend/apps/staff-portal/src/pages/grc/AuditUniverseDetailPage.tsx



---

**File:** `frontend/apps/staff-portal/src/pages/grc/AuditUniverseDetailPage.tsx`  
**Route:** `/service/grc/audit-universe/:universeId`

---

## 1. Overall Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← (back)   Audit Universe: 2025/2026         [Submit…] [Badge]    │  ← Header row
├─────────────────────────────────────────────────────────────────────┤
│  Card: Universe Details (2-column grid)                             │
├─────────────────────────────────────────────────────────────────────┤
│  Card: Review Information (conditional — only if reviewed/approved) │
├─────────────────────────────────────────────────────────────────────┤
│  Card: Description (conditional — only if description exists)       │
├─────────────────────────────────────────────────────────────────────┤
│  Section: Auditable Entities (table with Add/Edit/Delete)           │
├─────────────────────────────────────────────────────────────────────┤
│  Card: Approval Workflow Console (iframe or empty state)            │
└─────────────────────────────────────────────────────────────────────┘
```

- **Wrapper:** `<div className="space-y-4 p-4">` — 16px padding all sides, 16px vertical gap between sections.
- **Responsive:** Cards use `md:grid-cols-2` (2 columns on ≥ 768px, 1 column below).

---

## 2. Loading & Error States

### Loading State
- Centered spinner in the middle of the viewport (`min-h-[300px]`).
- `<Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />`
- No text label — spinner only.

### Error State
- Full-width destructive `<Alert>` with `AlertCircle` icon + message:  
  _"Failed to load audit universe. It may not exist or you may not have access."_
- Below the alert: an outline `<Button>` — `← Go Back` (navigates back in history).

---

## 3. Header Row

```
[←]  Audit Universe: 2025/2026          [Submit for Approval]  [Status Badge]
      View audit universe details
```

| Element | Detail |
|---|---|
| Back button | `variant="ghost" size="icon"`, `ChevronLeft` icon only, `aria-label="Back"` |
| Title `<h1>` | `text-2xl font-semibold` — "Audit Universe: {fiscal_year.year_code}" |
| Subtitle `<p>` | `text-sm text-muted-foreground` — "View audit universe details" |
| Submit button | Solid (default variant), `Send` icon + "Submit for Approval" text. **Only shown** when `status === 'draft'` AND no workflow has been started AND user has `grc:audit_universe:manage` permission (via `<ProtectedComponent>`). While pending: spinner replaces Send icon. |
| Status Badge | Custom Tailwind classes (see Status Colors). Always visible. |

### Status Badge Colors
| Status | Classes |
|---|---|
| `draft` | `bg-gray-100 text-gray-800` |
| `under_review` | `bg-yellow-100 text-yellow-800` |
| `approved` | `bg-green-100 text-green-800` |
| `archived` | `bg-gray-100 text-gray-500` |

Status label text is Title-Cased with underscores replaced by spaces (`under_review` → `Under Review`).

---

## 4. Universe Details Card

- **Component:** `<Card>` with `<CardHeader pb-2>` + `<CardContent>`
- **Card Title:** `text-base flex items-center gap-2` (explicit className) + `FileText` icon (h-4 w-4) — "Universe Details". The `font-semibold` is applied automatically by `CardTitle`'s own default class (`text-2xl font-semibold`); passing `text-base` only overrides the size, not the weight.
- **Content Layout:** `grid gap-4 md:grid-cols-2` (left column + right column)

### Left Column
| Label | Value style |
|---|---|
| Fiscal Year | `text-sm text-muted-foreground` label, `font-medium` value |
| Status | `text-sm text-muted-foreground` label, `<Badge>` with status color classes |
| Created | `text-sm text-muted-foreground` label, plain `<p>` — formatted as "March 14, 2026" |

### Right Column
| Label | Value style |
|---|---|
| Last Updated | Same pattern as Created; falls back to `created_at` if `updated_at` is null |

**Date format:** `en-US` locale — `{ year: 'numeric', month: 'long', day: 'numeric' }` → "March 14, 2026". Missing dates render as `—`.

---

## 5. Review Information Card

**Conditional:** Only rendered when `universe.reviewed_by` OR `universe.approved_by` is set.

- **Card Title:** `text-base` + `Users` icon — "Review Information"
- **Content Layout:** `grid gap-4 md:grid-cols-2 lg:grid-cols-4`
- Each field: `text-sm text-muted-foreground` label + `<UserDisplay userId={...} className="font-medium mt-1" />` value.

### Fields (each conditional)
| Field | Shown when |
|---|---|
| Reviewed By | `universe.reviewed_by` is truthy |
| Approved By | `universe.approved_by` is truthy |

---

## 6. Description Card

**Conditional:** Only rendered when `universe.description` is truthy.

- **Card Title:** `text-base` + `AlignLeft` icon — "Description"
- **Content:** `<p className="text-sm leading-relaxed">` — raw description text, no truncation on detail page.

---

## 7. Auditable Entities Section

**Component:** `<AuditableEntitiesSection universeId={...} universeStatus={...} />`  
**Wrapper:** `<div className="space-y-4">` (self-contained section, NOT inside a Card wrapper)

### Section Header
```
Auditable Entities                              [+ Add Entity]
3 entities in this universe
```

| Element | Detail |
|---|---|
| Title `<h2>` | `text-lg font-semibold` |
| Subtitle `<p>` | `text-sm text-muted-foreground` — "{n} entity/entities in this universe" |
| Add Entity button | `size="sm"`, `Plus` icon + "Add Entity". **Only shown** when `universeStatus === 'draft'` or `'under_review'` |

### Entity Table States

**Loading:**
- Inline loader — `Loader2` spin + "Loading auditable entities…" in `text-muted-foreground`

**Empty:**
- Centered text in a dashed border box (`border border-dashed rounded-md py-8`)
- "No auditable entities added yet."
- If modifiable: hint text below — `text-xs` — "Click "Add Entity" to define directorates, units, processes, or systems to audit."

**Populated — Table Structure:**

Wrapped in `<div className="border rounded-md">` → `<Table>` from `@ui/table`.

| Column | Cell Style |
|---|---|
| Code | `font-mono text-sm` |
| Name | `font-medium` |
| Type | `<Badge variant="outline" className="capitalize">` with human-readable type label |
| Description | `max-w-xs truncate text-muted-foreground` — truncated with ellipsis, `—` if empty |
| Created | `text-sm text-muted-foreground` — `toLocaleDateString()` |
| Actions | Right-aligned (`text-right`). Only shown when `isModifiable`. Contains Edit (`Pencil` ghost icon button) + Delete (`Trash2` ghost icon button, `text-destructive`) |

### Entity Type Labels
| Key | Label |
|---|---|
| `directorate` | Directorate |
| `unit` | Unit |
| `zone` | Zone |
| `process` | Process |
| `system` | System |
| `project` | Project |

### Dialogs

**Add / Edit Entity Dialog** — `<CreateAuditableEntityDialog>` (reused for both modes):
- `mode="create"` pre-fills `defaultUniverseId`
- `mode="edit"` pre-fills all fields from selected `AuditableEntity`
- Opens as modal dialog

**Delete Confirmation Dialog** — `<AlertDialog>`:
- Title: "Delete Auditable Entity?"
- Description: "This will remove this entity from the audit universe. This action cannot be undone."
- Preview box: gray muted block (`rounded-md bg-muted p-3`) showing `{code} — {name}` and `Type: {label}`
- Buttons: `Cancel` (outline) + `Delete Entity` (destructive red). While deleting: spinner + "Deleting…"

---

## 8. Approval Workflow Console

**Component:** `<EmbeddedWorkflowConsole>` — rendered at the bottom of the page.

It renders in one of three states:

### State A — Loading Workflow Status
- `<Card>` with centered spinner and "Loading workflow status…" text (`text-sm text-muted-foreground`)

### State B — Workflow Exists (workflow plan ID is set)
```
┌─────────────────────────────────────────────────────┐
│ ⎇ Workflow Console  · REF123       [status]  [↗ Open in New Tab] │
│   Audit Universe                                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│           [iframe — WO Django HTML console]         │
│               height: 600px (default)               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

- **Card header:** flex row, `py-3`
  - Left: `GitBranch` icon + "Workflow Console" title (`text-base`) + optional reference in `font-mono text-xs text-muted-foreground`
  - `CardDescription`: entityTitle ("Audit Universe")
  - Right: optional status `<Badge variant="outline" className="capitalize text-xs">` + "Open in New Tab" outline button (`ExternalLink` icon)
- **iframe:** `w-full h-full border-0`, `sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"`
- While iframe loads: overlay spinner "Loading workflow console…" (`bg-background/80`)
- On iframe error: destructive `<Alert>` with "Failed to load workflow console"

### State C — No Workflow Started
```
┌─────────────────────────────────────────────────────┐
│ ⎇ Approval Workflow                                │
│   Audit Universe                                    │
│                                                     │
│        [circle bg-muted]                            │
│          ⎇ (faded icon)                            │
│                                                     │
│        No workflow started                          │
│   Submit this audit universe to start the           │
│         approval workflow.                          │
│                                                     │
│          [Submit for Approval]                      │  ← only if isDraft + onSubmit
└─────────────────────────────────────────────────────┘
```

- `min-h-[300px]` on the card
- Large faded icon: `GitBranch h-8 w-8 text-muted-foreground opacity-50` inside a `rounded-full bg-muted p-4` circle
- Label: `font-medium text-muted-foreground` — "No workflow started"
- Hint text: `text-sm text-muted-foreground`
- Optional Submit button: shown when `onSubmit` prop is provided. Code condition is `(isDraft || noWorkflow) && onSubmit`. Since State C is only entered when there is no `workflowPlanId`, `noWorkflow` is always `true` here — so in practice the button renders whenever `onSubmit` is passed, regardless of `isDraft`.

---

## 9. Interaction Patterns

| Action | Trigger | Guard |
|---|---|---|
| Navigate back | Click `←` ghost icon button | None |
| Submit universe for approval | "Submit for Approval" button (header or WC console) | `status === 'draft'` + no workflow + `grc:audit_universe:manage` permission |
| Add auditable entity | "+ Add Entity" button → opens create dialog | `universeStatus === 'draft'` or `'under_review'` |
| Edit auditable entity | `Pencil` icon button in table row → opens edit dialog | Same status guard as above |
| Delete auditable entity | `Trash2` icon button → opens AlertDialog confirm | Same status guard as above |
| Open WO console in new tab | "Open in New Tab" button in workflow console | Requires `workflowPlanId` to be set |

---

## 10. Permission-Gated Elements

| Element | Guard mechanism |
|---|---|
| "Submit for Approval" button in header | `<ProtectedComponent service="grc" resource="audit_universe" action="manage">` |
| Add / Edit / Delete entity buttons | `isModifiable` flag (pure status check, no RBAC wrapper) |

---

## 11. Component Dependency Tree

```
AuditUniverseDetailPage
├── UserDisplay                    — resolves userId → name
├── ProtectedComponent             — RBAC wrapper
├── AuditableEntitiesSection       — self-contained child table
│   ├── CreateAuditableEntityDialog (create + edit modes)
│   └── AlertDialog (delete confirm)
└── EmbeddedWorkflowConsole        — WO iframe or empty state
```

---

## 12. Key Data Fields Displayed

| Field | Source |
|---|---|
| Fiscal Year | `universe.fiscal_year.year_code` |
| Status | `universe.status` |
| Created | `universe.created_at` |
| Last Updated | `universe.updated_at` (falls back to `created_at`) |
| Reviewed By | `universe.reviewed_by` (UUID → UserDisplay) |
| Approved By | `universe.approved_by` (UUID → UserDisplay) |
| Description | `universe.description` |
| Workflow Plan ID | `workflowStatus.workflow_plan_id` (live) or `universe.workflow_plan_id` (fallback) |





**THE REFERENCE FILES ARE:**
1. frontend/apps/staff-portal/src/pages/grc/AuditPlanDetailPage.tsx
2. frontend/apps/staff-portal/src/pages/grc/AuditUniverseDetailPage.tsx



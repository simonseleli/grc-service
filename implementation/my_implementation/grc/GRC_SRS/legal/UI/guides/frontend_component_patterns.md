# Frontend Component Patterns — Internal Audit Module (GRC)

> **Scope:** Reusable UI component patterns and design system conventions for all GRC/Internal Audit pages in the Staff Portal.  
> **Does NOT cover:** Core layout rules, routing, RBAC, pagination state management, or API/hook layer — those are in [frontend_core_patterns.md](./frontend_core_patterns.md). Workflow-enabled Detail Pages — those follow [NEW_DETAIL_PAGE_REFERENCE.md](./NEW_DETAIL_PAGE_REFERENCE.md).  
> **Stack:** React 18, TypeScript, react-hook-form v7, Zod, TanStack Query v5, Tailwind CSS, shadcn/ui, lucide-react.  
> **Verified against:** Actual source files in `frontend/apps/staff-portal/src/` — March 2026.

---

## 0. Path Aliases (Reminder)

| Alias | Resolves to |
|---|---|
| `@staff` | `apps/staff-portal/src/` |
| `@shared` | `packages/shared/src/` |
| `@ui` | `packages/shared/src/ui/` |

---

## 1. Table Component Patterns

### 1.1 GenericListPage — Column Definitions

Column definitions for `<GenericListPage>` are declared as a `const` array at module scope (outside the component function).

**Basic column (string value):**

```tsx
const columns = [
  { key: 'reference_number', label: 'Ref', sortable: true },
  { key: 'title',            label: 'Title', sortable: true },
  { key: 'status',           label: 'Status', sortable: true },
  { key: 'updatedAt',        label: 'Last Updated', sortable: true },
];
```

**Column with custom render function:**

```tsx
const columns = [
  { key: 'reference_number', label: 'Ref', sortable: true },

  // Two-line render (engagement reference + subtitle)
  {
    key: 'engagement',
    label: 'Engagement',
    sortable: false,
    render: (item: AuditMemo) => (
      <div className="flex flex-col">
        <span className="font-medium text-sm">{item.engagement?.reference_number ?? 'N/A'}</span>
        <span className="text-xs text-muted-foreground">{item.engagement?.title ?? ''}</span>
      </div>
    ),
  },

  // Badge render (status)
  {
    key: 'status',
    label: 'Status',
    sortable: true,
    render: (item: AuditMemo) => (
      <Badge className={getStatusColor(item.status)}>
        {item.status?.toUpperCase()}
      </Badge>
    ),
  },

  // Badge render (enum type)
  {
    key: 'memo_type',
    label: 'Type',
    sortable: true,
    render: (item: AuditMemo) => (
      <Badge variant="outline">
        {MEMO_TYPE_LABELS[item.memo_type] ?? item.memo_type}
      </Badge>
    ),
  },

  // Date render
  {
    key: 'scheduled_date',
    label: 'Date',
    sortable: true,
    render: (item: AuditMeeting) => (
      <span className="text-sm">
        {item.scheduled_date ? new Date(item.scheduled_date).toLocaleDateString() : 'TBD'}
      </span>
    ),
  },

  // Simple scalar render
  {
    key: 'attendees',
    label: 'Attendees',
    sortable: false,
    render: (item: AuditMeeting) => (
      <span className="text-sm">{item.attendees?.length ?? 0}</span>
    ),
  },
];
```

**Column type signature:**

```ts
interface Column<T = any> {
  key: string;              // maps to a key on the transformed ListItem
  label: string;            // displayed as <TableHead>
  sortable?: boolean;       // enables client-side sort UI
  render?: (item: T) => React.ReactNode;  // custom cell renderer
}
```

Rules:
- `sortable: false` must be explicit for computed/joined columns that have no single sortable field.
- `render` receives the **raw API item** (not the `transformedItem`), when the column array is typed and `GenericListPage` passes the original item through.
- Place `const columns = [...]` at module scope — NOT inside the component function body.

### 1.2 Sorting

`GenericListPage` handles client-side sort UI internally. No additional state is needed in the page component for sorting.

- Mark columns with `sortable: true` to enable click-to-sort.
- Server-side ordering is NOT used in current GRC pages — all sorting is client-side within the fetched page.

### 1.3 Filtering

Filters are owned by the page as local state and passed to the data-fetch hook:

```tsx
// Search filter example (verified in AuditPlansPage-like patterns):
const [searchQuery, setSearchQuery] = useState('');

const { data } = useAuditFindings(page, pageSize, {
  search: searchQuery || undefined,    // omit empty strings
});

// Date-range filter:
const [fromDate, setFromDate] = useState('');
const { data } = useAuditFindings(page, pageSize, {
  date_from: fromDate || undefined,
});
```

- Reset `page` to `1` whenever any filter value changes.
- Use `undefined` (not empty string) to omit a filter from the query params.

### 1.4 Pagination Integration with GenericListPage

Pass these props every time — none are optional when `enableServerPagination` is needed:

```tsx
<GenericListPage
  title="Audit Findings"
  items={activeItems}
  columns={columns}
  userRole="admin"
  onView={handleView}
  onEdit={handleEdit}
  onDelete={handleDelete}
  showCreateButton={false}              // manual button in header
  pagination={
    data
      ? {
          page: data.page,
          page_size: data.page_size,
          total_pages: Math.max(1, Math.ceil(data.count / pageSize)),
          count: data.count,
        }
      : undefined
  }
  currentPage={page}
  pageSize={pageSize}
  onPageChange={setPage}
  onPageSizeChange={(newSize) => {
    setPageSize(newSize);
    setPage(1);
  }}
/>
```

- `Math.max(1, ...)` prevents `total_pages: 0` when the list is empty.
- `showCreateButton={false}` is used when the create button is placed in the page header (canonical pattern). Use `onCreateNew={() => setIsCreateOpen(true)}` and `showCreateButton={true}` when the button lives inside `GenericListPage`.

### 1.5 Action Handlers (View / Edit / Delete)

```tsx
const handleView = (id: string) => {
  const item = activeItems.find((m) => m.id === id);
  if (item) { setSelectedItem(item); setIsDetailOpen(true); }
};

const handleEdit = (id: string) => {
  const item = activeItems.find((m) => m.id === id);
  if (item && item.status === 'draft') setEditingItem(item);  // status gate
};

const handleDelete = (id: string) => {
  const item = activeItems.find((m) => m.id === id);
  if (!item) return;
  // Business guard — toast, then bail out:
  if (item.status === 'approved') {
    toast.error('Cannot delete this item', {
      description: 'Approved items cannot be deleted.',
    });
    return;
  }
  setDeletingItem(item);
};
```

- Pass `onEdit={undefined}` and `onDelete={undefined}` when the current user lacks permission — this hides those action columns entirely.

### 1.6 Raw Table — Sub-tables Inside Detail Pages

For embedded child lists inside a detail page or section component, use the raw `<Table>` from `@ui/table`. Wrap in a `border rounded-md` container:

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table';

<div className="border rounded-md">
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Code</TableHead>
        <TableHead>Name</TableHead>
        <TableHead>Type</TableHead>
        <TableHead>Status</TableHead>
        {isModifiable && <TableHead className="text-right">Actions</TableHead>}
      </TableRow>
    </TableHeader>
    <TableBody>
      {items.length === 0 ? (
        <TableRow>
          <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
            No items added yet.
          </TableCell>
        </TableRow>
      ) : (
        items.map((item) => (
          <TableRow key={item.id}>
            <TableCell className="font-mono text-sm">{item.code}</TableCell>
            <TableCell className="font-medium">{item.name}</TableCell>
            <TableCell>
              <Badge variant="outline" className="capitalize">
                {TYPE_LABELS[item.type] ?? item.type}
              </Badge>
            </TableCell>
            <TableCell className="max-w-xs truncate text-muted-foreground">
              {item.description || '—'}
            </TableCell>
            {isModifiable && (
              <TableCell className="text-right">
                <Button variant="ghost" size="sm" onClick={() => setEditItem(item)}>
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setDeletingItem(item)}>
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </TableCell>
            )}
          </TableRow>
        ))
      )}
    </TableBody>
  </Table>
</div>
```

Rules:
- First identifying column (code, ref number): `className="font-mono text-sm"` or `"font-medium"`.
- Actions column header: `className="text-right"` — action buttons right-aligned with `text-right` on the cell too.
- Empty state: single `<TableRow>` spanning the full `colSpan`, centred, `py-8`.
- Status columns: always inline `<Badge className={getStatusColor(status)}>`.

### 1.7 Smart Selection — SmartSelect Component

`<SmartSelect>` at `@staff/components/grc/SmartSelect` is a combobox with inline search, built on shadcn `Popover` + `Command`. Use it for large dropdown lists where basic `<Select>` would be unwieldy.

```tsx
import { SmartSelect } from '@staff/components/grc/SmartSelect';

// Inside a FormField render prop:
<SmartSelect
  value={field.value}
  onChange={field.onChange}
  options={engagements.map((e) => ({
    value: e.id,
    label: `${e.reference_number} — ${e.title}`,
  }))}
  placeholder="Select an engagement..."
  searchPlaceholder="Search engagements..."
  emptyText="No engagements found"
  isLoading={isLoadingEngagements}
  disabled={mode === 'edit'}       // lock when editing linked records
/>
```

**`SmartSelect` props:**

| Prop | Type | Default | Notes |
|---|---|---|---|
| `value` | `string \| undefined` | — | Controlled value (UUID) |
| `onChange` | `(value: string) => void` | — | Called with selected UUID |
| `options` | `SelectOption[]` | — | `{ value: string; label: string; disabled?: boolean }` |
| `placeholder` | `string` | `'Select an option...'` | Button label when empty |
| `searchPlaceholder` | `string` | `'Search...'` | Input placeholder |
| `emptyText` | `string` | `'No results found.'` | Shown when filtered list is empty |
| `disabled` | `boolean` | `false` | Greys out the trigger |
| `isLoading` | `boolean` | `false` | Shows spinner inside trigger |
| `allowQuickAdd` | `boolean` | `false` | Enables inline "add new" — not used in Internal Audit forms |

Use `SmartSelect` for: engagements, audit plans, auditable entities, fiscal year (when list is large), findings, recommendations.  
Use `<Select>` (shadcn) for: short static enums (plan type, memo type, priority, report type).

---

## 2. Form Patterns

### 2.1 Form Stack

All GRC dialog forms use this exact stack:

```
react-hook-form (useForm)
  + zodResolver (@hookform/resolvers/zod)
  + Zod schema (z.object({...}))
  + shadcn Form components (@ui/form)
```

### 2.2 Zod Schema Conventions

Define the schema at module scope (outside the component), immediately after imports:

```ts
const auditPlanSchema = z.object({
  // Required string
  title: z.string().min(5, 'Title must be at least 5 characters').max(200, 'Title too long'),

  // Required enum (static list)
  plan_type: z.string().min(1, 'Plan type is required'),

  // Required FK (UUID from SmartSelect)
  fiscal_year_id: z.string().min(1, 'Fiscal year is required'),

  // Optional string
  management_comments: z.string().optional(),

  // Coerced number (optional)
  staff_count: z.coerce.number().min(0).optional(),

  // Enum union
  priority: z.enum(['high', 'medium', 'low'], {
    required_error: 'Priority is required',
  }),

  // Date string (ISO format from <input type="date">)
  target_date: z.string().min(1, 'Target date is required'),

  // Regex-validated code
  code: z
    .string()
    .min(2, 'Code must be at least 2 characters')
    .max(50, 'Code too long')
    .regex(/^[A-Z0-9-]+$/, 'Code must be uppercase alphanumeric with hyphens only'),

  // Dynamic arrays (for useFieldArray)
  procedures: z.array(procedureSchema),
});
```

**Cross-field validation with `.refine()`:**

```ts
const fiscalYearSchema = z.object({
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
}).refine(
  (data) => new Date(data.end_date) > new Date(data.start_date),
  { message: 'End date must be after start date', path: ['end_date'] }
);
```

### 2.3 Form Initialisation

```tsx
const form = useForm<FormValues>({
  resolver: zodResolver(schema),
  defaultValues: entity
    ? {
        title: entity.title,
        plan_type: entity.plan_type,
        fiscal_year_id: entity.fiscal_year.id,   // unwrap nested FK -> id
        management_comments: entity.management_comments || '',
        staff_count: entity.resource_allocation?.staff_count ?? undefined,
      }
    : {
        title: '',
        plan_type: 'annual',     // sensible default for enums
        fiscal_year_id: '',
        management_comments: '',
        staff_count: undefined,
      },
});
```

Rules:
- `undefined` (not `null`) for optional number fields — `z.coerce.number().optional()` treats `undefined` as absent.
- Empty string `''` for optional text fields — avoids uncontrolled/controlled warnings on `<Input>`.
- Always unwrap nested FK objects to their `.id` string in `defaultValues`.

### 2.4 Resetting on Dialog Open

Always reset the form inside a `useEffect` keyed on `[open, entity, form]`:

```tsx
useEffect(() => {
  if (open && mode === 'edit' && entity) {
    form.reset({
      title: entity.title,
      plan_type: entity.plan_type,
      // ...
    });
  } else if (open && mode === 'create') {
    form.reset({
      title: '',
      plan_type: 'annual',
      // ...
    });
  }
}, [open, mode, entity, form]);
```

Do NOT use `form.reset()` inside `onSubmit` before `onSuccess` — it clears state before the mutation confirms.

### 2.5 Input Types

#### Text Input

```tsx
<FormField
  control={form.control}
  name="title"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Plan Title *</FormLabel>
      <FormControl>
        <Input
          placeholder="e.g., Risk-Based Internal Audit Plan for FY 2025/2026"
          disabled={!canEdit}
          {...field}
        />
      </FormControl>
      <FormDescription>
        A descriptive title for the audit plan (5–200 characters)
      </FormDescription>
      <FormMessage />
    </FormItem>
  )}
/>
```

#### Auto-uppercase Code Input

```tsx
<Input
  placeholder="e.g., ICT-001"
  {...field}
  onChange={(e) => field.onChange(e.target.value.toUpperCase())}
/>
```

#### Textarea

```tsx
<FormField
  control={form.control}
  name="body"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Body</FormLabel>
      <FormControl>
        <Textarea
          placeholder="Memo content..."
          rows={8}
          {...field}
        />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

#### Date Input

```tsx
<FormField
  control={form.control}
  name="target_date"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Target Date *</FormLabel>
      <FormControl>
        <Input type="date" {...field} />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

#### Number Input

```tsx
<FormField
  control={form.control}
  name="staff_count"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Staff Count</FormLabel>
      <FormControl>
        <Input type="number" min={0} {...field} />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

Use `z.coerce.number()` in the schema to convert the string value from `<Input type="number">`.

#### Select (shadcn) — Short Static Enum

```tsx
<FormField
  control={form.control}
  name="plan_type"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Plan Type *</FormLabel>
      <Select
        onValueChange={field.onChange}
        value={field.value}
        disabled={!canEdit}
      >
        <FormControl>
          <SelectTrigger>
            <SelectValue placeholder="Select plan type" />
          </SelectTrigger>
        </FormControl>
        <SelectContent>
          {PLAN_TYPES.map((type) => (
            <SelectItem key={type.value} value={type.value}>
              {type.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <FormDescription>The type of audit plan</FormDescription>
      <FormMessage />
    </FormItem>
  )}
/>
```

Import:
```ts
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@ui/select';
```

#### SmartSelect — Large FK Lookup

```tsx
<FormField
  control={form.control}
  name="engagement_id"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Engagement</FormLabel>
      <FormControl>
        <SmartSelect
          value={field.value}
          onChange={field.onChange}
          options={engagements.map((e) => ({
            value: e.id,
            label: `${e.reference_number} — ${e.title}`,
          }))}
          placeholder="Select an engagement..."
          isLoading={isLoadingEngagements}
          disabled={mode === 'edit'}
        />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

Note: `<FormControl>` wraps `<SmartSelect>` directly — no `<SelectTrigger>` wrapper needed.

### 2.6 Grid Layouts Inside Forms

```tsx
{/* 2-column grid */}
<div className="grid grid-cols-2 gap-4">
  <FormField name="memo_type" ... />
  <FormField name="title" ... />
</div>

{/* 3-column grid */}
<div className="grid grid-cols-3 gap-4">
  <FormField name="staff_count" ... />
  <FormField name="total_audit_hours" ... />
  <FormField name="budget_allocated" ... />
</div>
```

### 2.7 Form Sections (Multi-section Forms)

For large forms (e.g., `CreateAuditReportDialog`), group fields under a section heading:

```tsx
<form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
  {/* Section 1 */}
  <div className="space-y-4">
    <h3 className="text-sm font-semibold text-foreground border-b pb-2">Basic Information</h3>
    <FormField name="title" ... />
    <div className="grid grid-cols-2 gap-4">
      <FormField name="engagement_id" ... />
      <FormField name="opinion_id" ... />
    </div>
  </div>

  {/* Section 2 */}
  <div className="space-y-4">
    <h3 className="text-sm font-semibold text-muted-foreground">Report Content</h3>
    <FormField name="executive_summary" ... />
    <FormField name="conclusion" ... />
  </div>
</form>
```

- Section heading: `<h3 className="text-sm font-semibold text-foreground border-b pb-2">` — **NOT** `text-muted-foreground`; the border-b gives a visual divider.
- For simple **sub-groups within a flat form** (not full sections), use `<p className="text-sm font-medium">Sub-group Label</p>` on a `<div className="space-y-3">` wrapper — no border, no h3.
- Top-level form spacing: `space-y-6` when sections are present; `space-y-4` for flat forms.

### 2.8 Dynamic Field Arrays (useFieldArray)

For repeating groups (e.g., procedures in an Audit Program):

```tsx
import { useFieldArray } from 'react-hook-form';

const { fields, append, remove } = useFieldArray({
  control: form.control,
  name: 'procedures',
});

// Render
{fields.map((field, index) => (
  <div key={field.id} className="border rounded-md p-3 space-y-3">
    <div className="flex justify-between items-center">
      <span className="text-sm font-medium">Procedure {index + 1}</span>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => remove(index)}
      >
        <Trash2 className="h-4 w-4 text-destructive" />
      </Button>
    </div>
    <FormField
      control={form.control}
      name={`procedures.${index}.procedure`}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Procedure Text *</FormLabel>
          <FormControl>
            <Textarea rows={2} {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  </div>
))}

<Button
  type="button"
  variant="outline"
  size="sm"
  onClick={() => append({ rcm_entry_id: null, procedure: '', sample_size: '', criteria: '' })}
>
  <Plus className="mr-2 h-4 w-4" />
  Add Procedure
</Button>
```

### 2.9 Cascading Selects

When one field filters the options of another (e.g., fiscal year → quarter):

```tsx
// Watch the parent field
const selectedFiscalYearId = form.watch('fiscal_year_id');

// Filter child options
const quarters = selectedFiscalYearId
  ? allQuarters.filter((q) => q.fiscal_year?.id === selectedFiscalYearId)
  : allQuarters;

// Clear child when parent changes and current child value is no longer valid
useEffect(() => {
  if (mode === 'create') {
    const currentQuarter = form.getValues('quarter_id');
    if (currentQuarter && selectedFiscalYearId) {
      const stillValid = quarters.some((q) => q.id === currentQuarter);
      if (!stillValid) {
        form.setValue('quarter_id', '');
      }
    }
  }
}, [selectedFiscalYearId, quarters, mode, form]);
```

### 2.10 onSubmit — Data Cleaning

Clean optional fields before handing data to `onSuccess`:

```tsx
const onSubmit = (data: FormValues) => {
  const cleanedData = {
    ...data,
    management_comments: data.management_comments?.trim() || undefined,
    prepared_by: data.prepared_by?.trim() || undefined,
    // Convert empty date strings to undefined
    planned_start_date: data.planned_start_date || undefined,
  };
  onSuccess(cleanedData);
  form.reset();  // reset AFTER calling onSuccess (parent decides whether to close)
};
```

Rules:
- Trim optional text fields. If empty after trim, send `undefined` (not `''`).
- Strip optional FK strings that are empty: `data.field || undefined`.
- `form.reset()` after `onSuccess(cleanedData)` — not before.

### 2.11 Validation Error Display

`<FormMessage />` automatically renders the Zod error for its parent `<FormField>`. No manual error extraction is needed:

```tsx
<FormItem>
  <FormLabel>Title *</FormLabel>
  <FormControl>
    <Input {...field} />
  </FormControl>
  <FormDescription>Optional helper text below the input.</FormDescription>
  <FormMessage />   {/* auto-renders error message in red */}
</FormItem>
```

- `<FormDescription>` renders as grey hint text below the input, above `<FormMessage>`.
- `<FormMessage>` renders only when there is an error; otherwise renders nothing.
- Do NOT add manual `{form.formState.errors.field && <p>...}` — use `<FormMessage>` exclusively.

### 2.12 Lazy-Loading Lookup Data in Dialogs

All lookup data for dialogs is fetched with the dialog's `open` prop as the `enabled` trigger — this prevents network requests when the dialog is closed:

```tsx
// FIMS Pattern: pass `open` as the enabled argument to all lookup hooks
const { data: fiscalYearsData, isLoading: isFiscalYearsLoading } = useFiscalYears(open);
const { data: quartersRaw,     isLoading: isLoadingQuarters }    = useQuarters(open);
const { data: severitiesData,  isLoading: isLoadingSeverities }  = useAuditSeverities(open);
const { data: engagementsData, isLoading: isLoadingEngagements } = useAuditEngagementsLookup(open);

// Combine multiple loading states into one flag
const isLoadingLookups = isFiscalYearsLoading || isLoadingQuarters || isLoadingSeverities;

// Filter inactive config items before building options
const fiscalYears = (fiscalYearsData?.results ?? []).filter((fy) => fy.is_active !== false);
const severities  = (severitiesData?.results  ?? []).filter((s)  => s.is_active  !== false);

// Business-rule filter: only expose engagements in eligible statuses
const availableEngagements = mode === 'create'
  ? engagements.filter((e) => e.status === 'fieldwork' || e.status === 'reporting')
  : engagements;
```

**Loading gate — show spinner, then form (never simultaneously):**

```tsx
{isLoadingLookups && (
  <div className="flex items-center justify-center py-8">
    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    <span className="ml-2 text-sm text-muted-foreground">Loading form data...</span>
  </div>
)}

{!isLoadingLookups && (
  <Form {...form}>
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      {/* fields */}
    </form>
  </Form>
)}
```

**SmartSelect disabled when parent not yet selected:**

```tsx
<SmartSelect
  placeholder={selectedFiscalYearId ? 'Select quarter...' : 'Select a fiscal year first'}
  disabled={isSubmitting || isLoadingLookups || !selectedFiscalYearId}
/>
```

**Inline alert when no valid options exist:**

```tsx
{mode === 'create' && availableEngagements.length === 0 && !isLoadingEngagements && (
  <Alert className="mt-2">
    <AlertTriangle className="h-4 w-4" />
    <AlertTitle>No Available Engagements</AlertTitle>
    <AlertDescription>
      Only engagements in 'fieldwork' or 'reporting' phase can have findings.
    </AlertDescription>
  </Alert>
)}
```

- Disable submit button also: `disabled={isSubmitting || availableEngagements.length === 0}`.

### 2.13 Nested Data Transformation in onSubmit

When the API expects a nested object but the form uses flat fields (e.g., `resource_allocation`):

```tsx
const onSubmit = (data: FormValues) => {
  const cleanedData: FormValues = {
    ...data,
    // Trim optional text
    management_comments: data.management_comments?.trim() || undefined,
    // Reconstruct nested object from flat form fields
    resource_allocation: (
      data.staff_count != null ||
      data.total_audit_hours != null ||
      data.budget_allocated != null
    ) ? {
      staff_count:       data.staff_count       ?? 0,
      total_audit_hours: data.total_audit_hours ?? 0,
      budget_allocated:  data.budget_allocated  ?? 0,
    } : undefined,
  };
  // Remove the flat fields that have been nested
  delete (cleanedData as any).staff_count;
  delete (cleanedData as any).total_audit_hours;
  delete (cleanedData as any).budget_allocated;
  // Strip empty auto-generated fields
  if (!cleanedData.reference_number) delete cleanedData.reference_number;
  onSuccess(cleanedData);
  form.reset();
};
```

### 2.14 Simple Utility Dialog (No react-hook-form)

For action dialogs that need only 2–3 fields and no Zod validation (e.g., "Generate Draft Plan"), use `<Label>` + `<Input>`/`<Select>` directly with `useState`:

```tsx
import { Label } from '@ui/label';

const [fiscalYearId, setFiscalYearId] = useState('');
const [universeId,   setUniverseId]   = useState('');

<Dialog open={open} onOpenChange={(isOpen) => {
  setOpen(isOpen);
  if (!isOpen) { setFiscalYearId(''); setUniverseId(''); }  // reset on close
}}>
  <DialogContent className="max-w-md">
    <DialogHeader>
      <DialogTitle>Generate Draft Plan</DialogTitle>
      <DialogDescription>Select a fiscal year and audit universe.</DialogDescription>
    </DialogHeader>

    <div className="space-y-4 py-2">
      <div className="space-y-1.5">
        <Label htmlFor="gen-fiscal-year">
          Fiscal Year <span className="text-destructive">*</span>
        </Label>
        <Select value={fiscalYearId} onValueChange={setFiscalYearId}>
          <SelectTrigger id="gen-fiscal-year">
            <SelectValue placeholder="Select fiscal year..." />
          </SelectTrigger>
          <SelectContent>
            {fiscalYears.map((fy) => (
              <SelectItem key={fy.id} value={fy.id}>
                {fy.name} ({fy.year_code})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>

    <DialogFooter>
      <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
      <Button
        onClick={handleAction}
        disabled={!fiscalYearId || !universeId || actionMutation.isPending}
      >
        {actionMutation.isPending
          ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Generating...</>
          : 'Generate'}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

Rules:
- Use `<Label htmlFor="...">` (not `<FormLabel>`) — no react-hook-form wrapper.
- Use `space-y-1.5` for label+input pairs (tighter than `space-y-4`).
- Reset all state in the `onOpenChange` handler when the dialog closes.
- `max-w-md` for 2–4 field utility dialogs (vs `max-w-2xl+` for full CRUD forms).

---

## 3. Modal (Dialog) Patterns

### 3.1 Standard Dialog — Create/Edit Form

Full verified pattern (confirmed across all GRC Create*Dialog components):

```tsx
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from '@ui/dialog';

<Dialog open={open} onOpenChange={onOpenChange}>
  <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
    <DialogHeader>
      <DialogTitle>
        {mode === 'create' ? 'Create Audit Memo' : 'Edit Audit Memo'}
      </DialogTitle>
      <DialogDescription>
        {mode === 'create'
          ? 'Create a new audit memo for an engagement.'
          : `Editing: ${memo?.reference_number}`}
      </DialogDescription>
    </DialogHeader>

    {/* Loading state — when lookup data is fetching */}
    {isLoading ? (
      <div className="flex justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    ) : (
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">

          {/* Fields here */}
          <FormField ... />

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</>
              ) : (
                mode === 'create' ? 'Create' : 'Save Changes'
              )}
            </Button>
          </DialogFooter>

        </form>
      </Form>
    )}
  </DialogContent>
</Dialog>
```

**Dialog size conventions:**

| Form Size | `max-w-` class |
|---|---|
| Simple (≤ 4 fields) | `max-w-lg` — e.g., `FiscalYearDialog` → `sm:max-w-[525px]` |
| Standard (5–10 fields) | `max-w-2xl` — e.g., `CreateAuditMemoDialog` |
| Complex (many fields, sections) | `max-w-3xl` — e.g., `CreateAuditPlanDialog`, `CreateAuditEngagementDialog` |
| Very large (field arrays, multi-section) | `max-w-4xl` — e.g., `CreateAuditFindingDialog`, `CreateAuditReportDialog`, `CreateAuditMeetingDialog` |

Always pair with `max-h-[90vh] overflow-y-auto` to keep tall forms scrollable.

### 3.2 Dialog Props Interface

Standard interface for all Create/Edit dialog components:

```ts
interface CreateEntityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: 'create' | 'edit';
  entity?: EntityType;              // undefined in create mode
  onSuccess: (data: EntityFormData) => void;
  isSubmitting?: boolean;           // passed as mutation.isPending from parent
  // Optional pre-fills:
  defaultEntityId?: string;         // pre-fills and locks a parent FK field
}
```

### 3.3 Dialog Open State — Owned by the Page

```tsx
// Create:
const [isCreateOpen, setIsCreateOpen] = useState(false);

// Edit — uses the entity itself as the gating state:
const [editingItem, setEditingItem] = useState<AuditPlan | null>(null);

// Render:
<CreateAuditPlanDialog
  open={isCreateOpen}
  onOpenChange={setIsCreateOpen}
  mode="create"
  onSuccess={(formData) =>
    createMutation.mutate(formData, {
      onSuccess: () => setIsCreateOpen(false),
    })
  }
  isSubmitting={createMutation.isPending}
/>

{editingItem && (
  <CreateAuditPlanDialog
    open={!!editingItem}
    onOpenChange={(open) => !open && setEditingItem(null)}
    mode="edit"
    auditPlan={editingItem}
    onSuccess={(formData) =>
      updateMutation.mutate(
        { id: editingItem.id, data: formData },
        { onSuccess: () => setEditingItem(null) },
      )
    }
    isSubmitting={updateMutation.isPending}
  />
)}
```

### 3.4 Inline Alert Inside a Dialog

Use a yellow warning banner (not a shadcn `<Alert>`) when a record is read-only due to status:

```tsx
{!canEdit && (
  <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
    This audit plan is <strong>{entity?.status}</strong> and cannot be edited.
    Only draft plans can be modified.
  </div>
)}
```

Use a shadcn `<Alert>` inside a dialog when there is a genuine data-availability problem:

```tsx
{mode === 'create' && availableFindings.length === 0 && !isLoadingFindings && (
  <Alert>
    <AlertTriangle className="h-4 w-4" />
    <AlertTitle>No Finalized Findings</AlertTitle>
    <AlertDescription>
      Only findings with 'final' status can have recommendations.
    </AlertDescription>
  </Alert>
)}
```

### 3.5 Detail-View Dialog (Read-only)

Some entities use a separate read-only dialog (`AuditMemoDetailDialog`, `AuditFindingDetailDialog`). These are not form dialogs — they display data only:

```tsx
<Dialog open={open} onOpenChange={onOpenChange}>
  <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
    <DialogHeader>
      <DialogTitle>{item.reference_number}</DialogTitle>
      <DialogDescription>{item.title}</DialogDescription>
    </DialogHeader>

    {/* Data display — use the same Card/grid patterns as detail pages */}
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-sm text-muted-foreground">Status</p>
          <Badge className={getStatusColor(item.status)}>{item.status}</Badge>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Created</p>
          <p className="font-medium">{new Date(item.created_at).toLocaleDateString()}</p>
        </div>
      </div>
    </div>

    <DialogFooter>
      <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## 4. Button and Action Patterns

### 4.1 Button Variants

| Variant | `variant=` | Use context |
|---|---|---|
| Primary | `default` (solid) | Create, Submit for Approval, Save Changes, Confirm |
| Secondary | `outline` | Edit, Export, Generate, Cancel (in dialogs), secondary CTAs |
| Tertiary / icon-only | `ghost` | Back button, inline row actions (Edit icon, Delete icon) |
| Destructive | `destructive` | Inside `<AlertDialogAction>` only — never in page headers |

### 4.2 Button Content — Icon + Text

```tsx
// Primary action with icon:
<Button onClick={() => setIsCreateOpen(true)}>
  <Plus className="mr-2 h-4 w-4" />
  Create Audit Plan
</Button>

// Secondary with icon:
<Button variant="outline" onClick={() => setIsGenerateOpen(true)}>
  <Sparkles className="mr-2 h-4 w-4" />
  Generate from Risk Assessments
</Button>

// Submit action (detail page):
<Button onClick={handleSubmit} disabled={submitMutation.isPending}>
  {submitMutation.isPending
    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    : <Send className="mr-2 h-4 w-4" />}
  Submit for Approval
</Button>

// Inline table row action (icon-only):
<Button variant="ghost" size="sm" onClick={() => setEditItem(item)}>
  <Pencil className="h-4 w-4" />
</Button>
<Button variant="ghost" size="sm" onClick={() => setDeletingItem(item)}>
  <Trash2 className="h-4 w-4 text-destructive" />
</Button>
```

Icon rules:
- Icon before text: `<Icon className="mr-2 h-4 w-4" />`.
- Icon-only buttons: `size="icon"` prop, icon has no margin.
- Destructive icon: `<Trash2 className="h-4 w-4 text-destructive" />` — red via text class, NOT via `variant="destructive"` on the ghost button.

### 4.3 Loading State on Submit Button

```tsx
<Button type="submit" disabled={isSubmitting}>
  {isSubmitting ? (
    <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</>
  ) : (
    mode === 'create' ? 'Create' : 'Save Changes'
  )}
</Button>
```

Rules:
- Always disable while `isPending` — never hide.
- Show spinner icon + progress label when loading.
- Do NOT disable buttons based on permission — hide them entirely (see §4.5).

### 4.4 Placement Conventions

**List page header (right side):**

```tsx
<div className="flex items-center justify-between">
  <div className="flex items-center gap-2">
    <PageIcon className="h-6 w-6 text-primary" />
    <h1 className="text-2xl font-bold">Page Title</h1>
  </div>
  <div className="flex items-center gap-2">
    {canManage && (
      <Button variant="outline" onClick={() => setIsSecondaryOpen(true)}>
        <SecondaryIcon className="mr-2 h-4 w-4" />
        Secondary Action
      </Button>
    )}
    {canManage && (
      <Button onClick={() => setIsCreateOpen(true)}>
        <Plus className="mr-2 h-4 w-4" />
        Primary Action
      </Button>
    )}
  </div>
</div>
```

- Primary (solid) action rightmost.
- Secondary (outline) actions to the left of primary.
- All header buttons inside `flex items-center gap-2`.

**Detail page header (right side, before status badge):**

```tsx
<div className="flex items-center gap-4">
  <Button variant="ghost" size="icon" onClick={handleBack} aria-label="Back">
    <ChevronLeft className="h-4 w-4" />
  </Button>
  <div className="flex-1">
    <h1 className="text-2xl font-semibold">{entity.title}</h1>
  </div>
  {/* CTAs go here — before the status badge */}
  {canDraftPlans && isDraft && (
    <Button onClick={handleSubmit} disabled={submitMutation.isPending}>
      <Send className="mr-2 h-4 w-4" />
      Submit for Approval
    </Button>
  )}
  <Badge className={statusColors[entity.status] ?? 'bg-gray-100 text-gray-800'}>
    {statusLabel}
  </Badge>
</div>
```

**Dialog footer:**

```tsx
<DialogFooter>
  <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
    Cancel
  </Button>
  <Button type="submit" disabled={isSubmitting}>
    {isSubmitting ? (
      <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</>
    ) : (
      'Save'
    )}
  </Button>
</DialogFooter>
```

Cancel is always `variant="outline"` and `type="button"` (not submit).

**Sub-section header (embedded child lists):**

```tsx
<div className="flex justify-between items-center">
  <div>
    <h2 className="text-lg font-semibold">Auditable Entities</h2>
    <p className="text-sm text-muted-foreground">
      {entities.length} {entities.length === 1 ? 'entity' : 'entities'} in this universe
    </p>
  </div>
  {isModifiable && (
    <Button size="sm" onClick={() => setIsCreateOpen(true)}>
      <Plus className="mr-2 h-4 w-4" />
      Add Entity
    </Button>
  )}
</div>
```

Use `size="sm"` for buttons in sub-section headers and inline table rows.

### 4.5 Role-Based Visibility

```tsx
const { canManagePlans, canApprovePlans } = useGRCPermissions();
const canDraftPlans = canManagePlans && !canApprovePlans;   // IA only
const canImprovePlans = canManagePlans && canApprovePlans;  // CIA only

// In JSX — hide entirely when not permitted:
{canDraftPlans && (
  <Button onClick={() => setIsCreateOpen(true)}>
    <Plus className="mr-2 h-4 w-4" />
    Create Audit Plan
  </Button>
)}

// Status + permission gate (both must be true):
{canDraftPlans && isDraft && !workflowPlanId && (
  <Button onClick={handleSubmit}>Submit for Approval</Button>
)}
```

Rules:
- **Never** render a button and disable it based on permission — hide it entirely.
- A button may be `disabled` for business/state reasons (wrong status, pending mutation).
- Always derive role booleans at the top of the component — do not scatter permission logic in JSX.
- For `onEdit` / `onDelete` passed to `GenericListPage`, pass `undefined` (not a no-op function) when not permitted:

```tsx
onEdit={canManagePlans ? handleEdit : undefined}
onDelete={canManagePlans ? handleDelete : undefined}
```

### 4.6 Confirm Dialog — Destructive Action (AlertDialog)

```tsx
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@ui/alert-dialog';

<AlertDialog open={!!deletingItem} onOpenChange={(open) => !open && setDeletingItem(null)}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Delete Audit Plan?</AlertDialogTitle>
      <AlertDialogDescription>
        "<strong>{deletingItem?.title}</strong>" will be permanently removed.
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

```tsx
// Confirm handler — always use onSettled (fires on success AND error):
const confirmDelete = () => {
  if (deletingItem) {
    deleteMutation.mutate(deletingItem.id, {
      onSettled: () => setDeletingItem(null),
    });
  }
};
```

Rules:
- Use `<AlertDialog>` (not `<Dialog>`) for all destructive confirmations.
- `AlertDialogAction` gets `className="bg-destructive hover:bg-destructive/90"` — not `variant="destructive"`.
- `onSettled` (not `onSuccess`) ensures the dialog always closes, even on error.
- Disable both `Cancel` and the action button while mutation is pending.

### 4.7 Component-Based Permission Gates

Two components exist for permission-gated rendering. Choose the right one for the context:

**`<PermissionGate>`** — from `@staff/components/grc/PermissionGate`. Uses GRC string permissions (`keyof GRCPermissions`). Preferred for GRC pages.

```tsx
import { PermissionGate, PermissionSwitch } from '@staff/components/grc/PermissionGate';

// Page-level gate — wraps entire page, shows denied message:
<PermissionGate
  permission="grc:config:system:manage"
  showDeniedMessage
  fallback={
    <div className="flex items-center justify-center min-h-[400px]">
      <p className="text-muted-foreground">Access Restricted</p>
    </div>
  }
>
  {/* page content */}
</PermissionGate>

// Component-level gate — silently hides element:
<PermissionGate permission="grc:audit_plan:manage">
  <Button>Create Plan</Button>
</PermissionGate>

// Multiple permissions (any one required):
<PermissionGate permission={['grc:audit_plan:manage', 'grc:audit_plan:view']}>
  <AuditPlanForm />
</PermissionGate>

// Multiple permissions (ALL required):
<PermissionGate permission={['grc:audit_plan:manage', 'grc:config:fiscal_year:manage']} requireAll>
  <AdvancedForm />
</PermissionGate>
```

**`<ProtectedComponent>`** — from `@staff/components/ProtectedComponent`. Uses service/resource/action. Used in older and shared components.

```tsx
import { ProtectedComponent } from '@staff/components/ProtectedComponent';

<ProtectedComponent service="grc" resource="audit_universe" action="manage">
  <Button onClick={handleSubmit}>Submit for Approval</Button>
</ProtectedComponent>
```

| Use case | Preferred approach |
|---|---|
| Page-level access gate with denied message | `<PermissionGate showDeniedMessage>` |
| Fine-grained UI visibility (GRC string perms) | `<PermissionGate>` |
| Service/resource/action visibility (shared perms) | `<ProtectedComponent>` |
| Decision logic in component body | `useGRCPermissions()` hooks |

---

## 5. Detail Page Pattern (Non-Workflow)

> For workflow-enabled detail pages, see [NEW_DETAIL_PAGE_REFERENCE.md](./NEW_DETAIL_PAGE_REFERENCE.md).  
> This section covers detail pages for entities that have no `EmbeddedWorkflowConsole`.

### 5.1 When to Use This Pattern

A "non-workflow detail page" is a page that:
- Navigates to a full URL (`/service/grc/<entity>/:id`) — not a dialog
- Displays a single entity record with cards and sections
- May have a child list/table embedded (e.g., RCM Entry list inside RCM Detail)
- Has NO `EmbeddedWorkflowConsole` at the bottom
- Has no approval submission CTA in the header

Examples: `AuditUniverseDetailPage` (simplified), `RCMDetailPage`, and any future config or reference-data detail pages.

### 5.2 Overall Page Structure

```tsx
// Loading guard first
if (isLoading) {
  return (
    <div className="flex items-center justify-center min-h-[300px]">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}

// Error / not found guard second
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

// Normal render
return (
  <div className="space-y-4 p-4">

    {/* 1. Header row */}
    <div className="flex items-center gap-4">
      <Button variant="ghost" size="icon" onClick={handleBack} aria-label="Back">
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <div className="flex-1">
        <h1 className="text-2xl font-semibold">{entity.title}</h1>
        <p className="text-sm text-muted-foreground">
          Ref: <span className="font-mono">{entity.reference_number}</span>
        </p>
      </div>
      {/* Optional: action CTAs */}
      {canEdit && (
        <Button variant="outline" onClick={() => setIsEditOpen(true)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </Button>
      )}
      {/* Status badge — always rightmost */}
      <Badge className={statusColors[entity.status] ?? 'bg-gray-100 text-gray-800'}>
        {statusLabel}
      </Badge>
    </div>

    {/* 2. Primary data card */}
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          Details
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <p className="text-sm text-muted-foreground">Fiscal Year</p>
            <p className="font-medium">{entity.fiscal_year?.year_code ?? '—'}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Status</p>
            <Badge className={`mt-1 ${statusColors[entity.status] ?? 'bg-gray-100 text-gray-800'}`}>
              {statusLabel}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>

    {/* 3. Conditional secondary cards (only render if data exists) */}
    {entity.description && (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <AlignLeft className="h-4 w-4 text-muted-foreground" />
            Description
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{entity.description}</p>
        </CardContent>
      </Card>
    )}

    {/* 4. Embedded child table section (optional) */}
    <ChildEntitiesSection
      parentId={entity.id}
      parentStatus={entity.status}
    />

  </div>
);
```

### 5.3 Header Row — Detail Pages

```
[←]  Entity Title                    [Optional CTA]  [Status Badge]
      Reference · subtitle
```

| Element | Detail |
|---|---|
| Back button | `variant="ghost" size="icon"`, icon `<ChevronLeft className="h-4 w-4" />`, `aria-label="Back"` |
| Title block | `<div className="flex-1">` — flex-1 pushes CTA and badge right |
| Title | `<h1 className="text-2xl font-semibold">` |
| Subtitle | `<p className="text-sm text-muted-foreground">` with `<span className="font-mono">` for codes |
| CTA buttons | Optional — `variant="outline"`, placed before status badge |
| Status badge | Always rightmost — custom Tailwind class map, never `variant=` prop |

`handleBack` navigates to the explicit list URL, never to `navigate(-1)`:

```tsx
const handleBack = () => navigate('/service/grc/audit-universe');
```

### 5.4 Cards

One card per logical section. Never use `<Separator>` inside a card to divide it.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';

<Card>
  <CardHeader className="pb-2">
    <CardTitle className="text-base flex items-center gap-2">
      <SectionIcon className="h-4 w-4 text-muted-foreground" />
      Section Name
    </CardTitle>
  </CardHeader>
  <CardContent>
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <p className="text-sm text-muted-foreground">Field Label</p>
        <p className="font-medium">{value ?? '—'}</p>
      </div>
    </div>
  </CardContent>
</Card>
```

Rules:
- `<CardHeader className="pb-2">` — always reduce bottom padding.
- `<CardTitle className="text-base flex items-center gap-2">` — small title (not default large).
- Icon in `<CardTitle>`: `h-4 w-4 text-muted-foreground`.
- Do NOT use `<CardDescription>`.
- Conditional cards: `{entity.field && (<Card>...)}</Card>}` — render nothing when the section has no data.
- Use `'—'` (em dash) as the null/empty placeholder for field values.

### 5.5 Grid Layouts on Detail Pages

| Use Case | Class |
|---|---|
| Standard 2-column data grid | `grid gap-4 md:grid-cols-2` |
| People / roles (4-up) | `grid gap-4 lg:grid-cols-4` |
| 3-column resource grid | `grid gap-4 md:grid-cols-2 lg:grid-cols-3` |
| Single column | default block flow — no grid class |

Field label/value pair:

```tsx
<div>
  <p className="text-sm text-muted-foreground">Field Label</p>
  <p className="font-medium">{value ?? '—'}</p>
</div>
```

For user references (UUID → display name), use `<UserDisplay>`:

```tsx
import { UserDisplay } from '@staff/components/UserDisplay';

<div>
  <p className="text-sm text-muted-foreground">Prepared By</p>
  <UserDisplay userId={entity.prepared_by} className="font-medium mt-1" />
</div>
```

### 5.6 Tabs — Multi-section Detail Pages

For detail pages with multiple distinct sections (e.g., `ConfigurationManagementPage`):

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';

// ALWAYS use controlled tabs (value + onValueChange + useState):
const [activeTab, setActiveTab] = useState('fiscal-years');

<Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
  {/* Grid layout for equal-width tabs (grid-cols-N = number of tabs): */}
  <TabsList className="grid w-full grid-cols-5">
    {/* Icon + text pattern — text hidden on small screens: */}
    <TabsTrigger value="fiscal-years" className="flex items-center gap-2">
      <Calendar className="h-4 w-4" />
      <span className="hidden sm:inline">Fiscal Years</span>
    </TabsTrigger>
    <TabsTrigger value="severities" className="flex items-center gap-2">
      <AlertTriangle className="h-4 w-4" />
      <span className="hidden sm:inline">Severities</span>
    </TabsTrigger>
    <TabsTrigger value="finding-types" className="flex items-center gap-2">
      <FileType className="h-4 w-4" />
      <span className="hidden sm:inline">Finding Types</span>
    </TabsTrigger>
  </TabsList>

  <TabsContent value="fiscal-years" className="space-y-4">
    {/* Each tab content wraps the tab's child component in a Card: */}
    <Card>
      <CardHeader>
        <CardTitle>Fiscal Years</CardTitle>
        <CardDescription>Configure fiscal year periods</CardDescription>
      </CardHeader>
      <CardContent>
        <FiscalYearsTab />
      </CardContent>
    </Card>
  </TabsContent>

  <TabsContent value="severities" className="space-y-4">
    <Card>
      <CardHeader>
        <CardTitle>Audit Severities</CardTitle>
        <CardDescription>Define severity levels for findings</CardDescription>
      </CardHeader>
      <CardContent>
        <AuditSeveritiesTab />
      </CardContent>
    </Card>
  </TabsContent>
</Tabs>
```

Rules:
- **Always use controlled tabs** — `value + onValueChange + useState`. Never use `defaultValue` (uncontrolled).
- `<TabsList className="grid w-full grid-cols-N">` — equal-width tabs via CSS grid. `N` = number of tabs.
- `<TabsTrigger className="flex items-center gap-2">` + icon + `<span className="hidden sm:inline">` — icon visible on mobile, text hidden until `sm` breakpoint.
- Each `<TabsContent>` receives `className="space-y-4"`.
- Tab child components are self-contained — they own their own `useQuery`, `useMutation`, and dialog state.
- Do not pass data down from the tab container to tab children — each tab fetches its own data.
- Tab content wraps the child in a `<Card>` with `<CardHeader>` + `<CardDescription>` + `<CardContent>`.
- Use `Tabs` only when there are 3+ logically distinct sections. For 1–2 sections, use stacked cards.

### 5.7 Embedded Child Table Section Component

When a detail page includes a child list (e.g., auditable entities inside an audit universe), extract it into a self-contained section component:

```tsx
// File: @staff/components/grc/ChildEntitiesSection.tsx

interface ChildEntitiesSectionProps {
  parentId: string;
  parentStatus: string;
}

export function ChildEntitiesSection({ parentId, parentStatus }: ChildEntitiesSectionProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editItem, setEditItem] = useState<Entity | null>(null);
  const [deletingItem, setDeletingItem] = useState<Entity | null>(null);

  const isModifiable = parentStatus === 'draft' || parentStatus === 'under_review';

  const { data, isLoading } = useEntities(1, 200, { parent: parentId });
  const createMutation = useCreateEntity();
  const updateMutation = useUpdateEntity();
  const deleteMutation = useDeleteEntity();

  const entities = (data?.results ?? []).filter((e) => e.is_active !== false);

  return (
    <div className="space-y-4">
      {/* Sub-section header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">Child Entities</h2>
          <p className="text-sm text-muted-foreground">
            {entities.length} {entities.length === 1 ? 'entity' : 'entities'}
          </p>
        </div>
        {isModifiable && (
          <Button size="sm" onClick={() => setIsCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add
          </Button>
        )}
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center text-muted-foreground py-8">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading...
        </div>
      ) : entities.length === 0 ? (
        // Empty state
        <div className="text-center text-muted-foreground py-8 border border-dashed rounded-md">
          No entities added yet.
        </div>
      ) : (
        // Table
        <div className="border rounded-md">
          <Table>
            {/* ... */}
          </Table>
        </div>
      )}

      {/* Create/Edit dialogs */}
      <CreateEntityDialog
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        mode="create"
        defaultParentId={parentId}
        onSuccess={(formData) =>
          createMutation.mutate(formData, { onSuccess: () => setIsCreateOpen(false) })
        }
        isSubmitting={createMutation.isPending}
      />
      {/* ... edit + delete dialogs */}
    </div>
  );
}
```

Rules:
- Section component receives only `parentId` and `parentStatus` as props.
- Section component owns ALL state: `useQuery`, `useMutation`, `useState` for dialogs.
- Fetch with a fixed large page size (e.g., `200`) to load all child records — no pagination inside sections.
- `isModifiable` gates the Add button and row-level Edit/Delete — computed from `parentStatus`.
- Always filter soft-deleted children: `.filter((e) => e.is_active !== false)`.

### 5.8 Loading and Error States — Detail Pages

```tsx
// Loading: centered spinner
if (isLoading) {
  return (
    <div className="flex items-center justify-center min-h-[300px]">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}

// Error / not found
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

Always check in order: loading → error → normal render. Never render partial data.

### 5.9 Status Label Computation

```ts
// Title-case with underscores replaced (verified in AuditPlanDetailPage.tsx):
const statusLabel =
  (entity.status?.charAt(0).toUpperCase() ?? '') +
  (entity.status?.slice(1).replace(/_/g, ' ') ?? '');
// 'management_review' → 'Management review'

// All words Title-Case (alternative):
const statusLabel = entity.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
// 'management_review' → 'Management Review'
```

Be consistent within a file — pick one form and use it throughout.

### 5.10 Status Colors (Reminder)

```ts
const statusColors: Record<string, string> = {
  draft:             'bg-gray-100 text-gray-800',
  approved:          'bg-green-100 text-green-800',
  rejected:          'bg-red-100 text-red-800',
  archived:          'bg-gray-100 text-gray-500',
  under_review:      'bg-yellow-100 text-yellow-800',
  management_review: 'bg-yellow-100 text-yellow-800',
  committee_review:  'bg-blue-100 text-blue-800',
  implementation:    'bg-purple-100 text-purple-800',
  pending:           'bg-yellow-100 text-yellow-800',
  discussed:         'bg-blue-100 text-blue-800',
  final:             'bg-green-100 text-green-800',
  active:            'bg-green-100 text-green-800',
  completed:         'bg-purple-100 text-purple-800',
  submitted:         'bg-blue-100 text-blue-800',
};
// Fallback: 'bg-gray-100 text-gray-800'
```

Always use `<Badge className={statusColors[entity.status] ?? 'bg-gray-100 text-gray-800'}>` — never `<Badge variant="...">` for entity status.

---

## 6. Special Component Patterns

### 6.1 Card with Embedded Table

When a table belongs conceptually inside a card section (e.g., RCM Entries, config lookup list), use `CardContent className="p-0"` so the table extends edge-to-edge. Place the add-entry button in the `CardHeader` using a flex-row layout:

```tsx
import { Skeleton } from '@ui/skeleton';

<Card>
  {/* Flex-row header — title on left, action button on right */}
  <CardHeader className="flex flex-row items-center justify-between pb-3">
    <div>
      <CardTitle className="text-base">RCM Entries</CardTitle>
      <CardDescription>Risk and control pairs for this matrix</CardDescription>
    </div>
    {isEditable && (
      <Button size="sm" onClick={() => setCreateOpen(true)}>
        <PlusCircle className="mr-2 h-4 w-4" />
        Add Entry
      </Button>
    )}
  </CardHeader>

  {/* p-0 removes default padding so the table fills the card edge-to-edge */}
  <CardContent className="p-0">
    {isLoading ? (
      <div className="p-6 space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    ) : entries.length === 0 ? (
      <p className="text-center text-muted-foreground py-10">
        No entries yet. Add the first one using the button above.
      </p>
    ) : (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Process Area</TableHead>
            <TableHead>Risk Description</TableHead>
            <TableHead>Priority</TableHead>
            {isEditable && <TableHead className="w-[80px]" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell className="align-top text-sm">{entry.process_area}</TableCell>
              <TableCell className="align-top text-sm text-muted-foreground">
                {entry.risk_description}
              </TableCell>
              <TableCell className="align-top">
                <Badge variant={entry.priority === 'high' ? 'destructive' : entry.priority === 'medium' ? 'default' : 'secondary'}
                  className="text-xs capitalize">
                  {entry.priority}
                </Badge>
              </TableCell>
              {isEditable && (
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setEditEntry(entry)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive"
                      onClick={() => setDeleteTarget(entry)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )}
  </CardContent>
</Card>
```

Rules:
- `<CardContent className="p-0">` — required when a `<Table>` fills the card.
- `<CardHeader className="flex flex-row items-center justify-between pb-3">` — places button inline with title.
- `<CardDescription>` **IS** used in this pattern (table-in-card headers), contrary to §5.4 which prohibits `CardDescription` on **data-display section cards**. The distinction: section cards (§5.4) never use it; table-in-card section headers may.
- `<Skeleton>` (not spinner) for table loading inside a card.
- Compact action icons: `size="icon" className="h-7 w-7"` with `h-3.5 w-3.5` icons.

### 6.2 Skeleton Loading State

Use `<Skeleton>` from `@ui/skeleton` for content-heavy detail page first-load (better UX than a centred spinner when the page has multiple complex sections):

```tsx
import { Skeleton } from '@ui/skeleton';

if (isLoading) {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-64" />       {/* page title */}
      <Skeleton className="h-32 w-full" />     {/* detail card */}
      <Skeleton className="h-64 w-full" />     {/* table card */}
    </div>
  );
}
```

**When to use Skeleton vs Loader2 spinner:**

| Scenario | Use |
|---|---|
| Detail page first-load (content-heavy) | `<Skeleton>` |
| Dialog loading lookup data | `<Loader2 animate-spin>` inline |
| Inline section loading (child table) | `<Loader2>` inline row |
| Mutation in progress (button) | `<Loader2>` inside button |

### 6.3 Tooltip on Disabled Buttons

Browsers do not fire mouse events on `disabled` HTML elements — wrapping with a `<span>` is required for the `<Tooltip>` to fire:

```tsx
import { Tooltip, TooltipContent, TooltipTrigger } from '@ui/tooltip';

<Tooltip>
  <TooltipTrigger asChild>
    {/* span wrapper required — disabled button swallows pointer events */}
    <span tabIndex={!canProceed ? 0 : undefined}>
      <Button
        onClick={handleAction}
        disabled={isPending || !canProceed}
      >
        {isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
        Start Workflow
      </Button>
    </span>
  </TooltipTrigger>
  {/* Only render tooltip content when the button is actually disabled */}
  {!canProceed && (
    <TooltipContent side="bottom" className="max-w-xs text-center">
      An approved Audit Program and a transmitted Engagement Notification
      are both required before starting the engagement workflow.
    </TooltipContent>
  )}
</Tooltip>
```

Rules:
- `tabIndex={0}` on the span only when the button is disabled — allows keyboard focus for accessibility.
- Only render `<TooltipContent>` inside the `{!canProceed && ...}` gate — avoids a tooltip on a normally-working button.
- `side="bottom"` and `className="max-w-xs text-center"` for multi-line explanations.

### 6.4 Evidence Attachment Section

`<EvidenceAttachmentSection>` at `@staff/components/grc/EvidenceAttachmentSection` handles file upload, download, and delete for Risk Assessments and Working Papers. It is self-contained — no need to replicate its internal logic.

```tsx
import { EvidenceAttachmentSection } from '@staff/components/grc/EvidenceAttachmentSection';

{/* Place inside a Card's CardContent, after the main fields: */}
<EvidenceAttachmentSection
  entityType="working-paper"     // 'risk-assessment' | 'working-paper'
  entityId={paperId}
  readonly={!canEdit}            // hides Upload + Delete when true
/>
```

The component renders:
- `<Separator>` at the top (visual divider from parent card content).
- "Evidence Attachments" heading + "Upload Evidence" outline button (hidden `<input type="file">` triggered on click).
- Table of uploaded files: filename, size, upload date, Download button, Delete button.
- Download uses `documentClient.get(/.../download/, { responseType: 'blob' })`.

Rules:
- Always pass `readonly={!canEdit}` — derive `canEdit` from status + permission in the parent component.
- Place `<EvidenceAttachmentSection>` inside the `<CardContent>` of a detail page card — it starts with its own `<Separator>`.
- Do NOT replicate file upload logic manually — use this component exclusively.

### 6.5 Multi-Action Dialog (No react-hook-form)

Some dialogs represent a workflow step rather than a CRUD form (e.g., `FindingLifecycleDialog` — save responses, then advance status). Use plain `useState` instead of `useForm`:

```tsx
// Local state with dirty tracking
const [auditeeResponse,      setAuditeeResponse]      = useState('');
const [savedAuditeeResponse, setSavedAuditeeResponse] = useState('');
const auditeeResponseDirty = auditeeResponse !== savedAuditeeResponse;

// Mirror current status locally for immediate optimistic UI
const [currentStatus, setCurrentStatus] = useState<'draft' | 'discussed' | 'final'>('draft');

// Key useEffect on entity?.id — NOT the full object — to avoid re-running on every refetch
useEffect(() => {
  if (!entity) return;
  setAuditeeResponse(entity.auditee_response ?? '');
  setSavedAuditeeResponse(entity.auditee_response ?? '');
  setCurrentStatus(entity.status);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [entity?.id]);

// Separate save mutation per field
const handleSaveResponse = () => {
  responseMutation.mutate(
    { id: entity.id, data: { auditee_response: auditeeResponse } },
    { onSuccess: () => setSavedAuditeeResponse(auditeeResponse) },
  );
};

// Status transition mutation — update local mirror on success
const handleTransition = (targetStatus: 'discussed' | 'final' | 'draft') => {
  transitionMutation.mutate(
    { id: entity.id, targetStatus },
    { onSuccess: (updated) => setCurrentStatus(updated.status) },
  );
};

// Precondition gate for transition
const canFinalize = !!savedAuditeeResponse.trim() && !!savedManagementResponse.trim();
```

In the dialog, each response field has its own "Save" button and inline saved/unsaved status indicator:

```tsx
<label className="text-sm font-medium">
  Auditee Response
  {savedAuditeeResponse ? (
    <span className="ml-2 text-xs text-green-600 font-normal">✓ Saved</span>
  ) : (
    <span className="ml-2 text-xs text-amber-600 font-normal">Required for finalisation</span>
  )}
</label>
<Textarea
  value={auditeeResponse}
  onChange={(e) => setAuditeeResponse(e.target.value)}
  disabled={currentStatus === 'final'}
/>
<Button
  size="sm"
  variant="outline"
  onClick={handleSaveResponse}
  disabled={responseMutation.isPending || !auditeeResponse.trim() || !auditeeResponseDirty}
>
  Save Response
</Button>
```

Rules:
- `// eslint-disable-next-line react-hooks/exhaustive-deps` is needed because the exhaustive-deps rule would want all `entity.*` fields in the deps array. Keying on `entity?.id` alone is intentional.
- The transition button shows the current status via a `<Badge>` + `STATUS_LABEL` map at the top of the dialog.
- `<DialogFooter>` has only a "Close" button — no submit; saves happen inline.

### 6.6 Inline Loading Indicator in List Pages

List pages show a non-blocking loading indicator while data fetches — data remains visible if cached, and the error Alert appears inline without hiding the list:

```tsx
{/* Non-blocking inline loading indicator — shows below header while fetching */}
{isLoading && (
  <div className="mb-4 flex items-center rounded-md border border-dashed bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    Loading audit plans...
  </div>
)}

{/* Inline error — visible above the (possibly empty) table */}
{error && (
  <Alert variant="destructive">
    <AlertTitle>Error loading audit plans</AlertTitle>
    <AlertDescription>
      {error instanceof Error ? error.message : 'Failed to load data'}
    </AlertDescription>
  </Alert>
)}
```

Alternative (full-page guard) — used when there is no cached data to show:

```tsx
if (isLoading) {
  return (
    <div className="flex h-full items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}
if (error) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-destructive">Error Loading Data</h2>
        <p className="text-sm text-muted-foreground mt-2">{(error as Error).message}</p>
      </div>
    </div>
  );
}
```

**Prefer the inline indicator** for list pages with paginated data (data is cached between navigations). Use full-page guard for simpler pages or first-time loads.

### 6.7 Date, Number, and Text Formatting Helpers

**Date formatting** — define a local `formatDate` helper in any detail page:

```tsx
const formatDate = (dateStr?: string | null): string => {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
};

// Usage:
<p className="font-medium">{formatDate(entity.created_at)}</p>
// → "March 14, 2026"
```

**Number formatting** — use `.toLocaleString()` for currency and large numbers:

```tsx
<p className="font-medium">
  {entity.budget_allocated?.toLocaleString() ?? '—'} TZS
</p>
```

**Comments / narrative text** — use `italic mt-1` after the label:

```tsx
<div>
  <p className="text-sm text-muted-foreground">Management Comments</p>
  <p className="text-sm leading-relaxed italic mt-1">{entity.management_comments}</p>
</div>
```

**Stacked field-value pairs in grid columns** — use `space-y-3` between fields inside a grid column:

```tsx
<div className="grid gap-4 md:grid-cols-2">
  <div className="space-y-3">
    <div>
      <p className="text-sm text-muted-foreground">Fiscal Year</p>
      <p className="font-medium">{entity.fiscal_year?.year_code ?? 'N/A'}</p>
    </div>
    <div>
      <p className="text-sm text-muted-foreground">Plan Type</p>
      <p className="font-medium">{PLAN_TYPE_LABELS[entity.plan_type] ?? entity.plan_type}</p>
    </div>
  </div>
</div>
```

**Status label computation** — `formatLabel` helper for all-words Title-Case:

```tsx
// Module-scope helper (define once per file that needs it):
function formatLabel(val: string): string {
  return val.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
// 'management_review' → 'Management Review'
// 'under_review'     → 'Under Review'
```

### 6.8 Real-Time Status Polling

For detail pages where status changes externally (e.g., a reviewer approves via the Workflow console), poll at a fixed interval while the entity is in a transitional state:

```tsx
import { useQueryClient } from '@tanstack/react-query';

const queryClient = useQueryClient();

useEffect(() => {
  // Exit condition: stop polling when no longer in transitional state
  if (paper?.review_status !== 'pending') return;

  const timer = setInterval(() => {
    queryClient.invalidateQueries({ queryKey: workingPaperKeys.detail(paperId!) });
  }, 8_000);

  return () => clearInterval(timer);  // cleanup prevents memory leak
}, [paper?.review_status, paperId, queryClient]);
```

Rules:
- Poll only while in a transitional state — the first `if` exits early once resolved.
- Return `clearInterval(timer)` cleanup — prevents memory leaks on unmount/re-render.
- Use `invalidateQueries` (respects stale time) — not `refetchQueries` (forces unconditional refetch).
- 8 seconds is the standard interval for workflow approval polling in GRC pages.

### 6.9 List Page Transform Function Pattern

When `GenericListPage`'s `items` prop needs computed/derived columns (e.g., human-readable enum labels, dates), define a module-scope transform function:

```tsx
// Module scope — NOT inside the component function body
function transformAuditPlanForList(plan: AuditPlan) {
  return {
    id: plan.id,
    title: plan.title,
    reference_number: plan.reference_number,
    fiscalYear: plan.fiscal_year?.year_code || 'N/A',
    planType: plan.plan_type.charAt(0).toUpperCase() + plan.plan_type.slice(1),
    status: plan.status,
    updatedAt: new Date(plan.updated_at || plan.created_at).toLocaleDateString(),
    // Keep original for action handlers:
    _original: plan as any,
  };
}

// In component:
const transformedItems = items.map(transformAuditPlanForList);

// Columns reference the TRANSFORMED keys:
const columns = [
  { key: 'reference_number', label: 'Reference', sortable: true },
  { key: 'fiscalYear',       label: 'Fiscal Year', sortable: true },
  { key: 'planType',         label: 'Type', sortable: true },
  { key: 'status',           label: 'Status', sortable: true },
  { key: 'updatedAt',        label: 'Last Updated', sortable: true },
];
```

Rules:
- Define the transform function at module scope — not inside the component (recreated on every render otherwise).
- Column `key` values match the **transformed** object keys, not the raw API field names.
- Attach `_original: plan` to the transformed item when action handlers need to read original API fields from the items list.
- For columns that use `render`, the render function receives the **raw item** (from `activeItems`, not `transformedItems`) — verify this against the actual `GenericListPage` implementation.


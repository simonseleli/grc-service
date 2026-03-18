# Fix: Delete Button Visibility — Role + Status Based Control

**Originally fixed:** 2026-03-10 (terminal status bug)
**Updated:** 2026-03-14 (per-item role+status control for Risk Assessments)
**Affected modules:** GRC — All list pages (Audit Reports, Recommendations, Plans, Findings, Risk Assessments)

---

## Phase 1 Fix (2026-03-10) — Terminal Status Bug

### Problem

Records in a terminal status (`approved`, `completed`, `closed`, `final`) showed **only a View button** — Delete was gone entirely, even when deletion might be valid for some modules.

### Root Cause

`ListActions.tsx` was too aggressive on terminal statuses:

```tsx
// BEFORE — wiped delete too
allowedActions = allowedActions.filter(a => a === 'view');
```

### Fix

Changed to keep `delete` in the allowed list for terminal items, and let each page's `handleDelete` enforce its own business rule:

```tsx
// AFTER — delete survives the terminal filter
allowedActions = allowedActions.filter(a => a === 'view' || a === 'delete');
```

Each page then guards in `handleDelete`:

```tsx
// Example: AuditReportsPage
if (item.status === 'approved' || item.status === 'distributed') {
  toast.error('Cannot delete this report', { description: '...' });
  return;
}
setDeletingItem(item);
```

---

## Phase 2 Fix (2026-03-14) — Per-Item Role+Status Visibility (Risk Assessments)

### Problem

Risk Assessments required a stricter, **role-aware** approach:
- The delete button was still visible to CIA (wrong role) and on `approved` items (wrong status)
- Clicking it silently did nothing — bad UX

The `approved` status is also terminal, but `delete` was being kept visible (Phase 1 behaviour) and then silently swallowed in `handleDelete`.

### Root Cause (two layers)

1. **`GenericListPage.tsx`** was passing `onDelete={handleDelete}` unconditionally to every row
2. **`ListActions.tsx`** rendered the Delete menu item as long as it was in `allowedActions`, regardless of whether the handler was `undefined`

### Fix — three-layer chain

**Layer 1 — `RiskAssessmentsPage.tsx`**: compute `canDelete` per item

```tsx
// Only IA can delete, and only draft assessments (not yet in the review chain)
const canDelete = item.status === 'draft' && canConductRiskAssessment;
```

This flag travels with the transformed item into `GenericListPage`.

**Layer 2 — `GenericListPage.tsx`**: pass handler conditionally per row

```tsx
onDelete={item.canDelete !== false ? onDelete : undefined}
```

When `canDelete` is `false`, `undefined` is passed as `onDelete` to `ListActions` for that row.

**Layer 3 — `ListActions.tsx`**: remove action when handler is absent

```tsx
if (!onDelete) {
  allowedActions = allowedActions.filter(a => a !== 'delete');
}
if (!onProgressUpdate) {
  allowedActions = allowedActions.filter(a => a !== 'progressUpdate');
}
```

This runs **after** all other role/status logic, so it overrides everything — including the `isTerminal` behaviour that was keeping `delete` visible.

---

## Final Delete Visibility: Risk Assessments

| Status | IA (`canConductRiskAssessment=true`) | CIA (`canConductRiskAssessment=false`) |
|---|---|---|
| `draft` | ✅ Visible & functional | ❌ Hidden |
| `submitted` | ❌ Hidden | ❌ Hidden |
| `reviewed` | ❌ Hidden | ❌ Hidden |
| `approved` | ❌ Hidden | ❌ Hidden |

---

## Delete Policy Per Module

| Module | Can Delete | Cannot Delete | Enforced by |
|---|---|---|---|
| **Risk Assessment** | `draft` (IA only) | `submitted`, `reviewed`, `approved`, and all statuses for CIA | Per-item `canDelete` flag + `ListActions` handler check |
| Audit Report | `draft`, `under_review` | `approved`, `distributed` | `handleDelete` toast guard |
| Audit Recommendation | `open`, `in_progress`, `implemented` | `verified`, `closed` | `handleDelete` toast guard |
| Audit Plan | `draft` | `active`, `completed` | `handleDelete` toast guard |
| Audit Finding | `draft`, `discussed` | — | Backend enforces |
| Audit Monitoring | any | — | Backend enforces if linked rec is `verified`/`closed` |

---

## Two Patterns Available for Future Modules

### Pattern A — Toast guard in `handleDelete` (simple, single-role pages)

Use when: any authenticated user can delete if the status allows it.

```tsx
const handleDelete = (id: string) => {
  const item = findOriginal(id);
  if (!item) return;
  if (['approved', 'distributed'].includes(item.status)) {
    toast.error('Cannot delete', { description: 'This record is final.' });
    return;
  }
  setDeletingItem(item);
};
```

### Pattern B — Per-item `canDelete` flag (role + status aware)

Use when: different roles have different delete permissions, or you want the button completely hidden (not just a toast).

```tsx
// In the transform map:
const canDelete = item.status === 'draft' && canConductPermission;

// In GenericListPage row:
onDelete={item.canDelete !== false ? onDelete : undefined}

// ListActions will automatically hide Delete when onDelete is undefined
```

> **Rule of thumb:** Pattern B is preferred when the button should be **invisible** to unauthorized users. Pattern A is acceptable when all users can see the button but some get a clear error message explaining why it's blocked.

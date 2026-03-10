# Fix: Delete Button Hidden on Terminal-Status Records

**Date:** 2026-03-10  
**Affected module:** GRC — All list pages (Audit Reports, Recommendations, Plans, Findings)

---

## The Problem

On any GRC list page, records in a "terminal" status (e.g. `approved`, `completed`, `closed`, `final`) showed **only a View button** — the Delete button was completely gone from the action menu.

This meant admins could not delete records even when deletion was perfectly safe (e.g. a `draft` audit report is different from a `distributed` one).

---

## Root Cause

**File:** `frontend/packages/shared/src/components/ListActions.tsx`

The shared `ListActions` component had a blanket rule:

```tsx
const terminalStatuses = ['approved', 'completed', 'closed', 'final'];
const isTerminal = terminalStatuses.includes(itemStatus?.toLowerCase() || '');
if (isTerminal) {
  // This wiped out delete too — too aggressive
  allowedActions = allowedActions.filter(a => a === 'view');
}
```

This was intended to block **editing** terminal records (correct), but it also silently removed **delete** from the menu — which is a separate concern that each module needs to decide on its own.

---

## The Fix

### 1. `frontend/packages/shared/src/components/ListActions.tsx`

Changed the filter to allow `delete` through for terminal statuses. Each page's `handleDelete` is now responsible for its own business rule.

```tsx
// BEFORE
allowedActions = allowedActions.filter(a => a === 'view');

// AFTER
allowedActions = allowedActions.filter(a => a === 'view' || a === 'delete');
```

### 2. `frontend/apps/staff-portal/src/pages/grc/AuditReportsPage.tsx`

Added guard in `handleDelete` + imported `toast` from `sonner`:

```tsx
if (item.status === 'approved' || item.status === 'distributed') {
  toast.error('Cannot delete this report', { description: '...' });
  return;
}
// else open delete dialog
```

### 3. `frontend/apps/staff-portal/src/pages/grc/AuditRecommendationsPage.tsx`

Added guard in `handleDelete` + imported `toast`:

```tsx
if (item.status === 'verified' || item.status === 'closed') {
  toast.error('Cannot delete this recommendation', { description: '...' });
  return;
}
```

### 4. `frontend/apps/staff-portal/src/pages/grc/AuditPlansPage.tsx`

Added guard in `handleDelete` + imported `toast`:

```tsx
if (item.status === 'active' || item.status === 'completed') {
  toast.error('Cannot delete this audit plan', { description: '...' });
  return;
}
```

---

## Delete Policy Per Module

| Module | Can Delete | Cannot Delete | Reason blocked |
|---|---|---|---|
| Audit Report | `draft`, `under_review` | `approved`, `distributed` | Approval fires GAP 12 events; distribution is a permanent auditee record |
| Audit Finding | `draft`, `discussed` | — | (backend enforces; `final` shows warning but is deletable) |
| Audit Recommendation | `open`, `in_progress`, `implemented` | `verified`, `closed` | Verified/closed recs are part of the final audit trail |
| Audit Plan | `draft` | `active`, `completed` | Active/completed plans have linked engagements |
| Audit Monitoring | any | — | Backend guards: blocks delete if linked recommendation is `verified`/`closed` |

---

## Result

- The **Delete option now appears** in the action menu for all records, regardless of status.
- Clicking Delete on a **protected record** shows a descriptive toast error explaining why.
- Clicking Delete on a **safe record** opens the normal confirmation dialog as before.
- Edit and workflow actions remain correctly blocked for terminal-status records (unchanged).

---

## Pattern for Future Modules

When adding a new GRC module:
1. `ListActions.tsx` does **not** need changing — it already allows delete through for all statuses.
2. In your page's `handleDelete`, add a guard:
   ```tsx
   const handleDelete = (id: string) => {
     const item = items.find(i => i.id === id);
     if (!item) return;
     if (LOCKED_STATUSES.includes(item.status)) {
       toast.error('Cannot delete', { description: 'Reason why...' });
       return;
     }
     setDeletingItem(item);
   };
   ```
3. The backend should also enforce the same rule independently as a safety net.

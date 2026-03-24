# Risk Management Config Tabs — Implementation Guide
## Frontend Gap: Risk Categories, Likelihoods, Impacts, Levels, NC Types, ISO Clauses

---

## TL;DR — Current State

| Layer | Status |
|-------|--------|
| **Backend models** (`grc-service/apps/core/models/lookups.py`) | ✅ FULLY DONE |
| **Backend serializers** (`lookup_serializers.py`) | ✅ FULLY DONE |
| **Backend API views** (`config_views.py`) | ✅ FULLY DONE |
| **Backend URL routes** (`config_urls.py`) | ✅ FULLY DONE |
| **Frontend TypeScript types** (`types/grc.ts`) | ❌ NOT DONE |
| **Frontend service functions** (`services/grcService.ts`) | ❌ NOT DONE |
| **Frontend hooks** (`hooks/useGRCConfig.ts`) | ❌ NOT DONE |
| **Frontend tab components** (`components/grc/config/`) | ❌ NOT DONE |
| **ConfigurationManagementPage.tsx** | ❌ NOT DONE (missing 6 tabs) |

> Also: `RiskRatingsTab.tsx` already exists but the [+ Add] and [Edit] buttons are
> **disabled** with "Coming Soon" — those mutations exist in `useGRCConfig.ts` but  
> the dialog/form component is never built.

The config page currently shows only 5 tabs, all audit-focused:
```
Fiscal Years | Severities | Finding Types | Risk Ratings | Audit Opinions
```

After implementation it should show **2 groups** (or 11 tabs):
```
── AUDIT CONFIG ─────────────────────────────────────────────────
  Fiscal Years  |  Severities  |  Finding Types  |  Audit Opinions

── RISK CONFIG ──────────────────────────────────────────────────
  Risk Categories  |  Likelihoods  |  Impacts  |  Risk Levels
  Risk Ratings (fix existing)  |  NC Types  |  ISO Clauses
```

---

## What the Backend Provides

### API Endpoints (all under `/api/v1/grc/config/`)

| Endpoint | Methods | View Class |
|----------|---------|------------|
| `config/risk-categories/` | GET, POST | `ConfigRiskCategoryView` |
| `config/risk-categories/<uuid:pk>/` | GET, PUT, DELETE | `ConfigRiskCategoryView` |
| `config/risk-likelihoods/` | GET, POST | `ConfigRiskLikelihoodView` |
| `config/risk-likelihoods/<uuid:pk>/` | GET, PUT, DELETE | `ConfigRiskLikelihoodView` |
| `config/risk-impacts/` | GET, POST | `ConfigRiskImpactView` |
| `config/risk-impacts/<uuid:pk>/` | GET, PUT, DELETE | `ConfigRiskImpactView` |
| `config/risk-levels/` | GET, POST | `ConfigRiskLevelView` |
| `config/risk-levels/<uuid:pk>/` | GET, PUT, DELETE | `ConfigRiskLevelView` |
| `config/non-conformance-types/` | GET, POST | `ConfigNonConformanceTypeView` |
| `config/non-conformance-types/<uuid:pk>/` | GET, PUT, DELETE | `ConfigNonConformanceTypeView` |
| `config/iso-clauses/` | GET, POST | `ConfigISOClauseView` |
| `config/iso-clauses/<uuid:pk>/` | GET, PUT, DELETE | `ConfigISOClauseView` |

DELETE is a soft-delete (sets `is_active = False`).
All UUIDs (uses `<uuid:pk>` in the URL, unlike the older int-PK config items).

### Backend Model Fields (what the API returns)

**RiskCategory** (`grc_risk_category`):
```
id, code, name, description, sort_order, is_active
```

**RiskLikelihood** (`grc_risk_likelihood`):
```
id, code, name, label, numerical_value, sort_order, is_active
```

**RiskImpact** (`grc_risk_impact`):
```
id, code, name, label, numerical_value, sort_order, is_active
```

**RiskLevel** (`grc_risk_level`):
```
id, code, name, min_score, max_score, color_code, sort_order, is_active
```

**NonConformanceType** (`grc_risk_nc_type`):
```
id, code, name, description, sort_order, is_active
```

**ISOClause** (`grc_risk_iso_clause`):
```
id, code, clause_number, title, description, parent_clause (FK self), sort_order, is_active
```

---

## Implementation Steps

There are **5 files to change** and **6 new files to create**.

```
STEP 1 — types/grc.ts              (add 12 interfaces)
STEP 2 — services/grcService.ts    (add 6 endpoint paths + 24 service functions)
STEP 3 — hooks/useGRCConfig.ts     (add 6 query key groups + ~24 hooks)
STEP 4 — components/grc/config/   (create 6 new tab components)
STEP 5 — ConfigurationManagementPage.tsx  (add 6 new tabs)
```

---

## STEP 1 — TypeScript Types (`types/grc.ts`)

Add these interfaces. Place them in the **GRC Config Types** section near `RiskRating`.

```ts
// ========== Risk Management Config Lookup Types ==========

export interface RiskCategory {
  id: string;
  code: string;
  name: string;
  description: string;
  sort_order: number;
  is_active: boolean;
}

export interface RiskCategoryFormData {
  code: string;
  name: string;
  description: string;
  sort_order?: number;
}

export interface RiskLikelihood {
  id: string;
  code: string;
  name: string;
  label: string;
  numerical_value: number;   // DecimalField — DRF may serialize as string; parse on use
  sort_order: number;
  is_active: boolean;
}

export interface RiskLikelihoodFormData {
  code: string;
  name: string;
  label: string;
  numerical_value: number;
  sort_order?: number;
}

export interface RiskImpact {
  id: string;
  code: string;
  name: string;
  label: string;
  numerical_value: number;
  sort_order: number;
  is_active: boolean;
}

export interface RiskImpactFormData {
  code: string;
  name: string;
  label: string;
  numerical_value: number;
  sort_order?: number;
}

export interface RiskLevel {
  id: string;
  code: string;
  name: string;
  min_score: number;
  max_score: number;
  color_code: string;  // hex e.g. '#EF4444'
  sort_order: number;
  is_active: boolean;
}

export interface RiskLevelFormData {
  code: string;
  name: string;
  min_score: number;
  max_score: number;
  color_code: string;
  sort_order?: number;
}

export interface NonConformanceType {
  id: string;
  code: string;
  name: string;
  description: string;
  sort_order: number;
  is_active: boolean;
}

export interface NonConformanceTypeFormData {
  code: string;
  name: string;
  description: string;
  sort_order?: number;
}

export interface ISOClause {
  id: string;
  code: string;
  clause_number: string;  // e.g. "4.1" or "7.1.5"
  title: string;
  description: string;
  parent_clause: string | null;  // UUID of parent ISOClause, or null for top-level
  sort_order: number;
  is_active: boolean;
}

export interface ISOClauseFormData {
  code: string;
  clause_number: string;
  title: string;
  description: string;
  parent_clause?: string | null;
  sort_order?: number;
}
```

---

## STEP 2 — Service Functions (`services/grcService.ts`)

### 2a. Add to `API_PATHS` const (inside the `// Configuration endpoints` section)

```ts
// Risk Management config lookups
riskCategories:         'config/risk-categories/',
riskLikelihoods:        'config/risk-likelihoods/',
riskImpacts:            'config/risk-impacts/',
riskLevels:             'config/risk-levels/',
nonConformanceTypes:    'config/non-conformance-types/',
isoClauses:             'config/iso-clauses/',
```

### 2b. Add service functions (add after the existing `deleteRiskRating` / `fetchAuditOpinions` block)

```ts
// ========== Risk Categories ==========
export async function fetchRiskCategories(): Promise<PaginatedResponse<RiskCategory>> {
  const response = await grcClient.get(ensureTrailingSlash(API_PATHS.riskCategories));
  return mapConfigResponse<RiskCategory>(response);
}

export async function createRiskCategory(data: RiskCategoryFormData): Promise<RiskCategory> {
  const response = await grcClient.post(ensureTrailingSlash(API_PATHS.riskCategories), data);
  return unwrap(response);
}

export async function updateRiskCategory(id: string, data: Partial<RiskCategoryFormData>): Promise<RiskCategory> {
  const response = await grcClient.put(
    `${ensureTrailingSlash(API_PATHS.riskCategories)}${id}/`,
    data
  );
  return unwrap(response);
}

export async function deleteRiskCategory(id: string): Promise<void> {
  await grcClient.delete(`${ensureTrailingSlash(API_PATHS.riskCategories)}${id}/`);
}

// ========== Risk Likelihoods ==========
export async function fetchRiskLikelihoods(): Promise<PaginatedResponse<RiskLikelihood>> {
  const response = await grcClient.get(ensureTrailingSlash(API_PATHS.riskLikelihoods));
  return mapConfigResponse<RiskLikelihood>(response);
}

export async function createRiskLikelihood(data: RiskLikelihoodFormData): Promise<RiskLikelihood> {
  const response = await grcClient.post(ensureTrailingSlash(API_PATHS.riskLikelihoods), data);
  return unwrap(response);
}

export async function updateRiskLikelihood(id: string, data: Partial<RiskLikelihoodFormData>): Promise<RiskLikelihood> {
  const response = await grcClient.put(
    `${ensureTrailingSlash(API_PATHS.riskLikelihoods)}${id}/`,
    data
  );
  return unwrap(response);
}

export async function deleteRiskLikelihood(id: string): Promise<void> {
  await grcClient.delete(`${ensureTrailingSlash(API_PATHS.riskLikelihoods)}${id}/`);
}

// ========== Risk Impacts ==========
export async function fetchRiskImpacts(): Promise<PaginatedResponse<RiskImpact>> {
  const response = await grcClient.get(ensureTrailingSlash(API_PATHS.riskImpacts));
  return mapConfigResponse<RiskImpact>(response);
}

export async function createRiskImpact(data: RiskImpactFormData): Promise<RiskImpact> {
  const response = await grcClient.post(ensureTrailingSlash(API_PATHS.riskImpacts), data);
  return unwrap(response);
}

export async function updateRiskImpact(id: string, data: Partial<RiskImpactFormData>): Promise<RiskImpact> {
  const response = await grcClient.put(
    `${ensureTrailingSlash(API_PATHS.riskImpacts)}${id}/`,
    data
  );
  return unwrap(response);
}

export async function deleteRiskImpact(id: string): Promise<void> {
  await grcClient.delete(`${ensureTrailingSlash(API_PATHS.riskImpacts)}${id}/`);
}

// ========== Risk Levels ==========
export async function fetchRiskLevels(): Promise<PaginatedResponse<RiskLevel>> {
  const response = await grcClient.get(ensureTrailingSlash(API_PATHS.riskLevels));
  return mapConfigResponse<RiskLevel>(response);
}

export async function createRiskLevel(data: RiskLevelFormData): Promise<RiskLevel> {
  const response = await grcClient.post(ensureTrailingSlash(API_PATHS.riskLevels), data);
  return unwrap(response);
}

export async function updateRiskLevel(id: string, data: Partial<RiskLevelFormData>): Promise<RiskLevel> {
  const response = await grcClient.put(
    `${ensureTrailingSlash(API_PATHS.riskLevels)}${id}/`,
    data
  );
  return unwrap(response);
}

export async function deleteRiskLevel(id: string): Promise<void> {
  await grcClient.delete(`${ensureTrailingSlash(API_PATHS.riskLevels)}${id}/`);
}

// ========== Non-Conformance Types ==========
export async function fetchNonConformanceTypes(): Promise<PaginatedResponse<NonConformanceType>> {
  const response = await grcClient.get(ensureTrailingSlash(API_PATHS.nonConformanceTypes));
  return mapConfigResponse<NonConformanceType>(response);
}

export async function createNonConformanceType(data: NonConformanceTypeFormData): Promise<NonConformanceType> {
  const response = await grcClient.post(ensureTrailingSlash(API_PATHS.nonConformanceTypes), data);
  return unwrap(response);
}

export async function updateNonConformanceType(id: string, data: Partial<NonConformanceTypeFormData>): Promise<NonConformanceType> {
  const response = await grcClient.put(
    `${ensureTrailingSlash(API_PATHS.nonConformanceTypes)}${id}/`,
    data
  );
  return unwrap(response);
}

export async function deleteNonConformanceType(id: string): Promise<void> {
  await grcClient.delete(`${ensureTrailingSlash(API_PATHS.nonConformanceTypes)}${id}/`);
}

// ========== ISO Clauses ==========
export async function fetchISOClauses(): Promise<PaginatedResponse<ISOClause>> {
  const response = await grcClient.get(ensureTrailingSlash(API_PATHS.isoClauses));
  return mapConfigResponse<ISOClause>(response);
}

export async function createISOClause(data: ISOClauseFormData): Promise<ISOClause> {
  const response = await grcClient.post(ensureTrailingSlash(API_PATHS.isoClauses), data);
  return unwrap(response);
}

export async function updateISOClause(id: string, data: Partial<ISOClauseFormData>): Promise<ISOClause> {
  const response = await grcClient.put(
    `${ensureTrailingSlash(API_PATHS.isoClauses)}${id}/`,
    data
  );
  return unwrap(response);
}

export async function deleteISOClause(id: string): Promise<void> {
  await grcClient.delete(`${ensureTrailingSlash(API_PATHS.isoClauses)}${id}/`);
}
```

> Note: The backend uses `PUT` (not `PATCH`) for the risk config views (see `_RiskLookupConfigBase.put()`).
> Contrast with the older `int-PK` config items (fiscal years, severities) which use `PATCH`.
> Use `grcClient.put(...)` for these new entities — using `patch` will get a 405.

---

## STEP 3 — TanStack Query Hooks (`hooks/useGRCConfig.ts`)

### 3a. Add to imports (top of file)

Add to the existing type import block:
```ts
import type {
  // ...existing...
  RiskCategory, RiskCategoryFormData,
  RiskLikelihood, RiskLikelihoodFormData,
  RiskImpact, RiskImpactFormData,
  RiskLevel, RiskLevelFormData,
  NonConformanceType, NonConformanceTypeFormData,
  ISOClause, ISOClauseFormData,
} from '@staff/types/grc';
```

### 3b. Add to `GRC_CONFIG_KEYS`

```ts
export const GRC_CONFIG_KEYS = {
  // ...existing keys...
  riskCategories:       ['grc', 'config', 'risk-categories'] as const,
  riskLikelihoods:      ['grc', 'config', 'risk-likelihoods'] as const,
  riskImpacts:          ['grc', 'config', 'risk-impacts'] as const,
  riskLevels:           ['grc', 'config', 'risk-levels'] as const,
  nonConformanceTypes:  ['grc', 'config', 'non-conformance-types'] as const,
  isoClauses:           ['grc', 'config', 'iso-clauses'] as const,
};
```

### 3c. Add hooks (append to end of file)

```ts
// ========== Risk Categories ==========
export function useRiskCategories(enabled: boolean = true) {
  return useQuery({
    queryKey: GRC_CONFIG_KEYS.riskCategories,
    queryFn: grcService.fetchRiskCategories,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateRiskCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskCategoryFormData) => grcService.createRiskCategory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskCategories });
      toast.success('Risk category created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to create risk category');
    },
  });
}

export function useUpdateRiskCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<RiskCategoryFormData> }) =>
      grcService.updateRiskCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskCategories });
      toast.success('Risk category updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to update risk category');
    },
  });
}

export function useDeleteRiskCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.deleteRiskCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskCategories });
      toast.success('Risk category deactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to deactivate risk category');
    },
  });
}

// ========== Risk Likelihoods ==========
export function useRiskLikelihoods(enabled: boolean = true) {
  return useQuery({
    queryKey: GRC_CONFIG_KEYS.riskLikelihoods,
    queryFn: grcService.fetchRiskLikelihoods,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateRiskLikelihood() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskLikelihoodFormData) => grcService.createRiskLikelihood(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskLikelihoods });
      toast.success('Risk likelihood created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to create risk likelihood');
    },
  });
}

export function useUpdateRiskLikelihood() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<RiskLikelihoodFormData> }) =>
      grcService.updateRiskLikelihood(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskLikelihoods });
      toast.success('Risk likelihood updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to update risk likelihood');
    },
  });
}

export function useDeleteRiskLikelihood() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.deleteRiskLikelihood(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskLikelihoods });
      toast.success('Risk likelihood deactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to deactivate risk likelihood');
    },
  });
}

// ========== Risk Impacts ==========
export function useRiskImpacts(enabled: boolean = true) {
  return useQuery({
    queryKey: GRC_CONFIG_KEYS.riskImpacts,
    queryFn: grcService.fetchRiskImpacts,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateRiskImpact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskImpactFormData) => grcService.createRiskImpact(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskImpacts });
      toast.success('Risk impact created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to create risk impact');
    },
  });
}

export function useUpdateRiskImpact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<RiskImpactFormData> }) =>
      grcService.updateRiskImpact(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskImpacts });
      toast.success('Risk impact updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to update risk impact');
    },
  });
}

export function useDeleteRiskImpact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.deleteRiskImpact(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskImpacts });
      toast.success('Risk impact deactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to deactivate risk impact');
    },
  });
}

// ========== Risk Levels ==========
export function useRiskLevels(enabled: boolean = true) {
  return useQuery({
    queryKey: GRC_CONFIG_KEYS.riskLevels,
    queryFn: grcService.fetchRiskLevels,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateRiskLevel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskLevelFormData) => grcService.createRiskLevel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskLevels });
      toast.success('Risk level created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to create risk level');
    },
  });
}

export function useUpdateRiskLevel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<RiskLevelFormData> }) =>
      grcService.updateRiskLevel(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskLevels });
      toast.success('Risk level updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to update risk level');
    },
  });
}

export function useDeleteRiskLevel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.deleteRiskLevel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.riskLevels });
      toast.success('Risk level deactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to deactivate risk level');
    },
  });
}

// ========== Non-Conformance Types ==========
export function useNonConformanceTypes(enabled: boolean = true) {
  return useQuery({
    queryKey: GRC_CONFIG_KEYS.nonConformanceTypes,
    queryFn: grcService.fetchNonConformanceTypes,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateNonConformanceType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: NonConformanceTypeFormData) => grcService.createNonConformanceType(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.nonConformanceTypes });
      toast.success('NC type created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to create NC type');
    },
  });
}

export function useUpdateNonConformanceType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NonConformanceTypeFormData> }) =>
      grcService.updateNonConformanceType(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.nonConformanceTypes });
      toast.success('NC type updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to update NC type');
    },
  });
}

export function useDeleteNonConformanceType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.deleteNonConformanceType(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.nonConformanceTypes });
      toast.success('NC type deactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to deactivate NC type');
    },
  });
}

// ========== ISO Clauses ==========
export function useISOClauses(enabled: boolean = true) {
  return useQuery({
    queryKey: GRC_CONFIG_KEYS.isoClauses,
    queryFn: grcService.fetchISOClauses,
    enabled,
    staleTime: 10 * 60 * 1000, // ISO clauses are stable, 10 min cache
  });
}

export function useCreateISOClause() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ISOClauseFormData) => grcService.createISOClause(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.isoClauses });
      toast.success('ISO clause created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to create ISO clause');
    },
  });
}

export function useUpdateISOClause() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ISOClauseFormData> }) =>
      grcService.updateISOClause(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.isoClauses });
      toast.success('ISO clause updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to update ISO clause');
    },
  });
}

export function useDeleteISOClause() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => grcService.deleteISOClause(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GRC_CONFIG_KEYS.isoClauses });
      toast.success('ISO clause deactivated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Failed to deactivate ISO clause');
    },
  });
}
```

---

## STEP 4 — Tab Components (`components/grc/config/`)

Create 6 new files. Below is the complete code for each.

### 4a. `RiskCategoriesTab.tsx`

```tsx
import { useState } from 'react';
import { Plus, Pencil, Trash2, Loader2, Tag } from 'lucide-react';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@ui/alert-dialog';
import { useRiskCategories, useDeleteRiskCategory } from '@staff/hooks/useGRCConfig';
import type { RiskCategory } from '@staff/types/grc';

export function RiskCategoriesTab() {
  const { data, isLoading, error } = useRiskCategories();
  const deleteMutation = useDeleteRiskCategory();
  const [deletingItem, setDeletingItem] = useState<RiskCategory | null>(null);

  const handleDelete = () => {
    if (deletingItem) {
      deleteMutation.mutate(deletingItem.id, { onSuccess: () => setDeletingItem(null) });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading risk categories...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load risk categories</p>
      </div>
    );
  }

  const items = data?.results ?? [];

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <p className="text-sm text-muted-foreground">
            {items.length} risk categor{items.length !== 1 ? 'ies' : 'y'} configured
          </p>
          <Button size="sm" disabled>
            <Plus className="mr-2 h-4 w-4" />
            Add Category (Coming Soon)
          </Button>
        </div>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Order</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    <Tag className="mx-auto h-8 w-8 mb-2 opacity-50" />
                    <p>No risk categories configured</p>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-sm">{item.code}</TableCell>
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                      {item.description}
                    </TableCell>
                    <TableCell>{item.sort_order}</TableCell>
                    <TableCell>
                      <Badge variant={item.is_active ? 'default' : 'secondary'}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" disabled>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setDeletingItem(item)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <AlertDialog open={!!deletingItem} onOpenChange={() => setDeletingItem(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate Risk Category?</AlertDialogTitle>
            <AlertDialogDescription>
              This will deactivate <strong>{deletingItem?.name}</strong>. It will no longer
              appear as an option on new risk assessment sheets.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Deactivating...</>
              ) : 'Deactivate'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
```

### 4b. `RiskLikelihoodsTab.tsx`

Same pattern as above. Columns: **Code | Name | Label | Value | Order | Status | Actions**

```tsx
import { useState } from 'react';
import { Plus, Pencil, Trash2, Loader2, BarChart2 } from 'lucide-react';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@ui/alert-dialog';
import { useRiskLikelihoods, useDeleteRiskLikelihood } from '@staff/hooks/useGRCConfig';
import type { RiskLikelihood } from '@staff/types/grc';

export function RiskLikelihoodsTab() {
  const { data, isLoading, error } = useRiskLikelihoods();
  const deleteMutation = useDeleteRiskLikelihood();
  const [deletingItem, setDeletingItem] = useState<RiskLikelihood | null>(null);

  const handleDelete = () => {
    if (deletingItem) {
      deleteMutation.mutate(deletingItem.id, { onSuccess: () => setDeletingItem(null) });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading likelihood levels...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load risk likelihoods</p>
      </div>
    );
  }

  const items = data?.results ?? [];

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <p className="text-sm text-muted-foreground">
            {items.length} likelihood level{items.length !== 1 ? 's' : ''} configured
          </p>
          <Button size="sm" disabled>
            <Plus className="mr-2 h-4 w-4" />
            Add Likelihood (Coming Soon)
          </Button>
        </div>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Label</TableHead>
                <TableHead>Numerical Value</TableHead>
                <TableHead>Order</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    <BarChart2 className="mx-auto h-8 w-8 mb-2 opacity-50" />
                    <p>No likelihood levels configured</p>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-sm">{item.code}</TableCell>
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{item.label}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{item.numerical_value}</Badge>
                    </TableCell>
                    <TableCell>{item.sort_order}</TableCell>
                    <TableCell>
                      <Badge variant={item.is_active ? 'default' : 'secondary'}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" disabled>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setDeletingItem(item)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <AlertDialog open={!!deletingItem} onOpenChange={() => setDeletingItem(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate Likelihood Level?</AlertDialogTitle>
            <AlertDialogDescription>
              This will deactivate <strong>{deletingItem?.name}</strong>.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Deactivating...</>
              ) : 'Deactivate'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
```

### 4c. `RiskImpactsTab.tsx`

Identical pattern to `RiskLikelihoodsTab.tsx` — just rename everything from Likelihood → Impact.
Columns: **Code | Name | Label | Numerical Value | Order | Status | Actions**

### 4d. `RiskLevelsTab.tsx`

Columns: **Code | Name | Score Range | Colour | Order | Status | Actions**

```tsx
import { useState } from 'react';
import { Plus, Pencil, Trash2, Loader2, Shield } from 'lucide-react';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@ui/alert-dialog';
import { useRiskLevels, useDeleteRiskLevel } from '@staff/hooks/useGRCConfig';
import type { RiskLevel } from '@staff/types/grc';

export function RiskLevelsTab() {
  const { data, isLoading, error } = useRiskLevels();
  const deleteMutation = useDeleteRiskLevel();
  const [deletingItem, setDeletingItem] = useState<RiskLevel | null>(null);

  const handleDelete = () => {
    if (deletingItem) {
      deleteMutation.mutate(deletingItem.id, { onSuccess: () => setDeletingItem(null) });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading risk levels...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load risk levels</p>
      </div>
    );
  }

  const items = data?.results ?? [];

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <p className="text-sm text-muted-foreground">
            {items.length} risk level{items.length !== 1 ? 's' : ''} configured
          </p>
          <Button size="sm" disabled>
            <Plus className="mr-2 h-4 w-4" />
            Add Risk Level (Coming Soon)
          </Button>
        </div>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Score Range</TableHead>
                <TableHead>Colour</TableHead>
                <TableHead>Order</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    <Shield className="mx-auto h-8 w-8 mb-2 opacity-50" />
                    <p>No risk levels configured</p>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-sm">{item.code}</TableCell>
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {item.min_score} – {item.max_score}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div
                          className="h-4 w-4 rounded-full border"
                          style={{ backgroundColor: item.color_code }}
                        />
                        <span className="font-mono text-xs">{item.color_code}</span>
                      </div>
                    </TableCell>
                    <TableCell>{item.sort_order}</TableCell>
                    <TableCell>
                      <Badge variant={item.is_active ? 'default' : 'secondary'}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" disabled>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setDeletingItem(item)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <AlertDialog open={!!deletingItem} onOpenChange={() => setDeletingItem(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate Risk Level?</AlertDialogTitle>
            <AlertDialogDescription>
              This will deactivate <strong>{deletingItem?.name}</strong>
              (score range {deletingItem?.min_score}–{deletingItem?.max_score}).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Deactivating...</>
              ) : 'Deactivate'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
```

### 4e. `NonConformanceTypesTab.tsx`

Same pattern as `RiskCategoriesTab.tsx` — just rename everything to NonConformanceType.
Columns: **Code | Name | Description | Order | Status | Actions**
Import: `useNonConformanceTypes, useDeleteNonConformanceType`

### 4f. `ISOClausesTab.tsx`

Columns: **Clause No. | Code | Title | Parent Clause | Order | Status | Actions**
Special: `parent_clause` is a UUID — on display, look up the parent's `clause_number` from the items list.
Import: `useISOClauses, useDeleteISOClause`

```tsx
// ISOClausesTab.tsx — key difference: hierarchical display + parent_clause lookup
const items = data?.results ?? [];
const clauseMap = new Map(items.map((c) => [c.id, c]));

// In the table row:
// <TableCell>{item.clause_number}</TableCell>
// <TableCell className="font-mono text-sm">{item.code}</TableCell>
// <TableCell className="font-medium">{item.title}</TableCell>
// <TableCell className="text-sm text-muted-foreground">
//   {item.parent_clause ? clauseMap.get(item.parent_clause)?.clause_number ?? '—' : '—'}
// </TableCell>
```

---

## STEP 5 — Update `ConfigurationManagementPage.tsx`

The current page uses a **5-column tab grid**. Adding 6 more tabs to a single flat grid would overflow on small screens.

The recommended approach is to split into **two `TabsList` rows** — one for Audit Config, one for Risk Config — or use a sidebar tab navigation.

The simpler approach that matches the existing `grid-cols-5` pattern is to just add to the grid and split onto two rows, which Tailwind handles automatically with `flex-wrap`:

### Replace the `TabsList` with two groups:

```tsx
// Replace the existing <TabsList className="grid w-full grid-cols-5"> block:

<div className="space-y-2">
  {/* Audit Configuration */}
  <div>
    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1 px-1">
      Audit Configuration
    </p>
    <TabsList className="grid w-full grid-cols-4">
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
      <TabsTrigger value="audit-opinions" className="flex items-center gap-2">
        <MessageSquare className="h-4 w-4" />
        <span className="hidden sm:inline">Audit Opinions</span>
      </TabsTrigger>
    </TabsList>
  </div>

  {/* Risk Management Configuration */}
  <div>
    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1 px-1">
      Risk &amp; QMS Configuration
    </p>
    <TabsList className="grid w-full grid-cols-6">
      <TabsTrigger value="risk-categories" className="flex items-center gap-2">
        <Tag className="h-4 w-4" />
        <span className="hidden sm:inline">Risk Categories</span>
      </TabsTrigger>
      <TabsTrigger value="risk-likelihoods" className="flex items-center gap-2">
        <BarChart2 className="h-4 w-4" />
        <span className="hidden sm:inline">Likelihoods</span>
      </TabsTrigger>
      <TabsTrigger value="risk-impacts" className="flex items-center gap-2">
        <Zap className="h-4 w-4" />
        <span className="hidden sm:inline">Impacts</span>
      </TabsTrigger>
      <TabsTrigger value="risk-levels" className="flex items-center gap-2">
        <Shield className="h-4 w-4" />
        <span className="hidden sm:inline">Risk Levels</span>
      </TabsTrigger>
      <TabsTrigger value="risk-ratings" className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4" />
        <span className="hidden sm:inline">Risk Ratings</span>
      </TabsTrigger>
      <TabsTrigger value="nc-types" className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4" />
        <span className="hidden sm:inline">NC Types</span>
      </TabsTrigger>
    </TabsList>
  </div>
</div>
```

### Add new icon imports to `ConfigurationManagementPage.tsx`:
```ts
import {
  Settings, Calendar, AlertTriangle, FileType, TrendingUp, RefreshCw, MessageSquare,
  Tag, BarChart2, Zap, Shield, AlertCircle,   // ← add these
} from 'lucide-react';
```

### Add new tab component imports:
```ts
import { RiskCategoriesTab } from '@staff/components/grc/config/RiskCategoriesTab';
import { RiskLikelihoodsTab } from '@staff/components/grc/config/RiskLikelihoodsTab';
import { RiskImpactsTab } from '@staff/components/grc/config/RiskImpactsTab';
import { RiskLevelsTab } from '@staff/components/grc/config/RiskLevelsTab';
import { NonConformanceTypesTab } from '@staff/components/grc/config/NonConformanceTypesTab';
import { ISOClausesTab } from '@staff/components/grc/config/ISOClausesTab';
```

### Add new `TabsContent` blocks (after the existing `audit-opinions` content):

```tsx
<TabsContent value="risk-categories" className="space-y-4">
  <Card>
    <CardHeader>
      <CardTitle>Risk Categories</CardTitle>
      <CardDescription>
        Classify risks by type — used on Risk Assessment Sheets and the IRR
      </CardDescription>
    </CardHeader>
    <CardContent><RiskCategoriesTab /></CardContent>
  </Card>
</TabsContent>

<TabsContent value="risk-likelihoods" className="space-y-4">
  <Card>
    <CardHeader>
      <CardTitle>Risk Likelihoods</CardTitle>
      <CardDescription>
        Standardized 1–5 likelihood scale used in the risk scoring matrix
      </CardDescription>
    </CardHeader>
    <CardContent><RiskLikelihoodsTab /></CardContent>
  </Card>
</TabsContent>

<TabsContent value="risk-impacts" className="space-y-4">
  <Card>
    <CardHeader>
      <CardTitle>Risk Impacts</CardTitle>
      <CardDescription>
        Standardized 1–5 impact scale used in the risk scoring matrix
      </CardDescription>
    </CardHeader>
    <CardContent><RiskImpactsTab /></CardContent>
  </Card>
</TabsContent>

<TabsContent value="risk-levels" className="space-y-4">
  <Card>
    <CardHeader>
      <CardTitle>Risk Levels</CardTitle>
      <CardDescription>
        Score thresholds for auto-classification — e.g. Low (1–5), Medium (6–12), High (13–25)
      </CardDescription>
    </CardHeader>
    <CardContent><RiskLevelsTab /></CardContent>
  </Card>
</TabsContent>

<TabsContent value="nc-types" className="space-y-4">
  <Card>
    <CardHeader>
      <CardTitle>Non-Conformance Types</CardTitle>
      <CardDescription>
        Major / Minor / Observation categories used on QMS Non-Conformances
      </CardDescription>
    </CardHeader>
    <CardContent><NonConformanceTypesTab /></CardContent>
  </Card>
</TabsContent>

<TabsContent value="iso-clauses" className="space-y-4">
  <Card>
    <CardHeader>
      <CardTitle>ISO 9001:2015 Clauses</CardTitle>
      <CardDescription>
        Clause hierarchy used on QMS Checklists and Non-Conformances (e.g. 4.1, 7.1.5)
      </CardDescription>
    </CardHeader>
    <CardContent><ISOClausesTab /></CardContent>
  </Card>
</TabsContent>
```

> Note: ISO Clauses are currently excluded from the second `TabsList` row above.
> They can be added as an 8th tab in the Risk & QMS group (7 columns total), or placed
> in a separate "QMS" row if the layout becomes too wide.

---

## STEP 6 — Fix `RiskRatingsTab.tsx` (Bonus)

The existing tab shows **[Add Risk Rating (Coming Soon)]** and disabled edit buttons.
The mutation hooks already exist (`useCreateRiskRating`, `useUpdateRiskRating`).

To fix: create a `RiskRatingDialog.tsx` form component and wire up the Create button.

Fields to collect:
```
name *       string
code *       string (auto-uppercase safe)
description  string
numerical_value *  number (1–25 or as configured)
color_code * string (hex color picker)
sort_order   number (default 0)
```

Then in `RiskRatingsTab.tsx`:
- Replace the disabled `<Button>` with `onClick={() => setIsCreateOpen(true)}`
- Enable the edit pencil button with `onClick={() => setEditingItem(item)}`
- Add `<RiskRatingDialog open={isCreateOpen} onClose={...} />` at bottom

---

## Secondary Impact: Lookup Dropdowns in Risk Pages

These config lookups are needed **not just for configuration** — they also power the dropdowns
in the Risk Assessment Sheet creation dialog and NC creation dialog.

### `CreateRiskAssessmentSheetDialog.tsx` needs:
```ts
// Currently may be using hardcoded strings or plain text inputs for:
// - risk_category  → should be a <Select> from useRiskCategories()
// - likelihood     → should be a <Select> from useRiskLikelihoods()
// - impact         → should be a <Select> from useRiskImpacts()
```

### `CreateNonConformanceDialog.tsx` needs:
```ts
// - nc_type (major/minor/observation)  → <Select> from useNonConformanceTypes()
// - iso_clause_violated                → <Select> from useISOClauses()
//   (hierarchical: group by parent_clause, or flat list sorted by clause_number)
```

> Check these dialogs — if they use text inputs today, wire them to the new hooks after
> implementing Steps 1–5.

---

## Summary Checklist

```
□ Step 1 — types/grc.ts: add 12 interfaces (6 entity + 6 FormData)
□ Step 2 — grcService.ts:
      □ 6 API_PATHS constants
      □ 24 service functions (fetch/create/update/delete × 6)
□ Step 3 — useGRCConfig.ts:
      □ 6 GRC_CONFIG_KEYS entries
      □ import 12 new types
      □ 24 hooks (useX, useCreateX, useUpdateX, useDeleteX × 6)
□ Step 4 — Create 6 tab component files:
      □ RiskCategoriesTab.tsx
      □ RiskLikelihoodsTab.tsx
      □ RiskImpactsTab.tsx
      □ RiskLevelsTab.tsx
      □ NonConformanceTypesTab.tsx
      □ ISOClausesTab.tsx
□ Step 5 — ConfigurationManagementPage.tsx:
      □ Add 6+ icon imports
      □ Add 6 tab component imports
      □ Split TabsList into Audit / Risk & QMS groups
      □ Add 6 TabsContent blocks
□ Step 6 (bonus) — Fix RiskRatingsTab: enable Create + Edit buttons
□ Step 7 (risk pages) — Wire dropdowns in:
      □ CreateRiskAssessmentSheetDialog (category, likelihood, impact)
      □ CreateNonConformanceDialog (nc_type, iso_clause)
```

---

*Backend is 100% ready. The frontend gap is entirely additive — no backend changes needed.*

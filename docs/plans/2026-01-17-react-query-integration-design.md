# React Query Integration Design

**Date:** 2026-01-17
**Status:** Implemented

## Problem

The frontend had several UX architecture issues:

1. **No caching** - Same data (project, materials, styles) fetched multiple times across pages
2. **Manual state management** - Each page used separate `useState` + `useEffect` for data
3. **No request deduplication** - Navigating between pages caused redundant API calls
4. **Manual polling** - Render job status polling implemented with `setInterval`
5. **No optimistic updates** - Actions didn't reflect immediately in UI

## Solution: React Query (TanStack Query)

Added React Query for server state management with these benefits:

- **Automatic caching** - Data cached for 30 seconds (stale) / 5 minutes (gc)
- **Request deduplication** - Same query only fetches once
- **Background refetching** - Data stays fresh automatically
- **Built-in polling** - `refetchInterval` replaces manual setInterval
- **Mutation hooks** - Clean separation of read/write operations

## Architecture

### Query Client Provider

```
src/components/Providers.tsx  - Client-side QueryClientProvider
src/app/layout.tsx            - Wraps app with Providers
```

Configuration:
- `staleTime: 30s` - Data considered fresh for 30 seconds
- `gcTime: 5min` - Cache data for 5 minutes
- `retry: 1` - Retry failed requests once
- `refetchOnWindowFocus: false` (dev) / `true` (prod)

### Custom Hooks

All hooks defined in `src/lib/hooks.ts`:

**Query Hooks (read):**
- `useProjects()` - List all projects
- `useProject(id)` - Get single project (cached across pages)
- `useMaterials()` - Get material library (long cache)
- `useStylePresets()` - Get style presets
- `useRenderStyles()` - Get render styles
- `usePipelineStatus()` - Check DALL-E availability
- `useBatchJob(id, { polling })` - Get batch job with optional 2s polling
- `usePreview(projectId)` - Get floor plan preview

**Mutation Hooks (write):**
- `useCreateProject()` - Create project, invalidates projects cache
- `useDeleteProject()` - Delete project, invalidates projects cache
- `useUploadFile(projectId)` - Upload file, invalidates project/floorPlan caches
- `useStartBatchRender()` - Start render job
- `useCancelBatchJob()` - Cancel render job

### Query Keys

Centralized query keys for cache management:

```typescript
export const queryKeys = {
  projects: ['projects'],
  project: (id) => ['project', id],
  floorPlan: (projectId) => ['floorPlan', projectId],
  materials: ['materials'],
  // ...
};
```

## Changes Made

### Home Page (`src/app/page.tsx`)
- Replaced `useState` + `useEffect` with `useProjects()` hook
- Replaced manual create/delete with mutation hooks
- Refresh button calls `refetch()` instead of custom function

### Project Page (`src/app/project/[id]/page.tsx`)
- Replaced manual fetch with `useProject(projectId)` hook
- Upload uses mutation hook with cache invalidation
- Reduced code from 55 lines to 26 lines for data handling

### Render Page (`src/app/project/[id]/render/page.tsx`)
- Replaced 5 parallel API calls with 5 query hooks
- Replaced manual `setInterval` polling with `useBatchJob` polling option
- Mutations handle render start/cancel

## Benefits

1. **Shared cache** - Navigate from project page to render page: project data already cached
2. **Automatic refetch** - Come back to tab: data refreshes in background
3. **Less code** - Removed ~60 lines of manual state/effect logic
4. **Better UX** - Faster perceived navigation due to cached data
5. **Simpler polling** - React Query handles interval cleanup automatically

## Future Improvements

- Add error boundaries with `useQueryErrorResetBoundary`
- Add suspense mode for loading states
- Consider optimistic updates for mutations
- Add prefetching for anticipated navigations

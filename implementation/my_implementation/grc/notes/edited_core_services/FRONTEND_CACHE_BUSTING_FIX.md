# Core Service Edit — Frontend PWA Cache + API Gateway Cache Headers

> **Files touched:**
> - `frontend/apps/staff-portal/vite.config.ts`
> - `api-gateway/config/nginx.conf`
>
> **Date:** March 17, 2026
> **Author:** GRC service developer
> **For senior review:** Yes — affects all staff-portal users across all browsers.

---

## 1. Summary of the Changes

### File 1: `frontend/apps/staff-portal/vite.config.ts`

In the VitePWA Workbox configuration:

1. **Removed `html` from `globPatterns`** — changed from `"**/*.{js,css,html,ico,png,svg,woff,woff2}"` to `"**/*.{js,css,ico,png,svg,woff,woff2}"` so `index.html` is no longer precached by the service worker.
2. **Added `navigateFallback: null`** and **`navigateFallbackDenylist: [/./]`** — prevents the service worker's NavigationRoute from intercepting page navigations and serving a cached `index.html`.

```ts
// BEFORE
workbox: {
    globPatterns: ["**/*.{js,css,html,ico,png,svg,woff,woff2}"],
    cleanupOutdatedCaches: true,
    clientsClaim: true,
    skipWaiting: true,
    ...
}

// AFTER
workbox: {
    globPatterns: ["**/*.{js,css,ico,png,svg,woff,woff2}"],
    navigateFallback: null,
    navigateFallbackDenylist: [/./],
    cleanupOutdatedCaches: true,
    clientsClaim: true,
    skipWaiting: true,
    ...
}
```

### File 2: `api-gateway/config/nginx.conf`

In the `location / { }` block (the frontend proxy catch-all at line ~1565):

Added three lines at the end of the block to strip ETag and force `no-store`:

```nginx
# Strip ETag + force no-store so browsers never serve stale HTML
# after source changes (HMR is disabled in this setup).
proxy_hide_header ETag;
add_header Cache-Control "no-store" always;
```

**Nothing else in either file was modified.**

---

## 2. The Problem

After rebuilding the staff-portal Docker image (`docker compose -f docker-compose.prod-local.yml build --no-cache staff-portal`) and restarting the container, **the browser continued to show the old UI**. The new UI was only visible after a hard refresh (Shift+Ctrl+R). Logging out and back in would show the old UI again.

This affected Chrome, Firefox, and Microsoft Edge.

---

## 3. Root Cause

The staff-portal uses **VitePWA** (`vite-plugin-pwa`) which registers a **Workbox service worker** in production builds. The Workbox config had:

1. **`globPatterns: ["**/*.{js,css,html,...}"]`** — This precached `index.html` into the service worker's internal cache (CacheStorage), separate from the browser's HTTP cache.
2. **`registerType: "autoUpdate"` with `skipWaiting: true` and `clientsClaim: true`** — The service worker takes control immediately.
3. **A `NavigationRoute`** — Workbox automatically registered a NavigationRoute that intercepted ALL page navigations (including login redirects) and served the precached `index.html` from CacheStorage.

The effect: every page navigation was intercepted by the service worker **before** the request ever reached the network. The service worker served its cached copy of `index.html`, which pointed to **old** JS chunk filenames. Since Vite uses content-hashed filenames for JS/CSS bundles, the old `index.html` referenced chunks that no longer existed in the new build — or worse, it loaded old chunks that did still exist in the service worker's precache.

**Hard refresh (Shift+Ctrl+R)** bypasses the service worker entirely — that's why it worked. But normal navigation, login/logout redirects, and typing the URL all go through the service worker, which served stale content.

---

## 4. Why Two Changes Were Needed

### The primary fix — `vite.config.ts` (service worker)

This is what actually solved the problem. By removing `html` from `globPatterns` and disabling the navigation fallback:
- `index.html` is no longer stored in CacheStorage
- Page navigations go directly to the network (nginx → `serve` static server)
- After a rebuild, the browser fetches the fresh `index.html` which references new JS chunk hashes

JS/CSS chunks remain cached by the service worker (via `StaleWhileRevalidate`), which is fine because Vite generates content-hashed filenames — a new build produces new filenames that won't collide with old cache entries.

### The safety net — `nginx.conf` (HTTP cache headers)

With the service worker no longer intercepting `index.html`, the browser's HTTP cache becomes the next layer that could serve stale content. The `Cache-Control: no-store` header tells the browser to **never** store `index.html` in its HTTP cache at all. The `proxy_hide_header ETag` prevents conditional caching via `If-None-Match`.

Without this, the browser could still cache `index.html` via standard HTTP caching (304 Not Modified responses, disk cache, etc.). This is the belt to the service worker fix's suspenders.

---

## 5. Impact

- **Staff-portal only.** The client-portal is not affected (it has its own build config).
- **PWA still works.** The manifest, icons, offline fonts/images, and JS/CSS caching are all intact. Only `index.html` is excluded from precaching.
- **Performance impact: negligible.** `index.html` is a small file (~2-4 KB). Fetching it fresh on each navigation adds one small network request. All heavy assets (JS, CSS, fonts, images) remain cached.
- **One-time browser action required.** Users who already had the old service worker installed needed to manually unregister it once (DevTools → Application → Service Workers → Unregister). After that, the new service worker (without `index.html` precaching) takes over permanently.

---

## 6. How to Verify

After rebuilding and restarting the staff-portal container:

```bash
# Check nginx sends no-store
curl -sI http://localhost:8080/ -H "Host: fcc-staff" | grep -i cache
# Expected: Cache-Control: no-store

# Rebuild and restart
cd frontend
docker compose -f docker-compose.prod-local.yml build staff-portal
docker compose -f docker-compose.prod-local.yml up -d staff-portal

# Open browser → navigate to staff portal → changes should be visible without hard refresh
```

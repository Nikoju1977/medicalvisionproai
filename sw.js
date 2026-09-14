/* Cache only the application shell. Never cache API responses or patient data. */
'use strict';
const BUILD = 'v16.2.0';
const SHELL = 'medvision-shell-' + BUILD;
const VENDOR = 'medvision-vendor-' + BUILD;
const PRECACHE = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png',
    './icon-maskable-192.png', './icon-maskable-512.png', './apple-touch-icon.png'];
const shellURLs = new Set(PRECACHE.map(path => new URL(path, self.registration.scope).href));
const vendorURLs = new Set(['https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js']);

self.addEventListener('install', event => {
    event.waitUntil(caches.open(SHELL).then(async cache => {
        // Keep the previous offline version if the replacement shell cannot load.
        await cache.addAll(['./', './index.html'].map(path => new Request(path, { cache: 'reload' })));
        await Promise.all(PRECACHE.slice(2).map(path => cache.add(new Request(path, { cache: 'reload' })).catch(() => {})));
        await self.skipWaiting();
    }));
});
self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys
        .filter(key => key.startsWith('medvision-') && key !== SHELL && key !== VENDOR)
        .map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
async function networkFirst(request) {
    const cache = await caches.open(SHELL);
    try {
        const response = await fetch(request);
        if (response.ok) { await cache.put(request, response.clone()).catch(() => {}); return response; }
        return await cache.match(request) || response;
    } catch (error) {
        return await cache.match(request) || await cache.match('./index.html') ||
            new Response('Hors ligne : reconnectez-vous une fois pour charger MedVision.', {
                status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' }
            });
    }
}
async function cacheFirst(request, name) {
    const cache = await caches.open(name);
    const cached = await cache.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone()).catch(() => {});
    return response;
}
self.addEventListener('fetch', event => {
    const request = event.request;
    // Allowlist includes path AND query. Same-origin API endpoints are excluded.
    if (request.method !== 'GET' || request.headers.has('authorization')) return;
    if (shellURLs.has(request.url)) {
        event.respondWith(request.mode === 'navigate' ? networkFirst(request) : cacheFirst(request, SHELL));
    } else if (vendorURLs.has(request.url)) {
        event.respondWith(cacheFirst(request, VENDOR));
    }
});
self.addEventListener('message', event => {
    const data = event.data || {};
    if (data.type === 'SKIP_WAITING') self.skipWaiting();
    if (data.type === 'GET_VERSION' && event.source) event.source.postMessage({ type: 'VERSION', build: BUILD });
    if (data.type === 'PURGE') event.waitUntil(caches.keys().then(keys => Promise.all(keys
        .filter(key => key.startsWith('medvision-')).map(key => caches.delete(key)))));
});

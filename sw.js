/* MedVision AI Pro — Service Worker
   Studio Niko Design · v12

   Règle cardinale : aucune donnée de santé ni aucune réponse de l'API Mistral
   ne doit être mise en cache. Seule la coquille applicative est stockée.
   Les examens et rapports restent dans IndexedDB, sous le contrôle de l'app.   */

'use strict';

const BUILD = 'v12.0.0';
const SHELL = 'medvision-shell-' + BUILD;
const VENDOR = 'medvision-vendor-' + BUILD;

// Chemins relatifs : fonctionne aussi bien à la racine que dans un sous-dossier
// GitHub Pages (/medicalvisionproai/).
const PRECACHE = [
    './',
    './index.html',
    './manifest.json',
    './icon-192.png',
    './icon-512.png',
    './icon-maskable-192.png',
    './icon-maskable-512.png',
    './apple-touch-icon.png'
];

// Hôtes dont les réponses ne doivent JAMAIS toucher le cache.
const NEVER_CACHE = [
    'api.mistral.ai',
    'api.groq.com',
    'api.cerebras.ai',
    'api.openai.com',
    'api.anthropic.com'
];

// Ressources tierces stables : mise en cache autorisée.
const VENDOR_HOSTS = [
    'fonts.googleapis.com',
    'fonts.gstatic.com',
    'cdnjs.cloudflare.com'
];

function isNeverCache(url) {
    return NEVER_CACHE.indexOf(url.hostname) >= 0;
}

function isVendor(url) {
    return VENDOR_HOSTS.indexOf(url.hostname) >= 0;
}

// ---------- Installation ----------
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(SHELL)
            // addAll est atomique : un seul 404 ferait échouer toute l'installation.
            // On tolère les absences pour ne jamais bloquer la mise à jour.
            .then(cache => Promise.all(PRECACHE.map(u =>
                cache.add(new Request(u, { cache: 'reload' })).catch(() => null)
            )))
            .then(() => self.skipWaiting())
    );
});

// ---------- Activation ----------
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys.filter(k => k.indexOf('medvision-') === 0 && k !== SHELL && k !== VENDOR)
                    .map(k => caches.delete(k))
            ))
            .then(() => self.clients.claim())
    );
});

// ---------- Stratégies ----------
function networkFirst(request, cacheName, fallback) {
    return fetch(request)
        .then(res => {
            if (res && res.ok) {
                const copy = res.clone();
                caches.open(cacheName).then(c => c.put(request, copy)).catch(() => {});
            }
            return res;
        })
        .catch(() => caches.match(request)
            .then(hit => hit || (fallback ? caches.match(fallback) : undefined))
            .then(hit => hit || new Response(
                '<!doctype html><meta charset="utf-8"><title>Hors ligne</title>' +
                '<body style="background:#050a12;color:#e8eef5;font-family:system-ui;padding:32px">' +
                '<h1 style="color:#06d6a0">Hors ligne</h1>' +
                '<p>MedVision n\'a pas encore été mis en cache sur cet appareil. ' +
                'Reconnectez-vous une fois pour terminer l\'installation.</p></body>',
                { headers: { 'Content-Type': 'text/html; charset=utf-8' }, status: 503 }
            ))
        );
}

function cacheFirst(request, cacheName) {
    return caches.match(request).then(hit => {
        if (hit) {
            // Rafraîchissement silencieux en arrière-plan
            fetch(request).then(res => {
                if (res && res.ok) caches.open(cacheName).then(c => c.put(request, res.clone())).catch(() => {});
            }).catch(() => {});
            return hit;
        }
        return fetch(request).then(res => {
            if (res && res.ok) {
                const copy = res.clone();
                caches.open(cacheName).then(c => c.put(request, copy)).catch(() => {});
            }
            return res;
        });
    });
}

self.addEventListener('fetch', event => {
    const req = event.request;

    // On ne touche qu'aux GET : POST vers l'API, uploads, etc. passent directement.
    if (req.method !== 'GET') return;

    let url;
    try { url = new URL(req.url); } catch (e) { return; }

    // Appels d'inférence : réseau seul, jamais interceptés ni stockés.
    if (isNeverCache(url)) return;

    // Schémas non http(s) (chrome-extension:, data:, blob:…)
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

    // Navigation : réseau d'abord pour recevoir les mises à jour,
    // repli sur la coquille en cache hors ligne.
    if (req.mode === 'navigate') {
        event.respondWith(networkFirst(req, SHELL, './index.html'));
        return;
    }

    // Polices et bibliothèques tierces : cache d'abord.
    if (isVendor(url)) {
        event.respondWith(cacheFirst(req, VENDOR));
        return;
    }

    // Même origine : cache d'abord (coquille, icônes, manifeste).
    if (url.origin === self.location.origin) {
        event.respondWith(cacheFirst(req, SHELL));
        return;
    }

    // Le reste part au réseau sans interception.
});

// ---------- Messages depuis la page ----------
self.addEventListener('message', event => {
    const d = event.data || {};
    if (d.type === 'SKIP_WAITING') self.skipWaiting();
    if (d.type === 'GET_VERSION' && event.source) event.source.postMessage({ type: 'VERSION', build: BUILD });
    if (d.type === 'PURGE') {
        event.waitUntil(caches.keys().then(ks => Promise.all(
            ks.filter(k => k.indexOf('medvision-') === 0).map(k => caches.delete(k))
        )));
    }
});

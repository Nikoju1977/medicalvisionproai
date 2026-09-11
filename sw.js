/* MedVision AI Pro — service worker
 * Studio Niko Design — Nicolas Julienne
 *
 * L'application enregistrait ./sw.js sans que ce fichier existe : l'appel
 * echouait dans un catch vide, `beforeinstallprompt` n'etait jamais emis et le
 * bouton « Installer » restait invisible en permanence.
 *
 * Perimetre volontairement etroit, pour un dispositif medical :
 *   - on met en cache la COQUILLE (document, jsPDF, polices) ;
 *   - on ne met JAMAIS en cache une requete vers un fournisseur IA ;
 *   - on ne met JAMAIS en cache une donnee de sante : images, comptes rendus et
 *     identites restent dans IndexedDB, chiffres, hors de portee du worker.
 */
'use strict';

const VERSION = 'medvision-v16.1';
const SHELL = VERSION + '-shell';

// Hotes dont la reponse ne doit jamais etre conservee.
const NEVER_CACHE = /(^|\.)(mistral\.ai|openai\.com|anthropic\.com)$/i;

// Hotes de coquille autorises au cache (CDN de jsPDF et polices).
const SHELL_HOSTS = /(^|\.)(cdnjs\.cloudflare\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)$/i;

self.addEventListener('install', e => {
    self.skipWaiting();
    e.waitUntil(caches.open(SHELL).then(c => c.add('./').catch(() => null)));
});

self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys()
            .then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

// Message depuis la page : purge complete (utile au verrouillage / changement de poste).
self.addEventListener('message', e => {
    if (e.data === 'purge') {
        e.waitUntil(caches.keys().then(ks => Promise.all(ks.map(k => caches.delete(k)))));
    }
});

self.addEventListener('fetch', e => {
    const req = e.request;
    if (req.method !== 'GET') return;                 // aucun POST n'est intercepte

    let url;
    try { url = new URL(req.url); } catch (err) { return; }
    if (!/^https?:$/.test(url.protocol)) return;
    if (NEVER_CACHE.test(url.hostname)) return;       // appels IA : passe-plat strict

    const sameOrigin = url.origin === self.location.origin;
    if (!sameOrigin && !SHELL_HOSTS.test(url.hostname)) return;

    // Navigation : reseau d'abord, cache en secours (hors ligne / reseau hospitalier coupe).
    if (req.mode === 'navigate') {
        e.respondWith(
            fetch(req)
                .then(r => {
                    const copy = r.clone();
                    caches.open(SHELL).then(c => c.put('./', copy)).catch(() => {});
                    return r;
                })
                .catch(() => caches.match('./').then(r => r || Response.error()))
        );
        return;
    }

    // Coquille statique : cache d'abord, revalidation en arriere-plan.
    e.respondWith(
        caches.match(req).then(hit => {
            const net = fetch(req)
                .then(r => {
                    if (r && (r.ok || r.type === 'opaque')) {
                        const copy = r.clone();
                        caches.open(SHELL).then(c => c.put(req, copy)).catch(() => {});
                    }
                    return r;
                })
                .catch(() => hit || Response.error());
            return hit || net;
        })
    );
});

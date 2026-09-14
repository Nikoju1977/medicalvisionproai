const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('sw.js', 'utf8');

function worker() {
    const listeners = {}, puts = [], deleted = [];
    let fail = false;
    const entries = new Map();
    const cache = {
        addAll: async () => { if (fail) throw new Error('Offline'); }, add: async () => {},
        match: async request => entries.get(typeof request === 'string' ? request : request.url),
        put: async (request, response) => { puts.push(request.url); entries.set(request.url, response); }
    };
    const context = {
        URL, Request, Response, Set, Promise,
        self: { registration: { scope: 'https://example.test/medicalvisionproai/' },
            addEventListener: (name, fn) => { listeners[name] = fn; },
            skipWaiting: () => { context.activated = true; }, clients: { claim() {} } },
        caches: { open: async () => cache, keys: async () => ['medvision-shell-old', 'other-app-cache'], delete: async k => { deleted.push(k); } },
        fetch: async () => { if (fail) throw new Error('Offline'); return new Response('shell'); }
    };
    // Browser Request accepts relative URLs; Node Request requires absolute URLs.
    context.Request = class extends Request { constructor(input, init) { super(new URL(input, context.self.registration.scope), init); } };
    vm.runInNewContext(source, context);
    return { listeners, puts, deleted, cache, entries, context, offline() { fail = true; } };
}
test('service worker never intercepts inference, patient endpoints, authorized requests or query URLs', async () => {
    const h = worker();
    for (const request of [
        new Request('https://api.mistral.ai/v1/models'),
        new Request('https://example.test/medicalvisionproai/patients/1'),
        new Request('https://example.test/medicalvisionproai/index.html?patient=1'),
        new Request('https://example.test/medicalvisionproai/index.html', { headers: { Authorization: 'Bearer test' } }),
        new Request('https://private.test/v1/chat/completions', { method: 'POST' })
    ]) {
        let intercepted = false; h.listeners.fetch({ request, respondWith() { intercepted = true; } });
        assert.equal(intercepted, false, request.url);
    }
    let promise;
    h.listeners.fetch({ request: new Request('https://example.test/medicalvisionproai/index.html'), respondWith(p) { promise = p; } });
    assert.equal((await promise).status, 200); assert.equal(h.puts.length, 1);
});
test('a failed shell installation keeps the previous cache and does not activate', async () => {
    const h = worker(); h.offline(); let promise;
    h.listeners.install({ waitUntil(p) { promise = p; } });
    await assert.rejects(promise, /Offline/); assert.equal(h.context.activated, undefined); assert.equal(h.deleted.length, 0);
});
test('offline navigation serves the cached shell', async () => {
    const h = worker(); h.entries.set('./index.html', new Response('cached shell')); h.offline(); let promise;
    h.listeners.fetch({ request: { method: 'GET', mode: 'navigate', url: 'https://example.test/medicalvisionproai/', headers: new Headers() }, respondWith(p) { promise = p; } });
    assert.equal(await (await promise).text(), 'cached shell');
});

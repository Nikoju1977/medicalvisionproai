const { test } = require('node:test');
const assert = require('node:assert/strict');
const { runtime } = require('./runtime.cjs');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

function app(t) { const host = runtime(); host.api.RL.minGap = 0; t.after(() => host.close()); return host; }
function mock(host, respond) {
    const calls = [];
    host.w.XMLHttpRequest = class {
        constructor() { this.headers = {}; }
        open(method, url) { this.method = method; this.url = url; }
        setRequestHeader(k, v) { this.headers[k] = v; }
        getResponseHeader(k) { return this.responseHeaders?.[k] || null; }
        send(payload) {
            const call = { url: this.url, method: this.method, body: payload ? JSON.parse(payload) : null, headers: this.headers };
            calls.push(call);
            this.timer = setTimeout(() => {
                const answer = respond(call);
                if (answer.hang) return;
                this.status = answer.status || 200; this.responseHeaders = answer.headers;
                this.responseText = JSON.stringify(answer.body); this.onload();
            }, 5);
        }
        abort() { clearTimeout(this.timer); this.onabort?.(); }
    };
    return calls;
}
const catalogue = { data: [{ id: 'ministral-14b-2512', capabilities: { vision: true } }] };
const response = value => ({ choices: [{ finish_reason: 'stop', message: { content: JSON.stringify(value) } }] });
function configure(host) {
    host.w.document.getElementById('akIn').value = 'synthetic-test-key'; host.w.saveKey();
}
async function picture(host, name = 'test.png', shade = '#ccc') {
    const canvas = host.canvas.createCanvas(100, 100), ctx = canvas.getContext('2d');
    ctx.fillStyle = shade; ctx.fillRect(0, 0, 100, 100);
    const file = new host.w.File([canvas.toBuffer('image/png')], name, { type: 'image/png' });
    return { file, item: await host.api.mkItem(canvas.toDataURL(), name, 'image', null) };
}
async function imported(host) {
    const p = await picture(host); await host.api.hFile({ files: [p.file], value: '' }); return p;
}
async function waitDone(host) {
    for (let n = 0; n < 500 && (host.api.S.busy || host.api.S.batchRunning); n++) await pause(20);
    assert.equal(host.api.S.busy, false, 'analysis released busy state');
    assert.equal(host.api.S.batchRunning, false, 'batch finished');
    assert.deepEqual(host.errors, [], 'no unhandled application errors');
}

test('invalid settings and failed diagnostics preserve the active connection', async t => {
    const h = app(t); configure(h);
    const before = JSON.stringify({ provider: h.api.S.provider, ak: h.api.S.ak });
    h.w.document.getElementById('providerSel').value = 'medgemma';
    h.w.document.getElementById('customBaseIn').value = 'javascript:invalid';
    h.w.saveKey(); await h.w.diagAPI();
    assert.equal(JSON.stringify({ provider: h.api.S.provider, ak: h.api.S.ak }), before);
    assert.equal(h.api.S.diagnosing, false);
    assert.equal(h.api.normalizeEndpoint('https://example.test/v1/chat/completions/'), 'https://example.test/v1');
    assert.equal(h.api.normalizeEndpoint('http://localhost:11434'), 'http://localhost:11434/v1');
    for (const url of ['http://example.test/v1', 'https://user:pass@example.test/v1', 'https://example.test/v1?key=secret']) assert.throws(() => h.api.normalizeEndpoint(url));
});
test('model discovery refuses non-vision models and propagates authentication failures', async t => {
    const h = app(t); configure(h);
    assert.equal(h.api.visionModels([{ id: 'ministral-14b-2512', capabilities: { vision: false } }, { id: 'unknown-text-model' }]).length, 0);
    assert.equal(h.api.visionModels([{ id: 'future-vision', capabilities: { vision: true } }])[0].id, 'future-vision');
    const calls = mock(h, () => ({ status: 401, body: { message: 'Invalid API key' } }));
    await assert.rejects(h.api.discoverModels(), e => e.status === 401);
    assert.equal(calls.length, 1); assert.ok(calls[0].url.endsWith('/models'));
});
test('general analysis discovers the configured model and renders a visible result', async t => {
    const h = app(t); configure(h); await imported(h);
    h.w.document.getElementById('genMode').checked = true;
    const calls = mock(h, c => ({ body: c.url.endsWith('/models') ? catalogue : response({ description: 'Carré gris de test', elements: [], limites: [] }) }));
    h.w.runAI(); await waitDone(h);
    const output = h.w.document.getElementById('aiO');
    assert.ok(output.classList.contains('vis')); assert.match(output.innerHTML, /Carré gris/);
    assert.equal(calls[1].body.model, 'ministral-14b-2512'); assert.equal(h.api.S.lastReport, null);
});
test('one corrupt file does not discard valid images and image limit is enforced before decoding', async t => {
    const h = app(t), good = await picture(h);
    const bad = new h.w.File(['not a PNG'], 'corrupt.png', { type: 'image/png' });
    await h.api.hFile({ files: [bad, good.file], value: '' });
    assert.equal(h.api.S.series.length, 1);
    assert.match(h.w.document.getElementById('importStatus').textContent, /corrupt.png/);
    h.api.S.series = Array.from({ length: 23 }, (_, i) => ({ ...good.item, id: 'i' + i }));
    await h.api.hFile({ files: [good.file, good.file, good.file], value: '' });
    assert.equal(h.api.S.series.length, 24);
});
test('deleting the active image preserves annotations on its neighbour', async t => {
    const h = app(t), a = (await picture(h, 'a.png')).item, b = (await picture(h, 'b.png')).item;
    a.ann.meas = [{ id: 'measurement-A', a: {x: 1, y: 1}, b: {x: 5, y: 5} }]; b.ann.meas = [{ id: 'measurement-B', a: {x: 2, y: 2}, b: {x: 8, y: 8} }];
    h.api.S.series = [a, b]; h.api.setActive(0, true); h.api.delItem(0);
    assert.equal(h.api.S.series[0].name, 'b.png');
    assert.equal(h.api.S.meas[0].id, 'measurement-B'); assert.equal(h.api.S.lastReport, null);
});
test('ROI indices are global after chunk remapping, including the ninth image', async t => {
    const h = app(t), p = (await picture(h)).item;
    h.api.S.series = Array.from({ length: 10 }, (_, i) => ({ ...p, id: 'i' + i, ann: { ...p.ann, aiRois: [] } }));
    h.api.S.imgSet = { map: [0, 0, 1, 1], parts: [] }; h.api.S.chunks = [];
    h.api.finish({ findings: [], rois: [{ image: 9, xmin: .1, ymin: .1, xmax: .2, ymax: .2 }] }, ['gen'], {}, Date.now(), 0);
    assert.equal(h.api.S.series[8].ann.aiRois.length, 1);
    assert.equal(h.api.S.series[1].ann.aiRois.length, 0);
});
test('MedGemma receives OpenAI image objects and uses its own model after provider changes', async t => {
    const h = app(t); configure(h); h.api.S.mdlVision = 'old-mistral-model';
    const $ = id => h.w.document.getElementById(id);
    $('providerSel').value = 'medgemma'; $('customBaseIn').value = 'https://private.example/v1'; $('customModelIn').value = 'medgemma-local';
    h.w.saveKey(); await imported(h); $('genMode').checked = true;
    const calls = mock(h, () => ({ body: response({ description: 'Objet de test' }) }));
    h.w.runAI(); await waitDone(h);
    assert.equal(calls[0].url, 'https://private.example/v1/chat/completions');
    assert.equal(calls[0].body.model, 'medgemma-local');
    assert.equal(typeof calls[0].body.messages[1].content[1].image_url.url, 'string');
    assert.equal(calls[0].headers.Authorization, undefined);
});
test('cancellation aborts pending HTTP and queued work without producing a report', async t => {
    const h = app(t); configure(h); await imported(h);
    h.w.document.getElementById('genMode').checked = true;
    const calls = mock(h, c => c.url.endsWith('/models') ? { body: catalogue } : { hang: true });
    h.w.runAI(); for (let n = 0; n < 100 && calls.length < 2; n++) await pause(10);
    assert.equal(calls.length, 2); h.w.cancelAnalysis(); await waitDone(h);
    assert.match(h.w.document.getElementById('aiO').innerHTML, /arrêtée/);
    assert.equal(h.api.RL.active, 0); assert.equal(h.api.RL.q.length, 0); assert.equal(h.api.S.lastReport, null);
    const controller = new AbortController(); h.api.RL.until = Date.now() + 60000;
    const queued = h.api.mcall({ body: {}, signal: controller.signal }); controller.abort();
    await assert.rejects(queued, e => e.status === -2); assert.equal(h.api.RL.q.length, 0);
});
test('manual batch mode triages every independent image and finishes even when one is unanalysable', async t => {
    const h = app(t); configure(h);
    const a = await picture(h, 'a.png', '#333'), b = await picture(h, 'b.png', '#eee');
    await h.api.hFile({ files: [a.file, b.file], value: '' });
    const $ = id => h.w.document.getElementById(id);
    $('modeSel').value = 'batch'; h.w.setMode(); $('zoomOff').checked = true; h.w.setZoom();
    const triages = [];
    mock(h, c => {
        if (c.url.endsWith('/models')) return { body: catalogue };
        const text = JSON.stringify(c.body.messages);
        if (text.includes('technicien en imagerie')) {
            triages.push(c.body.messages[1].content[1].image_url);
            return { body: response({ modalite: 'Radiographie', region: 'Thorax', incidence: 'Face', qualite: 'test', artefacts: [], analysable: triages.length !== 2 }) };
        }
        return { body: response({ severite: 'nonev', findings: [], rois: [], limites: ['Test technique uniquement'] }) };
    });
    h.w.runAI(); await waitDone(h);
    assert.equal(triages.length, 2); assert.notEqual(triages[0], triages[1]);
    assert.equal(h.api.S.batch.length, 2); assert.match(h.api.S.batch[1].err, /non analysable/);
    assert.equal(h.api.S.only, null); assert.equal(h.api.S.lastReport, null);
});
test('encrypted save/load restores all images, annotations and context without appending to another exam', async t => {
    const h = app(t), rows = [];
    h.api.S.db = { transaction() {
        const tx = { objectStore() { return {
            add(record) { rows.push(record); setTimeout(() => tx.oncomplete?.(), 0); },
            index() { return { getAll(pid) { const req = {}; setTimeout(() => { req.result = rows.filter(r => r.pid === pid); req.onsuccess(); }, 0); return req; } }; }
        }; } }; return tx;
    } };
    await h.api.VAULT.create('123456');
    const a = await picture(h, 'a.png'), b = await picture(h, 'b.png');
    await h.api.hFile({ files: [a.file, b.file], value: '' });
    const $ = id => h.w.document.getElementById(id);
    $('patL').value = '1'; $('notes').value = 'Synthetic note'; $('ctxInd').value = 'Synthetic context';
    h.api.S.series[1].ann.meas = [{ id: 'B' }];
    await h.w.saveExam();
    assert.equal(rows.length, 1); assert.equal(rows[0].data._enc, 'A256GCM');
    assert.ok(!JSON.stringify(rows[0]).includes('Synthetic note'));
    h.w.clrSeries(); await imported(h); $('notes').value = 'Other context';
    await h.w.loadPat();
    assert.equal(h.api.S.series.length, 2); assert.equal(h.api.S.series[1].ann.meas[0].id, 'B');
    assert.equal($('notes').value, 'Synthetic note'); assert.equal($('ctxInd').value, 'Synthetic context');
    $('patL').value = '2'; await h.w.loadPat();
    assert.equal(h.api.S.series.length, 0); assert.equal($('notes').value, '');
});
test('content-block JSON replies work and missing model errors do not retry four schema variants', async t => {
    const h = app(t); configure(h);
    let calls = mock(h, () => ({ body: { choices: [{ message: { content: [{ type: 'text', text: '{"ok":true}' }] } }] } }));
    const schema = { name: 'test', def: { type: 'object', properties: { ok: { type: 'boolean' } } } };
    assert.equal((await h.api.mchat('model', [{ role: 'system', content: 'JSON' }], schema)).ok, true);
    calls = mock(h, () => ({ status: 404, body: { message: 'Unknown model' } }));
    await assert.rejects(h.api.mchat('missing', [{ role: 'system', content: 'JSON' }], schema), e => e.status === 404);
    assert.equal(calls.length, 1);
    assert.equal(h.api.retryDelay('2'), 2);
    assert.ok(h.api.retryDelay(new Date(Date.now() + 5000).toUTCString()) > 3);
});

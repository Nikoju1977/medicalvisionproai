const { test } = require('node:test');
const assert = require('node:assert/strict');
const { runtime } = require('./runtime.cjs');

test('production triage never routes a saved MedGemma model through Mistral', async t => {
    const h = runtime('dist/index.html'); t.after(() => h.close());
    const s = h.api.S;
    s.provider = 'mistral';
    s.customModel = 'google/medgemma-1.5-4b-it';
    s.mdlForce = '';
    s.mdlPool = [{ id: 'ministral-14b-2512', rank: 100 }];
    await h.api.prepareModels();
    assert.equal(h.api.medicalModelFor('triage', 'triage'), 'ministral-14b-2512');
    assert.deepEqual(Array.from(h.api.medicalAvailableModels(), m => m.id), ['ministral-14b-2512']);
});

test('production custom endpoint uses only advertised models when available', async t => {
    const h = runtime('dist/index.html'); t.after(() => h.close());
    const s = h.api.S;
    s.provider = 'medgemma';
    s.customModel = 'google/medgemma-1.5-4b-it';
    s.mdlForce = s.customModel;
    s.mdlPool = [{ id: 'server-vision-model', rank: 20 }];
    await h.api.prepareModels();
    assert.equal(h.api.medicalModelFor('triage', 'triage'), 'server-vision-model');
    assert.deepEqual(Array.from(h.api.medicalAvailableModels(), m => m.id), ['server-vision-model']);
});

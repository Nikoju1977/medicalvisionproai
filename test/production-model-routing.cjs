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


test('production medical skills route pulmonary CT to the pulmonary skill with safety guardrails', async t => {
    const h = runtime('dist/index.html'); t.after(() => h.close());
    const selected = Array.from(h.api.medicalSkillsFor({
        agent: 'pulmo', modality: 'CT thorax', region: 'thorax', purpose: 'vision', text: 'nodule pulmonaire'
    }), x => x.name);
    assert.ok(selected.includes('pulmonary-nodule-characterization'));
    assert.ok(selected.includes('dicom-quality-and-calibration-review'));
    const prompt = h.api.medicalSkillsPrompt({
        agent: 'pulmo', modality: 'CT', region: 'thorax', purpose: 'vision', text: 'nodule'
    });
    assert.match(prompt, /validation humaine/i);
    assert.match(prompt, /UNKNOWN/);
});

test('every production medical skill is draft-only and requires human review', async t => {
    const h = runtime('dist/index.html'); t.after(() => h.close());
    assert.ok(h.api.MEDICAL_SKILLS.length >= 15);
    for (const skill of h.api.MEDICAL_SKILLS) {
        assert.equal(skill.metadata.draft_only, true, skill.name);
        assert.equal(skill.metadata.human_review_required, true, skill.name);
    }
});


test('benchmark disable hook requires explicit benchmark mode', async t => {
    const h = runtime('dist/index.html'); t.after(() => h.close());
    const context = { agent: 'pulmo', modality: 'CT', region: 'thorax', purpose: 'vision', text: 'nodule pulmonaire' };

    h.w.__MEDVISION_BENCH_DISABLE_SKILLS = true;
    assert.match(h.api.medicalSkillsPrompt(context), /SKILL pulmonary-nodule-characterization/);

    h.w.__MEDVISION_BENCH_MODE = true;
    assert.equal(h.api.medicalSkillsPrompt(context), '');

    h.w.__MEDVISION_BENCH_DISABLE_SKILLS = false;
    assert.match(h.api.medicalSkillsPrompt(context), /SKILL pulmonary-nodule-characterization/);
});

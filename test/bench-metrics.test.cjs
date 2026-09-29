const { test } = require('node:test');
const assert = require('node:assert/strict');
const { lexicalScore, summarize, compareAB, mcnemarExact } = require('./bench-metrics.cjs');

test('lexical annotation scoring supports alternatives and forbidden terms', () => {
    const s = lexicalScore('Opacité alvéolaire basale droite. Pas de pneumothorax.', {
        expected_terms_any: [['opacité', 'condensation'], ['droite', 'right']],
        forbidden_terms: ['fracture']
    });
    assert.equal(s.required_groups, 2);
    assert.equal(s.required_matched, 2);
    assert.equal(s.required_coverage, 1);
    assert.equal(s.forbidden_hits, 0);
});

test('benchmark summary calculates diagnostic and efficiency metrics', () => {
    const rows = [
        { statut: 'ok', label: 'anomalie', predit: 'anomalie', anomalies: 1, ms: 100, usage: { requests: 2, request_chars: 1000, total_tokens: 100 } },
        { statut: 'ok', label: 'anomalie', predit: 'normal', anomalies: 0, ms: 200, usage: { requests: 2, request_chars: 900, total_tokens: 90 } },
        { statut: 'ok', label: 'normal', predit: 'normal', anomalies: 0, ms: 150, usage: { requests: 2, request_chars: 800, total_tokens: 80 } },
        { statut: 'ok', label: 'normal', predit: 'anomalie', anomalies: 2, ms: 250, usage: { requests: 2, request_chars: 1100, total_tokens: 110 } }
    ];
    const s = summarize(rows);
    assert.equal(s.sensitivity, 0.5);
    assert.equal(s.specificity, 0.5);
    assert.equal(s.accuracy, 0.5);
    assert.equal(s.false_positive_findings_per_normal, 1);
    assert.equal(s.median_ms, 175);
    assert.equal(s.mean_total_tokens, 95);
});

test('paired A/B comparison counts direction of corrected errors', () => {
    const rows = [
        { condition: 'baseline', case_id: 'a', statut: 'ok', label: 'anomalie', predit: 'normal', ms: 100, model_signature: 'm1', usage: {} },
        { condition: 'skills', case_id: 'a', statut: 'ok', label: 'anomalie', predit: 'anomalie', ms: 120, model_signature: 'm1', usage: {} },
        { condition: 'baseline', case_id: 'b', statut: 'ok', label: 'normal', predit: 'normal', ms: 100, model_signature: 'm1', usage: {} },
        { condition: 'skills', case_id: 'b', statut: 'ok', label: 'normal', predit: 'normal', ms: 110, model_signature: 'm1', usage: {} },
        { condition: 'baseline', case_id: 'c', statut: 'ok', label: 'normal', predit: 'normal', ms: 100, model_signature: 'm1', usage: {} },
        { condition: 'skills', case_id: 'c', statut: 'ok', label: 'normal', predit: 'anomalie', ms: 110, model_signature: 'm1', usage: {} }
    ];
    const c = compareAB(rows);
    assert.equal(c.paired.eligible_pairs, 3);
    assert.equal(c.paired.skills_correct_baseline_wrong, 1);
    assert.equal(c.paired.baseline_correct_skills_wrong, 1);
    assert.equal(c.paired.both_correct, 1);
    assert.equal(c.paired.mcnemar_exact_p, 1);
    assert.equal(mcnemarExact(0, 0), 1);
});

test('A/B comparison excludes model mismatches by default', () => {
    const rows = [
        { condition: 'baseline', case_id: 'x', statut: 'ok', label: 'normal', predit: 'normal', model_signature: 'm1', usage: {} },
        { condition: 'skills', case_id: 'x', statut: 'ok', label: 'normal', predit: 'normal', model_signature: 'm2', usage: {} }
    ];
    const c = compareAB(rows);
    assert.equal(c.paired.eligible_pairs, 0);
    assert.equal(c.paired.excluded_model_mismatch, 1);
});

'use strict';

function ratio(a, b) {
    return b ? a / b : null;
}

function median(values) {
    const xs = values.filter(Number.isFinite).slice().sort((a, b) => a - b);
    if (!xs.length) return null;
    const m = Math.floor(xs.length / 2);
    return xs.length % 2 ? xs[m] : (xs[m - 1] + xs[m]) / 2;
}

function mean(values) {
    const xs = values.filter(Number.isFinite);
    return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
}

function wilson(successes, total, z = 1.96) {
    if (!total) return null;
    const p = successes / total;
    const z2 = z * z;
    const den = 1 + z2 / total;
    const center = (p + z2 / (2 * total)) / den;
    const half = z * Math.sqrt((p * (1 - p) + z2 / (4 * total)) / total) / den;
    return { low: Math.max(0, center - half), high: Math.min(1, center + half) };
}

function choose(n, k) {
    if (k < 0 || k > n) return 0;
    k = Math.min(k, n - k);
    let out = 1;
    for (let i = 1; i <= k; i++) out = out * (n - k + i) / i;
    return out;
}

function mcnemarExact(skillsWin, baselineWin) {
    const n = skillsWin + baselineWin;
    if (!n) return 1;
    const k = Math.min(skillsWin, baselineWin);
    let tail = 0;
    for (let i = 0; i <= k; i++) tail += choose(n, i) * Math.pow(0.5, n);
    return Math.min(1, 2 * tail);
}

function normalizeText(value) {
    return String(value == null ? '' : value)
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();
}

function lexicalScore(text, item) {
    const haystack = normalizeText(text);
    const groups = Array.isArray(item.expected_terms_any) ? item.expected_terms_any : [];
    const forbidden = Array.isArray(item.forbidden_terms) ? item.forbidden_terms : [];
    const requiredMatched = groups.filter(group => {
        const terms = Array.isArray(group) ? group : [group];
        return terms.some(term => haystack.includes(normalizeText(term)));
    }).length;
    const forbiddenHits = forbidden.filter(term => haystack.includes(normalizeText(term)));
    return {
        required_groups: groups.length,
        required_matched: requiredMatched,
        required_coverage: groups.length ? requiredMatched / groups.length : null,
        forbidden_hits: forbiddenHits.length,
        forbidden_terms_hit: forbiddenHits
    };
}

function summarize(rows) {
    const ok = rows.filter(r => r.statut === 'ok');
    const vp = ok.filter(r => r.label === 'anomalie' && r.predit === 'anomalie').length;
    const fn = ok.filter(r => r.label === 'anomalie' && r.predit === 'normal').length;
    const vn = ok.filter(r => r.label === 'normal' && r.predit === 'normal').length;
    const fp = ok.filter(r => r.label === 'normal' && r.predit === 'anomalie').length;
    const normalRows = ok.filter(r => r.label === 'normal');

    const sensitivity = ratio(vp, vp + fn);
    const specificity = ratio(vn, vn + fp);
    const accuracy = ratio(vp + vn, ok.length);
    const usages = ok.map(r => r.usage || {});
    const withTokenUsage = usages.filter(u => Number.isFinite(u.total_tokens) && u.total_tokens > 0);
    const lexical = ok.filter(r => Number.isFinite(r.required_coverage));

    return {
        submitted: rows.length,
        completed: ok.length,
        failed: rows.filter(r => r.statut === 'echec' || r.statut === 'erreur').length,
        non_analyzable: rows.filter(r => r.statut === 'non_analysable').length,
        confusion: { vp, fn, vn, fp },
        sensitivity,
        sensitivity_ci95: wilson(vp, vp + fn),
        specificity,
        specificity_ci95: wilson(vn, vn + fp),
        accuracy,
        accuracy_ci95: wilson(vp + vn, ok.length),
        false_positive_findings_per_normal: normalRows.length
            ? normalRows.reduce((a, r) => a + (Number(r.anomalies) || 0), 0) / normalRows.length : null,
        median_ms: median(ok.map(r => Number(r.ms))),
        mean_requests: mean(usages.map(u => Number(u.requests))),
        mean_request_chars: mean(usages.map(u => Number(u.request_chars))),
        token_usage_available_cases: withTokenUsage.length,
        mean_total_tokens: mean(withTokenUsage.map(u => Number(u.total_tokens))),
        mean_prompt_tokens: mean(withTokenUsage.map(u => Number(u.prompt_tokens))),
        mean_completion_tokens: mean(withTokenUsage.map(u => Number(u.completion_tokens))),
        mean_required_coverage: mean(lexical.map(r => Number(r.required_coverage))),
        mean_forbidden_hits: mean(ok.map(r => Number(r.forbidden_hits) || 0))
    };
}

function compareAB(rows, options = {}) {
    const baseline = rows.filter(r => r.condition === 'baseline');
    const skills = rows.filter(r => r.condition === 'skills');
    const baseSummary = summarize(baseline);
    const skillsSummary = summarize(skills);
    const key = r => String(r.case_id || r.file || '');
    const bm = new Map(baseline.map(r => [key(r), r]));
    const sm = new Map(skills.map(r => [key(r), r]));
    const pairs = [];

    for (const [id, b] of bm) {
        const s = sm.get(id);
        if (!s) continue;
        const sameModel = !b.model_signature || !s.model_signature || b.model_signature === s.model_signature;
        if (options.requireSameModel !== false && !sameModel) continue;
        if (b.statut !== 'ok' || s.statut !== 'ok') continue;
        pairs.push({ id, baseline: b, skills: s, sameModel });
    }

    let skillsWin = 0, baselineWin = 0, bothCorrect = 0, bothWrong = 0;
    for (const p of pairs) {
        const bc = p.baseline.predit === p.baseline.label;
        const sc = p.skills.predit === p.skills.label;
        if (sc && !bc) skillsWin++;
        else if (bc && !sc) baselineWin++;
        else if (bc && sc) bothCorrect++;
        else bothWrong++;
    }

    const delta = (a, b) => (Number.isFinite(a) && Number.isFinite(b)) ? a - b : null;
    const ratioMetric = (a, b) => (Number.isFinite(a) && Number.isFinite(b) && b !== 0) ? a / b : null;

    return {
        baseline: baseSummary,
        skills: skillsSummary,
        paired: {
            eligible_pairs: pairs.length,
            excluded_model_mismatch: [...bm.entries()].filter(([id, b]) => {
                const s = sm.get(id);
                return s && b.statut === 'ok' && s.statut === 'ok' &&
                    b.model_signature && s.model_signature && b.model_signature !== s.model_signature;
            }).length,
            skills_correct_baseline_wrong: skillsWin,
            baseline_correct_skills_wrong: baselineWin,
            both_correct: bothCorrect,
            both_wrong: bothWrong,
            mcnemar_exact_p: mcnemarExact(skillsWin, baselineWin)
        },
        deltas: {
            sensitivity: delta(skillsSummary.sensitivity, baseSummary.sensitivity),
            specificity: delta(skillsSummary.specificity, baseSummary.specificity),
            accuracy: delta(skillsSummary.accuracy, baseSummary.accuracy),
            false_positive_findings_per_normal: delta(
                skillsSummary.false_positive_findings_per_normal,
                baseSummary.false_positive_findings_per_normal
            ),
            median_ms: delta(skillsSummary.median_ms, baseSummary.median_ms),
            median_latency_ratio: ratioMetric(skillsSummary.median_ms, baseSummary.median_ms),
            mean_total_tokens: delta(skillsSummary.mean_total_tokens, baseSummary.mean_total_tokens),
            total_token_ratio: ratioMetric(skillsSummary.mean_total_tokens, baseSummary.mean_total_tokens),
            mean_request_chars: delta(skillsSummary.mean_request_chars, baseSummary.mean_request_chars),
            request_char_ratio: ratioMetric(skillsSummary.mean_request_chars, baseSummary.mean_request_chars),
            mean_required_coverage: delta(skillsSummary.mean_required_coverage, baseSummary.mean_required_coverage),
            mean_forbidden_hits: delta(skillsSummary.mean_forbidden_hits, baseSummary.mean_forbidden_hits)
        }
    };
}

module.exports = { ratio, median, mean, wilson, mcnemarExact, lexicalScore, summarize, compareAB };

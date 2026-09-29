from pathlib import Path
import json
from medical_skills import load_catalog

p = Path('index.html')
s = p.read_text(encoding='utf-8')
MARK = '// MEDICAL_SKILLS_ENGINE_V1'

catalog = load_catalog()
payload = json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))

block = r'''
// MEDICAL_SKILLS_ENGINE_V1
const MEDICAL_SKILLS = Object.freeze(__PAYLOAD__);

function medicalSkillNorm(value) {
    return String(value == null ? '' : value)
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .trim().toLowerCase();
}

function medicalSkillMatch(values, actual) {
    const list = Array.isArray(values) ? values.map(medicalSkillNorm).filter(Boolean) : [];
    if (!list.length || list.includes('*')) return { ok: true, specific: false };
    actual = medicalSkillNorm(actual);
    if (!actual) return { ok: true, specific: false };
    const ok = list.some(value => actual === value || actual.includes(value) || value.includes(actual));
    return { ok: ok, specific: ok };
}

function medicalSkillsFor(context) {
    const ctx = context || {};
    const purpose = medicalSkillNorm(ctx.purpose || 'vision');
    const agent = medicalSkillNorm(ctx.agent || 'gen');
    const modality = medicalSkillNorm(ctx.modality || '');
    const region = medicalSkillNorm(ctx.region || '');
    const haystack = medicalSkillNorm([
        ctx.text || '', ctx.indication || '', ctx.task || '', modality, region, agent, purpose
    ].join(' '));

    return MEDICAL_SKILLS.map(skill => {
        const meta = skill.metadata || {};
        const pm = medicalSkillMatch(meta.purposes, purpose);
        const am = medicalSkillMatch(meta.agents, agent);
        const mm = medicalSkillMatch(meta.modalities, modality);
        const rm = medicalSkillMatch(meta.regions, region);
        if (!pm.ok || !am.ok || !mm.ok || !rm.ok) return null;

        let score = Math.max(0, Number(meta.priority) || 0) / 100;
        if (pm.specific) score += 8;
        if (am.specific) score += 6;
        if (mm.specific) score += 5;
        if (rm.specific) score += 4;

        let tagHits = 0;
        (meta.tags || []).forEach(tag => {
            const n = medicalSkillNorm(tag);
            if (n && haystack.includes(n)) { score += 2; tagHits++; }
        });
        if (meta.require_tag_match && tagHits === 0) return null;
        if (meta.always) score += 1.5;
        if (score < 2) return null;
        return { skill: skill, score: score };
    }).filter(Boolean)
      .sort((a, b) => b.score - a.score || a.skill.name.localeCompare(b.skill.name))
      .slice(0, Math.max(1, Math.min(3, Number(ctx.maxSkills) || 2)))
      .map(row => row.skill);
}

function medicalSkillsPrompt(context) {
    // Benchmark-only A/B hook. It is inert unless the explicit benchmark mode flag is also set.
    if (window.__MEDVISION_BENCH_MODE === true && window.__MEDVISION_BENCH_DISABLE_SKILLS === true) return '';
    const selected = medicalSkillsFor(context);
    if (!selected.length) return '';
    const sections = [
        'COMPÉTENCES MÉDICALES SÉLECTIONNÉES :',
        'Ces compétences structurent un brouillon de travail. Elles ne remplacent ni la politique de preuves, ni les contrôles du pipeline, ni la validation humaine.'
    ];
    selected.forEach(skill => {
        sections.push('[SKILL ' + skill.name + ']\n' + skill.instructions);
    });
    sections.push(
        'RÈGLES TRANSVERSALES DES SKILLS :\n' +
        '- Ne transforme jamais une hypothèse en fait observé.\n' +
        '- Toute donnée absente reste UNKNOWN / non évaluable.\n' +
        '- Ne crée jamais de mesure, score, recommandation, référence ou diagnostic non étayé.\n' +
        '- La sortie reste un brouillon soumis à validation humaine qualifiée.'
    );
    return sections.join('\n\n');
}
'''.replace('__PAYLOAD__', payload)

if MARK in s:
    raise SystemExit('medical skills engine already injected')

anchor = 'function analyzeWithAI(auto) {'
if anchor not in s:
    raise SystemExit('medical skills injection anchor not found')
s = s.replace(anchor, block + '\n\n' + anchor, 1)

old_sig = 'function withMedicalKnowledge(messages, agentKey) {'
new_sig = 'function withMedicalKnowledge(messages, agentKey, tri) {'
if old_sig not in s:
    raise SystemExit('withMedicalKnowledge signature not found')
s = s.replace(old_sig, new_sig, 1)

old_add = 'const add = medicalKnowledgePrompt(agentKey);'
new_add = """const add = [
        medicalKnowledgePrompt(agentKey),
        medicalSkillsPrompt({
            agent: agentKey,
            modality: tri && tri.modalite,
            region: tri && tri.region,
            indication: tri && (tri.indication || tri.motif),
            text: tri ? JSON.stringify(tri) : '',
            purpose: 'vision'
        })
    ].filter(Boolean).join('\\n\\n');"""
if old_add not in s:
    raise SystemExit('medical knowledge prompt assembly not found')
s = s.replace(old_add, new_add, 1)

old_call = 'withMedicalKnowledge(lectureMsg(grp, tri, grille, set), expertKey);'
new_call = 'withMedicalKnowledge(lectureMsg(grp, tri, grille, set), expertKey, tri);'
if old_call not in s:
    raise SystemExit('expert skill routing call not found')
s = s.replace(old_call, new_call, 1)

# Benchmark instrumentation is completely inert in normal application use.
# It records logical API calls, request size, and provider-reported token usage when available.
mcall_open = """function mcall(o) {
    o = Object.assign({}, o, { config: o.config || configSnapshot(), signal: 'signal' in o ? o.signal : (S.analysisController && S.analysisController.signal) });"""
mcall_instrumented = """function mcall(o) {
    o = Object.assign({}, o, { config: o.config || configSnapshot(), signal: 'signal' in o ? o.signal : (S.analysisController && S.analysisController.signal) });
    if (window.__MEDVISION_BENCH_MODE === true) {
        S.benchUsage = S.benchUsage || { requests: 0, request_chars: 0, responses_with_usage: 0, prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
        S.benchUsage.requests += 1;
        try { S.benchUsage.request_chars += JSON.stringify(o.body || {}).length; } catch (e) {}
    }"""
if mcall_open not in s:
    raise SystemExit('mcall benchmark instrumentation anchor not found')
s = s.replace(mcall_open, mcall_instrumented, 1)

mcall_success = """if (x.status >= 200 && x.status < 300) {
                if (!d || typeof d !== 'object') return settle(reject, { status: 200, msg: 'Le serveur a renvoyé une réponse vide ou non JSON.' });
                return settle(resolve, d);"""
mcall_success_instrumented = """if (x.status >= 200 && x.status < 300) {
                if (!d || typeof d !== 'object') return settle(reject, { status: 200, msg: 'Le serveur a renvoyé une réponse vide ou non JSON.' });
                if (window.__MEDVISION_BENCH_MODE === true && d.usage && typeof d.usage === 'object') {
                    S.benchUsage = S.benchUsage || { requests: 0, request_chars: 0, responses_with_usage: 0, prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
                    S.benchUsage.responses_with_usage += 1;
                    ['prompt_tokens', 'completion_tokens', 'total_tokens'].forEach(k => {
                        const v = Number(d.usage[k]);
                        if (Number.isFinite(v)) S.benchUsage[k] += v;
                    });
                }
                return settle(resolve, d);"""
if mcall_success not in s:
    raise SystemExit('mcall success benchmark instrumentation anchor not found')
s = s.replace(mcall_success, mcall_success_instrumented, 1)

p.write_text(s, encoding='utf-8')
print(f'Medical Skills Engine V1 injected with {len(catalog)} validated skills')

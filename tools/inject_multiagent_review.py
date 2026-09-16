from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARK = '// MEDICAL_MULTIAGENT_REVIEW_V1'

block = r'''
// MEDICAL_MULTIAGENT_REVIEW_V1
// Double lecture indépendante + critique contradictoire + audit d'orchestration.
// La lecture B ne reçoit jamais la sortie de la lecture A. Quand l'endpoint ne propose
// qu'un seul modèle, la seconde lecture reste utile mais est explicitement marquée
// comme non indépendante au niveau modèle.
const SCH_MEDICAL_CRITIC = {
    name: 'medical_critic',
    def: {
        type: 'object', additionalProperties: false,
        required: ['agreement', 'confirmed_findings', 'disputed_findings', 'possible_misses', 'possible_overcalls', 'safety_flags', 'risk_level', 'requires_human_review', 'summary'],
        properties: {
            agreement: { type: 'number' },
            confirmed_findings: { type: 'array', items: { type: 'string' } },
            disputed_findings: { type: 'array', items: { type: 'string' } },
            possible_misses: { type: 'array', items: { type: 'string' } },
            possible_overcalls: { type: 'array', items: { type: 'string' } },
            safety_flags: { type: 'array', items: { type: 'string' } },
            risk_level: { type: 'string', enum: ['low', 'moderate', 'high'] },
            requires_human_review: { type: 'boolean' },
            summary: { type: 'string' }
        }
    }
};

function medicalIndependentModelFor(agentKey, primaryModel) {
    const p = medicalAgentProfile(agentKey);
    const prefs = (p.crosscheck || []).concat(p.primary || []);
    let id = '';
    for (const wanted of prefs) {
        const candidate = medicalResolvePreferred([wanted]);
        if (candidate && candidate !== primaryModel) { id = candidate; break; }
    }
    if (!id) {
        const alternatives = medicalAvailableModels()
            .map(m => m && m.id).filter(Boolean)
            .filter(x => x !== primaryModel)
            .sort((a, b) => medicalModelRank(b) - medicalModelRank(a));
        id = alternatives[0] || primaryModel || medicalModelFor(agentKey, 'crosscheck');
    }
    S.agentModelTrace = S.agentModelTrace || {};
    S.agentModelTrace[agentKey + ':second_read'] = id || '';
    return id;
}

function medicalIndependentPrompt(messages, agentKey) {
    const out = (messages || []).map(m => ({ role: m.role, content: m.content }));
    const rule = [
        'LECTURE B INDÉPENDANTE :',
        '- Effectue une seconde lecture complète et aveugle de l’examen.',
        '- Tu ne connais pas la lecture A et tu ne dois pas chercher à confirmer une conclusion présupposée.',
        '- Repars de la grille spécialisée, cherche activement les faux positifs et les anomalies manquées.',
        '- Rapporte aussi les signes négatifs réellement évaluables et les limites techniques.',
        '- Une discordance potentielle avec un autre lecteur n’est pas une erreur : elle sera arbitrée par un agent critique.',
        medicalKnowledgePrompt(agentKey)
    ].join('\n');
    const i = out.findIndex(m => m.role === 'system' && typeof m.content === 'string');
    if (i >= 0) out[i] = { role: 'system', content: out[i].content + '\n\n' + rule };
    else out.unshift({ role: 'system', content: rule });
    return out;
}

function medicalCriticFallback(message) {
    return {
        agreement: 0,
        confirmed_findings: [],
        disputed_findings: [],
        possible_misses: [],
        possible_overcalls: [],
        safety_flags: [message || 'Seconde lecture indisponible'],
        risk_level: 'high',
        requires_human_review: true,
        summary: message || 'Critique multi-agent incomplète.'
    };
}

function medicalCriticForLecture(l, tri) {
    if (!l || !l.r2) {
        l.critic = medicalCriticFallback('La seconde lecture n’a pas abouti ; validation humaine renforcée requise.');
        return Promise.resolve(l);
    }
    const criticModel = medicalModelFor(l.k || 'gen', 'reasoning');
    S.agentModelTrace = S.agentModelTrace || {};
    S.agentModelTrace[(l.k || 'gen') + ':critic'] = criticModel || '';
    const independent = !!l.independent;
    const sys = [
        'Tu es un agent critique médical contradicteur chargé de comparer deux lectures du MÊME examen.',
        'Tu ne réalises pas une troisième lecture d’image : tu audites la cohérence, les omissions, surinterprétations et risques de sécurité.',
        'Ne fusionne pas mécaniquement. Une divergence importante doit rester visible et imposer une validation humaine.',
        'Ne transforme jamais une référence bibliographique en observation du patient.',
        'Le champ agreement est compris entre 0 et 1.',
        'Si les deux lectures proviennent du même modèle, considère que leur indépendance est réduite et mentionne-le dans safety_flags.',
        medicalKnowledgePrompt(l.k || 'gen')
    ].join('\n');
    const user = [
        'EXAMEN : ' + String(tri && tri.modalite || '') + ' — ' + String(tri && tri.region || '') + ' — ' + String(tri && tri.incidence || ''),
        'INDÉPENDANCE DES MODÈLES : ' + (independent ? 'oui' : 'non/réduite'),
        'MODÈLE LECTURE A : ' + String(l.models && l.models.primary || ''),
        'MODÈLE LECTURE B : ' + String(l.models && l.models.second || ''),
        '',
        'LECTURE A :', JSON.stringify(l.r),
        '',
        'LECTURE B :', JSON.stringify(l.r2),
        '',
        medicalEvidencePrompt(l.evidence)
    ].join('\n');
    return mchat(criticModel, [
        { role: 'system', content: sys },
        { role: 'user', content: user }
    ], SCH_MEDICAL_CRITIC, { effort: 'high', max_tokens: 3500, max_tokens_max: 8000, timeout: 120000 })
        .then(c => {
            c.agreement = Math.max(0, Math.min(1, Number(c.agreement) || 0));
            if (!independent) {
                c.safety_flags = Array.isArray(c.safety_flags) ? c.safety_flags : [];
                c.safety_flags.push('Lectures A/B issues du même modèle ou d’un endpoint mono-modèle : indépendance réduite.');
            }
            l.critic = c;
            return l;
        })
        .catch(e => {
            l.critic = medicalCriticFallback('Agent critique indisponible : ' + String(e && (e.msg || e.message) || e));
            return l;
        });
}

function medicalCriticForLectures(lectures, tri) {
    return Promise.all((lectures || []).map(l => medicalCriticForLecture(l, tri)));
}

function medicalMultiagentAudit(lectures) {
    const rows = (lectures || []).map(l => ({
        expert: l.k || '',
        primary_model: l.models && l.models.primary || '',
        second_model: l.models && l.models.second || '',
        model_independent: !!l.independent,
        second_read_available: !!l.r2,
        second_read_failures: Array.isArray(l.secondFailures) ? l.secondFailures.length : 0,
        critic_agreement: l.critic && typeof l.critic.agreement === 'number' ? l.critic.agreement : null,
        critic_risk: l.critic && l.critic.risk_level || 'high',
        human_review: !l.critic || l.critic.requires_human_review !== false,
        safety_flags: l.critic && Array.isArray(l.critic.safety_flags) ? l.critic.safety_flags.slice(0, 8) : []
    }));
    return {
        architecture: 'double_read_blinded + critic + consensus',
        experts: rows,
        all_second_reads_available: rows.length > 0 && rows.every(x => x.second_read_available),
        all_model_independent: rows.length > 0 && rows.every(x => x.model_independent),
        requires_human_review: rows.length === 0 || rows.some(x => x.human_review || x.critic_risk === 'high')
    };
}
'''

if MARK not in s:
    anchor = '// MEDICAL_EVIDENCE_RAG_V1'
    if anchor not in s:
        raise SystemExit('recent evidence layer must be injected before multi-agent review')
    s = s.replace(anchor, block + '\n\n' + anchor, 1)

# Every specialist gets a blinded reader B. It uses a different advertised medical
# model whenever possible, but never sees reader A's answer.
needle_models = """const visionModel = medicalModelFor(expertKey, 'vision');
                        jobs.push("""
replacement_models = """const visionModel = medicalModelFor(expertKey, 'vision');
                        const secondModel = medicalIndependentModelFor(expertKey, visionModel);
                        const secondBase = medicalIndependentPrompt(base, expertKey);
                        jobs.push("""
if needle_models in s and 'const secondModel = medicalIndependentModelFor' not in s:
    s = s.replace(needle_models, replacement_models, 1)

old_tail = """                              ).then(msgs => mchat(visionModel, msgs, SCH_LECTURE,
                                  { effort: 'high', max_tokens: panel ? 4000 : 6000, max_tokens_max: 16000, timeout: 180000,
                                    onBudget: bg => updPipe(3, 'active', done + '/' + total + ' · budget ' + bg) }))
                                .then(r => { updPipe(3, 'active', (++done) + '/' + total); return { k: grp[0], grp: grp, ci: ci, r: remapImages(r, set) }; })
                                .catch(e => { updPipe(3, 'active', (++done) + '/' + total); return { k: grp[0], grp: grp, ci: ci, err: e }; })"""
new_tail = """                              ).then(msgs => mchat(visionModel, msgs, SCH_LECTURE,
                                  { effort: 'high', max_tokens: panel ? 4000 : 6000, max_tokens_max: 16000, timeout: 180000,
                                    onBudget: bg => updPipe(3, 'active', done + '/' + total + ' · budget A ' + bg) }))
                                .then(r => {
                                    const readB = (S.zoomOff || !zoomUseful(set)
                                        ? Promise.resolve(secondBase)
                                        : inspectRounds(secondModel, secondBase, set,
                                            { effort: 'medium', timeout: 90000 },
                                            (rr, motif) => updPipe(3, 'active', done + '/' + total + ' · relecture zoom ' + rr)))
                                        .then(msgs2 => mchat(secondModel, msgs2, SCH_LECTURE,
                                            { effort: 'high', max_tokens: panel ? 4000 : 6000, max_tokens_max: 16000, timeout: 180000,
                                              onBudget: bg => updPipe(3, 'active', done + '/' + total + ' · budget B ' + bg) }))
                                        .then(r2 => ({ r: r, r2: r2, err2: null }))
                                        .catch(err2 => ({ r: r, r2: null, err2: err2 }));
                                    return readB;
                                })
                                .then(pair => {
                                    updPipe(3, 'active', (++done) + '/' + total);
                                    return {
                                        k: grp[0], grp: grp, ci: ci,
                                        r: remapImages(pair.r, set),
                                        r2: pair.r2 ? remapImages(pair.r2, set) : null,
                                        err2: pair.err2 || null,
                                        models: { primary: visionModel, second: secondModel },
                                        independent: !!secondModel && secondModel !== visionModel
                                    };
                                })
                                .catch(e => { updPipe(3, 'active', (++done) + '/' + total); return { k: grp[0], grp: grp, ci: ci, err: e }; })"""
if old_tail in s:
    s = s.replace(old_tail, new_tail, 1)

old_init = """const e = byExp[x.k] || (byExp[x.k] = { k: x.k, grp: x.grp, lots: [], trunc: false, r: {
                                findings: [], signes_negatifs: [], differentiel: [],
                                recommandations: [], rois: [], severite: 'norm' } });"""
new_init = """const e = byExp[x.k] || (byExp[x.k] = {
                                k: x.k, grp: x.grp, lots: [], secondLots: [], trunc: false,
                                models: x.models || {}, independent: !!x.independent, secondFailures: [],
                                r: { findings: [], signes_negatifs: [], differentiel: [], recommandations: [], rois: [], severite: 'norm' },
                                r2: { findings: [], signes_negatifs: [], differentiel: [], recommandations: [], rois: [], severite: 'norm' }
                            });"""
if old_init in s:
    s = s.replace(old_init, new_init, 1)

needle_merge = """if (SEVRANK[r.severite] < SEVRANK[e.r.severite]) e.r.severite = r.severite;"""
extra_merge = """if (SEVRANK[r.severite] < SEVRANK[e.r.severite]) e.r.severite = r.severite;
                            if (x.models) e.models = x.models;
                            e.independent = e.independent || !!x.independent;
                            if (x.r2) {
                                e.secondLots.push(x.ci);
                                const r2 = x.r2;
                                ['findings', 'signes_negatifs', 'differentiel', 'recommandations', 'rois']
                                    .forEach(f => { if (Array.isArray(r2[f])) e.r2[f] = e.r2[f].concat(r2[f]); });
                                if (SEVRANK[r2.severite] < SEVRANK[e.r2.severite]) e.r2.severite = r2.severite;
                            } else if (x.err2) {
                                e.secondFailures.push(String(x.err2 && (x.err2.msg || x.err2.message) || x.err2));
                            }"""
if needle_merge in s and 'e.secondLots.push(x.ci)' not in s:
    s = s.replace(needle_merge, extra_merge, 1)

# If no B reading succeeded for an expert, make the absence explicit instead of
# passing an empty synthetic reading to the critic.
needle_lectures = "const lectures = Object.keys(byExp).map(k => byExp[k]);"
replacement_lectures = "const lectures = Object.keys(byExp).map(k => { const l = byExp[k]; if (!l.secondLots.length) l.r2 = null; return l; });"
if needle_lectures in s:
    s = s.replace(needle_lectures, replacement_lectures, 1)

# Evidence first, then critic: the critic gets recent literature as context, while
# being explicitly forbidden to turn literature into patient findings.
old_evidence_chain = """return medicalEvidenceForLectures(lectures, tri).then(enriched => ({
                            lectures: enriched, tri: tri, single: (!panel && enriched[0]) ? enriched[0].r : null,
                            chunks: CH.length, failed: res.length - good.length
                        }));"""
new_evidence_chain = """return medicalEvidenceForLectures(lectures, tri)
                        .then(enriched => medicalCriticForLectures(enriched, tri))
                        .then(enriched => ({
                            lectures: enriched, tri: tri, single: (!panel && enriched[0]) ? enriched[0].r : null,
                            chunks: CH.length, failed: res.length - good.length
                        }));"""
if old_evidence_chain in s:
    s = s.replace(old_evidence_chain, new_evidence_chain, 1)

# Enrich the panel dossier with reader B and the critic's adjudication record.
old_dossier = "const dossier = ok.map(l => '### ' + AG[l.k].n + '\\nLECTURE EXPERTE:\\n' + JSON.stringify(l.r) + '\\n\\n' + medicalEvidencePrompt(l.evidence)).join('\\n\\n---\\n\\n');"
new_dossier = "const dossier = ok.map(l => '### ' + AG[l.k].n + '\\nLECTURE A:\\n' + JSON.stringify(l.r) + '\\n\\nLECTURE B INDÉPENDANTE:\\n' + JSON.stringify(l.r2) + '\\n\\nCRITIQUE CONTRADICTOIRE:\\n' + JSON.stringify(l.critic) + '\\n\\n' + medicalEvidencePrompt(l.evidence)).join('\\n\\n---\\n\\n');"
if old_dossier in s:
    s = s.replace(old_dossier, new_dossier, 1)

needle_consensus_rule = '"- Les blocs de preuves Europe PMC/PubMed sont du CONTEXTE SCIENTIFIQUE externe, pas des observations du patient. Ne transforme jamais un résultat de littérature en finding d’image.",'
extra_consensus_rule = needle_consensus_rule + "\n                        \"- Chaque spécialiste peut fournir une lecture A, une lecture B aveugle et une critique contradictoire. Préserve explicitement les divergences non résolues au lieu de les lisser.\",\n                        \"- Une alerte de sécurité du critique ou une divergence majeure doit rester visible dans les limites et conduire à une validation humaine.\","
if needle_consensus_rule in s and 'lecture B aveugle' not in s:
    s = s.replace(needle_consensus_rule, extra_consensus_rule, 1)

# Single-expert mode still gets a full audit trail even though it bypasses the panel consensus call.
needle_single = """rep._lectures = out.lectures || [];
                        return finish(rep, agents, tri, t0, steps.length - 1);"""
replacement_single = """rep._lectures = out.lectures || [];
                        rep.audit_multiagent = medicalMultiagentAudit(rep._lectures);
                        return finish(rep, agents, tri, t0, steps.length - 1);"""
if needle_single in s:
    s = s.replace(needle_single, replacement_single, 1)

# Panel mode attaches the same audit object to the final report.
needle_panel = """rep._lectures = ok;
                            return finish(rep, agents, tri, t0, 5);"""
replacement_panel = """rep._lectures = ok;
                            rep.audit_multiagent = medicalMultiagentAudit(ok);
                            return finish(rep, agents, tri, t0, 5);"""
if needle_panel in s:
    s = s.replace(needle_panel, replacement_panel, 1)

# Persist a compact, inspectable multi-agent audit record in report metadata.
needle_meta = "preuves_recentes: (rep._lectures || []).map(l => ({ expert: l.k, source: l.evidence && l.evidence.source || '', retrieved_at: l.evidence && l.evidence.retrieved_at || '', count: l.evidence && l.evidence.items ? l.evidence.items.length : 0, error: l.evidence && l.evidence.error || '' })),"
if needle_meta in s and 'audit_multiagent:' not in s:
    s = s.replace(needle_meta, needle_meta + "\n        audit_multiagent: rep.audit_multiagent || medicalMultiagentAudit(rep._lectures || []),", 1)

s = s.replace("const APP_VERSION = 'v16.3.0';", "const APP_VERSION = 'v16.4.0';", 1)

required = [
    'MEDICAL_MULTIAGENT_REVIEW_V1',
    'const secondModel = medicalIndependentModelFor',
    'LECTURE B INDÉPENDANTE',
    'medicalCriticForLectures(enriched, tri)',
    'CRITIQUE CONTRADICTOIRE',
    'audit_multiagent:',
    "APP_VERSION = 'v16.4.0'"
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('multi-agent medical review injection incomplete: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('Medical Multi-Agent Review V1 injected into index.html')

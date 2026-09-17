from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARK = '// MEDICAL_LLM_STACK_V3'

block = r'''
// MEDICAL_LLM_STACK_V3
// Modèles médicaux ouverts vérifiés au 2026-09-17.
// Aucun modèle n'est déclaré universellement "meilleur" : le routage dépend de la tâche et de la modalité.
// IMPORTANT : les poids d'un LLM ne constituent pas une source de recommandation clinique à jour.
// Les connaissances paramétriques servent d'arrière-plan ; toute recommandation dite récente
// doit être étayée par une source datée injectée par la couche de preuves/RAG.
const MEDICAL_MODELS = Object.freeze({
    lingshuI8: Object.freeze({
        id: 'lingshu-medical-mllm/Lingshu-I-8B',
        kind: 'multimodal',
        release: '2026',
        use: ['general_medical_vqa', 'reporting', 'radiology', 'ct', 'mri', 'pathology', 'fundus', 'oct', 'endoscopy'],
        label: 'Lingshu-I-8B medical multimodal'
    }),
    lingshu32: Object.freeze({
        id: 'lingshu-medical-mllm/Lingshu-32B',
        kind: 'multimodal',
        release: '2025-09-17',
        use: ['deep_crosscheck', 'clinical_reasoning', 'reporting', 'multimodal_vqa'],
        label: 'Lingshu-32B medical multimodal'
    }),
    medgemma15: Object.freeze({
        id: 'google/medgemma-1.5-4b-it',
        kind: 'multimodal',
        release: '2026-01-13',
        use: ['triage', 'vision', 'ct', 'mri', 'pathology', 'dermatology', 'ophthalmology', 'ehr'],
        label: 'MedGemma 1.5 4B multimodal'
    }),
    medgemma27mm: Object.freeze({
        id: 'google/medgemma-27b-it',
        kind: 'multimodal',
        release: '2025-07-09',
        use: ['vision', 'crosscheck', 'longitudinal', 'reporting'],
        label: 'MedGemma 27B multimodal'
    }),
    medgemma27text: Object.freeze({
        id: 'google/medgemma-27b-text-it',
        kind: 'text',
        release: '2025-05-20',
        use: ['clinical_reasoning', 'differential', 'consensus', 'synthesis'],
        label: 'MedGemma 27B text clinical reasoning'
    }),
    medvisionV0: Object.freeze({
        id: 'YongchengYAO/MedVision-V0-7B',
        kind: 'multimodal-quantitative',
        release: '2026-09',
        use: ['detection', 'lesion_measurement', 'angle_distance', 'quantitative_imaging'],
        label: 'MedVision-V0-7B quantitative medical imaging'
    }),
    medsiglip: Object.freeze({
        id: 'google/medsiglip-448',
        kind: 'encoder',
        release: '2025-07-09',
        use: ['classification', 'retrieval', 'embeddings'],
        label: 'MedSigLIP 448 medical image encoder'
    })
});

const MEDICAL_EVIDENCE_POLICY = Object.freeze({
    universal: ['HAS', 'WHO', 'PubMed', 'Cochrane', 'NICE', 'EMA'],
    radio: ['ACR', 'ESR', 'RSNA'], pulmo: ['ERS', 'ATS'], neuro: ['EAN', 'AAN'],
    cardio: ['ESC', 'AHA/ACC'], dermato: ['EADV', 'AAD'], ophtalmo: ['AAO'],
    ortho: ['AAOS', 'ESSKA'], seno: ['ACR BI-RADS', 'EUSOBI'], digest: ['ESGE', 'EASL'],
    uro: ['EAU'], gyneco: ['FIGO', 'ISUOG'], vasc: ['ESVS'], onco: ['ESMO'],
    patho: ['WHO Classification of Tumours', 'CAP'], pedia: ['AAP', 'ESPR'],
    endo: ['ESE', 'ETA'], dentaire: ['EFP', 'FDI'], trauma: ['ERC', 'ATLS'],
    gen: ['HAS', 'NICE']
});

function medicalModelRank(id) {
    id = String(id || '').toLowerCase();
    if (/lingshu[-_/]?i[-_]?8b/.test(id)) return 145;
    if (/lingshu[-_/]?32b/.test(id)) return 140;
    if (id === MEDICAL_MODELS.medgemma15.id.toLowerCase() || /medgemma[-_:]?1\.5[-_:]?4b/.test(id)) return 135;
    if (id === MEDICAL_MODELS.medgemma27mm.id.toLowerCase() || /medgemma[-_:]?27b(?!.*text)/.test(id)) return 130;
    if (id === MEDICAL_MODELS.medgemma27text.id.toLowerCase() || /medgemma[-_:]?27b.*text|medgemma.*text.*27b/.test(id)) return 125;
    if (/medvision[-_/]?v0[-_]?7b/.test(id)) return 115;
    if (/medgemma|lingshu|medvision/.test(id)) return 90;
    return 20;
}

function medicalAvailableModels() {
    const models = [];
    (S.mdlPool || []).forEach(m => { if (m && m.id && !models.some(x => x.id === m.id)) models.push(m); });
    [S.customModel, S.mdlVision, S.mdlFast, S.mdlSynth].forEach(id => {
        if (id && !models.some(x => x.id === id)) models.push({ id: id });
    });
    return models;
}

function medicalResolvePreferred(preferred) {
    const available = medicalAvailableModels();
    for (const wanted of preferred || []) {
        const exact = available.find(m => m.id === wanted);
        if (exact) return exact.id;
        const wn = wanted.toLowerCase().replace(/[^a-z0-9]+/g, '');
        const alias = available.find(m => {
            const an = String(m.id || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
            if (an === wn) return true;
            if (wn.includes('lingshui8b') && /lingshu.*i.*8b/.test(an)) return true;
            if (wn.includes('lingshu32b') && /lingshu.*32b/.test(an)) return true;
            if (wn.includes('medgemma154b') && /medgemma.*15.*4b/.test(an)) return true;
            if (wn.includes('medgemma27btext') && /medgemma.*27b.*text|medgemma.*text.*27b/.test(an)) return true;
            if (wn.includes('medvisionv07b') && /medvision.*v0.*7b/.test(an)) return true;
            return false;
        });
        if (alias) return alias.id;
    }
    return '';
}

function medicalAgentProfile(agentKey) {
    // Les lectures expertes actuelles reçoivent des images : les primaires restent multimodaux.
    // Le 27B text est réservé aux étapes purement textuelles (raisonnement/consensus).
    const broad = [MEDICAL_MODELS.lingshuI8.id, MEDICAL_MODELS.medgemma15.id, MEDICAL_MODELS.lingshu32.id, MEDICAL_MODELS.medgemma27mm.id];
    const deepVisual = [MEDICAL_MODELS.lingshu32.id, MEDICAL_MODELS.medgemma27mm.id, MEDICAL_MODELS.medgemma15.id, MEDICAL_MODELS.lingshuI8.id];
    const pathology = [MEDICAL_MODELS.medgemma15.id, MEDICAL_MODELS.lingshuI8.id, MEDICAL_MODELS.lingshu32.id, MEDICAL_MODELS.medgemma27mm.id];
    const primary = agentKey === 'patho' ? pathology : broad;
    return {
        key: agentKey,
        primary: primary,
        reasoning: [MEDICAL_MODELS.medgemma27text.id, MEDICAL_MODELS.lingshu32.id, MEDICAL_MODELS.lingshuI8.id, MEDICAL_MODELS.medgemma27mm.id, MEDICAL_MODELS.medgemma15.id],
        crosscheck: deepVisual,
        quantitative: [MEDICAL_MODELS.medvisionV0.id, MEDICAL_MODELS.lingshu32.id, MEDICAL_MODELS.lingshuI8.id],
        evidence: (MEDICAL_EVIDENCE_POLICY[agentKey] || []).concat(MEDICAL_EVIDENCE_POLICY.universal)
    };
}

function medicalModelFor(agentKey, purpose) {
    const p = medicalAgentProfile(agentKey);
    let pref;
    if (purpose === 'reasoning' || purpose === 'consensus') pref = p.reasoning;
    else if (purpose === 'crosscheck') pref = p.crosscheck;
    else if (purpose === 'quantitative') pref = p.quantitative;
    else pref = p.primary;
    let id = medicalResolvePreferred(pref);
    if (!id) {
        // Endpoint mono-modèle : utilisation explicite du modèle réellement configuré.
        if (S.provider === 'medgemma' && S.customModel) id = S.customModel;
        else if (purpose === 'reasoning' || purpose === 'consensus') id = S.mdlSynth || S.mdlVision || S.mdlFast;
        else if (purpose === 'triage') id = S.mdlFast || S.mdlVision;
        else id = S.mdlVision || S.mdlFast;
    }
    S.agentModelTrace = S.agentModelTrace || {};
    S.agentModelTrace[agentKey + ':' + purpose] = id || '';
    return id;
}

function medicalKnowledgePrompt(agentKey) {
    const p = medicalAgentProfile(agentKey);
    return [
        'POLITIQUE DE CONNAISSANCE MÉDICALE :',
        '- Utilise tes connaissances médicales paramétriques comme arrière-plan, jamais comme preuve qu’une recommandation est à jour.',
        '- Une recommandation dite actuelle/récente doit être fondée sur un document daté fourni au contexte ou par une couche de recherche externe.',
        '- Si aucune source récente n’est fournie, indique explicitement que l’actualité de la recommandation n’est pas vérifiée.',
        '- Distingue observation, hypothèse, diagnostic différentiel, niveau de confiance et limite de l’examen.',
        '- N’invente jamais de référence, DOI, guideline, score, seuil, indication ou contre-indication.',
        '- Sources prioritaires pour cet agent : ' + p.evidence.join(', ') + '.',
        '- Toute décision clinique finale reste sous validation humaine.'
    ].join('\n');
}

function withMedicalKnowledge(messages, agentKey) {
    const out = (messages || []).map(m => ({ role: m.role, content: m.content }));
    const add = medicalKnowledgePrompt(agentKey);
    const i = out.findIndex(m => m.role === 'system' && typeof m.content === 'string');
    if (i >= 0) out[i] = { role: 'system', content: out[i].content + '\n\n' + add };
    else out.unshift({ role: 'system', content: add });
    return out;
}
'''

# Replace an earlier generated medical stack when rerunning the injector.
for old_mark in ('// MEDICAL_LLM_STACK_V2', '// MEDICAL_LLM_STACK_V1'):
    if old_mark in s:
        start = s.index(old_mark)
        end = s.index('function analyzeWithAI(auto) {', start)
        s = s[:start] + block + '\n' + s[end:]
        break
else:
    if MARK not in s:
        anchor = 'function analyzeWithAI(auto) {'
        if anchor not in s:
            raise SystemExit('anchor analyzeWithAI not found')
        s = s.replace(anchor, block + '\n' + anchor, 1)

# Allow the medical OpenAI-compatible endpoint to expose several models. If /models is unavailable,
# keep the explicitly configured model as the safe mono-model fallback.
old_discover = """function discoverModels(config) {
    config = config || configSnapshot();
    if (config.provider === 'medgemma') return Promise.resolve([{ id: config.customModel, rank: 100, lbl: config.customModel }]);
    return mcall({ method: 'GET', path: '/models', timeout: 15000, config, retries: 1 })
        .then(d => {
            const models = visionModels(d.data);
            if (!models.length) throw { status: 200, msg: 'Aucun modèle avec capacité vision confirmé pour cette clé. Vérifiez l’accès dans votre compte Mistral.' };
            return models;
        });
}"""
new_discover = """function discoverModels(config) {
    config = config || configSnapshot();
    if (config.provider === 'medgemma') {
        const fallback = [{ id: config.customModel, rank: medicalModelRank(config.customModel), lbl: config.customModel }];
        return mcall({ method: 'GET', path: '/models', timeout: 15000, config, retries: 1, signal: null })
            .then(d => {
                const seen = new Set();
                const models = ((d && d.data) || []).filter(m => m && typeof m.id === 'string')
                    .map(m => ({ id: m.id, rank: medicalModelRank(m.id), lbl: m.name || m.id }))
                    .filter(m => { if (seen.has(m.id)) return false; seen.add(m.id); return true; })
                    .sort((a, b) => b.rank - a.rank);
                if (config.customModel && !seen.has(config.customModel))
                    models.push({ id: config.customModel, rank: medicalModelRank(config.customModel), lbl: config.customModel });
                return models.length ? models : fallback;
            })
            .catch(() => fallback);
    }
    return mcall({ method: 'GET', path: '/models', timeout: 15000, config, retries: 1 })
        .then(d => {
            const models = visionModels(d.data);
            if (!models.length) throw { status: 200, msg: 'Aucun modèle avec capacité vision confirmé pour cette clé. Vérifiez l’accès dans votre compte Mistral.' };
            return models;
        });
}"""
if old_discover in s:
    s = s.replace(old_discover, new_discover, 1)

# A configured medical model is a fallback/entry point, not a command to force every role
# when the endpoint advertises a richer medical model pool.
old_force = """function applyForce() {
    if (!S.mdlForce) return;
    S.mdlVision = S.mdlSynth = S.mdlFast = S.mdlForce;
}"""
new_force = """function applyForce() {
    if (!S.mdlForce) return;
    if ((S.provider || 'mistral') === 'medgemma') return;
    S.mdlVision = S.mdlSynth = S.mdlFast = S.mdlForce;
}"""
if old_force in s:
    s = s.replace(old_force, new_force, 1)

# Reset trace at the beginning of each medical analysis.
needle_trace = "S.lastReport = null; S.lastMeta = null;\n    const signal = S.analysisController.signal;"
if needle_trace in s:
    s = s.replace(needle_trace, "S.lastReport = null; S.lastMeta = null; S.agentModelTrace = {};\n    const signal = S.analysisController.signal;", 1)

# Per-agent routing for the expert reading stage.
old = """const base = lectureMsg(grp, tri, grille, set);
                        jobs.push(
                            (S.zoomOff || !zoomUseful(set)
                                ? Promise.resolve(base)
                                : inspectRounds(S.mdlVision, base, set,"""
new = """const expertKey = grp[0] || 'gen';
                        const base = withMedicalKnowledge(lectureMsg(grp, tri, grille, set), expertKey);
                        const visionModel = medicalModelFor(expertKey, 'vision');
                        jobs.push(
                            (S.zoomOff || !zoomUseful(set)
                                ? Promise.resolve(base)
                                : inspectRounds(visionModel, base, set,"""
if old in s:
    s = s.replace(old, new, 1)

s = s.replace(".then(msgs => mchat(S.mdlVision, msgs, SCH_LECTURE,",
              ".then(msgs => mchat(visionModel, msgs, SCH_LECTURE,", 1)

# Triage uses a medical multimodal model when the configured endpoint provides one.
s = s.replace("return mchat(S.mdlFast, triMsg, SCH_TRIAGE,",
              "return mchat(medicalModelFor('triage', 'triage'), withMedicalKnowledge(triMsg, 'triage'), SCH_TRIAGE,", 1)

# Consensus is text-only: prefer a deeper medical reasoning model when available.
s = s.replace("return mchat(S.mdlSynth, [\n                        { role: 'system', content: synSys },",
              "return mchat(medicalModelFor('consensus', 'consensus'), [\n                        { role: 'system', content: synSys + '\\n\\n' + medicalKnowledgePrompt('consensus') },", 1)

# Persist the actual role->model assignments in the audit/report metadata.
needle_meta = "fournisseur_ia: S.provider || 'mistral', modele_vision: S.mdlVision, modele_triage: S.mdlFast, modele_synthese: S.mdlSynth,"
if needle_meta in s:
    s = s.replace(needle_meta,
        "fournisseur_ia: S.provider || 'mistral', modele_vision: S.mdlVision, modele_triage: S.mdlFast, modele_synthese: S.mdlSynth,\n        modeles_agents: Object.assign({}, S.agentModelTrace || {}),", 1)

# Make recent specialist models selectable as endpoint fallbacks.
needle = '<option value="google/medgemma-27b-it">MedGemma 27B — multimodal, plus lourd</option>'
if needle in s:
    additions = needle
    if 'google/medgemma-27b-text-it">MedGemma 27B Text' not in s:
        additions += '\n                <option value="google/medgemma-27b-text-it">MedGemma 27B Text — raisonnement clinique (texte uniquement)</option>'
    if 'lingshu-medical-mllm/Lingshu-I-8B' not in s:
        additions += '\n                <option value="lingshu-medical-mllm/Lingshu-I-8B">Lingshu-I-8B — médical multimodal récent</option>'
    if 'lingshu-medical-mllm/Lingshu-32B' not in s:
        additions += '\n                <option value="lingshu-medical-mllm/Lingshu-32B">Lingshu-32B — médical multimodal approfondi</option>'
    if 'YongchengYAO/MedVision-V0-7B' not in s:
        additions += '\n                <option value="YongchengYAO/MedVision-V0-7B">MedVision-V0-7B — mesures quantitatives d’imagerie</option>'
    s = s.replace(needle, additions, 1)

# Version bump is idempotent from either base or an earlier generated pass.
s = s.replace("const APP_VERSION = 'v16.2.0';", "const APP_VERSION = 'v16.3.0';", 1)

# Hard validation: fail loudly instead of silently producing a half-wired medical stack.
required = [
    'MEDICAL_LLM_STACK_V3',
    "medicalModelFor(expertKey, 'vision')",
    "medicalModelFor('triage', 'triage')",
    "medicalModelFor('consensus', 'consensus')",
    'modeles_agents: Object.assign({}, S.agentModelTrace || {})',
    'lingshu-medical-mllm/Lingshu-I-8B',
    'lingshu-medical-mllm/Lingshu-32B',
    'YongchengYAO/MedVision-V0-7B',
    'google/medgemma-27b-text-it',
    "APP_VERSION = 'v16.3.0'"
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('medical LLM injection incomplete: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('Medical LLM stack V3 injected into index.html')

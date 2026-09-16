from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARK = '// MEDICAL_LLM_STACK_V1'

block = r'''
// MEDICAL_LLM_STACK_V1
// Modèles médicaux ouverts vérifiés au 2026-09-17.
// Important : les poids d'un LLM ne constituent pas une source de recommandation clinique à jour.
// Les sorties restent préliminaires et doivent être corrélées/validées par un professionnel.
const MEDICAL_MODELS = Object.freeze({
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
    seno: ['ACR BI-RADS', 'EUSOBI'], digest: ['ESGE', 'EASL'], uro: ['EAU'],
    gyneco: ['FIGO', 'ISUOG'], vasc: ['ESVS'], onco: ['ESMO'],
    pediatre: ['AAP', 'ESPR'], trauma: ['ERC', 'ATLS'], gen: ['HAS', 'NICE']
});

function medicalAvailableModels() {
    const ids = new Set((S.mdlPool || []).map(m => m && m.id).filter(Boolean));
    if (S.customModel) ids.add(S.customModel);
    if (S.mdlVision) ids.add(S.mdlVision);
    if (S.mdlFast) ids.add(S.mdlFast);
    if (S.mdlSynth) ids.add(S.mdlSynth);
    return ids;
}

function medicalAgentProfile(agentKey) {
    const a = AG[agentKey] || {};
    const transversal = !!a.transversal || agentKey === 'gen' || agentKey === 'trauma';
    const visual = !transversal || /radio|pulmo|neuro|cardio|dermato|ophtal|seno|digest|uro|gyneco|dentaire|vasc|endo|pedi/i.test(agentKey || '');
    return {
        key: agentKey,
        primary: visual ? [MEDICAL_MODELS.medgemma15.id, MEDICAL_MODELS.medgemma27mm.id]
                        : [MEDICAL_MODELS.medgemma27text.id, MEDICAL_MODELS.medgemma15.id],
        reasoning: [MEDICAL_MODELS.medgemma27text.id, MEDICAL_MODELS.medgemma27mm.id, MEDICAL_MODELS.medgemma15.id],
        crosscheck: [MEDICAL_MODELS.medgemma27mm.id, MEDICAL_MODELS.medgemma15.id, MEDICAL_MODELS.medgemma27text.id],
        evidence: (MEDICAL_EVIDENCE_POLICY[agentKey] || []).concat(MEDICAL_EVIDENCE_POLICY.universal)
    };
}

function medicalModelFor(agentKey, purpose) {
    const available = medicalAvailableModels();
    const p = medicalAgentProfile(agentKey);
    let pref;
    if (purpose === 'reasoning' || purpose === 'consensus') pref = p.reasoning;
    else if (purpose === 'crosscheck') pref = p.crosscheck;
    else pref = p.primary;
    for (const id of pref) if (available.has(id)) return id;
    // Endpoint mono-modèle : ne jamais inventer qu'un 27B est disponible.
    if (S.provider === 'medgemma' && S.customModel) return S.customModel;
    return purpose === 'reasoning' || purpose === 'consensus'
        ? (S.mdlSynth || S.mdlVision || S.mdlFast)
        : (purpose === 'triage' ? (S.mdlFast || S.mdlVision) : (S.mdlVision || S.mdlFast));
}

function medicalKnowledgePrompt(agentKey) {
    const p = medicalAgentProfile(agentKey);
    return [
        'POLITIQUE DE CONNAISSANCE MÉDICALE :',
        '- Utilise tes connaissances médicales comme arrière-plan, jamais comme preuve qu’une recommandation est à jour.',
        '- Une recommandation dite actuelle/récente doit être fondée sur un document daté fourni au contexte ou par une couche de recherche externe.',
        '- Si aucune source récente n’est fournie, indique explicitement que l’actualité de la recommandation n’est pas vérifiée.',
        '- Distingue observation, hypothèse, diagnostic différentiel, niveau de confiance et limite de l’examen.',
        '- N’invente jamais de référence, DOI, guideline, score ou seuil.',
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

if MARK not in s:
    anchor = 'function analyzeWithAI(auto) {'
    if anchor not in s:
        raise SystemExit('anchor analyzeWithAI not found')
    s = s.replace(anchor, block + '\n' + anchor, 1)

# Per-agent routing for the expert lecture stage.
old = """const base = lectureMsg(grp, tri, grille, set);\n                        jobs.push(\n                            (S.zoomOff || !zoomUseful(set)\n                                ? Promise.resolve(base)\n                                : inspectRounds(S.mdlVision, base, set,"""
new = """const expertKey = grp[0] || 'gen';\n                        const base = withMedicalKnowledge(lectureMsg(grp, tri, grille, set), expertKey);\n                        const visionModel = medicalModelFor(expertKey, 'vision');\n                        jobs.push(\n                            (S.zoomOff || !zoomUseful(set)\n                                ? Promise.resolve(base)\n                                : inspectRounds(visionModel, base, set,"""
if old in s:
    s = s.replace(old, new, 1)

s = s.replace(".then(msgs => mchat(S.mdlVision, msgs, SCH_LECTURE,",
              ".then(msgs => mchat(visionModel, msgs, SCH_LECTURE,", 1)

# Triage uses the most suitable medical multimodal model available.
s = s.replace("return mchat(S.mdlFast, triMsg, SCH_TRIAGE,",
              "return mchat(medicalModelFor('triage', 'triage'), withMedicalKnowledge(triMsg, 'triage'), SCH_TRIAGE,", 1)

# Consensus prefers the 27B medical reasoning model when the configured endpoint exposes it.
s = s.replace("return mchat(S.mdlSynth, [\n                        { role: 'system', content: synSys },",
              "return mchat(medicalModelFor('consensus', 'consensus'), [\n                        { role: 'system', content: synSys + '\\n\\n' + medicalKnowledgePrompt('consensus') },", 1)

# Make the verified 27B text reasoning model selectable in the MedGemma datalist.
needle = '<option value="google/medgemma-27b-it">MedGemma 27B — multimodal, plus lourd</option>'
extra = needle + '\n                <option value="google/medgemma-27b-text-it">MedGemma 27B Text — raisonnement clinique</option>'
if needle in s and 'google/medgemma-27b-text-it">MedGemma 27B Text' not in s:
    s = s.replace(needle, extra, 1)

s = s.replace("const APP_VERSION = 'v16.2.0';", "const APP_VERSION = 'v16.3.0';", 1)

p.write_text(s, encoding='utf-8')
print('Medical LLM stack injected into index.html')

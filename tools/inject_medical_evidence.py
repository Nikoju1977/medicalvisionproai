from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARK = '// MEDICAL_EVIDENCE_RAG_V1'

block = r'''
// MEDICAL_EVIDENCE_RAG_V1
// Couche de preuves récentes : Europe PMC limité à PubMed (SRC:MED).
// Confidentialité : aucune identité patient ni contexte clinique libre n'est envoyé.
// Les requêtes sont construites uniquement à partir de la spécialité, modalité/région
// et de libellés de diagnostic différentiel structurés, puis nettoyées localement.
const MEDICAL_EVIDENCE_QUERY_MAP = Object.freeze({
    radio: 'diagnostic imaging radiology', pulmo: 'pulmonary lung imaging', neuro: 'neurologic neuroimaging',
    trauma: 'trauma emergency imaging', cardio: 'cardiovascular cardiac imaging', dermato: 'dermatology skin imaging',
    ophtalmo: 'ophthalmology retinal imaging', ortho: 'orthopedic musculoskeletal imaging', onco: 'oncology cancer imaging',
    patho: 'pathology histopathology', pedia: 'pediatric imaging', endo: 'endocrinology imaging',
    seno: 'breast imaging', digest: 'gastrointestinal hepatobiliary imaging', uro: 'urology genitourinary imaging',
    gyneco: 'gynecology pelvic imaging', dentaire: 'dental oral imaging', vasc: 'vascular imaging', gen: 'clinical imaging'
});

function medicalEvidenceSafeText(v, maxLen) {
    if (typeof v !== 'string') return '';
    let x = v.slice(0, maxLen || 120);
    // Rejette tout contenu ressemblant à un identifiant/contact/date/numéro patient.
    x = x.replace(/https?:\/\/\S+/gi, ' ')
         .replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, ' ')
         .replace(/\b(?:\+?\d[\d .()/-]{6,}\d)\b/g, ' ')
         .replace(/\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b/g, ' ')
         .replace(/\b\d{4,}\b/g, ' ')
         .replace(/[<>\[\]{}]/g, ' ')
         .replace(/\s+/g, ' ').trim();
    return x;
}

function medicalEvidenceDifferentials(reading) {
    const out = [];
    const arr = reading && Array.isArray(reading.differentiel) ? reading.differentiel : [];
    arr.slice(0, 4).forEach(item => {
        let v = '';
        if (typeof item === 'string') v = item;
        else if (item && typeof item === 'object') {
            for (const k of ['diagnostic', 'hypothese', 'hypothèse', 'label', 'nom', 'name']) {
                if (typeof item[k] === 'string') { v = item[k]; break; }
            }
        }
        v = medicalEvidenceSafeText(v, 90);
        // Un différentiel bibliographique doit rester un terme médical court, pas un récit clinique.
        if (v && v.length <= 90 && !/\b(patient|monsieur|madame|né|née|adresse|téléphone|telephone)\b/i.test(v)) out.push(v);
    });
    return Array.from(new Set(out)).slice(0, 3);
}

function medicalEvidenceQuery(agentKey, tri, reading) {
    const base = MEDICAL_EVIDENCE_QUERY_MAP[agentKey] || MEDICAL_EVIDENCE_QUERY_MAP.gen;
    const region = medicalEvidenceSafeText(tri && tri.region || '', 60);
    const modality = medicalEvidenceSafeText(tri && tri.modalite || '', 60);
    const dx = medicalEvidenceDifferentials(reading);
    const now = new Date();
    const from = new Date(Date.UTC(now.getUTCFullYear() - 5, now.getUTCMonth(), now.getUTCDate()));
    const iso = d => d.toISOString().slice(0, 10);
    const terms = [base, region, modality].filter(Boolean).map(x => '(' + x.replace(/[():\[\]"]/g, ' ') + ')');
    if (dx.length) terms.push('(' + dx.map(x => '"' + x.replace(/"/g, '') + '"').join(' OR ') + ')');
    return terms.join(' AND ') + ' AND SRC:MED AND FIRST_PDATE:[' + iso(from) + ' TO ' + iso(now) + ']';
}

function medicalEvidencePubTypes(r) {
    const p = r && r.pubTypeList && r.pubTypeList.pubType;
    if (Array.isArray(p)) return p.map(String);
    if (typeof p === 'string') return [p];
    if (typeof r.pubType === 'string') return [r.pubType];
    return [];
}

function medicalEvidenceScore(r) {
    const t = medicalEvidencePubTypes(r).join(' ').toLowerCase();
    let q = 0;
    if (/practice guideline|guideline/.test(t)) q += 80;
    if (/systematic review/.test(t)) q += 70;
    if (/meta-analysis|meta analysis/.test(t)) q += 65;
    if (/randomized controlled trial|randomised controlled trial/.test(t)) q += 45;
    if (/review/.test(t)) q += 30;
    const y = parseInt(r && (r.pubYear || r.firstPublicationDate || ''), 10);
    if (Number.isFinite(y)) q += Math.max(0, y - (new Date().getUTCFullYear() - 5));
    return q;
}

function medicalRecentEvidence(agentKey, tri, reading) {
    const query = medicalEvidenceQuery(agentKey, tri, reading);
    const url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + new URLSearchParams({
        query: query, format: 'json', resultType: 'core', pageSize: '8', sort: 'P_PDATE_D desc', synonym: 'true'
    }).toString();
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = ctl ? setTimeout(() => ctl.abort(), 8000) : null;
    return fetch(url, { method: 'GET', mode: 'cors', credentials: 'omit', signal: ctl ? ctl.signal : undefined })
        .then(r => { if (!r.ok) throw new Error('Europe PMC HTTP ' + r.status); return r.json(); })
        .then(j => {
            const rows = (((j || {}).resultList || {}).result || []).slice();
            rows.sort((a, b) => medicalEvidenceScore(b) - medicalEvidenceScore(a));
            const items = rows.slice(0, 5).map(r => ({
                title: String(r.title || '').slice(0, 300),
                year: String(r.pubYear || (r.firstPublicationDate || '').slice(0, 4) || ''),
                journal: String(r.journalTitle || '').slice(0, 120),
                authors: String(r.authorString || '').slice(0, 180),
                types: medicalEvidencePubTypes(r).slice(0, 6),
                pmid: String(r.pmid || (r.source === 'MED' ? r.id || '' : '')),
                doi: String(r.doi || ''),
                abstract: String(r.abstractText || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 900)
            }));
            return { source: 'Europe PMC / PubMed', query: query, retrieved_at: new Date().toISOString(), items: items, error: '' };
        })
        .catch(e => ({ source: 'Europe PMC / PubMed', query: query, retrieved_at: new Date().toISOString(), items: [], error: String(e && e.message || e) }))
        .finally(() => { if (timer) clearTimeout(timer); });
}

function medicalEvidenceForLectures(lectures, tri) {
    return Promise.all((lectures || []).map(l =>
        medicalRecentEvidence(l.k || 'gen', tri, l.r || {}).then(ev => { l.evidence = ev; return l; })
    ));
}

function medicalEvidencePrompt(evidence) {
    if (!evidence || !Array.isArray(evidence.items) || !evidence.items.length)
        return 'Aucune preuve bibliographique récente n’a pu être récupérée automatiquement. Ne prétends pas disposer de recommandations à jour.';
    const lines = [
        'PREUVES BIBLIOGRAPHIQUES RÉCENTES (métadonnées Europe PMC/PubMed) :',
        'Ces références servent à vérifier le contexte scientifique. Un titre ou résumé ne suffit jamais à prouver une recommandation clinique.',
        'Ne cite que les PMID/DOI effectivement présents. N’invente aucune source.'
    ];
    evidence.items.forEach((it, i) => {
        lines.push((i + 1) + '. ' + it.title + ' — ' + (it.journal || 'revue non précisée') + ' (' + (it.year || 'date inconnue') + ')' +
            (it.types && it.types.length ? ' [' + it.types.join(', ') + ']' : '') +
            (it.pmid ? ' PMID:' + it.pmid : '') + (it.doi ? ' DOI:' + it.doi : '') +
            (it.abstract ? '\n   Résumé: ' + it.abstract : ''));
    });
    return lines.join('\n');
}
'''

if MARK not in s:
    anchor = '// MEDICAL_LLM_STACK_V3'
    if anchor not in s:
        raise SystemExit('medical LLM stack V3 must be injected first')
    s = s.replace(anchor, block + '\n\n' + anchor, 1)

# After consolidating each specialist's lots, retrieve a de-identified recent evidence pack per specialist.
old_return = """return { lectures: lectures, tri: tri, single: (!panel && lectures[0]) ? lectures[0].r : null,
                                 chunks: CH.length, failed: res.length - good.length };"""
new_return = """return medicalEvidenceForLectures(lectures, tri).then(enriched => ({
                            lectures: enriched, tri: tri, single: (!panel && enriched[0]) ? enriched[0].r : null,
                            chunks: CH.length, failed: res.length - good.length
                        }));"""
if old_return in s:
    s = s.replace(old_return, new_return, 1)

# Single-expert mode still carries its recent evidence pack into the report object.
old_single = """const rep = toConsensus(out.single, agents, tri);
                        return finish(rep, agents, tri, t0, steps.length - 1);"""
new_single = """const rep = toConsensus(out.single, agents, tri);
                        rep._evidence = out.lectures && out.lectures[0] ? out.lectures[0].evidence : null;
                        rep._lectures = out.lectures || [];
                        return finish(rep, agents, tri, t0, steps.length - 1);"""
if old_single in s:
    s = s.replace(old_single, new_single, 1)

# Panel consensus receives evidence next to each independent specialist reading.
old_dossier = "const dossier = ok.map(l => '### ' + AG[l.k].n + '\\n' + JSON.stringify(l.r)).join('\\n\\n');"
new_dossier = "const dossier = ok.map(l => '### ' + AG[l.k].n + '\\nLECTURE EXPERTE:\\n' + JSON.stringify(l.r) + '\\n\\n' + medicalEvidencePrompt(l.evidence)).join('\\n\\n---\\n\\n');"
if old_dossier in s:
    s = s.replace(old_dossier, new_dossier, 1)

# Tell the consensus model how to use external evidence without confusing literature with case findings.
needle_rule = '"- Quand les experts se contredisent, ne tranche pas arbitrairement : documente la divergence et les positions.",'
extra_rule = needle_rule + "\n                        \"- Les blocs de preuves Europe PMC/PubMed sont du CONTEXTE SCIENTIFIQUE externe, pas des observations du patient. Ne transforme jamais un résultat de littérature en finding d’image.\",\n                        \"- Pour toute affirmation présentée comme récente, appuie-toi uniquement sur les références datées fournies ; sinon marque explicitement l’incertitude d’actualité.\","
if needle_rule in s and 'CONTEXTE SCIENTIFIQUE externe' not in s:
    s = s.replace(needle_rule, extra_rule, 1)

# Persist evidence provenance without copying the full abstracts into metadata.
needle_meta = "modeles_agents: Object.assign({}, S.agentModelTrace || {}),"
if needle_meta in s and 'preuves_recentes:' not in s:
    s = s.replace(needle_meta, needle_meta + "\n        preuves_recentes: (rep._lectures || []).map(l => ({ expert: l.k, source: l.evidence && l.evidence.source || '', retrieved_at: l.evidence && l.evidence.retrieved_at || '', count: l.evidence && l.evidence.items ? l.evidence.items.length : 0, error: l.evidence && l.evidence.error || '' })),", 1)

required = [
    'MEDICAL_EVIDENCE_RAG_V1',
    'medicalEvidenceForLectures(lectures, tri)',
    'medicalEvidencePrompt(l.evidence)',
    'preuves_recentes:',
    'Europe PMC / PubMed'
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('medical evidence injection incomplete: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('Recent medical evidence RAG V1 injected into index.html')

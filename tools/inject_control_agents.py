from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARK = '// MEDICAL_CONTROL_AGENTS_V1'

block = r'''
// MEDICAL_CONTROL_AGENTS_V1
// Agents de contrôle non diagnostiques : qualité, niveau de preuve, incertitude/sécurité et provenance.
// Ils n'ajoutent aucun finding et ne remplacent jamais la validation humaine.
function medicalControlSafeArray(v) {
    return Array.isArray(v) ? v : [];
}

function medicalControlQualityAgent(tri) {
    tri = tri || {};
    const reasons = [];
    const artefacts = medicalControlSafeArray(tri.artefacts).map(x => String(x || '').slice(0, 120));
    const qualityLabel = String(tri.qualite || '').trim();
    const q = qualityLabel.toLowerCase();
    let status = 'pass';

    if (tri.analysable === false) {
        status = 'fail';
        reasons.push('Triage : examen déclaré non analysable.');
    }
    if (/non[ -]?diagnost|insuff|mauvais|poor|inad[eé]quat|non exploitable/.test(q)) {
        status = 'fail';
        reasons.push('Qualité technique explicitement insuffisante au triage.');
    } else if (/limit|moyen|dégrad|degrad|suboptimal|artefact/.test(q) && status !== 'fail') {
        status = 'caution';
        reasons.push('Qualité technique limitée au triage.');
    }
    if (artefacts.length && status === 'pass') {
        status = 'caution';
        reasons.push('Artefacts signalés au triage.');
    }

    const series = medicalControlSafeArray(S.series);
    const dimensionIssues = [];
    series.forEach((it, i) => {
        const img = it && it.img;
        const w = Number(img && (img.naturalWidth || img.width) || 0);
        const h = Number(img && (img.naturalHeight || img.height) || 0);
        if (!(w > 0 && h > 0)) dimensionIssues.push('image_' + (i + 1) + ':dimensions_indisponibles');
        else if (w < 128 || h < 128) dimensionIssues.push('image_' + (i + 1) + ':tres_faible_resolution');
    });
    if (dimensionIssues.length && status === 'pass') {
        status = 'caution';
        reasons.push('Une ou plusieurs images ont des dimensions absentes ou très faibles.');
    }

    let dicom = null;
    try { dicom = typeof dicomSeriesGeometrySummary === 'function' ? dicomSeriesGeometrySummary() : null; }
    catch (e) { dicom = null; }

    return {
        agent: 'QualityAgent',
        status: status,
        analysable: tri.analysable !== false,
        quality_label: qualityLabel,
        artefacts: artefacts.slice(0, 12),
        image_count: series.length,
        dimension_issues: dimensionIssues.slice(0, 12),
        dicom_geometry_available: !!dicom,
        requires_human_review: status !== 'pass',
        reasons: reasons
    };
}

function medicalEvidenceTier(item) {
    item = item || {};
    const types = medicalControlSafeArray(item.types).join(' ').toLowerCase();
    const sourceType = String(item.source_type || '').toLowerCase();
    if (/practice guideline|guideline|consensus statement/.test(types)) return 'high';
    if (/systematic review|meta-analysis|meta analysis/.test(types)) return 'high';
    if (/randomized controlled trial|randomised controlled trial|controlled clinical trial/.test(types)) return 'moderate';
    if (/review/.test(types)) return 'moderate';
    if (sourceType === 'trial_registry' || /clinical trial registry/.test(types)) return 'registry';
    return 'context';
}

function medicalEvidenceGraderForLecture(l) {
    const ev = l && l.evidence || {};
    const items = medicalControlSafeArray(ev.items);
    const counts = { high: 0, moderate: 0, registry: 0, context: 0 };
    const graded = items.map(it => {
        const tier = medicalEvidenceTier(it);
        counts[tier] = (counts[tier] || 0) + 1;
        return {
            title: String(it && it.title || '').slice(0, 220),
            tier: tier,
            year: String(it && it.year || ''),
            pmid: String(it && it.pmid || ''),
            doi: String(it && it.doi || ''),
            registry_id: String(it && it.registry_id || '')
        };
    });
    let overall = 'none';
    if (counts.high) overall = 'high';
    else if (counts.moderate) overall = 'moderate';
    else if (counts.registry) overall = 'registry';
    else if (counts.context) overall = 'context';

    const warnings = [];
    if (!items.length) warnings.push('Aucune référence récente récupérée automatiquement.');
    if (items.length && counts.registry === items.length) warnings.push('Les seules références sont des enregistrements de registre ; elles ne prouvent pas un résultat clinique.');

    const out = {
        agent: 'EvidenceGrader',
        expert: l && l.k || '',
        overall_tier: overall,
        counts: counts,
        references: graded,
        warnings: warnings,
        note: 'Classement documentaire interne ; ce n’est pas une cotation GRADE officielle.'
    };
    if (l) l.evidence_grade = out;
    return out;
}

function medicalEvidenceGraderForLectures(lectures) {
    (lectures || []).forEach(l => medicalEvidenceGraderForLecture(l));
    return Promise.resolve(lectures || []);
}

function medicalEvidenceGraderSummary(lectures) {
    const rows = (lectures || []).map(l => l.evidence_grade || medicalEvidenceGraderForLecture(l));
    const rank = { none: 0, context: 1, registry: 1, moderate: 2, high: 3 };
    let best = 'none';
    rows.forEach(r => { if ((rank[r.overall_tier] || 0) > (rank[best] || 0)) best = r.overall_tier; });
    return {
        agent: 'EvidenceGrader',
        best_available_tier: best,
        experts: rows,
        warning: 'La force documentaire ne transforme jamais une référence en observation du patient.'
    };
}

function medicalUncertaintySafetyAgent(lectures, tri) {
    const quality = medicalControlQualityAgent(tri);
    const audit = medicalMultiagentAudit(lectures || []);
    const evidence = medicalEvidenceGraderSummary(lectures || []);
    const reasons = [];
    const experts = medicalControlSafeArray(audit.experts);
    const highCritic = experts.some(x => x && x.critic_risk === 'high');
    const missingSecond = experts.length === 0 || experts.some(x => !x.second_read_available);
    const weakIndependence = experts.length > 0 && experts.some(x => !x.model_independent);
    const unresolved = (lectures || []).reduce((n, l) => n + medicalControlSafeArray(l && l.critic && l.critic.disputed_findings).length, 0);

    if (quality.status === 'fail') reasons.push('Qualité technique insuffisante ou examen non analysable.');
    else if (quality.status === 'caution') reasons.push('Qualité technique à interpréter avec prudence.');
    if (missingSecond) reasons.push('Une ou plusieurs secondes lectures sont absentes.');
    if (weakIndependence) reasons.push('Indépendance des modèles réduite pour au moins une double lecture.');
    if (highCritic) reasons.push('Au moins un critique signale un niveau de risque élevé.');
    if (unresolved) reasons.push(String(unresolved) + ' divergence(s) non résolue(s) restent présentes.');
    if (evidence.best_available_tier === 'none') reasons.push('Aucune preuve documentaire récente récupérée pour contextualiser les affirmations dites actuelles.');

    let reliability = 'strong';
    if (quality.status === 'fail' || highCritic || missingSecond) reliability = 'limited';
    else if (quality.status === 'caution' || weakIndependence || unresolved > 0) reliability = 'moderate';

    const abstain = quality.status === 'fail' || highCritic || experts.length === 0;
    const humanReview = abstain || audit.requires_human_review || unresolved > 0 || weakIndependence;

    return {
        agent: 'UncertaintySafetyAgent',
        pipeline_reliability: reliability,
        reliability_scope: 'Fiabilité du pipeline et de ses contrôles, pas probabilité d’une maladie.',
        reader_agreement: experts.length ? experts.map(x => x.critic_agreement).filter(x => typeof x === 'number') : [],
        model_independence: audit.all_model_independent ? 'high' : 'reduced',
        quality_status: quality.status,
        evidence_tier: evidence.best_available_tier,
        unresolved_conflicts: unresolved,
        abstain: abstain,
        human_review_required: humanReview,
        reasons: reasons
    };
}

function medicalProvenanceAgent(lectures, tri, control) {
    const evidenceRefs = [];
    (lectures || []).forEach(l => {
        medicalControlSafeArray(l && l.evidence && l.evidence.items).forEach(it => {
            evidenceRefs.push({
                expert: l.k || '',
                title: String(it && it.title || '').slice(0, 220),
                pmid: String(it && it.pmid || ''),
                doi: String(it && it.doi || ''),
                registry_id: String(it && it.registry_id || ''),
                source: String(l && l.evidence && l.evidence.source || '')
            });
        });
    });

    let dicom = null;
    try { dicom = typeof dicomSeriesGeometrySummary === 'function' ? dicomSeriesGeometrySummary() : null; }
    catch (e) { dicom = null; }

    return {
        agent: 'ProvenanceAgent',
        generated_at: new Date().toISOString(),
        scope: 'pipeline_lineage_not_claim_entailment',
        note: 'Cette provenance décrit l’origine des données et des étapes ; elle ne prouve pas qu’une référence soutient chaque phrase du rapport.',
        inputs: {
            image_count: medicalControlSafeArray(S.series).length,
            modality: String(tri && tri.modalite || ''),
            region: String(tri && tri.region || ''),
            incidence: String(tri && tri.incidence || ''),
            dicom_geometry: dicom
        },
        agents: (lectures || []).map(l => ({
            expert: l.k || '',
            reader_a_model: l.models && l.models.primary || '',
            reader_b_model: l.models && l.models.second || '',
            model_independent: !!l.independent,
            critic_risk: l.critic && l.critic.risk_level || '',
            critic_agreement: l.critic && typeof l.critic.agreement === 'number' ? l.critic.agreement : null,
            quantitative_model: l.quantitative && l.quantitative.model || ''
        })),
        evidence_references: evidenceRefs.slice(0, 40),
        control_agents: {
            quality: control && control.quality && control.quality.status || '',
            evidence: control && control.evidence && control.evidence.best_available_tier || '',
            uncertainty: control && control.uncertainty && control.uncertainty.pipeline_reliability || ''
        }
    };
}

function medicalControlAgentsForLectures(lectures, tri) {
    const quality = medicalControlQualityAgent(tri);
    (lectures || []).forEach(l => { if (l) l.quality_control = quality; });
    return medicalEvidenceGraderForLectures(lectures || []);
}

function medicalControlSummary(lectures, tri) {
    const quality = medicalControlQualityAgent(tri);
    const evidence = medicalEvidenceGraderSummary(lectures || []);
    const uncertainty = medicalUncertaintySafetyAgent(lectures || [], tri);
    return {
        architecture: 'quality + evidence_grader + uncertainty_safety + provenance',
        quality: quality,
        evidence: evidence,
        uncertainty: uncertainty
    };
}
'''

if MARK not in s:
    anchor = '// DICOM_CALIBRATION_V1'
    if anchor not in s:
        raise SystemExit('DICOM calibration layer must be injected before control agents')
    s = s.replace(anchor, block + '\n\n' + anchor, 1)

old_chain = """return medicalEvidenceForLectures(lectures, tri)
                        .then(enriched => medicalCriticForLectures(enriched, tri))
                        .then(enriched => medicalQuantitativeForLectures(enriched, tri))
                        .then(enriched => ({
                            lectures: enriched, tri: tri, single: (!panel && enriched[0]) ? enriched[0].r : null,
                            chunks: CH.length, failed: res.length - good.length
                        }));"""
new_chain = """return medicalEvidenceForLectures(lectures, tri)
                        .then(enriched => medicalCriticForLectures(enriched, tri))
                        .then(enriched => medicalQuantitativeForLectures(enriched, tri))
                        .then(enriched => medicalControlAgentsForLectures(enriched, tri))
                        .then(enriched => ({
                            lectures: enriched, tri: tri, single: (!panel && enriched[0]) ? enriched[0].r : null,
                            chunks: CH.length, failed: res.length - good.length
                        }));"""
if old_chain in s:
    s = s.replace(old_chain, new_chain, 1)

single = "rep.quantitative_measurements = medicalQuantitativeSummary(rep._lectures);"
if single in s and 'rep.control_agents = medicalControlSummary(rep._lectures, tri);' not in s:
    s = s.replace(single, single + "\n                        rep.control_agents = medicalControlSummary(rep._lectures, tri);\n                        rep.uncertainty_safety = rep.control_agents.uncertainty;\n                        rep.provenance = medicalProvenanceAgent(rep._lectures, tri, rep.control_agents);", 1)

panel = "rep.quantitative_measurements = medicalQuantitativeSummary(ok);"
if panel in s and 'rep.control_agents = medicalControlSummary(ok, tri);' not in s:
    s = s.replace(panel, panel + "\n                            rep.control_agents = medicalControlSummary(ok, tri);\n                            rep.uncertainty_safety = rep.control_agents.uncertainty;\n                            rep.provenance = medicalProvenanceAgent(ok, tri, rep.control_agents);", 1)

needle_meta = "dicom_geometry: dicomSeriesGeometrySummary(),"
metadata_marker = "uncertainty_safety: rep.uncertainty_safety ||"
if needle_meta in s and metadata_marker not in s:
    s = s.replace(needle_meta, needle_meta + "\n        control_agents: rep.control_agents || medicalControlSummary(rep._lectures || [], tri),\n        uncertainty_safety: rep.uncertainty_safety || medicalUncertaintySafetyAgent(rep._lectures || [], tri),\n        provenance: rep.provenance || medicalProvenanceAgent(rep._lectures || [], tri, rep.control_agents || medicalControlSummary(rep._lectures || [], tri)),", 1)

s = s.replace("const APP_VERSION = 'v16.6.0';", "const APP_VERSION = 'v16.7.0';", 1)

required = [
    'MEDICAL_CONTROL_AGENTS_V1',
    'medicalControlQualityAgent',
    'medicalEvidenceGraderForLectures',
    'medicalUncertaintySafetyAgent',
    'medicalProvenanceAgent',
    'medicalControlAgentsForLectures(enriched, tri)',
    'control_agents: rep.control_agents ||',
    'uncertainty_safety: rep.uncertainty_safety ||',
    'provenance: rep.provenance ||',
    "APP_VERSION = 'v16.7.0'"
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('control agents injection incomplete: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('Medical Control Agents V1 injected into index.html')

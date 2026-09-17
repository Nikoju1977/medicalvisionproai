from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARK = '// MEDICAL_QUANTITATIVE_PASS_V1'

block = r'''
// MEDICAL_QUANTITATIVE_PASS_V1
// Passe quantitative post-détection. Elle ne s'active que si MedVision-V0-7B
// est réellement exposé par l'endpoint. En l'absence de calibration DICOM
// (Pixel Spacing), aucune dimension physique (mm/cm) n'est inventée.
const SCH_MEDICAL_QUANT = {
    name: 'medical_quantitative_measurement',
    def: {
        type: 'object', additionalProperties: false,
        required: ['label', 'local_xmin', 'local_ymin', 'local_xmax', 'local_ymax',
                   'angle_available', 'angle_deg', 'confidence', 'measurement_type', 'notes'],
        properties: {
            label: { type: 'string' },
            local_xmin: { type: 'number' }, local_ymin: { type: 'number' },
            local_xmax: { type: 'number' }, local_ymax: { type: 'number' },
            angle_available: { type: 'boolean' },
            angle_deg: { type: 'number' },
            confidence: { type: 'number' },
            measurement_type: { type: 'string' },
            notes: { type: 'string' }
        }
    }
};

function medicalQuantitativeModel() {
    // Sécurité : pas de fallback vers un LLM généraliste pour prétendre faire une
    // mesure quantitative spécialisée. Si le modèle dédié n'est pas servi, on saute.
    const id = medicalResolvePreferred([MEDICAL_MODELS.medvisionV0.id]);
    if (!id) return '';
    S.agentModelTrace = S.agentModelTrace || {};
    S.agentModelTrace['quantitative:measurement'] = id;
    return id;
}

function medicalClamp01(x) {
    x = Number(x);
    return Number.isFinite(x) ? Math.max(0, Math.min(1, x)) : 0;
}

function medicalQuantitativeCandidates(reading) {
    const rois = reading && Array.isArray(reading.rois) ? reading.rois : [];
    return rois.filter(r => r && Number.isFinite(Number(r.xmin)) && Number.isFinite(Number(r.ymin)) &&
        Number.isFinite(Number(r.xmax)) && Number.isFinite(Number(r.ymax)) && Number(r.image) >= 1)
        .filter(r => medicalClamp01(r.xmax) > medicalClamp01(r.xmin) && medicalClamp01(r.ymax) > medicalClamp01(r.ymin))
        .slice(0, 4);
}

function medicalQuantitativeCrop(roi) {
    const imageIndex = Math.max(0, Number(roi.image || 1) - 1);
    const it = S.series && S.series[imageIndex];
    const src = it && it.img;
    if (!src) return null;
    const sw = Number(src.naturalWidth || src.videoWidth || src.width || 0);
    const sh = Number(src.naturalHeight || src.videoHeight || src.height || 0);
    if (!(sw > 1 && sh > 1)) return null;

    let x0 = medicalClamp01(roi.xmin), y0 = medicalClamp01(roi.ymin);
    let x1 = medicalClamp01(roi.xmax), y1 = medicalClamp01(roi.ymax);
    const rw = Math.max(0.01, x1 - x0), rh = Math.max(0.01, y1 - y0);
    const padx = Math.max(0.03, rw * 0.35), pady = Math.max(0.03, rh * 0.35);
    const cx0 = Math.max(0, x0 - padx), cy0 = Math.max(0, y0 - pady);
    const cx1 = Math.min(1, x1 + padx), cy1 = Math.min(1, y1 + pady);
    const sx = Math.floor(cx0 * sw), sy = Math.floor(cy0 * sh);
    const cw = Math.max(2, Math.ceil((cx1 - cx0) * sw));
    const ch = Math.max(2, Math.ceil((cy1 - cy0) * sh));

    const c = document.createElement('canvas');
    c.width = cw; c.height = ch;
    const ctx = c.getContext('2d');
    if (!ctx) return null;
    try { ctx.drawImage(src, sx, sy, cw, ch, 0, 0, cw, ch); }
    catch (e) { return null; }

    return {
        image: imageIndex + 1,
        data_url: c.toDataURL('image/jpeg', 0.92),
        source_width: sw, source_height: sh,
        crop: { xmin: cx0, ymin: cy0, xmax: cx1, ymax: cy1 },
        seed_roi: { xmin: x0, ymin: y0, xmax: x1, ymax: y1 }
    };
}

function medicalQuantitativeToOriginal(local, crop) {
    const b = crop.crop;
    const bw = b.xmax - b.xmin, bh = b.ymax - b.ymin;
    let x0 = b.xmin + medicalClamp01(local.local_xmin) * bw;
    let y0 = b.ymin + medicalClamp01(local.local_ymin) * bh;
    let x1 = b.xmin + medicalClamp01(local.local_xmax) * bw;
    let y1 = b.ymin + medicalClamp01(local.local_ymax) * bh;
    if (x1 < x0) { const t = x0; x0 = x1; x1 = t; }
    if (y1 < y0) { const t = y0; y0 = y1; y1 = t; }
    x0 = medicalClamp01(x0); y0 = medicalClamp01(y0);
    x1 = medicalClamp01(x1); y1 = medicalClamp01(y1);
    const nw = Math.max(0, x1 - x0), nh = Math.max(0, y1 - y0);
    return {
        xmin: x0, ymin: y0, xmax: x1, ymax: y1,
        normalized_width: nw, normalized_height: nh,
        normalized_area: nw * nh,
        pixel_width: Math.round(nw * crop.source_width),
        pixel_height: Math.round(nh * crop.source_height)
    };
}

function medicalQuantitativeMeasureOne(model, agentKey, tri, roi) {
    const crop = medicalQuantitativeCrop(roi);
    if (!crop) return Promise.resolve({ ok: false, image: Number(roi.image || 1), label: roi.label || '', error: 'crop_unavailable' });
    const sys = [
        'Tu es un moteur de mesure quantitative d’imagerie médicale.',
        'Ta tâche est UNIQUEMENT de raffiner géométriquement la région déjà détectée dans le crop fourni.',
        'N’établis aucun nouveau diagnostic et ne modifies pas le libellé clinique fourni.',
        'Retourne une boîte locale normalisée 0..1 dans le crop.',
        'Si un angle anatomique pertinent est directement mesurable, renseigne angle_available=true et angle_deg ; sinon false et angle_deg=0.',
        'AUCUNE CALIBRATION PHYSIQUE N’EST FOURNIE : n’invente jamais mm, cm, surface physique ou volume.',
        'Le résultat sera reconverti de manière déterministe dans le repère de l’image originale.',
        medicalKnowledgePrompt(agentKey)
    ].join('\n');
    const userText = [
        'Spécialité : ' + String(agentKey || 'gen'),
        'Examen : ' + String(tri && tri.modalite || '') + ' — ' + String(tri && tri.region || ''),
        'Libellé de la ROI détectée : ' + String(roi.label || 'ROI'),
        'ROI initiale dans l’image originale : ' + JSON.stringify(crop.seed_roi),
        'Le crop contient cette ROI avec une marge. Raffine seulement sa géométrie.'
    ].join('\n');
    return mchat(model, [
        { role: 'system', content: sys },
        { role: 'user', content: [{ type: 'text', text: userText }, { type: 'image_url', image_url: crop.data_url }] }
    ], SCH_MEDICAL_QUANT, { effort: 'medium', max_tokens: 1200, max_tokens_max: 2500, timeout: 90000 })
        .then(q => {
            const geom = medicalQuantitativeToOriginal(q, crop);
            return {
                ok: true,
                model: model,
                image: crop.image,
                label: String(q.label || roi.label || 'ROI'),
                confidence: Math.max(0, Math.min(1, Number(q.confidence) || 0)),
                measurement_type: String(q.measurement_type || 'bounding_box'),
                angle_available: !!q.angle_available,
                angle_deg: q.angle_available ? Number(q.angle_deg) || 0 : null,
                geometry: geom,
                calibration: 'pixel_only_no_physical_spacing',
                physical_units_available: false,
                notes: String(q.notes || '')
            };
        })
        .catch(e => ({
            ok: false, model: model, image: crop.image, label: String(roi.label || 'ROI'),
            error: String(e && (e.msg || e.message) || e)
        }));
}

function medicalQuantitativeForLecture(l, tri) {
    const model = medicalQuantitativeModel();
    const candidates = medicalQuantitativeCandidates(l && l.r);
    if (!l) return Promise.resolve(l);
    if (!model) {
        l.quantitative = { available: false, model: '', calibrated: false, measurements: [], reason: 'dedicated_model_not_available' };
        return Promise.resolve(l);
    }
    if (!candidates.length) {
        l.quantitative = { available: true, model: model, calibrated: false, measurements: [], reason: 'no_localizable_roi' };
        return Promise.resolve(l);
    }
    return Promise.all(candidates.map(r => medicalQuantitativeMeasureOne(model, l.k || 'gen', tri, r)))
        .then(rows => {
            l.quantitative = {
                available: true,
                model: model,
                calibrated: false,
                physical_units_available: false,
                measurements: rows,
                reason: 'physical_spacing_not_available'
            };
            return l;
        });
}

function medicalQuantitativeForLectures(lectures, tri) {
    return Promise.all((lectures || []).map(l => medicalQuantitativeForLecture(l, tri)));
}

function medicalQuantitativeSummary(lectures) {
    const rows = (lectures || []).map(l => ({
        expert: l.k || '',
        available: !!(l.quantitative && l.quantitative.available),
        model: l.quantitative && l.quantitative.model || '',
        calibrated: !!(l.quantitative && l.quantitative.calibrated),
        physical_units_available: !!(l.quantitative && l.quantitative.physical_units_available),
        measurements: l.quantitative && Array.isArray(l.quantitative.measurements) ? l.quantitative.measurements : [],
        reason: l.quantitative && l.quantitative.reason || ''
    }));
    return {
        mode: 'post_detection_quantitative',
        physical_calibration: false,
        warning: 'Mesures physiques indisponibles sans Pixel Spacing/calibration fiable.',
        experts: rows,
        total_successful_measurements: rows.reduce((n, r) => n + r.measurements.filter(x => x && x.ok).length, 0)
    };
}
'''

if MARK not in s:
    anchor = '// MEDICAL_MULTIAGENT_REVIEW_V1'
    if anchor not in s:
        raise SystemExit('multi-agent review layer must be injected before quantitative pass')
    s = s.replace(anchor, block + '\n\n' + anchor, 1)

old_chain = """return medicalEvidenceForLectures(lectures, tri)
                        .then(enriched => medicalCriticForLectures(enriched, tri))
                        .then(enriched => ({
                            lectures: enriched, tri: tri, single: (!panel && enriched[0]) ? enriched[0].r : null,
                            chunks: CH.length, failed: res.length - good.length
                        }));"""
new_chain = """return medicalEvidenceForLectures(lectures, tri)
                        .then(enriched => medicalCriticForLectures(enriched, tri))
                        .then(enriched => medicalQuantitativeForLectures(enriched, tri))
                        .then(enriched => ({
                            lectures: enriched, tri: tri, single: (!panel && enriched[0]) ? enriched[0].r : null,
                            chunks: CH.length, failed: res.length - good.length
                        }));"""
if old_chain in s:
    s = s.replace(old_chain, new_chain, 1)

needle_single = "rep.audit_multiagent = medicalMultiagentAudit(rep._lectures);"
if needle_single in s and 'rep.quantitative_measurements = medicalQuantitativeSummary(rep._lectures);' not in s:
    s = s.replace(needle_single, needle_single + "\n                        rep.quantitative_measurements = medicalQuantitativeSummary(rep._lectures);", 1)

needle_panel = "rep.audit_multiagent = medicalMultiagentAudit(ok);"
if needle_panel in s and 'rep.quantitative_measurements = medicalQuantitativeSummary(ok);' not in s:
    s = s.replace(needle_panel, needle_panel + "\n                            rep.quantitative_measurements = medicalQuantitativeSummary(ok);", 1)

needle_meta = "audit_multiagent: rep.audit_multiagent || medicalMultiagentAudit(rep._lectures || []),"
if needle_meta in s and 'quantitative_measurements:' not in s:
    s = s.replace(needle_meta, needle_meta + "\n        quantitative_measurements: rep.quantitative_measurements || medicalQuantitativeSummary(rep._lectures || []),", 1)

s = s.replace("const APP_VERSION = 'v16.4.0';", "const APP_VERSION = 'v16.5.0';", 1)

required = [
    'MEDICAL_QUANTITATIVE_PASS_V1',
    'medicalQuantitativeForLectures(enriched, tri)',
    'dedicated_model_not_available',
    'pixel_only_no_physical_spacing',
    'quantitative_measurements:',
    "APP_VERSION = 'v16.5.0'"
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('quantitative medical pass injection incomplete: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('Medical Quantitative Pass V1 injected into index.html')

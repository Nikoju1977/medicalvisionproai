from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARK = '// DICOM_CALIBRATION_V1'

block = r'''
// DICOM_CALIBRATION_V1
// Calibration physique à partir des métadonnées DICOM. La priorité est donnée à
// Pixel Spacing (0028,0030), exprimé en mm : row spacing puis column spacing.
// Imager Pixel Spacing est conservé comme information mais n'active jamais, seul,
// une mesure patient en mm afin d'éviter une erreur de grossissement géométrique.
function dicomIsFile(f) {
    return !!f && (/\.dcm$/i.test(f.name || '') || /application\/dicom/i.test(f.type || ''));
}

function dicomBaseName(name) {
    return String(name || '').replace(/\.[^.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function dicomReadAscii(bytes, start, len) {
    let out = '';
    const end = Math.min(bytes.length, start + len);
    for (let i = start; i < end; i++) out += String.fromCharCode(bytes[i]);
    return out.replace(/[\u0000 ]+$/g, '').trim();
}

function dicomElementAt(view, bytes, off, explicitVR, littleEndian) {
    if (off < 0 || off + 8 > bytes.length) return null;
    const group = view.getUint16(off, littleEndian);
    const element = view.getUint16(off + 2, littleEndian);
    let vr = '', len = 0, valueOff = 0;
    if (explicitVR) {
        vr = String.fromCharCode(bytes[off + 4], bytes[off + 5]);
        if (!/^[A-Z]{2}$/.test(vr)) return null;
        const longVR = /^(OB|OD|OF|OL|OV|OW|SQ|UC|UR|UT|UN)$/.test(vr);
        if (longVR) {
            if (off + 12 > bytes.length) return null;
            len = view.getUint32(off + 8, littleEndian); valueOff = off + 12;
        } else {
            len = view.getUint16(off + 6, littleEndian); valueOff = off + 8;
        }
    } else {
        len = view.getUint32(off + 4, littleEndian); valueOff = off + 8;
    }
    if (len === 0xffffffff || valueOff + len > bytes.length) return null;
    return { group, element, vr, len, valueOff };
}

function dicomFindTag(view, bytes, group, element, explicitVR, littleEndian, limit) {
    const end = Math.min(bytes.length - 8, limit || bytes.length - 8);
    for (let off = 0; off <= end; off++) {
        if (view.getUint16(off, littleEndian) !== group || view.getUint16(off + 2, littleEndian) !== element) continue;
        const el = dicomElementAt(view, bytes, off, explicitVR, littleEndian);
        if (el) return el;
    }
    return null;
}

function dicomStringValue(view, bytes, group, element, explicitVR, littleEndian, limit) {
    const el = dicomFindTag(view, bytes, group, element, explicitVR, littleEndian, limit);
    return el ? dicomReadAscii(bytes, el.valueOff, el.len) : '';
}

function dicomNumberList(v) {
    return String(v || '').split('\\').map(x => Number(String(x).trim())).filter(Number.isFinite);
}

async function dicomParseCalibrationFile(file) {
    const MAX_HEADER = 32 * 1024 * 1024;
    const blob = file.slice(0, Math.min(file.size, MAX_HEADER));
    const buf = blob.arrayBuffer ? await blob.arrayBuffer() : await new Promise((res, rej) => {
        const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => rej(new Error('lecture DICOM impossible')); r.readAsArrayBuffer(blob);
    });
    const bytes = new Uint8Array(buf), view = new DataView(buf);
    if (bytes.length < 16) throw new Error('DICOM trop court');

    // File Meta Information est toujours Explicit VR Little Endian.
    const ts = dicomStringValue(view, bytes, 0x0002, 0x0010, true, true, Math.min(bytes.length, 1024 * 1024));
    if (ts === '1.2.840.10008.1.2.1.99') throw new Error('DICOM Deflated non pris en charge pour la calibration locale');
    const implicit = ts === '1.2.840.10008.1.2';
    const bigEndian = ts === '1.2.840.10008.1.2.2';
    const explicit = !implicit;
    const le = !bigEndian;

    let pixelLimit = bytes.length;
    const pix = dicomFindTag(view, bytes, 0x7fe0, 0x0010, explicit, le, bytes.length);
    if (pix) pixelLimit = Math.max(0, pix.valueOff - (explicit ? 12 : 8));

    const rowsEl = dicomFindTag(view, bytes, 0x0028, 0x0010, explicit, le, pixelLimit);
    const colsEl = dicomFindTag(view, bytes, 0x0028, 0x0011, explicit, le, pixelLimit);
    const readUS = el => el && el.len >= 2 ? view.getUint16(el.valueOff, le) : null;
    const rows = readUS(rowsEl), columns = readUS(colsEl);

    const px = dicomNumberList(dicomStringValue(view, bytes, 0x0028, 0x0030, explicit, le, pixelLimit));
    const imagerPx = dicomNumberList(dicomStringValue(view, bytes, 0x0018, 0x1164, explicit, le, pixelLimit));
    const sliceThickness = Number(dicomStringValue(view, bytes, 0x0018, 0x0050, explicit, le, pixelLimit)) || null;
    const spacingBetweenSlices = Number(dicomStringValue(view, bytes, 0x0018, 0x0088, explicit, le, pixelLimit)) || null;
    const ipp = dicomNumberList(dicomStringValue(view, bytes, 0x0020, 0x0032, explicit, le, pixelLimit));
    const iop = dicomNumberList(dicomStringValue(view, bytes, 0x0020, 0x0037, explicit, le, pixelLimit));

    const rowMm = px.length >= 2 && px[0] > 0 ? px[0] : null;
    const colMm = px.length >= 2 && px[1] > 0 ? px[1] : null;
    const imagerRowMm = imagerPx.length >= 2 && imagerPx[0] > 0 ? imagerPx[0] : null;
    const imagerColMm = imagerPx.length >= 2 && imagerPx[1] > 0 ? imagerPx[1] : null;

    return {
        fileName: file.name,
        transferSyntaxUID: ts || '', rows, columns,
        rowMm, colMm, imagerRowMm, imagerColMm,
        sliceThicknessMm: sliceThickness,
        spacingBetweenSlicesMm: spacingBetweenSlices,
        imagePositionPatient: ipp.length >= 3 ? ipp.slice(0, 3) : null,
        imageOrientationPatient: iop.length >= 6 ? iop.slice(0, 6) : null,
        sopInstanceUID: dicomStringValue(view, bytes, 0x0008, 0x0018, explicit, le, pixelLimit),
        seriesInstanceUID: dicomStringValue(view, bytes, 0x0020, 0x000e, explicit, le, pixelLimit),
        frameOfReferenceUID: dicomStringValue(view, bytes, 0x0020, 0x0052, explicit, le, pixelLimit),
        instanceNumber: Number(dicomStringValue(view, bytes, 0x0020, 0x0013, explicit, le, pixelLimit)) || null,
        physicalValid: !!(rowMm && colMm),
        source: rowMm && colMm ? 'Pixel Spacing (0028,0030)' : (imagerRowMm && imagerColMm ? 'Imager Pixel Spacing only (0018,1164)' : 'no physical spacing')
    };
}

function dicomAttachCalibration(meta, preferredItems) {
    const pool = (preferredItems && preferredItems.length ? preferredItems : S.series || []).filter(Boolean);
    const base = dicomBaseName(meta.fileName);
    let candidates = pool.filter(it => dicomBaseName(it.name) === base);
    if (!candidates.length && meta.rows && meta.columns) {
        candidates = pool.filter(it => Number(it.h) === Number(meta.rows) && Number(it.w) === Number(meta.columns));
    }
    if (candidates.length !== 1) return { attached: false, reason: candidates.length ? 'ambiguous_match' : 'no_matching_image' };
    const it = candidates[0];
    if (!(meta.rows && meta.columns) || Number(it.h) !== Number(meta.rows) || Number(it.w) !== Number(meta.columns))
        return { attached: false, reason: 'dimension_mismatch' };

    it.ann = it.ann || newAnn();
    it.ann.dicomCal = Object.assign({}, meta, {
        validPhysical: !!meta.physicalValid,
        verifiedDimensions: true,
        matchedImage: it.name
    });
    if (it === S.series[S.active]) {
        S.dicomCal = it.ann.dicomCal;
        upCal();
    }
    return { attached: true, item: it, calibrated: !!meta.physicalValid };
}

async function dicomImportCalibrationFiles(files, preferredItems) {
    const out = { parsed: 0, attached: 0, calibrated: 0, warnings: [] };
    for (const f of files || []) {
        try {
            const meta = await dicomParseCalibrationFile(f); out.parsed++;
            const a = dicomAttachCalibration(meta, preferredItems);
            if (a.attached) { out.attached++; if (a.calibrated) out.calibrated++; }
            else out.warnings.push((f.name || 'DICOM') + ': ' + a.reason);
        } catch (e) { out.warnings.push((f.name || 'DICOM') + ': ' + String(e && e.message || e)); }
    }
    return out;
}

function dicomPhysicalLength(dxPx, dyPx, cal) {
    if (!cal || !cal.validPhysical || !(cal.rowMm > 0) || !(cal.colMm > 0)) return null;
    const x = Number(dxPx) * cal.colMm, y = Number(dyPx) * cal.rowMm;
    const mm = Math.sqrt(x * x + y * y);
    if (!(mm > 0)) return null;
    const uPx = MET.uDist();
    const ux = cal.colMm * uPx, uy = cal.rowMm * uPx;
    const u = Math.sqrt(Math.pow((x / mm) * ux, 2) + Math.pow((y / mm) * uy, 2));
    return { mm: mm, u: u, U: u * MET.K, relPct: mm ? (u / mm) * 100 : 0 };
}

function dicomPhysicalGeometry(imageNo, geom) {
    const it = S.series && S.series[Math.max(0, Number(imageNo || 1) - 1)];
    const cal = it && it.ann && it.ann.dicomCal;
    if (!cal || !cal.validPhysical || !geom) return null;
    const widthMm = Number(geom.pixel_width || 0) * cal.colMm;
    const heightMm = Number(geom.pixel_height || 0) * cal.rowMm;
    return {
        source: cal.source,
        row_mm_per_px: cal.rowMm,
        col_mm_per_px: cal.colMm,
        width_mm: widthMm,
        height_mm: heightMm,
        bounding_box_area_mm2: widthMm * heightMm,
        note: 'Surface = aire de la boîte englobante, pas une segmentation lésionnelle.'
    };
}

function dicomSeriesGeometrySummary() {
    const rows = (S.series || []).map((it, idx) => ({ idx, cal: it && it.ann && it.ann.dicomCal })).filter(x => x.cal && x.cal.validPhysical);
    const bySeries = {};
    rows.forEach(x => { const k = x.cal.seriesInstanceUID || 'unknown'; (bySeries[k] || (bySeries[k] = [])).push(x); });
    const series = Object.keys(bySeries).map(k => {
        const a = bySeries[k];
        const spacings = [];
        if (a.length > 1 && a.every(x => x.cal.imagePositionPatient && x.cal.imageOrientationPatient)) {
            const o = a[0].cal.imageOrientationPatient;
            const r = o.slice(0,3), c = o.slice(3,6);
            const n = [r[1]*c[2]-r[2]*c[1], r[2]*c[0]-r[0]*c[2], r[0]*c[1]-r[1]*c[0]];
            const pos = a.map(x => x.cal.imagePositionPatient[0]*n[0] + x.cal.imagePositionPatient[1]*n[1] + x.cal.imagePositionPatient[2]*n[2]).sort((x,y)=>x-y);
            for (let i=1;i<pos.length;i++) if (Math.abs(pos[i]-pos[i-1]) > 1e-6) spacings.push(Math.abs(pos[i]-pos[i-1]));
        }
        spacings.sort((x,y)=>x-y);
        const median = spacings.length ? spacings[Math.floor(spacings.length/2)] : null;
        const consistent = median ? spacings.every(v => Math.abs(v-median) <= Math.max(0.1, median*0.05)) : false;
        return {
            seriesInstanceUID: k,
            calibratedImages: a.length,
            slice_spacing_mm: median,
            slice_spacing_consistent: consistent,
            volume_geometry_ready: !!(median && consistent),
            volume_note: 'Géométrie volumique disponible, mais aucun volume lésionnel n’est calculé sans segmentation surfacique par coupe.'
        };
    });
    return { series: series };
}
'''

if MARK not in s:
    anchor = '// MEDICAL_QUANTITATIVE_PASS_V1'
    if anchor not in s:
        raise SystemExit('quantitative pass must be injected before DICOM calibration')
    s = s.replace(anchor, block + '\n\n' + anchor, 1)

# Image chooser also accepts DICOM metadata sidecars.
s = s.replace('accept="image/jpeg,image/png,image/webp,image/bmp,.jpg,.jpeg,.png,.webp,.bmp"',
              'accept="image/jpeg,image/png,image/webp,image/bmp,application/dicom,.jpg,.jpeg,.png,.webp,.bmp,.dcm"', 1)
s = s.replace('JPEG, PNG, WebP, BMP · 24 images maximum · 30 Mo par image. Exportez les DICOM en PNG/JPEG depuis votre lecteur.',
              'JPEG, PNG, WebP, BMP · DICOM accepté comme métadonnées de calibration · 24 images maximum · 30 Mo par image. Pour l’affichage, exportez encore le DICOM en PNG/JPEG à dimensions natives.', 1)

# Persist per-image DICOM calibration.
s = s.replace("function newAnn() { return { pxMm: null, uRelCal: null, calD: null, calMm: null, meas: [], rois: [], drw: [], aiRois: [] };",
              "function newAnn() { return { pxMm: null, uRelCal: null, calD: null, calMm: null, dicomCal: null, meas: [], rois: [], drw: [], aiRois: [] };", 1)
s = s.replace("pxMm: null, comp: false, ak: '', mdl:", "pxMm: null, dicomCal: null, comp: false, ak: '', mdl:", 1)
s = s.replace("S.pxMm = null; S.uRelCal = null; S.calD = null; S.calMm = null;",
              "S.pxMm = null; S.dicomCal = null; S.uRelCal = null; S.calD = null; S.calMm = null;", 1)
s = s.replace("it.ann = { pxMm: S.pxMm, uRelCal: S.uRelCal, calD: S.calD, calMm: S.calMm, meas: S.meas, rois: S.rois, drw: S.drw, aiRois: S.aiRois };",
              "it.ann = { pxMm: S.pxMm, uRelCal: S.uRelCal, calD: S.calD, calMm: S.calMm, dicomCal: S.dicomCal || null, meas: S.meas, rois: S.rois, drw: S.drw, aiRois: S.aiRois };", 1)
s = s.replace("S.pxMm = a.pxMm; S.uRelCal = a.uRelCal || null; S.calD = a.calD || null; S.calMm = a.calMm || null;",
              "S.pxMm = a.pxMm; S.dicomCal = a.dicomCal || null; S.uRelCal = a.uRelCal || null; S.calD = a.calD || null; S.calMm = a.calMm || null;", 1)

# DICOM calibration takes precedence over manual isotropic calibration in display and length tool.
needle_cal = """function upCal() {
    const el = $('calS');
    if (S.pxMm) {"""
replacement_cal = """function upCal() {
    const el = $('calS');
    if (S.dicomCal && S.dicomCal.validPhysical) {
        el.textContent = 'DICOM · ' + S.dicomCal.rowMm.toFixed(4) + '×' + S.dicomCal.colMm.toFixed(4) + ' mm/px · Pixel Spacing';
        el.style.color = 'var(--ac)';
        return;
    }
    if (S.pxMm) {"""
if needle_cal in s:
    s = s.replace(needle_cal, replacement_cal, 1)

old_meas = "const _m = S.pxMm ? MET.length(dp, S.pxMm, S.uRelCal) : null;"
new_meas = "const _m = (S.dicomCal && S.dicomCal.validPhysical) ? dicomPhysicalLength(m.b.x - m.a.x, m.b.y - m.a.y, S.dicomCal) : (S.pxMm ? MET.length(dp, S.pxMm, S.uRelCal) : null);"
s = s.replace(old_meas, new_meas, 1)
s = s.replace("if (!S.pxMm) {\n                const mm = prompt('Calibration : longueur réelle de ce segment, en mm ?');",
              "if (!S.pxMm && !(S.dicomCal && S.dicomCal.validPhysical)) {\n                const mm = prompt('Calibration : longueur réelle de ce segment, en mm ?');", 1)

# hFile: DICOM sidecars do not consume image slots.
old_hfile = """    const room = SERIES_MAX - S.series.length;
    if (room <= 0) return toast('Série pleine (24 images maximum)');
    S.importing = true;
    const status = $('importStatus'), items = [], failures = [];
    try {
        for (const f of files.slice(0, room)) {
            status.textContent = 'Importation : ' + (items.length + failures.length + 1) + '/' + Math.min(files.length, room);
            try {
                if (!/\\.(jpe?g|png|webp|bmp)$/i.test(f.name) && !/^image\\/(jpeg|png|webp|bmp)$/.test(f.type)) throw new Error('format non pris en charge');
                if (f.size > 30 * 1024 * 1024) throw new Error('limite de 30 Mo dépassée');
                items.push(await mkItem(await readAsURL(f), f.name, 'image', null));
            } catch (e) { failures.push(f.name + ' : ' + e.message); }
        }
        addItems(items);
        status.textContent = items.length + ' image(s) importée(s).' +
            (files.length > room ? ' Limite de 24 images atteinte.' : '') +
            (failures.length ? ' Fichiers ignorés : ' + failures.join(' ; ') : '');
    } finally { S.importing = false; }"""
new_hfile = """    const dicomFiles = files.filter(dicomIsFile);
    const imageFiles = files.filter(f => !dicomIsFile(f));
    const room = SERIES_MAX - S.series.length;
    if (room <= 0 && !dicomFiles.length) return toast('Série pleine (24 images maximum)');
    S.importing = true;
    const status = $('importStatus'), items = [], failures = [];
    try {
        for (const f of imageFiles.slice(0, Math.max(0, room))) {
            status.textContent = 'Importation : ' + (items.length + failures.length + 1) + '/' + Math.min(imageFiles.length, Math.max(0, room));
            try {
                if (!/\\.(jpe?g|png|webp|bmp)$/i.test(f.name) && !/^image\\/(jpeg|png|webp|bmp)$/.test(f.type)) throw new Error('format non pris en charge');
                if (f.size > 30 * 1024 * 1024) throw new Error('limite de 30 Mo dépassée');
                items.push(await mkItem(await readAsURL(f), f.name, 'image', null));
            } catch (e) { failures.push(f.name + ' : ' + e.message); }
        }
        addItems(items);
        const dc = dicomFiles.length ? await dicomImportCalibrationFiles(dicomFiles, items.length ? items : S.series) : {parsed:0,attached:0,calibrated:0,warnings:[]};
        status.textContent = items.length + ' image(s) importée(s).' +
            (imageFiles.length > Math.max(0, room) ? ' Limite de 24 images atteinte.' : '') +
            (dc.parsed ? ' DICOM: ' + dc.attached + '/' + dc.parsed + ' apparié(s), ' + dc.calibrated + ' calibré(s).' : '') +
            (failures.length ? ' Fichiers ignorés : ' + failures.join(' ; ') : '') +
            (dc.warnings.length ? ' DICOM: ' + dc.warnings.join(' ; ') : '');
    } finally { S.importing = false; }"""
if old_hfile in s:
    s = s.replace(old_hfile, new_hfile, 1)

# Quantitative results gain physical geometry only when a verified DICOM calibration exists.
s = s.replace("const geom = medicalQuantitativeToOriginal(q, crop);\n            return {",
              "const geom = medicalQuantitativeToOriginal(q, crop);\n            const physical = dicomPhysicalGeometry(crop.image, geom);\n            return {", 1)
s = s.replace("calibration: 'pixel_only_no_physical_spacing',\n                physical_units_available: false,",
              "calibration: physical ? 'DICOM Pixel Spacing (0028,0030)' : 'pixel_only_no_physical_spacing',\n                physical_units_available: !!physical,\n                physical: physical,", 1)

old_quant_summary = """                calibrated: false,
                physical_units_available: false,
                measurements: rows,
                reason: 'physical_spacing_not_available'"""
new_quant_summary = """                calibrated: rows.some(x => x && x.physical_units_available),
                physical_units_available: rows.some(x => x && x.physical_units_available),
                measurements: rows,
                reason: rows.some(x => x && x.physical_units_available) ? 'dicom_pixel_spacing' : 'physical_spacing_not_available'"""
s = s.replace(old_quant_summary, new_quant_summary, 1)
s = s.replace("physical_calibration: false,\n        warning: 'Mesures physiques indisponibles sans Pixel Spacing/calibration fiable.',",
              "physical_calibration: rows.some(r => r.physical_units_available),\n        warning: rows.some(r => r.physical_units_available) ? 'Mesures physiques fondées sur DICOM Pixel Spacing avec dimensions image vérifiées.' : 'Mesures physiques indisponibles sans Pixel Spacing/calibration fiable.',\n        dicom_geometry: dicomSeriesGeometrySummary(),", 1)

# Audit metadata includes DICOM geometry provenance.
needle_meta = "quantitative_measurements: rep.quantitative_measurements || medicalQuantitativeSummary(rep._lectures || []),"
if needle_meta in s and 'dicom_geometry:' not in s:
    s = s.replace(needle_meta, needle_meta + "\n        dicom_geometry: dicomSeriesGeometrySummary(),", 1)

s = s.replace("const APP_VERSION = 'v16.5.0';", "const APP_VERSION = 'v16.6.0';", 1)

required = [
    'DICOM_CALIBRATION_V1',
    'Pixel Spacing (0028,0030)',
    'dicomImportCalibrationFiles',
    'dicomPhysicalLength',
    'dicomPhysicalGeometry',
    'dicomSeriesGeometrySummary',
    'dicomCal: null',
    "APP_VERSION = 'v16.6.0'"
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('DICOM calibration injection incomplete: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('DICOM Calibration V1 injected into index.html')

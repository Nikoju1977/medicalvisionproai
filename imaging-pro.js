/* MedVision Imaging Pro v17
 * Local DICOM volume viewer: uncompressed grayscale DICOM, MPR, window/level,
 * synchronized crosshair, CT HU readout and axial cine.
 * No network requests are made by this module.
 */
(function (global) {
'use strict';

const MVI = {
    version: '17.1.2',
    state: {
        volume: null,
        x: 0, y: 0, z: 0,
        center: 0, width: 1,
        cine: null,
        projection: 'slice', slab: 1,
        thresholdEnabled: false, thresholdMin: 0, thresholdMax: 0,
        canvasMap: new Map()
    }
};

const $ = id => document.getElementById(id);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const finite = v => Number.isFinite(v);

function readAscii(bytes, start, len) {
    let out = '';
    const end = Math.min(bytes.length, start + Math.max(0, len));
    for (let i = start; i < end; i++) out += String.fromCharCode(bytes[i]);
    return out.replace(/[\u0000 ]+$/g, '').trim();
}

function elementAt(view, bytes, off, explicitVR, littleEndian) {
    if (off < 0 || off + 8 > bytes.length) return null;
    const group = view.getUint16(off, littleEndian);
    const element = view.getUint16(off + 2, littleEndian);
    let vr = '', len, valueOff;
    if (explicitVR) {
        vr = String.fromCharCode(bytes[off + 4], bytes[off + 5]);
        if (!/^[A-Z]{2}$/.test(vr)) return null;
        const longVR = /^(OB|OD|OF|OL|OV|OW|SQ|UC|UR|UT|UN)$/.test(vr);
        if (longVR) {
            if (off + 12 > bytes.length) return null;
            len = view.getUint32(off + 8, littleEndian);
            valueOff = off + 12;
        } else {
            len = view.getUint16(off + 6, littleEndian);
            valueOff = off + 8;
        }
    } else {
        len = view.getUint32(off + 4, littleEndian);
        valueOff = off + 8;
    }
    if (len === 0xffffffff || valueOff + len > bytes.length) return null;
    return { group, element, vr, len, valueOff, off };
}

function findTag(view, bytes, group, element, explicitVR, littleEndian, start, limit) {
    const from = Math.max(0, start || 0);
    const end = Math.min(bytes.length - 8, limit == null ? bytes.length - 8 : limit);
    // DICOM data elements are even-aligned. Candidate validation in elementAt
    // prevents arbitrary byte matches from being accepted as elements.
    for (let off = from + (from & 1); off <= end; off += 2) {
        if (view.getUint16(off, littleEndian) !== group ||
            view.getUint16(off + 2, littleEndian) !== element) continue;
        const el = elementAt(view, bytes, off, explicitVR, littleEndian);
        if (el) return el;
    }
    return null;
}

function stringTag(view, bytes, group, element, explicitVR, littleEndian, start, limit) {
    const el = findTag(view, bytes, group, element, explicitVR, littleEndian, start, limit);
    return el ? readAscii(bytes, el.valueOff, el.len) : '';
}

function numberList(value) {
    return String(value || '').split('\\').map(v => Number(v.trim())).filter(Number.isFinite);
}

function firstNumber(value, fallback) {
    const a = numberList(value);
    return a.length ? a[0] : fallback;
}

function usTag(view, bytes, group, element, explicitVR, littleEndian, start, limit, fallback) {
    const el = findTag(view, bytes, group, element, explicitVR, littleEndian, start, limit);
    if (!el || el.len < 2) return fallback;
    return view.getUint16(el.valueOff, littleEndian);
}

function median(values) {
    const a = values.filter(v => finite(v) && v > 0).slice().sort((x, y) => x - y);
    if (!a.length) return null;
    const m = Math.floor(a.length / 2);
    return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

function normalFromIOP(iop) {
    if (!iop || iop.length < 6) return null;
    const r = iop.slice(0, 3), c = iop.slice(3, 6);
    const n = [
        r[1] * c[2] - r[2] * c[1],
        r[2] * c[0] - r[0] * c[2],
        r[0] * c[1] - r[1] * c[0]
    ];
    const d = Math.hypot(n[0], n[1], n[2]);
    return d > 0 ? n.map(v => v / d) : null;
}

function projection(ipp, iop) {
    const n = normalFromIOP(iop);
    if (!n || !ipp || ipp.length < 3) return null;
    return ipp[0] * n[0] + ipp[1] * n[1] + ipp[2] * n[2];
}

function supportedTransferSyntax(uid) {
    const ts = String(uid || '').trim();
    if (!ts || ts === '1.2.840.10008.1.2' || ts === '1.2.840.10008.1.2.1' || ts === '1.2.840.10008.1.2.2') return true;
    return false;
}

function parseDicomBuffer(buffer, fileName) {
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    if (bytes.length < 16) throw new Error('DICOM trop court');

    const hasPreamble = bytes.length >= 132 &&
        bytes[128] === 68 && bytes[129] === 73 && bytes[130] === 67 && bytes[131] === 77;
    const datasetStart = hasPreamble ? 132 : 0;

    // File meta information is Explicit VR Little Endian.
    const ts = stringTag(view, bytes, 0x0002, 0x0010, true, true, datasetStart, Math.min(bytes.length, datasetStart + 1024 * 1024));
    if (!supportedTransferSyntax(ts)) {
        if (ts === '1.2.840.10008.1.2.1.99') throw new Error('DICOM Deflated non pris en charge');
        if (/^1\.2\.840\.10008\.1\.2\.4\./.test(ts)) throw new Error('DICOM JPEG/JPEG-LS/JPEG2000 compressé non pris en charge par ce lecteur local');
        if (ts === '1.2.840.10008.1.2.5') throw new Error('DICOM RLE compressé non pris en charge par ce lecteur local');
        throw new Error('Transfer Syntax DICOM non prise en charge : ' + (ts || 'inconnue'));
    }

    const implicit = !ts || ts === '1.2.840.10008.1.2';
    const bigEndian = ts === '1.2.840.10008.1.2.2';
    const explicit = !implicit;
    const le = !bigEndian;

    const rows = usTag(view, bytes, 0x0028, 0x0010, explicit, le, datasetStart, bytes.length, 0);
    const columns = usTag(view, bytes, 0x0028, 0x0011, explicit, le, datasetStart, bytes.length, 0);
    const samples = usTag(view, bytes, 0x0028, 0x0002, explicit, le, datasetStart, bytes.length, 1);
    const bitsAllocated = usTag(view, bytes, 0x0028, 0x0100, explicit, le, datasetStart, bytes.length, 0);
    const bitsStored = usTag(view, bytes, 0x0028, 0x0101, explicit, le, datasetStart, bytes.length, bitsAllocated);
    const pixelRepresentation = usTag(view, bytes, 0x0028, 0x0103, explicit, le, datasetStart, bytes.length, 0);
    const numberOfFrames = Math.max(1, Math.round(firstNumber(stringTag(view, bytes, 0x0028, 0x0008, explicit, le, datasetStart, bytes.length), 1)));
    const photometric = stringTag(view, bytes, 0x0028, 0x0004, explicit, le, datasetStart, bytes.length) || 'MONOCHROME2';

    if (!(rows > 0 && columns > 0)) throw new Error('Rows/Columns DICOM absents');
    if (samples !== 1) throw new Error('Seuls les DICOM monochromes sont pris en charge en v17');
    if (bitsAllocated !== 8 && bitsAllocated !== 16) throw new Error('Bits Allocated non pris en charge : ' + bitsAllocated);
    if (rows * columns * numberOfFrames > 120000000) throw new Error('Volume DICOM trop volumineux pour le navigateur');

    const pixel = findTag(view, bytes, 0x7fe0, 0x0010, explicit, le, datasetStart, bytes.length);
    if (!pixel) throw new Error('Pixel Data DICOM introuvable');
    const bytesPerSample = bitsAllocated / 8;
    const expected = rows * columns * numberOfFrames * bytesPerSample;
    if (pixel.len < expected) throw new Error('Pixel Data tronqué');

    const slope = firstNumber(stringTag(view, bytes, 0x0028, 0x1053, explicit, le, datasetStart, pixel.off), 1);
    const intercept = firstNumber(stringTag(view, bytes, 0x0028, 0x1052, explicit, le, datasetStart, pixel.off), 0);
    const windowCenter = firstNumber(stringTag(view, bytes, 0x0028, 0x1050, explicit, le, datasetStart, pixel.off), null);
    const windowWidth = firstNumber(stringTag(view, bytes, 0x0028, 0x1051, explicit, le, datasetStart, pixel.off), null);
    const pixelSpacing = numberList(stringTag(view, bytes, 0x0028, 0x0030, explicit, le, datasetStart, pixel.off));
    const ipp = numberList(stringTag(view, bytes, 0x0020, 0x0032, explicit, le, datasetStart, pixel.off));
    const iop = numberList(stringTag(view, bytes, 0x0020, 0x0037, explicit, le, datasetStart, pixel.off));
    const sliceThickness = firstNumber(stringTag(view, bytes, 0x0018, 0x0050, explicit, le, datasetStart, pixel.off), null);
    const spacingBetweenSlices = firstNumber(stringTag(view, bytes, 0x0018, 0x0088, explicit, le, datasetStart, pixel.off), null);
    const instanceNumber = firstNumber(stringTag(view, bytes, 0x0020, 0x0013, explicit, le, datasetStart, pixel.off), null);
    const seriesUID = stringTag(view, bytes, 0x0020, 0x000e, explicit, le, datasetStart, pixel.off) || 'series-unknown';
    const modality = stringTag(view, bytes, 0x0008, 0x0060, explicit, le, datasetStart, pixel.off) || '';
    const studyDescription = stringTag(view, bytes, 0x0008, 0x1030, explicit, le, datasetStart, pixel.off) || '';
    const seriesDescription = stringTag(view, bytes, 0x0008, 0x103e, explicit, le, datasetStart, pixel.off) || '';

    const count = rows * columns * numberOfFrames;
    const data = new Float32Array(count);
    const mask = bitsStored > 0 && bitsStored < bitsAllocated ? (Math.pow(2, bitsStored) - 1) : null;
    const signBit = pixelRepresentation && bitsStored > 0 ? Math.pow(2, bitsStored - 1) : null;
    const signRange = pixelRepresentation && bitsStored > 0 ? Math.pow(2, bitsStored) : null;

    let min = Infinity, max = -Infinity;
    for (let i = 0; i < count; i++) {
        const off = pixel.valueOff + i * bytesPerSample;
        let raw = bitsAllocated === 8 ? view.getUint8(off) : view.getUint16(off, le);
        if (mask != null) raw &= mask;
        if (pixelRepresentation && signBit != null && raw >= signBit) raw -= signRange;
        const value = raw * slope + intercept;
        data[i] = value;
        if (value < min) min = value;
        if (value > max) max = value;
    }

    return {
        fileName: fileName || 'dicom',
        transferSyntaxUID: ts || '1.2.840.10008.1.2',
        rows, columns, numberOfFrames, bitsAllocated, bitsStored, pixelRepresentation,
        photometric, slope, intercept, windowCenter, windowWidth,
        pixelSpacing: pixelSpacing.length >= 2 ? pixelSpacing.slice(0, 2) : null,
        imagePositionPatient: ipp.length >= 3 ? ipp.slice(0, 3) : null,
        imageOrientationPatient: iop.length >= 6 ? iop.slice(0, 6) : null,
        sliceThickness, spacingBetweenSlices, instanceNumber, seriesUID, modality,
        studyDescription, seriesDescription, data, min, max
    };
}

function slicesFromParsed(parsed) {
    const one = parsed.rows * parsed.columns;
    const basePos = projection(parsed.imagePositionPatient, parsed.imageOrientationPatient);
    const step = parsed.spacingBetweenSlices || parsed.sliceThickness || 1;
    const out = [];
    for (let frame = 0; frame < parsed.numberOfFrames; frame++) {
        const start = frame * one;
        out.push({
            parsed,
            data: parsed.data.subarray(start, start + one),
            position: finite(basePos) ? basePos + frame * step : null,
            instance: finite(parsed.instanceNumber) ? parsed.instanceNumber + frame : frame,
            frame
        });
    }
    return out;
}

function buildVolume(parsedFiles) {
    const groups = new Map();
    parsedFiles.forEach(p => {
        const k = p.seriesUID || 'series-unknown';
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(...slicesFromParsed(p));
    });
    if (!groups.size) throw new Error('Aucune série DICOM exploitable');

    let slices = Array.from(groups.values()).sort((a, b) => b.length - a.length)[0];
    const first = slices[0].parsed;
    slices = slices.filter(s => s.parsed.rows === first.rows && s.parsed.columns === first.columns);
    if (!slices.length) throw new Error('Série DICOM vide après contrôle des dimensions');

    const hasPosition = slices.every(s => finite(s.position));
    slices.sort(hasPosition
        ? (a, b) => a.position - b.position
        : (a, b) => (a.instance || 0) - (b.instance || 0));

    const diffs = [];
    if (hasPosition) for (let i = 1; i < slices.length; i++) {
        const d = Math.abs(slices[i].position - slices[i - 1].position);
        if (d > 1e-6) diffs.push(d);
    }
    const spacingZ = median(diffs) || first.spacingBetweenSlices || first.sliceThickness || 1;
    const spacingY = first.pixelSpacing && first.pixelSpacing[0] > 0 ? first.pixelSpacing[0] : 1;
    const spacingX = first.pixelSpacing && first.pixelSpacing[1] > 0 ? first.pixelSpacing[1] : 1;

    let min = Infinity, max = -Infinity;
    slices.forEach(s => {
        if (s.parsed.min < min) min = s.parsed.min;
        if (s.parsed.max > max) max = s.parsed.max;
    });
    let center = finite(first.windowCenter) ? first.windowCenter : (min + max) / 2;
    let width = finite(first.windowWidth) && first.windowWidth > 1 ? first.windowWidth : Math.max(1, max - min);

    return {
        rows: first.rows,
        columns: first.columns,
        slices,
        spacingX, spacingY, spacingZ,
        modality: first.modality,
        photometric: first.photometric,
        studyDescription: first.studyDescription,
        seriesDescription: first.seriesDescription,
        seriesUID: first.seriesUID,
        min, max, center, width
    };
}

function voxel(volume, x, y, z) {
    if (!volume || z < 0 || z >= volume.slices.length ||
        y < 0 || y >= volume.rows || x < 0 || x >= volume.columns) return null;
    return volume.slices[z].data[y * volume.columns + x];
}

function windowByte(value, center, width, invert) {
    width = Math.max(1, width);
    let v = ((value - (center - width / 2)) / width) * 255;
    v = clamp(Math.round(v), 0, 255);
    return invert ? 255 - v : v;
}

function planeInfo(volume, plane) {
    if (plane === 'axial') return { w: volume.columns, h: volume.rows, sx: volume.spacingX, sy: volume.spacingY };
    if (plane === 'coronal') return { w: volume.columns, h: volume.slices.length, sx: volume.spacingX, sy: volume.spacingZ };
    return { w: volume.rows, h: volume.slices.length, sx: volume.spacingY, sy: volume.spacingZ };
}

function planeValue(volume, plane, px, py) {
    const s = MVI.state;
    const coord = plane === 'axial' ? [px, py, s.z] :
        plane === 'coronal' ? [px, s.y, volume.slices.length - 1 - py] :
        [s.x, px, volume.slices.length - 1 - py];
    if (s.projection === 'slice' || s.slab <= 1) return voxel(volume, ...coord);
    const axis = plane === 'axial' ? 2 : plane === 'coronal' ? 1 : 0;
    const limit = [volume.columns, volume.rows, volume.slices.length][axis];
    const start = Math.max(0, coord[axis] - Math.floor((s.slab - 1) / 2));
    const end = Math.min(limit - 1, coord[axis] + Math.ceil((s.slab - 1) / 2));
    let result = s.projection === 'mip' ? -Infinity : Infinity;
    for (let i = start; i <= end; i++) {
        coord[axis] = i;
        const value = voxel(volume, ...coord);
        result = s.projection === 'mip' ? Math.max(result, value) : Math.min(result, value);
    }
    return result;
}

function crosshairSource(plane, info) {
    const s = MVI.state, v = s.volume;
    if (plane === 'axial') return { x: s.x, y: s.y };
    if (plane === 'coronal') return { x: s.x, y: v.slices.length - 1 - s.z };
    return { x: s.y, y: v.slices.length - 1 - s.z };
}

function prepareCanvas(canvas) {
    const dpr = Math.min(global.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(240, Math.round((rect.width || 320) * dpr));
    const h = Math.max(240, Math.round((rect.height || 320) * dpr));
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;
    return { w, h, dpr };
}

function renderPlane(plane) {
    const v = MVI.state.volume;
    const canvas = $('mvi-' + plane);
    if (!v || !canvas) return;
    const info = planeInfo(v, plane);
    const src = document.createElement('canvas');
    src.width = info.w; src.height = info.h;
    const sx = src.getContext('2d', { alpha: false });
    const img = sx.createImageData(info.w, info.h);
    const inv = String(v.photometric).toUpperCase() === 'MONOCHROME1';
    let q = 0;
    for (let y = 0; y < info.h; y++) {
        for (let x = 0; x < info.w; x++) {
            const value = planeValue(v, plane, x, y);
            const g = windowByte(value, MVI.state.center, MVI.state.width, inv);
            const marked = MVI.state.thresholdEnabled && value >= MVI.state.thresholdMin && value <= MVI.state.thresholdMax;
            img.data[q++] = marked ? Math.round(g * .55 + 115) : g;
            img.data[q++] = marked ? Math.round(g * .55 + 45) : g;
            img.data[q++] = marked ? Math.round(g * .55 + 10) : g;
            img.data[q++] = 255;
        }
    }
    sx.putImageData(img, 0, 0);

    const target = prepareCanvas(canvas);
    const ctx = canvas.getContext('2d', { alpha: false });
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, target.w, target.h);
    const physicalAspect = Math.max(0.05, (info.w * info.sx) / Math.max(1e-6, info.h * info.sy));
    let dw = target.w, dh = dw / physicalAspect;
    if (dh > target.h) { dh = target.h; dw = dh * physicalAspect; }
    const dx = (target.w - dw) / 2, dy = (target.h - dh) / 2;
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(src, dx, dy, dw, dh);

    const c = crosshairSource(plane, info);
    const cx = dx + (c.x + 0.5) / info.w * dw;
    const cy = dy + (c.y + 0.5) / info.h * dh;
    ctx.save();
    ctx.strokeStyle = 'rgba(0,229,255,.9)';
    ctx.lineWidth = Math.max(1, target.dpr);
    ctx.beginPath();
    ctx.moveTo(dx, cy); ctx.lineTo(dx + dw, cy);
    ctx.moveTo(cx, dy); ctx.lineTo(cx, dy + dh);
    ctx.stroke();
    ctx.restore();

    MVI.state.canvasMap.set(canvas, { plane, info, dx, dy, dw, dh });
}

function updateReadout() {
    const v = MVI.state.volume;
    if (!v) return;
    const s = MVI.state;
    const value = voxel(v, s.x, s.y, s.z);
    const unit = String(v.modality).toUpperCase() === 'CT' ? 'HU' : 'valeur';
    const pos = [
        (s.x * v.spacingX).toFixed(1),
        (s.y * v.spacingY).toFixed(1),
        (s.z * v.spacingZ).toFixed(1)
    ];
    const el = $('mvi-readout');
    if (el) el.textContent =
        'Voxel [' + s.x + ', ' + s.y + ', ' + s.z + '] · ' +
        (finite(value) ? value.toFixed(1) : '—') + ' ' + unit +
        ' · ≈ ' + pos.join(' / ') + ' mm';

    const xs = $('mvi-x'), ys = $('mvi-y'), zs = $('mvi-z');
    if (xs) xs.value = s.x;
    if (ys) ys.value = s.y;
    if (zs) zs.value = s.z;
    const wl = $('mvi-wl');
    if (wl) wl.textContent = 'C ' + Math.round(s.center) + ' · W ' + Math.round(s.width);
}

function renderAll() {
    renderPlane('axial');
    renderPlane('coronal');
    renderPlane('sagittal');
    updateReadout();
}

function setCrosshair(x, y, z) {
    const v = MVI.state.volume;
    if (!v) return;
    if (finite(x)) MVI.state.x = clamp(Math.round(x), 0, v.columns - 1);
    if (finite(y)) MVI.state.y = clamp(Math.round(y), 0, v.rows - 1);
    if (finite(z)) MVI.state.z = clamp(Math.round(z), 0, v.slices.length - 1);
    renderAll();
}

function canvasPointer(ev) {
    const canvas = ev.currentTarget;
    const m = MVI.state.canvasMap.get(canvas);
    const v = MVI.state.volume;
    if (!m || !v) return;
    const rect = canvas.getBoundingClientRect();
    const cx = (ev.clientX - rect.left) * canvas.width / Math.max(1, rect.width);
    const cy = (ev.clientY - rect.top) * canvas.height / Math.max(1, rect.height);
    if (cx < m.dx || cx > m.dx + m.dw || cy < m.dy || cy > m.dy + m.dh) return;
    const px = clamp(Math.floor((cx - m.dx) / m.dw * m.info.w), 0, m.info.w - 1);
    const py = clamp(Math.floor((cy - m.dy) / m.dh * m.info.h), 0, m.info.h - 1);
    if (m.plane === 'axial') setCrosshair(px, py, null);
    else if (m.plane === 'coronal') setCrosshair(px, null, v.slices.length - 1 - py);
    else setCrosshair(null, px, v.slices.length - 1 - py);
}

function setWindow(center, width) {
    if (finite(center)) MVI.state.center = center;
    if (finite(width)) MVI.state.width = Math.max(1, width);
    const ci = $('mvi-center'), wi = $('mvi-width');
    if (ci) ci.value = Math.round(MVI.state.center);
    if (wi) wi.value = Math.round(MVI.state.width);
    renderAll();
}

function preset(name) {
    const v = MVI.state.volume;
    if (!v) return;
    const presets = {
        auto: [(v.min + v.max) / 2, Math.max(1, v.max - v.min)],
        soft: [40, 400],
        lung: [-600, 1500],
        bone: [500, 2000],
        brain: [40, 80]
    };
    const p = presets[name] || presets.auto;
    setWindow(p[0], p[1]);
}

function stopCine() {
    if (MVI.state.cine) clearInterval(MVI.state.cine);
    MVI.state.cine = null;
    const b = $('mvi-cine');
    if (b) b.textContent = '▶ Cine axial';
}

function toggleCine() {
    if (!MVI.state.volume) return;
    if (MVI.state.cine) return stopCine();
    const fps = clamp(Number(($('mvi-fps') || {}).value || 12), 1, 30);
    MVI.state.cine = setInterval(() => {
        const v = MVI.state.volume;
        MVI.state.z = (MVI.state.z + 1) % v.slices.length;
        renderAll();
    }, Math.round(1000 / fps));
    const b = $('mvi-cine');
    if (b) b.textContent = '⏸ Stop cine';
}

function renderAxialToCanvas(scale) {
    const v = MVI.state.volume;
    if (!v) return null;
    const c = document.createElement('canvas');
    c.width = v.columns * (scale || 1);
    c.height = v.rows * (scale || 1);
    const raw = document.createElement('canvas');
    raw.width = v.columns; raw.height = v.rows;
    const ctx = raw.getContext('2d', { alpha: false });
    const img = ctx.createImageData(v.columns, v.rows);
    const inv = String(v.photometric).toUpperCase() === 'MONOCHROME1';
    const slice = v.slices[MVI.state.z].data;
    let q = 0;
    for (let i = 0; i < slice.length; i++) {
        const g = windowByte(slice[i], MVI.state.center, MVI.state.width, inv);
        img.data[q++] = g; img.data[q++] = g; img.data[q++] = g; img.data[q++] = 255;
    }
    ctx.putImageData(img, 0, 0);
    const out = c.getContext('2d', { alpha: false });
    out.imageSmoothingEnabled = true;
    out.drawImage(raw, 0, 0, c.width, c.height);
    return c;
}

function sendCurrentSliceToAI() {
    const c = renderAxialToCanvas(1);
    const input = $('fIn');
    if (!c || !input) return;
    c.toBlob(blob => {
        if (!blob) return;
        const file = new File([blob], 'DICOM_' + (MVI.state.volume.modality || 'IMG') + '_slice_' + (MVI.state.z + 1) + '.png', { type: 'image/png' });
        try {
            const dt = new DataTransfer();
            dt.items.add(file);
            input.files = dt.files;
            input.dispatchEvent(new Event('change', { bubbles: true }));
            const gen = $('genMode');
            if (gen) gen.checked = false;
            if (global.toast) global.toast('Coupe DICOM ajoutée à la série pour analyse médicale.');
        } catch (e) {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = file.name;
            a.click();
            setTimeout(() => URL.revokeObjectURL(a.href), 2000);
        }
    }, 'image/png');
}

async function loadFiles(files) {
    const list = Array.from(files || []);
    if (!list.length) return;
    stopCine();
    const panel = $('mvi-panel');
    if (panel) panel.hidden = false;
    const status = $('mvi-status');
    const parsed = [], errors = [];
    for (let i = 0; i < list.length; i++) {
        const file = list[i];
        if (status) status.textContent = 'Lecture DICOM ' + (i + 1) + '/' + list.length + ' · ' + file.name;
        try {
            if (file.size > 512 * 1024 * 1024) throw new Error('fichier > 512 Mo');
            parsed.push(parseDicomBuffer(await file.arrayBuffer(), file.name));
        } catch (e) {
            errors.push(file.name + ' : ' + (e && e.message ? e.message : e));
        }
    }
    if (!parsed.length) {
        if (status) status.textContent = 'Aucun DICOM exploitable. ' + errors.join(' · ');
        return;
    }
    const v = buildVolume(parsed);
    MVI.state.volume = v;
    MVI.state.x = Math.floor(v.columns / 2);
    MVI.state.y = Math.floor(v.rows / 2);
    MVI.state.z = Math.floor(v.slices.length / 2);
    MVI.state.center = v.center;
    MVI.state.width = v.width;
    MVI.state.thresholdEnabled = false;
    MVI.state.thresholdMin = v.min;
    MVI.state.thresholdMax = v.max;
    MVI.state.projection = 'slice';
    MVI.state.slab = 1;
    if ($('mvi-projection')) $('mvi-projection').value = 'slice';
    if ($('mvi-slab')) $('mvi-slab').value = 1;
    if ($('mvi-threshold-enabled')) $('mvi-threshold-enabled').checked = false;
    if ($('mvi-threshold-min')) $('mvi-threshold-min').value = Math.round(v.min);
    if ($('mvi-threshold-max')) $('mvi-threshold-max').value = Math.round(v.max);

    const xs = $('mvi-x'), ys = $('mvi-y'), zs = $('mvi-z');
    if (xs) { xs.max = v.columns - 1; xs.value = MVI.state.x; }
    if (ys) { ys.max = v.rows - 1; ys.value = MVI.state.y; }
    if (zs) { zs.max = v.slices.length - 1; zs.value = MVI.state.z; }

    const title = $('mvi-title');
    if (title) title.textContent =
        (v.modality || 'DICOM') + ' · ' + v.columns + '×' + v.rows + '×' + v.slices.length +
        ' · ' + v.spacingX.toFixed(3) + '×' + v.spacingY.toFixed(3) + '×' + v.spacingZ.toFixed(3) + ' mm';
    const ci = $('mvi-center'), wi = $('mvi-width');
    if (ci) ci.value = Math.round(v.center);
    if (wi) wi.value = Math.round(v.width);
    if (status) status.textContent =
        parsed.length + ' fichier(s) DICOM lus · série principale ' + v.slices.length + ' coupe(s)' +
        (errors.length ? ' · ' + errors.length + ' ignoré(s): ' + errors.join(' · ') : '');
    renderAll();
}

function injectStyle() {
    if ($('mvi-style')) return;
    const s = document.createElement('style');
    s.id = 'mvi-style';
    s.textContent = [
        '.mvi-panel{margin-top:12px;border-color:rgba(0,229,255,.35)}',
        '.mvi-head{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:10px}',
        '.mvi-head strong{color:var(--cy)}',
        '.mvi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}',
        '.mvi-view{background:#000;border:1px solid var(--bd);border-radius:10px;overflow:hidden;position:relative;min-width:0}',
        '.mvi-view canvas{display:block;width:100%;height:auto;aspect-ratio:1/1;background:#000;cursor:crosshair}',
        '.mvi-view b{position:absolute;left:7px;top:6px;color:var(--cy);font:600 .65rem var(--fmono);background:rgba(0,0,0,.65);padding:2px 5px;border-radius:4px}',
        '.mvi-tools{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:10px 0}',
        '.mvi-tools input[type=number]{width:90px;font-size:.78rem!important;padding:7px}',
        '.mvi-sliders{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}',
        '.mvi-slider{font-size:.66rem;color:var(--txd)}',
        '.mvi-slider input{padding:0;width:100%;accent-color:var(--cy)}',
        '.mvi-status,.mvi-readout{font: .67rem var(--fmono);color:var(--txd);line-height:1.5;margin-top:8px;overflow-wrap:anywhere}',
        '@media(max-width:760px){.mvi-grid{grid-template-columns:1fr}.mvi-view canvas{aspect-ratio:4/3}.mvi-sliders{grid-template-columns:1fr}}'
    ].join('');
    document.head.appendChild(s);
}

function injectUI() {
    if ($('mvi-panel')) return;
    injectStyle();
    const imageInput = $('fIn');
    if (!imageInput) return;

    const actions = imageInput.closest('.file-pick')?.parentElement || imageInput.parentElement;
    const dicomButton = document.createElement('button');
    dicomButton.className = 'bt';
    dicomButton.type = 'button';
    dicomButton.innerHTML = '<span>DICOM / MPR</span>';
    dicomButton.setAttribute('aria-label', 'Importer une série DICOM pour reconstruction multiplanaire');
    const dicomInput = document.createElement('input');
    dicomInput.id = 'mvi-dicom-input';
    dicomInput.type = 'file';
    dicomInput.hidden = true;
    dicomInput.multiple = true;
    dicomInput.accept = '.dcm,application/dicom';
    dicomButton.addEventListener('click', () => dicomInput.click());
    dicomInput.addEventListener('change', () => {
        const files = dicomInput.files;
        dicomInput.value = '';
        loadFiles(files);
    });
    actions.insertBefore(dicomButton, imageInput.closest('.file-pick')?.nextSibling || imageInput.nextSibling);
    actions.insertBefore(dicomInput, dicomButton.nextSibling);

    const host = imageInput.closest('.cd') || imageInput.parentElement;
    const panel = document.createElement('section');
    panel.id = 'mvi-panel';
    panel.className = 'cd mvi-panel';
    panel.hidden = true;
    panel.innerHTML =
        '<div class="mvi-head"><div><strong>Imagerie Pro · MPR</strong><div id="mvi-title" class="sub">Aucune série DICOM</div></div>' +
        '<button class="bt" type="button" id="mvi-clear">Fermer</button></div>' +
        '<div class="mvi-grid">' +
          '<div class="mvi-view"><b>AXIAL</b><canvas id="mvi-axial"></canvas></div>' +
          '<div class="mvi-view"><b>CORONAL</b><canvas id="mvi-coronal"></canvas></div>' +
          '<div class="mvi-view"><b>SAGITTAL</b><canvas id="mvi-sagittal"></canvas></div>' +
        '</div>' +
        '<div class="mvi-tools">' +
          '<button class="bt" type="button" data-mvi-preset="auto">Auto</button>' +
          '<button class="bt" type="button" data-mvi-preset="soft">Tissus mous</button>' +
          '<button class="bt" type="button" data-mvi-preset="lung">Poumon</button>' +
          '<button class="bt" type="button" data-mvi-preset="bone">Os</button>' +
          '<button class="bt" type="button" data-mvi-preset="brain">Cerveau</button>' +
          '<label class="sub">Centre <input id="mvi-center" type="number" step="1"></label>' +
          '<label class="sub">Largeur <input id="mvi-width" type="number" min="1" step="1"></label>' +
          '<span id="mvi-wl" class="sub"></span>' +
        '</div>' +
        '<div class="mvi-tools">' +
          '<label class="sub">Projection <select id="mvi-projection"><option value="slice">Coupe</option><option value="mip">MIP</option><option value="minip">MinIP</option></select></label>' +
          '<label class="sub">Épaisseur (voxels) <input id="mvi-slab" type="number" min="1" max="51" step="2" value="1"></label>' +
          '<label class="sub"><input id="mvi-threshold-enabled" type="checkbox"> Masque de seuil</label>' +
          '<label class="sub">Min <input id="mvi-threshold-min" type="number" step="1"></label>' +
          '<label class="sub">Max <input id="mvi-threshold-max" type="number" step="1"></label>' +
        '</div><div class="mvi-tools">' +
          '<button class="bt" type="button" id="mvi-cine">▶ Cine axial</button>' +
          '<label class="sub">FPS <input id="mvi-fps" type="number" min="1" max="30" value="12"></label>' +
          '<button class="bt bp" type="button" id="mvi-send-ai">Analyser la coupe active</button>' +
        '</div>' +
        '<div class="mvi-sliders">' +
          '<label class="mvi-slider">X<input id="mvi-x" type="range" min="0" max="0" value="0"></label>' +
          '<label class="mvi-slider">Y<input id="mvi-y" type="range" min="0" max="0" value="0"></label>' +
          '<label class="mvi-slider">Z<input id="mvi-z" type="range" min="0" max="0" value="0"></label>' +
        '</div>' +
        '<div id="mvi-readout" class="mvi-readout"></div>' +
        '<div id="mvi-status" class="mvi-status">Importez des DICOM monochromes non compressés. MIP/MinIP et masque de seuil sont des outils exploratoires, sans segmentation IA ni validation diagnostique. JPEG/JPEG2000/RLE restent non pris en charge.</div>';
    host.insertAdjacentElement('afterend', panel);

    ['axial', 'coronal', 'sagittal'].forEach(p => $('mvi-' + p).addEventListener('pointerdown', canvasPointer));
    panel.querySelectorAll('[data-mvi-preset]').forEach(b => b.addEventListener('click', () => preset(b.dataset.mviPreset)));
    $('mvi-center').addEventListener('change', e => setWindow(Number(e.target.value), MVI.state.width));
    $('mvi-width').addEventListener('change', e => setWindow(MVI.state.center, Number(e.target.value)));
    $('mvi-x').addEventListener('input', e => setCrosshair(Number(e.target.value), null, null));
    $('mvi-y').addEventListener('input', e => setCrosshair(null, Number(e.target.value), null));
    $('mvi-z').addEventListener('input', e => setCrosshair(null, null, Number(e.target.value)));
    $('mvi-cine').addEventListener('click', toggleCine);
    $('mvi-projection').addEventListener('change', e => { MVI.state.projection = e.target.value; renderAll(); });
    $('mvi-slab').addEventListener('change', e => { MVI.state.slab = clamp(Math.round(Number(e.target.value) || 1), 1, 51); e.target.value = MVI.state.slab; renderAll(); });
    $('mvi-threshold-enabled').addEventListener('change', e => { MVI.state.thresholdEnabled = e.target.checked; renderAll(); });
    ['min', 'max'].forEach(bound => $('mvi-threshold-' + bound).addEventListener('change', e => {
        const value = Number(e.target.value);
        if (finite(value)) MVI.state[bound === 'min' ? 'thresholdMin' : 'thresholdMax'] = value;
        renderAll();
    }));
    $('mvi-send-ai').addEventListener('click', sendCurrentSliceToAI);
    $('mvi-clear').addEventListener('click', () => {
        stopCine();
        MVI.state.volume = null;
        panel.hidden = true;
    });
    global.addEventListener('resize', () => {
        if (MVI.state.volume && !panel.hidden) renderAll();
    });
}

MVI.parseDicomBuffer = parseDicomBuffer;
MVI.buildVolume = buildVolume;
MVI.planeValue = planeValue;
MVI.loadFiles = loadFiles;
MVI.renderAll = renderAll;
MVI.setWindow = setWindow;
MVI.setCrosshair = setCrosshair;
MVI.preset = preset;
MVI.sendCurrentSliceToAI = sendCurrentSliceToAI;

global.MedVisionImagingPro = MVI;

if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', injectUI, { once: true });
    else injectUI();
}

})(typeof window !== 'undefined' ? window : globalThis);

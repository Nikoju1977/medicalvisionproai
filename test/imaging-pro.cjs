const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const context = vm.createContext({ console, Uint8Array, Float32Array, DataView, ArrayBuffer, Math, Number, String, Map, Set, globalThis: null });
context.globalThis = context;
vm.runInContext(fs.readFileSync('imaging-pro.js', 'utf8'), context, { filename: 'imaging-pro.js' });
const api = context.MedVisionImagingPro;
assert.ok(api, 'Imaging Pro API exposed');

function padEven(buf, pad = 0x20) {
    if (buf.length % 2 === 0) return buf;
    return Buffer.concat([buf, Buffer.from([pad])]);
}
function ascii(s, pad = 0x20) { return padEven(Buffer.from(String(s), 'ascii'), pad); }
function tagShort(group, element, vr, value) {
    const head = Buffer.alloc(8);
    head.writeUInt16LE(group, 0); head.writeUInt16LE(element, 2);
    head.write(vr, 4, 2, 'ascii'); head.writeUInt16LE(value.length, 6);
    return Buffer.concat([head, value]);
}
function tagLong(group, element, vr, value) {
    const head = Buffer.alloc(12);
    head.writeUInt16LE(group, 0); head.writeUInt16LE(element, 2);
    head.write(vr, 4, 2, 'ascii'); head.writeUInt16LE(0, 6); head.writeUInt32LE(value.length, 8);
    return Buffer.concat([head, value]);
}
function us(value) {
    const b = Buffer.alloc(2); b.writeUInt16LE(value, 0); return b;
}
function makeDicom({ instance = 1, z = 0, raw = [0, 1024, 1124, 2048] } = {}) {
    const preamble = Buffer.alloc(132); preamble.write('DICM', 128, 4, 'ascii');
    const meta = tagShort(0x0002, 0x0010, 'UI', ascii('1.2.840.10008.1.2.1', 0));
    const pixels = Buffer.alloc(raw.length * 2);
    raw.forEach((v, i) => pixels.writeUInt16LE(v & 0xffff, i * 2));
    const ds = [
        tagShort(0x0008, 0x0060, 'CS', ascii('CT')),
        tagShort(0x0008, 0x1030, 'LO', ascii('Synthetic study')),
        tagShort(0x0008, 0x103e, 'LO', ascii('Synthetic axial')),
        tagShort(0x0020, 0x000e, 'UI', ascii('1.2.3.4.5', 0)),
        tagShort(0x0020, 0x0013, 'IS', ascii(String(instance))),
        tagShort(0x0020, 0x0032, 'DS', ascii('0\\0\\' + z)),
        tagShort(0x0020, 0x0037, 'DS', ascii('1\\0\\0\\0\\1\\0')),
        tagShort(0x0018, 0x0050, 'DS', ascii('2.5')),
        tagShort(0x0018, 0x0088, 'DS', ascii('2.5')),
        tagShort(0x0028, 0x0002, 'US', us(1)),
        tagShort(0x0028, 0x0004, 'CS', ascii('MONOCHROME2')),
        tagShort(0x0028, 0x0010, 'US', us(2)),
        tagShort(0x0028, 0x0011, 'US', us(2)),
        tagShort(0x0028, 0x0030, 'DS', ascii('0.5\\0.5')),
        tagShort(0x0028, 0x0100, 'US', us(16)),
        tagShort(0x0028, 0x0101, 'US', us(16)),
        tagShort(0x0028, 0x0102, 'US', us(15)),
        tagShort(0x0028, 0x0103, 'US', us(0)),
        tagShort(0x0028, 0x1050, 'DS', ascii('40')),
        tagShort(0x0028, 0x1051, 'DS', ascii('400')),
        tagShort(0x0028, 0x1052, 'DS', ascii('-1024')),
        tagShort(0x0028, 0x1053, 'DS', ascii('1')),
        tagLong(0x7fe0, 0x0010, 'OW', pixels)
    ];
    return Buffer.concat([preamble, meta, ...ds]);
}

test('Imaging Pro decodes uncompressed 16-bit CT pixels into HU', () => {
    const b = makeDicom();
    const p = api.parseDicomBuffer(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), 'ct1.dcm');
    assert.equal(p.rows, 2);
    assert.equal(p.columns, 2);
    assert.equal(p.modality, 'CT');
    assert.deepEqual(Array.from(p.pixelSpacing), [0.5, 0.5]);
    assert.deepEqual(Array.from(p.data), [-1024, 0, 100, 1024]);
    assert.equal(p.windowCenter, 40);
    assert.equal(p.windowWidth, 400);
});

test('Imaging Pro builds and sorts a calibrated 3D series', () => {
    const a = makeDicom({ instance: 2, z: 2.5 });
    const b = makeDicom({ instance: 1, z: 0 });
    const pa = api.parseDicomBuffer(a.buffer.slice(a.byteOffset, a.byteOffset + a.byteLength), 'a.dcm');
    const pb = api.parseDicomBuffer(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), 'b.dcm');
    const v = api.buildVolume([pa, pb]);
    assert.equal(v.slices.length, 2);
    assert.equal(v.spacingX, 0.5);
    assert.equal(v.spacingY, 0.5);
    assert.equal(v.spacingZ, 2.5);
    assert.equal(v.slices[0].instance, 1);
    assert.equal(v.slices[1].instance, 2);
});

test('Imaging Pro refuses compressed transfer syntaxes instead of mis-decoding them', () => {
    const b = makeDicom();
    const needle = Buffer.from('1.2.840.10008.1.2.1\0', 'ascii');
    const at = b.indexOf(needle);
    assert.ok(at > 0);
    const replacement = Buffer.from('1.2.840.10008.1.2.5\0', 'ascii');
    replacement.copy(b, at, 0, Math.min(replacement.length, needle.length));
    assert.throws(
        () => api.parseDicomBuffer(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), 'rle.dcm'),
        /RLE|Transfer Syntax/
    );
});

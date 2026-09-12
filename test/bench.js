// Banc de mesure — MedVision AI Pro
//
// Fait tourner le pipeline REEL sur un lot d'images annotees et calcule
// sensibilite, specificite et taux de faux positifs. C'est la seule facon
// de repondre a « est-ce que l'application voit juste ».
//
//   node test/bench.js index.html cases/manifest.json --key=CLE_MISTRAL
//   node test/bench.js index.html cases/manifest.json --base=http://localhost:11434/v1 --model=medgemma:4b
//
// Options : --experts=3  --single  --nozoom  --out=resultats.csv  --limit=N
//
// Format du manifeste (JSON) :
//   [ { "file": "cases/n001.png", "label": "normal" },
//     { "file": "cases/p012.png", "label": "anomalie", "attendu": "opacite alveolaire LID" } ]
//
// « label » vaut "normal" ou "anomalie". « attendu » est facultatif et sert
// seulement a la relecture humaine du CSV.
//
// Prerequis : npm install jsdom canvas

const { JSDOM, VirtualConsole } = require('jsdom');
const { createCanvas, loadImage } = require('canvas');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const APP = args[0];
const MANIFEST = args[1];
const opt = {};
args.slice(2).forEach(a => {
    const m = a.match(/^--([^=]+)(?:=(.*))?$/);
    if (m) opt[m[1]] = m[2] === undefined ? true : m[2];
});

if (!APP || !MANIFEST) {
    console.error('usage: node test/bench.js <index.html> <manifest.json> [--key=… | --base=… --model=…]');
    process.exit(2);
}
if (!opt.key && !opt.base) {
    console.error('Il faut --key=<cle Mistral> ou --base=<endpoint compatible OpenAI>.');
    console.error('Sans acces a un modele, aucune mesure n\'est possible : ce banc ne simule rien.');
    process.exit(2);
}

const cases = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'))
    .slice(0, opt.limit ? parseInt(opt.limit, 10) : undefined);
const root = path.dirname(path.resolve(MANIFEST));

// Severites qui comptent comme « anomalie rapportee ».
// norm = examine et normal ; nonev = non evaluable, donc ni l'un ni l'autre.
const POSITIVE = { crit: 1, high: 1, mod: 1, low: 1 };

function newApp() {
    const vc = new VirtualConsole();
    const dom = new JSDOM(fs.readFileSync(APP, 'utf8'), {
        runScripts: 'dangerously', pretendToBeVisual: true,
        url: 'https://nikoju1977.github.io/medicalvisionproai/',
        virtualConsole: vc, resources: 'usable'
    });
    return dom.window;
}

const wait = ms => new Promise(r => setTimeout(r, ms));

async function runCase(c) {
    const w = newApp();
    await wait(1800);

    if (opt.base) {
        w.document.getElementById('providerSel').value = 'medgemma';
        w.providerChanged();
        w.document.getElementById('customBaseIn').value = opt.base;
        if (opt.model) w.document.getElementById('customModelIn').value = opt.model;
    } else {
        w.document.getElementById('akIn').value = opt.key;
    }
    if (opt.single) w.document.getElementById('singleRead').checked = true;
    if (opt.nozoom) { w.document.getElementById('zoomOff').checked = true; w.setZoom(); }
    w.saveKey();

    // Chargement par le vrai champ fichier, donc vrai pre-traitement.
    const img = await loadImage(path.resolve(root, c.file));
    const cv = createCanvas(img.width, img.height);
    cv.getContext('2d').drawImage(img, 0, 0);
    const buf = Buffer.from(cv.toDataURL('image/png').split(',')[1], 'base64');
    const inp = w.document.getElementById('fIn');
    Object.defineProperty(inp, 'files', {
        value: [new w.File([new Uint8Array(buf)], path.basename(c.file), { type: 'image/png' })],
        configurable: true
    });
    inp.dispatchEvent(new w.Event('change'));
    await wait(2500);

    const t0 = Date.now();
    w.runAI();
    for (let i = 0; i < 3000 && w.__busy !== false; i++) {
        await wait(200);
        const h = w.document.getElementById('aiO').innerHTML;
        if (/Analyse interrompue|Image non analysable/.test(h)) break;
        if (/class="sev |CONCLUSION|Conclusion/.test(h) && !/Analyse .{0,12}en cours/.test(h)) break;
    }
    const dur = Date.now() - t0;
    const html = w.document.getElementById('aiO').innerHTML;

    if (/Analyse interrompue/.test(html)) {
        return { ...c, statut: 'echec', detail: (html.match(/<p>([^<]{0,120})/) || [, ''])[1], ms: dur };
    }
    if (/Image non analysable/.test(html)) {
        return { ...c, statut: 'non_analysable', detail: '', ms: dur };
    }

    // On lit le rapport structure plutot que le HTML quand il est accessible.
    let findings = [];
    try {
        const r = w.eval('S.lastReport');
        if (r && Array.isArray(r.findings)) findings = r.findings;
    } catch (e) { /* IIFE : repli sur le DOM */ }

    let pos, nonev;
    if (findings.length) {
        pos = findings.filter(f => POSITIVE[f.severite]).length;
        nonev = findings.filter(f => f.severite === 'nonev').length;
    } else {
        const badges = html.match(/class="sev sev-([a-z]+)"/g) || [];
        pos = badges.filter(b => /sev-(crit|high|mod|low)"/.test(b)).length;
        nonev = badges.filter(b => /sev-nonev"/.test(b)).length;
    }

    return {
        ...c, statut: 'ok', ms: dur,
        anomalies: pos, non_evaluables: nonev,
        predit: pos > 0 ? 'anomalie' : 'normal',
        texte: findings.map(f => f.texte).join(' | ').slice(0, 300)
    };
}

(async () => {
    const out = [];
    for (let i = 0; i < cases.length; i++) {
        const c = cases[i];
        process.stderr.write('  [' + (i + 1) + '/' + cases.length + '] ' + c.file + ' … ');
        let r;
        try { r = await runCase(c); }
        catch (e) { r = { ...c, statut: 'erreur', detail: String(e.message).slice(0, 120) }; }
        process.stderr.write(r.statut + (r.predit ? ' -> ' + r.predit : '') + '\n');
        out.push(r);
        await wait(1500);   // on ne bouscule pas le fournisseur
    }

    const ok = out.filter(r => r.statut === 'ok');
    const VP = ok.filter(r => r.label === 'anomalie' && r.predit === 'anomalie').length;
    const FN = ok.filter(r => r.label === 'anomalie' && r.predit === 'normal').length;
    const VN = ok.filter(r => r.label === 'normal' && r.predit === 'normal').length;
    const FP = ok.filter(r => r.label === 'normal' && r.predit === 'anomalie').length;
    const pct = (a, b) => b ? (100 * a / b).toFixed(1) + ' %' : 'n/a';

    console.log('');
    console.log('=== RESULTATS =========================================');
    console.log('cas soumis            : ' + cases.length);
    console.log('analyses abouties     : ' + ok.length +
                '   (echecs ' + out.filter(r => r.statut === 'echec' || r.statut === 'erreur').length +
                ', non analysables ' + out.filter(r => r.statut === 'non_analysable').length + ')');
    console.log('');
    console.log('                 predit anomalie   predit normal');
    console.log('  reel anomalie        ' + String(VP).padStart(6) + '          ' + String(FN).padStart(6));
    console.log('  reel normal          ' + String(FP).padStart(6) + '          ' + String(VN).padStart(6));
    console.log('');
    console.log('sensibilite  : ' + pct(VP, VP + FN) + '   (anomalies detectees)');
    console.log('specificite  : ' + pct(VN, VN + FP) + '   (normaux non sur-appeles)');
    console.log('faux positifs par image normale : ' +
        (VN + FP ? (ok.filter(r => r.label === 'normal').reduce((a, r) => a + (r.anomalies || 0), 0) / (VN + FP)).toFixed(2) : 'n/a'));
    console.log('duree mediane : ' +
        (ok.length ? Math.round(ok.map(r => r.ms).sort((a, b) => a - b)[Math.floor(ok.length / 2)] / 1000) + ' s' : 'n/a'));
    console.log('');
    console.log('Ces chiffres decrivent le comportement de l\'application sur CE lot,');
    console.log('avec CE modele. Ils ne constituent pas une validation clinique.');
    console.log('=======================================================');

    const csv = ['fichier;label;predit;statut;anomalies;non_evaluables;ms;texte']
        .concat(out.map(r => [r.file, r.label, r.predit || '', r.statut,
            r.anomalies == null ? '' : r.anomalies, r.non_evaluables == null ? '' : r.non_evaluables,
            r.ms || '', '"' + String(r.texte || r.detail || '').replace(/"/g, "'") + '"'].join(';')))
        .join('\n');
    const dest = opt.out || 'bench-resultats.csv';
    fs.writeFileSync(dest, csv, 'utf8');
    console.log('detail par cas : ' + dest);
    process.exit(0);
})();

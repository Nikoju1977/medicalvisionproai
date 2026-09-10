// Banc de test bout-en-bout : pilote l'application reelle dans un navigateur
// headless, avec une API Mistral simulee. Aucune cle, aucun appel reseau.
const { JSDOM, VirtualConsole } = require('jsdom');
const { createCanvas } = require('canvas');
const fs = require('fs');

const FILE = process.argv[2] || 'index.html';
const SCENARIO = process.argv[3] || 'nominal';   // nominal | rate-limit | lot-perdu | tronque

const errs = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => { const m = String(e.message || e);
    // Bruit d'environnement : le bac a sable n'a pas acces aux CDN de polices.
    if (/Could not load link|fonts\.googleapis|cdnjs/.test(m)) return;
    errs.push(m); });

const dom = new JSDOM(fs.readFileSync(FILE, 'utf8'), {
    runScripts: 'dangerously', pretendToBeVisual: true,
    url: 'https://nikoju1977.github.io/medicalvisionproai/', virtualConsole: vc, resources: 'usable'
});
const w = dom.window;

// ---------- API Mistral simulee ----------
const calls = { models: 0, triage: 0, lecture: 0, consensus: 0, refus429: 0 };

function bodyKind(body) {
    const s = JSON.stringify(body || {});
    if (/technicien en imagerie/.test(s)) return 'triage';
    if (/concertation pluridisciplinaire/.test(s)) return 'consensus';
    return 'lecture';
}
const R_TRIAGE = {
    modalite: 'Radiographie thoracique', region: 'Thorax', incidence: 'Face',
    qualite: 'bonne', artefacts: [], analysable: true
};
const R_LECTURE = {
    severite: 'mod',
    findings: [{ texte: 'Opacite alveolaire du lobe inferieur droit', severite: 'mod', confiance: 0.8, localisation: 'LID', mesure: '', image: 1 }],
    signes_negatifs: ['Pas d epanchement pleural'], differentiel: ['Pneumopathie'],
    recommandations: ['Correlation clinique'], rois: [{ image: 1, xmin: 0.3, ymin: 0.4, xmax: 0.5, ymax: 0.6 }]
};
const R_CONSENSUS = {
    synthese: 'Opacite basale droite.', severite_globale: 'mod', accord: 0.9,
    indication: 'Toux febrile', technique: 'Radiographie de face',
    resultats: 'Opacite alveolaire du lobe inferieur droit.', conclusion: 'Aspect evocateur de pneumopathie du LID.',
    diagnostic_principal: { libelle: 'Pneumopathie du LID', probabilite: 'probable', arguments_pour: ['Opacite'], arguments_contre: [] },
    elements_discriminants: ['Biologie'], drapeaux_rouges: [], limites: ['Cliche unique de face'],
    findings: R_LECTURE.findings, rois: R_LECTURE.rois, coherence_vues: 'Vue unique.'
};

function respond(kind) {
    if (kind === 'triage') return R_TRIAGE;
    if (kind === 'consensus') return R_CONSENSUS;
    return R_LECTURE;
}

function installMockXHR() {
    let lectureSeen = 0;
    function Mock() { this.headers = {}; }
    Mock.prototype.open = function (m, url) { this.method = m; this.url = url; };
    Mock.prototype.setRequestHeader = function (k, v) { this.headers[k] = v; };
    Mock.prototype.getResponseHeader = function (k) { return this.respHeaders ? this.respHeaders[String(k).toLowerCase()] : null; };
    Mock.prototype.send = function (payload) {
        const self = this;
        const body = payload ? JSON.parse(payload) : null;
        setTimeout(function () {
            if (/\/models$/.test(self.url)) {
                calls.models++;
                self.status = 200;
                self.responseText = JSON.stringify({ data: [
                    { id: 'mistral-medium-3-5', capabilities: { vision: true } },
                    { id: 'mistral-small-2603', capabilities: { vision: true } },
                    { id: 'mistral-large-2610', capabilities: { vision: true } },
                    { id: 'codestral-2508', capabilities: { vision: false } }
                ] });
                return self.onload();
            }
            const kind = bodyKind(body);
            calls[kind]++;

            // 429 sur le premier triage : verifie le gouverneur de debit
            if (SCENARIO === 'rate-limit' && kind === 'triage' && calls.triage === 1) {
                calls.refus429++;
                self.status = 429; self.respHeaders = { 'retry-after': '1' };
                self.responseText = JSON.stringify({ message: 'Requests rate limit exceeded' });
                return self.onload();
            }
            // Un lot en echec definitif : verifie la couverture reelle
            if (SCENARIO === 'lot-perdu' && kind === 'lecture') {
                lectureSeen++;
                // 403 : ni repris par le gouverneur ni degrade par mchat.
                // La lecture est donc definitivement perdue -- le cas qui doit
                // etre signale et qui, avant v14.4, passait pour une lecture complete.
                if (lectureSeen === 2) {
                    self.status = 403; self.respHeaders = {};
                    self.responseText = JSON.stringify({ message: 'forbidden' });
                    return self.onload();
                }
            }
            // Reponse coupee : verifie la remontee de _partiel
            if (SCENARIO === 'tronque' && kind === 'lecture') {
                self.status = 200;
                self.responseText = JSON.stringify({ choices: [{ finish_reason: 'stop',
                    message: { content: JSON.stringify(R_LECTURE).slice(0, 140) } }] });
                return self.onload();
            }
            self.status = 200;
            self.responseText = JSON.stringify({ choices: [{ finish_reason: 'stop',
                message: { content: JSON.stringify(respond(kind)) } }] });
            self.onload();
        }, 5);
    };
    w.XMLHttpRequest = Mock;
}

// ---------- Image de test ----------
function testImage() {
    const c = createCanvas(600, 600);
    const x = c.getContext('2d');
    x.fillStyle = '#111'; x.fillRect(0, 0, 600, 600);
    x.fillStyle = '#bbb'; x.beginPath(); x.arc(300, 300, 180, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#666'; x.fillRect(340, 360, 90, 90);
    return c.toDataURL('image/png');
}

function dataUrlToFile(u, name) {
    const b64 = u.split(',')[1];
    const buf = Buffer.from(b64, 'base64');
    return new w.File([new Uint8Array(buf)], name, { type: 'image/png' });
}

const t = (ms) => new Promise(r => setTimeout(r, ms));

(async function () {
    await t(1200);
    installMockXHR();

    const $ = id => w.document.getElementById(id);
    const out = [];
    const check = (label, cond, detail) => {
        out.push((cond ? '  OK    ' : '  ECHEC ') + label + (detail ? '   ' + detail : ''));
        if (!cond) process.exitCode = 1;
    };

    // 1 — cle API par le chemin de l'interface
    $('akIn').value = 'test-key-000';
    w.saveKey();
    await t(100);

    // 2 — chargement d'image par le vrai champ fichier
    const inp = $('fIn');
    const f = dataUrlToFile(testImage(), 'thorax.png');
    Object.defineProperty(inp, 'files', { value: [f], configurable: true });
    inp.dispatchEvent(new w.Event('change'));
    await t(1500);

    const cnt = ($('serCount') || {}).textContent || '';
    check('image chargee dans la serie', /\d/.test(cnt), cnt || 'bandeau vide');

    // 3 — analyse complete
    const t0 = Date.now();
    w.runAI();
    for (let i = 0; i < 200 && !/Compte rendu|Synth|severite|Analyse interrompue|Resume|Résumé/i.test($('aiO').innerHTML); i++) await t(100);
    const dur = Date.now() - t0;
    const html = $('aiO').innerHTML;

    out.push('--- scenario : ' + SCENARIO + '  (' + dur + ' ms)');
    check('erreurs JS bloquantes', errs.length === 0, errs.length ? errs[0].slice(0, 120) : 'aucune');
    check('/v1/models interroge', calls.models >= 1, calls.models + ' appel(s)');
    check('triage effectue', calls.triage >= 1, calls.triage + ' appel(s)');
    check('lecture experte effectuee', calls.lecture >= 1, calls.lecture + ' appel(s)');
    check('compte rendu rendu a l ecran', !/Analyse interrompue/.test(html) && html.length > 400, html.length + ' caracteres');
    check('conclusion presente', /pneumopathie/i.test(html), '');

    if (SCENARIO === 'rate-limit') {
        check('429 emis par le simulateur', calls.refus429 === 1, '');
        check('reprise apres 429 (gouverneur)', calls.triage >= 2, calls.triage + ' tentatives de triage');
        check('analyse aboutie malgre le 429', !/Analyse interrompue/.test(html), '');
    }
    if (SCENARIO === 'lot-perdu') {
        check('perte signalee a l utilisateur',
            /en .{0,3}chec|partielle|incompl/i.test(html),
            (html.match(/[^<>]*en .{0,3}chec[^<>]*/i) || ['aucun avertissement'])[0].trim().slice(0, 70));
    }
    if (SCENARIO === 'tronque') {
        check('troncature signalee a l utilisateur',
            /tronqu|incomplet|interrompue/i.test(html), 'avertissement present dans le rendu');
    }

    console.log(out.join('\n'));
    process.exit(process.exitCode || 0);
})();

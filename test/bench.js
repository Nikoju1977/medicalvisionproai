// Banc de mesure A/B — MedVision AI Pro
//
// Compare le MEME pipeline et le MEME fournisseur avec/sans Medical Skills Engine.
// Il mesure sensibilite, specificite, faux positifs, latence, volume de requete et,
// quand l'API le fournit, tokens prompt/completion/total.
//
//   npm run build
//   MISTRAL_API_KEY=... node test/bench.js dist/index.html cases/manifest.json --ab
//   node test/bench.js dist/index.html cases/manifest.json --ab --base=http://localhost:11434/v1 --model=medgemma:4b
//
// Options : --ab --baseline --single --nozoom --limit=N --out=resultats.csv
//           --summary=resultats.json --sleep=1500
//
// Prerequis experimentaux : npm install --no-save jsdom canvas
// Les images sont envoyees au fournisseur configure : utiliser uniquement des donnees autorisees.

const { JSDOM, VirtualConsole } = require('jsdom');
const { createCanvas, loadImage } = require('canvas');
const fs = require('fs');
const path = require('path');
const { lexicalScore, summarize, compareAB } = require('./bench-metrics.cjs');

const args = process.argv.slice(2);
const APP = args[0];
const MANIFEST = args[1];
const opt = {};
args.slice(2).forEach(a => {
    const m = a.match(/^--([^=]+)(?:=(.*))?$/);
    if (m) opt[m[1]] = m[2] === undefined ? true : m[2];
});

if (!APP || !MANIFEST) {
    console.error('usage: node test/bench.js <index.html> <manifest.json> [--ab] [--key=… | --base=… --model=…]');
    process.exit(2);
}

const apiKey = opt.key || process.env.MISTRAL_API_KEY || '';
if (!apiKey && !opt.base) {
    console.error('Il faut MISTRAL_API_KEY, --key=<cle Mistral>, ou --base=<endpoint OpenAI-compatible>.');
    console.error('Sans acces a un vrai modele, ce banc ne produit aucune mesure de performance.');
    process.exit(2);
}

const appSource = fs.readFileSync(APP, 'utf8');
if (opt.ab && !appSource.includes('MEDICAL_SKILLS_ENGINE_V1')) {
    console.error('Le mode --ab exige un artefact construit contenant MEDICAL_SKILLS_ENGINE_V1.');
    console.error('Lancez d’abord: npm run build, puis utilisez dist/index.html.');
    process.exit(2);
}

const manifestData = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
if (!Array.isArray(manifestData)) {
    console.error('Le manifeste doit etre un tableau JSON.');
    process.exit(2);
}

const cases = manifestData
    .slice(0, opt.limit ? parseInt(opt.limit, 10) : undefined)
    .map((c, i) => ({ case_id: c.case_id || c.id || String(i + 1), ...c }));
const root = path.dirname(path.resolve(MANIFEST));
const sleepMs = opt.sleep ? Math.max(0, parseInt(opt.sleep, 10) || 0) : 1500;

// Severites qui comptent comme « anomalie rapportee ».
// norm = examine et normal ; nonev = non evaluable, donc ni l'un ni l'autre.
const POSITIVE = { crit: 1, high: 1, mod: 1, low: 1 };

function newApp(skillsEnabled) {
    const vc = new VirtualConsole();
    const dom = new JSDOM(appSource, {
        runScripts: 'dangerously',
        pretendToBeVisual: true,
        url: 'https://nikoju1977.github.io/medicalvisionproai/',
        virtualConsole: vc,
        resources: 'usable',
        beforeParse(w) {
            w.__MEDVISION_BENCH_MODE = true;
            w.__MEDVISION_BENCH_DISABLE_SKILLS = !skillsEnabled;
        }
    });
    return dom.window;
}

const wait = ms => new Promise(r => setTimeout(r, ms));

function conditionLabel(skillsEnabled) {
    return skillsEnabled ? 'skills' : 'baseline';
}

function normalizeUsage(raw) {
    const u = raw && typeof raw === 'object' ? raw : {};
    const n = k => Number.isFinite(Number(u[k])) ? Number(u[k]) : 0;
    return {
        requests: n('requests'),
        request_chars: n('request_chars'),
        responses_with_usage: n('responses_with_usage'),
        prompt_tokens: n('prompt_tokens'),
        completion_tokens: n('completion_tokens'),
        total_tokens: n('total_tokens')
    };
}

function modelSignature(trace, fallback) {
    const ids = [];
    if (trace && typeof trace === 'object') {
        Object.values(trace).forEach(id => { if (id && !ids.includes(String(id))) ids.push(String(id)); });
    }
    if (!ids.length && fallback) ids.push(String(fallback));
    return ids.sort().join('|');
}

async function runCase(c, skillsEnabled) {
    const condition = conditionLabel(skillsEnabled);
    const w = newApp(skillsEnabled);
    const started = Date.now();
    try {
        await wait(1800);

        if (opt.base) {
            w.document.getElementById('providerSel').value = 'medgemma';
            w.providerChanged();
            w.document.getElementById('customBaseIn').value = opt.base;
            if (opt.model) w.document.getElementById('customModelIn').value = opt.model;
        } else {
            w.document.getElementById('akIn').value = apiKey;
        }
        if (opt.single) w.document.getElementById('singleRead').checked = true;
        if (opt.nozoom) { w.document.getElementById('zoomOff').checked = true; w.setZoom(); }
        w.saveKey();

        // Remise a zero juste avant le cas. L'instrumentation est inactive hors benchmark.
        try {
            w.eval("S.benchUsage = { requests: 0, request_chars: 0, responses_with_usage: 0, prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }");
        } catch (e) {}

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
        for (let i = 0; i < 3000; i++) {
            await wait(200);
            const h = w.document.getElementById('aiO').innerHTML;
            if (/Analyse interrompue|Image non analysable/.test(h)) break;
            if (/class="sev |CONCLUSION|Conclusion/.test(h) && !/Analyse .{0,12}en cours/.test(h)) break;
        }
        const dur = Date.now() - t0;
        const html = w.document.getElementById('aiO').innerHTML;

        let usage = {}, trace = {}, fallbackModel = '';
        try {
            usage = normalizeUsage(w.eval('S.benchUsage || {}'));
            trace = w.eval('S.agentModelTrace || {}');
            fallbackModel = w.eval('S.mdlVision || S.mdlFast || ""');
        } catch (e) {}

        const common = {
            ...c,
            condition,
            skills_enabled: skillsEnabled,
            ms: dur,
            usage,
            model_signature: modelSignature(trace, fallbackModel)
        };

        if (/Analyse interrompue/.test(html)) {
            return { ...common, statut: 'echec', detail: (html.match(/<p>([^<]{0,160})/) || [, ''])[1] };
        }
        if (/Image non analysable/.test(html)) {
            return { ...common, statut: 'non_analysable', detail: '' };
        }

        // Rapport structure en priorite, DOM en repli.
        let report = null, findings = [];
        try {
            report = w.eval('S.lastReport');
            if (report && Array.isArray(report.findings)) findings = report.findings;
        } catch (e) {}

        let pos, nonev;
        if (findings.length) {
            pos = findings.filter(f => POSITIVE[f.severite]).length;
            nonev = findings.filter(f => f.severite === 'nonev').length;
        } else {
            const badges = html.match(/class="sev sev-([a-z]+)"/g) || [];
            pos = badges.filter(b => /sev-(crit|high|mod|low)"/.test(b)).length;
            nonev = badges.filter(b => /sev-nonev"/.test(b)).length;
        }

        const plain = findings.length
            ? JSON.stringify(findings)
            : html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
        const lex = lexicalScore(plain, c);

        return {
            ...common,
            statut: 'ok',
            anomalies: pos,
            non_evaluables: nonev,
            predit: pos > 0 ? 'anomalie' : 'normal',
            texte: plain.slice(0, 1200),
            ...lex
        };
    } catch (e) {
        return {
            ...c,
            condition,
            skills_enabled: skillsEnabled,
            statut: 'erreur',
            detail: String(e && e.message || e).slice(0, 240),
            ms: Date.now() - started,
            usage: {}
        };
    } finally {
        try { w.close(); } catch (e) {}
    }
}

function pct(value) {
    return Number.isFinite(value) ? (100 * value).toFixed(1) + ' %' : 'n/a';
}

function ci(ci95) {
    return ci95 ? ' [' + pct(ci95.low) + ' ; ' + pct(ci95.high) + ']' : '';
}

function num(value, digits = 2) {
    return Number.isFinite(value) ? value.toFixed(digits) : 'n/a';
}

function printSummary(title, s) {
    console.log('');
    console.log('=== ' + title + ' ========================================');
    console.log('cas soumis          : ' + s.submitted);
    console.log('analyses abouties   : ' + s.completed + '  (echecs ' + s.failed + ', non analysables ' + s.non_analyzable + ')');
    console.log('sensibilite         : ' + pct(s.sensitivity) + ci(s.sensitivity_ci95));
    console.log('specificite         : ' + pct(s.specificity) + ci(s.specificity_ci95));
    console.log('exactitude binaire  : ' + pct(s.accuracy) + ci(s.accuracy_ci95));
    console.log('FP findings / normal: ' + num(s.false_positive_findings_per_normal));
    console.log('latence mediane     : ' + (Number.isFinite(s.median_ms) ? Math.round(s.median_ms) + ' ms' : 'n/a'));
    console.log('requetes moyennes   : ' + num(s.mean_requests));
    console.log('taille requete moy. : ' + (Number.isFinite(s.mean_request_chars) ? Math.round(s.mean_request_chars) + ' caracteres' : 'n/a'));
    if (s.token_usage_available_cases) {
        console.log('tokens totaux moyens: ' + num(s.mean_total_tokens, 0) + '  (usage API dispo sur ' + s.token_usage_available_cases + ' cas)');
    } else {
        console.log('tokens totaux moyens: n/a (fournisseur sans champ usage exploitable)');
    }
    if (Number.isFinite(s.mean_required_coverage)) {
        console.log('couverture annotations lexicales: ' + pct(s.mean_required_coverage));
    }
    console.log('mentions interdites moyennes    : ' + num(s.mean_forbidden_hits));
}

function csvCell(value) {
    if (value == null) return '';
    const s = typeof value === 'object' ? JSON.stringify(value) : String(value);
    return '"' + s.replace(/"/g, '""') + '"';
}

function writeOutputs(out) {
    const headers = [
        'case_id', 'file', 'condition', 'label', 'predit', 'statut', 'anomalies', 'non_evaluables',
        'ms', 'model_signature', 'requests', 'request_chars', 'prompt_tokens', 'completion_tokens',
        'total_tokens', 'required_coverage', 'forbidden_hits', 'attendu', 'texte', 'detail'
    ];
    const csv = [headers.join(';')].concat(out.map(r => headers.map(h => {
        if (h === 'requests' || h === 'request_chars' || h === 'prompt_tokens' || h === 'completion_tokens' || h === 'total_tokens') {
            return csvCell((r.usage || {})[h]);
        }
        return csvCell(r[h]);
    }).join(';'))).join('\n');

    const dest = opt.out || (opt.ab ? 'bench-ab-resultats.csv' : 'bench-resultats.csv');
    fs.writeFileSync(dest, csv, 'utf8');
    return dest;
}

(async () => {
    const out = [];
    for (let i = 0; i < cases.length; i++) {
        const c = cases[i];
        let conditions;
        if (opt.ab) {
            // Ordre alterne pour limiter un biais temporel systematique fournisseur/cache.
            conditions = i % 2 === 0 ? [false, true] : [true, false];
        } else {
            conditions = [!opt.baseline];
        }

        for (const skillsEnabled of conditions) {
            const condition = conditionLabel(skillsEnabled);
            process.stderr.write(
                '  [' + (i + 1) + '/' + cases.length + '] ' + c.file + ' [' + condition + '] … '
            );
            const r = await runCase(c, skillsEnabled);
            process.stderr.write(r.statut + (r.predit ? ' -> ' + r.predit : '') + '\n');
            out.push(r);
            if (sleepMs) await wait(sleepMs);
        }
    }

    if (opt.ab) {
        const comparison = compareAB(out, { requireSameModel: opt['allow-model-mismatch'] ? false : true });
        printSummary('BASELINE SANS SKILLS', comparison.baseline);
        printSummary('AVEC MEDICAL SKILLS', comparison.skills);

        console.log('');
        console.log('=== COMPARAISON APPARIEE ===============================');
        console.log('paires eligibles                    : ' + comparison.paired.eligible_pairs);
        console.log('paires exclues (modeles differents) : ' + comparison.paired.excluded_model_mismatch);
        console.log('skills corrigent une erreur baseline: ' + comparison.paired.skills_correct_baseline_wrong);
        console.log('baseline correcte / skills en erreur: ' + comparison.paired.baseline_correct_skills_wrong);
        console.log('McNemar exact p                     : ' + num(comparison.paired.mcnemar_exact_p, 4));
        console.log('delta sensibilite                   : ' + pct(comparison.deltas.sensitivity));
        console.log('delta specificite                   : ' + pct(comparison.deltas.specificity));
        console.log('delta exactitude                    : ' + pct(comparison.deltas.accuracy));
        console.log('ratio latence mediane skills/base   : ' + num(comparison.deltas.median_latency_ratio, 3));
        console.log('ratio taille requete skills/base    : ' + num(comparison.deltas.request_char_ratio, 3));
        console.log('ratio tokens skills/base            : ' + num(comparison.deltas.total_token_ratio, 3));

        const summaryPath = opt.summary || 'bench-ab-summary.json';
        fs.writeFileSync(summaryPath, JSON.stringify({
            generated_at: new Date().toISOString(),
            app: path.resolve(APP),
            manifest: path.resolve(MANIFEST),
            cases: cases.length,
            options: {
                single: !!opt.single,
                nozoom: !!opt.nozoom,
                provider: opt.base ? 'openai-compatible' : 'mistral',
                model: opt.model || null,
                require_same_model: !opt['allow-model-mismatch']
            },
            comparison
        }, null, 2) + '\n', 'utf8');
        console.log('resume JSON                         : ' + summaryPath);
    } else {
        printSummary(opt.baseline ? 'BASELINE SANS SKILLS' : 'MEDICAL SKILLS', summarize(out));
    }

    const dest = writeOutputs(out);
    console.log('detail par cas                      : ' + dest);
    console.log('');
    console.log('Ces mesures decrivent CE lot, CE fournisseur, CE modele et CETTE configuration.');
    console.log('Elles servent a comparer des versions et a detecter des regressions.');
    console.log('Elles ne constituent pas une validation clinique ni une autorisation diagnostique.');
    process.exit(0);
})();

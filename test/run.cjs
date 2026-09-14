const fs = require('node:fs');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');
const assert = require('node:assert/strict');
const html = fs.readFileSync('index.html', 'utf8');
for (const block of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(block[1]);
new vm.Script(fs.readFileSync('sw.js', 'utf8'));
const version = html.match(/APP_VERSION = 'v([\d.]+)'/)[1];
assert.equal(JSON.parse(fs.readFileSync('manifest.json')).version, version);
assert.equal(JSON.parse(fs.readFileSync('package.json')).version, version);
assert.equal(fs.readFileSync('sw.js', 'utf8').match(/BUILD = 'v([\d.]+)'/)[1], version);
console.log('Syntax and application/cache versions OK: ' + version);
let failures = 0;
for (const scenario of ['nominal', 'rate-limit', 'lot-perdu', 'tronque', 'quota']) {
    const result = spawnSync(process.execPath, ['test/e2e.js', 'index.html', scenario], { stdio: 'inherit', timeout: 120000 });
    if (result.status !== 0) failures++;
}
const regressions = spawnSync(process.execPath, ['--test', 'test/regressions.cjs', 'test/service-worker.cjs'], { stdio: 'inherit', timeout: 60000 });
if (regressions.status !== 0) failures++;
process.exitCode = failures ? 1 : 0;

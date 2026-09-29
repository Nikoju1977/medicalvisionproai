from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DIST = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'dist'
if not DIST.is_absolute():
    DIST = ROOT / DIST

errors = []

def read(path):
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        errors.append('missing file: ' + str(path.relative_to(DIST) if path.is_relative_to(DIST) else path))
        return ''

package = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
lock = json.loads((ROOT / 'package-lock.json').read_text(encoding='utf-8'))
release_version = package['version']

if lock.get('version') != release_version:
    errors.append(f'package-lock version {lock.get("version")} != package version {release_version}')
if (lock.get('packages') or {}).get('', {}).get('version') != release_version:
    errors.append('package-lock root package version is not aligned')

required_files = [
    'index.html',
    'manifest.json',
    'sw.js',
    'web-knowledge.js',
    'web-knowledge-ui.js',
    'imaging-pro.js',
    'skills-manifest.json',
    'apple-touch-icon.png',
    'icon-192.png',
    'icon-512.png',
    'icon-maskable-192.png',
    'icon-maskable-512.png',
]
for name in required_files:
    if not (DIST / name).is_file():
        errors.append('missing runtime asset: ' + name)

for forbidden in ['tools', 'test', '.github', 'corrections.patch', 'package-lock.json']:
    if (DIST / forbidden).exists():
        errors.append('development artifact leaked into dist: ' + forbidden)

index = read(DIST / 'index.html')
manifest_text = read(DIST / 'manifest.json')
sw = read(DIST / 'sw.js')
skills_text = read(DIST / 'skills-manifest.json')

m = re.search(r"APP_VERSION = 'v([\d.]+)'", index)
index_version = m.group(1) if m else None
m = re.search(r"BUILD = 'v([\d.]+)'", sw)
sw_version = m.group(1) if m else None

try:
    manifest_version = json.loads(manifest_text).get('version')
except json.JSONDecodeError:
    manifest_version = None
    errors.append('manifest.json is invalid JSON')

versions = {
    'package.json': release_version,
    'index.html': index_version,
    'manifest.json': manifest_version,
    'sw.js': sw_version,
}
for name, value in versions.items():
    if value != release_version:
        errors.append(f'{name} version {value!r} != release version {release_version!r}')

markers = [
    'MEDICAL_LLM_STACK_V3',
    'MEDICAL_EVIDENCE_RAG_V1',
    'MEDICAL_MULTIAGENT_REVIEW_V1',
    'MEDICAL_QUANTITATIVE_PASS_V1',
    'DICOM_CALIBRATION_V1',
    'MEDICAL_CONTROL_AGENTS_V1',
    'MEDICAL_SKILLS_ENGINE_V1',
    'src="web-knowledge.js"',
    'src="web-knowledge-ui.js"',
    'src="imaging-pro.js"',
]
for marker in markers:
    if marker not in index:
        errors.append('production index missing marker: ' + marker)

quant_start = index.find('function medicalQuantitativeSummary(lectures)')
finish_start = index.find('function finish(rep,')
if quant_start >= 0 and finish_start >= 0:
    quant_body = index[quant_start:index.find('\n}\n', quant_start) + 2]
    finish_body = index[finish_start:index.find('\n}\n', finish_start) + 2]
    if 'rep.control_agents' in quant_body or 'rep.provenance' in quant_body:
        errors.append('report metadata was injected into quantitative summary')
    for field in ['dicom_geometry:', 'control_agents: rep.control_agents', 'uncertainty_safety: rep.uncertainty_safety', 'provenance: rep.provenance']:
        if field not in finish_body:
            errors.append('production report metadata missing ' + field)

try:
    skills_manifest = json.loads(skills_text)
    if skills_manifest.get('skill_count', 0) < 15:
        errors.append('skills manifest must contain at least 15 validated skills')
    for skill in skills_manifest.get('skills', []):
        meta = skill.get('metadata') or {}
        if meta.get('human_review_required') is not True or meta.get('draft_only') is not True:
            errors.append('unsafe skill metadata: ' + str(skill.get('name')))
except json.JSONDecodeError:
    errors.append('skills-manifest.json is invalid JSON')

for pdf_marker in [
    'function ensurePdfLibrary()',
    'Sécurité du pipeline',
    'Double lecture / critique',
    'Passage quantitatif',
    'Provenance des preuves récentes',
    'M0.medical_skills',
    'M0.uncertainty_safety',
    'M0.audit_multiagent',
    'M0.quantitative_measurements',
    'M0.provenance',
]:
    if pdf_marker not in index:
        errors.append('PDF export missing medical audit marker: ' + pdf_marker)

for asset in ['./web-knowledge.js', './web-knowledge-ui.js', './imaging-pro.js', './skills-manifest.json']:
    if asset not in sw:
        errors.append('service worker does not precache ' + asset)

if errors:
    print('Distribution validation FAILED:')
    for error in errors:
        print(' - ' + error)
    raise SystemExit(1)

print(f'Distribution validation OK: MedVision v{release_version}, coherent PWA metadata and runtime-only artifact.')

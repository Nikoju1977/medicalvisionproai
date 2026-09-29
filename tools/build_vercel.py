from pathlib import Path
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
SOURCE_INDEX = ROOT / 'index.html'

INJECTORS = [
    'inject_medical_llm_stack.py',
    'inject_medical_evidence.py',
    'inject_multiagent_review.py',
    'inject_quantitative_pass.py',
    'inject_dicom_calibration.py',
    'inject_control_agents.py',
    'inject_medical_skills.py',
    'inject_web_knowledge_loader.py',
]

RUNTIME_FILES = [
    '.nojekyll',
    'index.html',
    'manifest.json',
    'sw.js',
    'web-knowledge.js',
    'web-knowledge-ui.js',
    'imaging-pro.js',
    'apple-touch-icon.png',
    'banner.svg',
    'icon.svg',
    'icon-192.png',
    'icon-512.png',
    'icon-maskable-192.png',
    'icon-maskable-512.png',
]

REQUIRED_MARKERS = [
    'MEDICAL_LLM_STACK_V3',
    'MEDICAL_EVIDENCE_RAG_V1',
    'MEDICAL_MULTIAGENT_REVIEW_V1',
    'MEDICAL_QUANTITATIVE_PASS_V1',
    'DICOM_CALIBRATION_V1',
    'MEDICAL_CONTROL_AGENTS_V1',
    'MEDICAL_SKILLS_ENGINE_V1',
    "medicalModelFor(expertKey, 'vision')",
    "medicalModelFor('consensus', 'consensus')",
    'medicalEvidenceForLectures(lectures, tri)',
    'medicalEvidencePrompt(l.evidence)',
    'const secondModel = medicalIndependentModelFor',
    'medicalCriticForLectures(enriched, tri)',
    'medicalQuantitativeForLectures(enriched, tri)',
    'medicalControlAgentsForLectures(enriched, tri)',
    'medicalControlQualityAgent',
    'medicalEvidenceGraderForLectures',
    'medicalUncertaintySafetyAgent',
    'medicalProvenanceAgent',
    'dicomImportCalibrationFiles',
    'dicomPhysicalGeometry',
    'dicomSeriesGeometrySummary',
    'LECTURE B INDÉPENDANTE',
    'CRITIQUE CONTRADICTOIRE',
    'dedicated_model_not_available',
    'modeles_agents',
    'preuves_recentes',
    'audit_multiagent',
    'quantitative_measurements',
    'dicom_geometry',
    'control_agents: rep.control_agents ||',
    'uncertainty_safety: rep.uncertainty_safety ||',
    'provenance: rep.provenance ||',
    'src="web-knowledge.js"',
    'src="web-knowledge-ui.js"',
    'src="imaging-pro.js"',
]

def run_tool(name):
    subprocess.check_call([sys.executable, str(ROOT / 'tools' / name)], cwd=ROOT)

release_version = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['version']
source_bytes = SOURCE_INDEX.read_bytes()
generated_index = None

try:
    # The historical injectors operate on index.html in place. Keep that implementation
    # isolated from the source tree by always restoring the exact original bytes.
    for injector in INJECTORS:
        run_tool(injector)

    subprocess.check_call(
        [sys.executable, str(ROOT / 'tools' / 'validate_medical_stack.py'), 'index.html'],
        cwd=ROOT,
    )
    generated_index = SOURCE_INDEX.read_text(encoding='utf-8')
finally:
    SOURCE_INDEX.write_bytes(source_bytes)

if generated_index is None:
    raise SystemExit('Production build failed before a generated index was captured.')

expected_version = f"APP_VERSION = 'v{release_version}'"
required = REQUIRED_MARKERS + [expected_version]
missing = [item for item in required if item not in generated_index]
if missing:
    raise SystemExit('Production build incomplete: ' + ', '.join(missing))

if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir(parents=True)

subprocess.check_call(
    [sys.executable, str(ROOT / 'tools' / 'medical_skills.py'), '--output', str(DIST / 'skills-manifest.json')],
    cwd=ROOT,
)

for name in RUNTIME_FILES:
    src = ROOT / name
    if not src.is_file():
        raise SystemExit('Production build incomplete: missing runtime asset ' + name)
    shutil.copy2(src, DIST / name)

# Replace the base shell with the generated production shell after copying the allowlist.
(DIST / 'index.html').write_text(generated_index, encoding='utf-8')

subprocess.check_call(
    [sys.executable, str(ROOT / 'tools' / 'validate_distribution.py'), str(DIST)],
    cwd=ROOT,
)

print(
    f'MedVision production dist v{release_version} built reproducibly '
    'with medical multi-agent stack, Medical Skills Engine, DICOM calibration, Imaging Pro MPR, control agents and web knowledge.'
)

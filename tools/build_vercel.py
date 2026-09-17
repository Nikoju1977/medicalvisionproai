from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

# Build-time injection keeps index.html reviewable in source while ensuring the deployed
# preview runs the medical router, dated evidence, multi-agent safety review,
# quantitative post-detection pass, verified DICOM physical calibration,
# deterministic control agents and a separate curated web-reference explorer.
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_medical_llm_stack.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_medical_evidence.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_multiagent_review.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_quantitative_pass.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_dicom_calibration.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_control_agents.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_web_knowledge_loader.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'validate_medical_stack.py'), 'index.html'], cwd=ROOT)

if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir(parents=True)

EXCLUDE = {'.git', '.github', 'dist', 'tools', 'test', 'node_modules', '__pycache__'}
for src in ROOT.iterdir():
    if src.name in EXCLUDE:
        continue
    dst = DIST / src.name
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

index = (DIST / 'index.html').read_text(encoding='utf-8')
required = [
    'MEDICAL_LLM_STACK_V3',
    'MEDICAL_EVIDENCE_RAG_V1',
    'MEDICAL_MULTIAGENT_REVIEW_V1',
    'MEDICAL_QUANTITATIVE_PASS_V1',
    'DICOM_CALIBRATION_V1',
    'MEDICAL_CONTROL_AGENTS_V1',
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
    "APP_VERSION = 'v16.7.0'"
]
missing = [item for item in required if item not in index]
if missing:
    raise SystemExit('Vercel build incomplete: ' + ', '.join(missing))

for asset in ['web-knowledge.js', 'web-knowledge-ui.js']:
    if not (DIST / asset).is_file():
        raise SystemExit('Vercel build incomplete: missing ' + asset)

print('Vercel dist built with Medical LLM Stack V3 + Evidence RAG V1 + Multi-Agent Review V1 + Quantitative Pass V1 + DICOM Calibration V1 + Medical Control Agents V1 + curated web knowledge explorer')

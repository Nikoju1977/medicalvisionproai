from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

# Build-time injection keeps index.html reviewable in source while ensuring the deployed
# preview runs the medical router, dated evidence, multi-agent safety review and
# calibration-safe quantitative post-detection pass.
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_medical_llm_stack.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_medical_evidence.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_multiagent_review.py')], cwd=ROOT)
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_quantitative_pass.py')], cwd=ROOT)

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
    "medicalModelFor(expertKey, 'vision')",
    "medicalModelFor('consensus', 'consensus')",
    'medicalEvidenceForLectures(lectures, tri)',
    'medicalEvidencePrompt(l.evidence)',
    'const secondModel = medicalIndependentModelFor',
    'medicalCriticForLectures(enriched, tri)',
    'medicalQuantitativeForLectures(enriched, tri)',
    'LECTURE B INDÉPENDANTE',
    'CRITIQUE CONTRADICTOIRE',
    'dedicated_model_not_available',
    'pixel_only_no_physical_spacing',
    'modeles_agents',
    'preuves_recentes',
    'audit_multiagent',
    'quantitative_measurements',
    "APP_VERSION = 'v16.5.0'"
]
missing = [item for item in required if item not in index]
if missing:
    raise SystemExit('Vercel build incomplete: ' + ', '.join(missing))

print('Vercel dist built with Medical LLM Stack V3 + Evidence RAG V1 + Multi-Agent Review V1 + Quantitative Pass V1')

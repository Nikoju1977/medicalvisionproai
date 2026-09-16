from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

# Build-time injection keeps the source index reviewable while ensuring the deployed
# preview actually runs the medical per-agent routing stack.
subprocess.check_call([sys.executable, str(ROOT / 'tools' / 'inject_medical_llm_stack.py')], cwd=ROOT)

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
    "medicalModelFor(expertKey, 'vision')",
    "medicalModelFor('consensus', 'consensus')",
    'modeles_agents',
    "APP_VERSION = 'v16.3.0'"
]
missing = [item for item in required if item not in index]
if missing:
    raise SystemExit('Vercel build incomplete: ' + ', '.join(missing))

print('Vercel dist built with Medical LLM Stack V3')

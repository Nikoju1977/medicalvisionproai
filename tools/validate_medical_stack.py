from pathlib import Path
import re
import subprocess
import sys
import tempfile

path = Path(sys.argv[1] if len(sys.argv) > 1 else 'index.html')
s = path.read_text(encoding='utf-8')

markers = [
    'MEDICAL_LLM_STACK_V3',
    'MEDICAL_EVIDENCE_RAG_V1',
    'MEDICAL_MULTIAGENT_REVIEW_V1',
    'MEDICAL_QUANTITATIVE_PASS_V1',
]
errors = []
for marker in markers:
    n = s.count('// ' + marker)
    if n != 1:
        errors.append(f'{marker}: expected exactly one marker, found {n}')

required = [
    "APP_VERSION = 'v16.5.0'",
    "medicalModelFor(expertKey, 'vision')",
    "medicalModelFor('consensus', 'consensus')",
    'medicalEvidenceForLectures(lectures, tri)',
    'medicalCriticForLectures(enriched, tri)',
    'medicalQuantitativeForLectures(enriched, tri)',
    'medicalIndependentModelFor(expertKey, visionModel)',
    "medicalResolvePreferred([MEDICAL_MODELS.medvisionV0.id])",
    'pixel_only_no_physical_spacing',
    'physical_units_available: false',
    'audit_multiagent:',
    'quantitative_measurements:',
]
for needle in required:
    if needle not in s:
        errors.append('missing: ' + needle)

# Pipeline order: evidence -> critic -> quantitative -> final output.
chain = re.search(
    r'return medicalEvidenceForLectures\(lectures, tri\)(.*?)chunks: CH\.length',
    s, re.S
)
if not chain:
    errors.append('medical enrichment chain not found')
else:
    body = chain.group(1)
    order = [
        body.find('medicalCriticForLectures(enriched, tri)'),
        body.find('medicalQuantitativeForLectures(enriched, tri)'),
    ]
    if min(order) < 0 or order != sorted(order):
        errors.append('enrichment chain order must be evidence -> critic -> quantitative')

# Blind reader B must be built from the image/messages, not from reader A output.
if 'const secondBase = medicalIndependentPrompt(base, expertKey);' not in s:
    errors.append('blinded second-reader prompt missing')
if re.search(r'medicalIndependentPrompt\([^\n]*\br\b', s):
    errors.append('second reader appears to receive reader A result')

# Evidence query must not use free-form clinical context or patient identity.
ev = re.search(r'function medicalEvidenceQuery\(.*?\n\}', s, re.S)
if not ev:
    errors.append('medicalEvidenceQuery not found')
else:
    ev_body = ev.group(0)
    for forbidden in ['clinCtx(', 'patient.name', 'patientName', 'S.patient']:
        if forbidden in ev_body:
            errors.append('evidence query contains forbidden patient/free-text context: ' + forbidden)

# Quantitative model is dedicated-only: no general-medical fallback may be used to
# present geometry as a specialized MedVision measurement.
qm = re.search(r'function medicalQuantitativeModel\(\).*?\n\}', s, re.S)
if not qm:
    errors.append('medicalQuantitativeModel not found')
else:
    qbody = qm.group(0)
    if "medicalResolvePreferred([MEDICAL_MODELS.medvisionV0.id])" not in qbody:
        errors.append('quantitative model is not restricted to dedicated MedVision-V0')
    if "medicalModelFor(" in qbody:
        errors.append('quantitative model has an unsafe general-model fallback')

# Syntax-check the generated inline JavaScript when Node is available.
blocks = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', s)
if blocks:
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as f:
            f.write('\n'.join(blocks))
            js_path = f.name
        p = subprocess.run(['node', '--check', js_path], text=True, capture_output=True)
        if p.returncode != 0:
            errors.append('node --check failed: ' + (p.stderr or p.stdout).strip()[:1000])
    except FileNotFoundError:
        pass

if errors:
    print('Medical stack validation FAILED:')
    for e in errors:
        print(' - ' + e)
    raise SystemExit(1)

print('Medical stack validation OK: v16.5.0, double-read, evidence, critic and calibration-safe quantitative pass.')

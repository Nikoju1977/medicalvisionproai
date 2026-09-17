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
    'DICOM_CALIBRATION_V1',
    'MEDICAL_CONTROL_AGENTS_V1',
]
errors = []
for marker in markers:
    n = s.count('// ' + marker)
    if n != 1:
        errors.append(f'{marker}: expected exactly one marker, found {n}')

required = [
    "APP_VERSION = 'v16.7.0'",
    "medicalModelFor(expertKey, 'vision')",
    "medicalModelFor('consensus', 'consensus')",
    'medicalEvidenceForLectures(lectures, tri)',
    'medicalCriticForLectures(enriched, tri)',
    'medicalQuantitativeForLectures(enriched, tri)',
    'medicalControlAgentsForLectures(enriched, tri)',
    'medicalIndependentModelFor(expertKey, visionModel)',
    "medicalResolvePreferred([MEDICAL_MODELS.medvisionV0.id])",
    'medicalControlQualityAgent',
    'medicalEvidenceGraderForLectures',
    'medicalUncertaintySafetyAgent',
    'medicalProvenanceAgent',
    'pipeline_lineage_not_claim_entailment',
    'Fiabilité du pipeline et de ses contrôles, pas probabilité d’une maladie.',
    'dicomImportCalibrationFiles',
    'dicomPhysicalLength',
    'dicomPhysicalGeometry',
    'dicomSeriesGeometrySummary',
    'Pixel Spacing (0028,0030)',
    'verifiedDimensions: true',
    'bounding_box_area_mm2',
    'volume_geometry_ready',
    'audit_multiagent:',
    'quantitative_measurements:',
    'dicom_geometry:',
    'control_agents:',
    'uncertainty_safety:',
    'provenance:',
    'src="web-knowledge.js"',
    'src="web-knowledge-ui.js"',
]
for needle in required:
    if needle not in s:
        errors.append('missing: ' + needle)

# Pipeline order: evidence -> critic -> quantitative -> control agents -> final output.
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
        body.find('medicalControlAgentsForLectures(enriched, tri)'),
    ]
    if min(order) < 0 or order != sorted(order):
        errors.append('enrichment chain order must be evidence -> critic -> quantitative -> control agents')

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

# Quantitative model is dedicated-only.
qm = re.search(r'function medicalQuantitativeModel\(\).*?\n\}', s, re.S)
if not qm:
    errors.append('medicalQuantitativeModel not found')
else:
    qbody = qm.group(0)
    if "medicalResolvePreferred([MEDICAL_MODELS.medvisionV0.id])" not in qbody:
        errors.append('quantitative model is not restricted to dedicated MedVision-V0')
    if "medicalModelFor(" in qbody:
        errors.append('quantitative model has an unsafe general-model fallback')

# Control agents are deliberately deterministic: they audit existing outputs and must
# not call an LLM or create new diagnostic findings.
control = re.search(r'// MEDICAL_CONTROL_AGENTS_V1(.*?)// DICOM_CALIBRATION_V1', s, re.S)
if not control:
    errors.append('control agents block not found')
else:
    cb = control.group(1)
    for forbidden in ['mchat(', 'mcall(', 'findings.push(', 'differentiel.push(', 'diagnostic:']:
        if forbidden in cb:
            errors.append('control agents must remain non-diagnostic/deterministic: ' + forbidden)
    if "scope: 'pipeline_lineage_not_claim_entailment'" not in cb:
        errors.append('provenance scope disclaimer missing')
    if "reliability_scope: 'Fiabilité du pipeline et de ses contrôles, pas probabilité d’une maladie.'" not in cb:
        errors.append('uncertainty reliability scope disclaimer missing')

# DICOM safety: patient-plane measurements require Pixel Spacing and exact Rows/Columns match.
dicom_attach = re.search(r'function dicomAttachCalibration\(.*?\n\}', s, re.S)
if not dicom_attach:
    errors.append('dicomAttachCalibration not found')
else:
    db = dicom_attach.group(0)
    for needle in ['dimension_mismatch', 'verifiedDimensions: true', 'physicalValid']:
        if needle not in db:
            errors.append('DICOM attach safety missing: ' + needle)

parse = re.search(r'async function dicomParseCalibrationFile\(.*?\n\}', s, re.S)
if not parse:
    errors.append('dicomParseCalibrationFile not found')
else:
    pb = parse.group(0)
    if '0x0028, 0x0030' not in pb:
        errors.append('DICOM Pixel Spacing tag not parsed')
    if '0x0018, 0x1164' not in pb:
        errors.append('Imager Pixel Spacing tag not retained')

# Imager Pixel Spacing alone must never become valid patient-plane calibration.
if "physicalValid: !!(rowMm && colMm)" not in s:
    errors.append('physicalValid must depend on Pixel Spacing, not detector spacing')

# Volume geometry may be declared ready, but lesion volume must not be synthesized from bounding boxes.
if re.search(r'lesion_volume_mm3|volume_mm3\s*:', s, re.I):
    errors.append('unsafe lesion volume synthesis detected')

# Syntax-check generated inline JavaScript when Node is available.
blocks = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', s)
try:
    if blocks:
        with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as f:
            f.write('\n'.join(blocks))
            js_path = f.name
        p = subprocess.run(['node', '--check', js_path], text=True, capture_output=True)
        if p.returncode != 0:
            errors.append('node --check failed: ' + (p.stderr or p.stdout).strip()[:1000])

    # Syntax-check the external web knowledge assets too.
    for asset in ['web-knowledge.js', 'web-knowledge-ui.js']:
        asset_path = path.parent / asset
        if not asset_path.is_file():
            errors.append('missing web knowledge asset: ' + asset)
            continue
        p = subprocess.run(['node', '--check', str(asset_path)], text=True, capture_output=True)
        if p.returncode != 0:
            errors.append(asset + ' node --check failed: ' + (p.stderr or p.stdout).strip()[:1000])
except FileNotFoundError:
    pass

if errors:
    print('Medical stack validation FAILED:')
    for e in errors:
        print(' - ' + e)
    raise SystemExit(1)

print('Medical stack validation OK: v16.7.0 with DICOM safeguards, deterministic control agents and curated web-reference explorer assets.')

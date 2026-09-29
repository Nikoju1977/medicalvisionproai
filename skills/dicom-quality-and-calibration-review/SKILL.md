---
name: "dicom-quality-and-calibration-review"
description: "Cross-cutting DICOM quality and calibration check that protects downstream measurements from geometry, spacing or acquisition mismatches."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"quality","purposes":["vision"],"agents":["*"],"modalities":["*"],"regions":["*"],"tags":["dicom","calibration","pixel spacing","quality"],"priority":35,"always":true}
---

# Objective

Check whether the supplied imaging context is technically adequate for the observations and measurements being requested.

# Procedure

1. Confirm that modality, orientation and series context are coherent when metadata is available.
2. Use patient-plane physical measurements only when the pipeline reports valid calibration and matching dimensions.
3. Treat detector spacing, screenshots and rescaled exports as insufficient for patient-plane measurement unless explicitly validated.
4. Identify compression, truncation, motion, incomplete coverage or other quality limits visible in the supplied data.
5. Propagate technical limitations into every dependent conclusion.

# Output discipline

- Never convert pixels to millimetres without validated calibration.
- Never synthesize lesion volume from a 2D bounding box.
- Make measurement provenance visible in the draft.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

---
name: "pathology-slide-review"
description: "Structured digital pathology image review with specimen context, tissue architecture, cytologic observations and limitations kept distinct."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"reading","purposes":["vision"],"agents":["patho"],"modalities":["wsi","pathology","histology","microscopy","slide"],"regions":["tissue","specimen","pathology"],"tags":["histology","pathology","slide","tissue"],"priority":94}
---

# Objective

Structure observations from a pathology image or slide without replacing microscopic review across the complete specimen.

# Procedure

1. Confirm specimen/site information only when provided; otherwise keep it UNKNOWN.
2. Assess image/scan quality and whether the supplied field is representative enough for the question.
3. Describe architecture, cellularity, cytologic atypia, necrosis, inflammation and other visible features as observations.
4. Avoid extrapolating from a cropped field to the entire specimen.
5. List additional stains, levels, molecular data or clinical context needed to support a classification.

# Output discipline

- Do not issue a definitive histopathologic diagnosis from incomplete slide coverage.
- Do not invent immunohistochemistry or molecular results.
- Require pathologist validation.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

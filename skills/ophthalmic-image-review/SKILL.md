---
name: "ophthalmic-image-review"
description: "Structured fundus/OCT image review with image quality, retinal layers, macula, optic disc and visible lesion description."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"reading","purposes":["vision"],"agents":["ophtalmo"],"modalities":["oct","fundus","retinography","retinographie","photo"],"regions":["eye","retina","macula","optic","oeil","retine"],"tags":["oct","retina","fundus","macula"],"priority":90}
---

# Objective

Review ophthalmic images using modality-specific visible structures while respecting segmentation and acquisition limits.

# Procedure

1. Assess image quality, field coverage and segmentation reliability where applicable.
2. For OCT, review retinal contour, layers, fluid spaces and vitreoretinal interface when visible.
3. For fundus images, review disc, macula, vessels and peripheral field actually captured.
4. Describe haemorrhage, exudate, drusen, pigmentary or structural abnormalities without forcing a disease label.
5. Compare with prior imaging using consistent landmarks when available.

# Output discipline

- Separate acquisition/segmentation artefact from suspected pathology.
- Do not infer visual function from image appearance alone.
- Require ophthalmic specialist validation.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

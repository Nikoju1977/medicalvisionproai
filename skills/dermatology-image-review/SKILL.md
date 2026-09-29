---
name: "dermatology-image-review"
description: "Structured dermatology or dermoscopy image description emphasizing morphology, distribution, image quality and uncertainty rather than diagnosis."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"reading","purposes":["vision"],"agents":["dermato"],"modalities":["photo","dermoscopy","dermoscopie","image"],"regions":["skin","cutaneous","peau"],"tags":["skin","lesion","dermoscopy","peau"],"priority":86}
---

# Objective

Describe visible cutaneous morphology reproducibly without using a photograph alone as a definitive diagnosis.

# Procedure

1. Assess focus, lighting, scale, colour fidelity and whether a reference ruler is present.
2. Describe lesion count, distribution, symmetry, border, colour, surface and visible secondary change.
3. For dermoscopy, report visible structures and patterns without inventing absent magnification or polarisation details.
4. Use size only when a calibrated scale exists.
5. List a limited visual differential and the clinical information required to refine it.

# Output discipline

- Do not infer palpation, symptoms or evolution unless supplied.
- Do not assign malignancy certainty from an image alone.
- Flag concerning visual features for human dermatologic review.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

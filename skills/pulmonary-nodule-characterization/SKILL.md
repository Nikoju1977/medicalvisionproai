---
name: "pulmonary-nodule-characterization"
description: "Structured CT review of a pulmonary nodule with morphology, measurements, comparison and uncertainty kept separate from clinical decision-making."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"reading","purposes":["vision"],"agents":["pulmo"],"modalities":["ct","scanner","tdm"],"regions":["thorax","chest","lung","poumon"],"tags":["nodule","pulmonary","pulmonaire"],"priority":95}
---

# Objective

Characterise a pulmonary nodule visible on CT without converting imaging features into an autonomous diagnosis or management decision.

# Procedure

1. Confirm that the target lesion is actually visible and identify series/image context when available.
2. Describe location, attenuation class, margins, morphology and associated signs using only evaluable features.
3. Use calibrated measurements already available from the pipeline; never estimate a millimetric value from appearance alone.
4. Compare with prior examinations when supplied, separating observed change from uncertainty caused by technique.
5. List plausible imaging differentials as hypotheses and state what additional evidence would discriminate them.

# Output discipline

- Separate observation, measurement, comparison, differential and limitations.
- Flag morphology or growth features that warrant explicit human review.
- Keep guideline-dependent management outside the skill unless dated evidence is provided.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

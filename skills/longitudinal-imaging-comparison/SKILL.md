---
name: "longitudinal-imaging-comparison"
description: "Longitudinal imaging comparison skill that separates true interval change from technique, plane and measurement variability."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"comparison","purposes":["vision"],"agents":["*"],"modalities":["*"],"regions":["*"],"tags":["prior","previous","comparison","evolution","follow-up","suivi","anterieur"],"priority":70,"require_tag_match":true}
---

# Objective

Compare current and prior imaging using matched features and explicit uncertainty about technical differences.

# Procedure

1. Identify which prior studies are actually available and comparable.
2. Match the same lesion or anatomical target before comparing size or appearance.
3. Prefer calibrated repeated measurements and note differences in plane, phase, sequence or reconstruction.
4. Classify change descriptively as increased, decreased, stable within measurement uncertainty, new, resolved or indeterminate.
5. Keep temporal association separate from causal interpretation.

# Output discipline

- Quote dates when available.
- Do not call progression or response when comparison quality is insufficient.
- List unmatched lesions or missing priors explicitly.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

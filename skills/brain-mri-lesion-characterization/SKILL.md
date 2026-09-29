---
name: "brain-mri-lesion-characterization"
description: "Structured MRI brain lesion characterization using supplied sequences, morphology, distribution and comparison without autonomous diagnosis."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"reading","purposes":["vision"],"agents":["neuro"],"modalities":["mri","irm","mr"],"regions":["brain","cerveau"],"tags":["lesion","mri","irm","enhancement"],"priority":91}
---

# Objective

Characterise a focal or multifocal brain MRI abnormality from the sequences actually available.

# Procedure

1. Inventory available sequences and identify missing sequences that limit interpretation.
2. Describe lesion number, location, signal pattern, diffusion behaviour and enhancement only when corresponding sequences exist.
3. Describe oedema, mass effect, haemorrhagic susceptibility or necrotic appearance when directly visible.
4. Compare with prior studies using the same feature vocabulary.
5. Build a bounded imaging differential and list discriminating missing information.

# Output discipline

- Tie every feature to an available sequence.
- Avoid histologic certainty from imaging appearance.
- Keep tumour grading or treatment implications as human-review questions unless source evidence is provided.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

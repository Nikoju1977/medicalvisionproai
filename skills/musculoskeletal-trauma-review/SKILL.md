---
name: "musculoskeletal-trauma-review"
description: "Structured musculoskeletal trauma review for radiographs or CT with alignment, fracture, joint and soft-tissue checks."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"reading","purposes":["vision"],"agents":["ortho"],"modalities":["xray","radiography","radiographie","rx","ct","scanner","tdm"],"regions":["bone","joint","musculoskeletal","os","articulation"],"tags":["trauma","fracture","luxation"],"priority":90}
---

# Objective

Review traumatic musculoskeletal imaging systematically while distinguishing visible injury from occult-injury risk.

# Procedure

1. Confirm side, region, projections or CT coverage.
2. Assess alignment and cortical continuity before focusing on any suspected fracture.
3. Describe fracture location, pattern and displacement only when visible and measurable.
4. Review adjacent joints and soft tissues for associated abnormalities.
5. Identify when image quality or missing projections limit exclusion of occult injury.

# Output discipline

- Separate fracture observations from classification labels.
- Do not generate a named classification unless all required features are evaluable.
- Flag neurovascular or treatment implications for clinician assessment, not as autonomous conclusions.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

---
name: "evidence-traceable-imaging-report"
description: "Evidence-traceable reporting skill that keeps patient observations separate from literature, guidelines and pipeline provenance."
metadata: {"version":1,"human_review_required":true,"draft_only":true,"stage":"reporting","purposes":["vision"],"agents":["*"],"modalities":["*"],"regions":["*"],"tags":["guideline","evidence","recommendation","report","compte rendu"],"priority":65,"require_tag_match":true}
---

# Objective

Prepare imaging conclusions so that observations, reasoning, external evidence and unresolved uncertainty remain auditable.

# Procedure

1. Keep patient-specific observations in a dedicated section sourced only from the examination and supplied context.
2. Attach external evidence only to the claim it supports, with date and source provenance when available.
3. Do not use literature as if it were an observation of this patient.
4. Mark recommendations as evidence-dependent and omit them when current evidence has not been verified.
5. Carry forward disagreements from reader A, reader B and critic instead of hiding them.

# Output discipline

- Separate observation, interpretation, evidence and recommendation.
- Never fabricate a citation or imply that model memory is a current guideline.
- End with explicit human-review requirements.

# Safety

- Produce a DRAFT only.
- Missing or non-evaluable information must remain UNKNOWN / non évaluable.
- Do not invent measurements, references, scores, diagnoses, indications or contraindications.
- Preserve disagreements and uncertainty instead of forcing consensus.
- Final clinical interpretation and action require qualified human review.

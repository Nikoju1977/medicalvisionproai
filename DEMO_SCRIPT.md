# MedVision AI Pro — 3-Minute Commercial Demo Script

## Objective

Demonstrate a coherent imaging workflow, not a diagnostic claim.

Use only synthetic, anonymized or otherwise authorized medical data.

## 0:00–0:20 — Positioning

Say:

> MedVision AI Pro is a browser-based medical-imaging workspace. It combines DICOM visualization, local multiplanar reconstruction, measurements, encrypted case storage and configurable vision AI without locking the product to a single AI provider.

Keep the application already open before the discussion starts.

## 0:20–1:05 — Imaging workflow

Import a prepared DICOM CT series.

Show:

- axial view;
- coronal view;
- sagittal view;
- synchronized crosshair;
- Window/Level;
- one CT preset;
- HU readout if the demo series supports it.

Key sentence:

> The imaging workflow is processed locally in the browser for the supported DICOM formats.

## 1:05–1:35 — Measurement and annotation

Create one measurement and one annotation.

Explain:

> The same workspace can keep the image series, annotations, context and report together rather than sending the user across several tools.

Avoid spending time on secondary controls.

## 1:35–2:10 — AI architecture

Open the AI configuration screen.

Show the provider/model selection without exposing a real API key.

Say:

> The AI layer is provider-agnostic. Today the application supports Mistral vision and private OpenAI-compatible endpoints, so an acquirer can connect its own validated model or internal inference service.

If an authorized demo endpoint is available, run a prepared test. Otherwise do not improvise a live medical analysis.

## 2:10–2:35 — Data control

Show local save / restore and the report workflow.

Say:

> Cases are persisted locally with AES-256-GCM encryption. Remote transmission happens only when an AI analysis is explicitly launched.

Then show PDF export if already tested on the device.

## 2:35–3:00 — Acquisition close

Finish with:

> MedVision is not being presented as a certified diagnostic device today. The opportunity is the integrated technical platform: imaging workflow, web deployment, encrypted local persistence and pluggable AI. I am looking for a strategic organization that can bring distribution, clinical validation and regulatory execution — through acquisition, licensing or co-development.

Then ask one question:

> Where would this fit best in your current imaging or AI roadmap?

## Demo preparation checklist

- Use a local or cached build already verified on the presentation device.
- Keep one synthetic DICOM series ready.
- Keep one standard image ready as fallback.
- Do not use identifiable patient data.
- Do not display API keys.
- Pre-test PDF export.
- Pre-test PWA reload and browser permissions.
- Disable unrelated notifications.
- Keep the GitHub repository and commercial one-pager open in separate tabs.
- Have a 30-second version ready if the contact is standing in a corridor.

## 30-second corridor version

> MedVision AI Pro is a browser-based imaging platform combining DICOM/MPR viewing, measurement tools, encrypted local cases and configurable medical-vision AI. The prototype is functional; I am looking for a strategic buyer or partner with distribution and regulatory capability to integrate and industrialize it.

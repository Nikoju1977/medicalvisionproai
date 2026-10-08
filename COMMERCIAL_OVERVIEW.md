# MedVision AI Pro — Commercial Overview

## Executive proposition

**MedVision AI Pro is a browser-based medical-imaging workspace combining DICOM viewing, local MPR reconstruction, measurement and annotation tools, encrypted local case storage and configurable multimodal AI.**

The product is positioned as a **technical platform and acquisition / integration opportunity**, not as a clinically certified diagnostic device.

## The problem

Medical-imaging workflows frequently require multiple products: a viewer, annotation software, reporting utilities, local storage and separate AI tools. This creates integration friction and makes it difficult to test new AI models inside a coherent imaging workflow.

## The product

MedVision brings the core elements of that workflow into one installable web application:

- supported DICOM CT/MR viewing;
- axial / coronal / sagittal MPR;
- synchronized crosshair, Window/Level, CT presets and HU reading;
- measurements, annotations and ROIs;
- encrypted local persistence;
- report export;
- Mistral vision or private OpenAI-compatible AI endpoints;
- PWA deployment and reproducible static build.

## Why it can matter to an acquirer

MedVision can shorten the path to a browser-based imaging prototype or companion product for an organization that already owns:

- PACS / RIS distribution;
- hospital software channels;
- radiology workflows;
- imaging hardware;
- tele-radiology infrastructure;
- validated medical AI models;
- regulatory and clinical capabilities.

The value is primarily in **product architecture, integrated workflow, implementation know-how and speed-to-integration**, rather than in claims of proprietary diagnostic performance.

## Potential transaction formats

- Strategic acquisition of the project and associated assets.
- Technology transfer into an existing imaging platform.
- White-label product.
- Commercial license plus implementation support.
- Co-development toward regulated use.
- Acquisition of selected private assets / future roadmap and transition support.

## Assets visible today

- Production-oriented static application.
- DICOM / MPR imaging module.
- AI routing and provider configuration.
- Local encryption and persistence workflow.
- PWA packaging and offline/update controls.
- Automated test and distribution validation.
- Deployment configuration for GitHub Pages and Vercel.
- Product documentation and security notes.

## Technical maturity

Current release: **17.1.5**.

Automated tests cover software integration, regressions, cache behavior, model routing and synthetic DICOM behavior. These tests do **not** constitute clinical validation.

## Regulatory position

MedVision is currently a **non-certified prototype**. Any deployment for diagnosis or regulated clinical decision support would require an appropriate quality, risk, clinical and regulatory program led by the acquiring or operating organization.

## Data-security position

- Local cases are encrypted with AES-256-GCM.
- Remote AI analysis is user-triggered.
- AI-provider credentials are not bundled in the repository.
- The current application does not guarantee removal of identifiers embedded in image pixels.
- Demonstrations should use synthetic or authorized anonymized data.

## Due-diligence note on licensing

The current public repository is released under the **MIT License**. A transaction seeking exclusivity should therefore be structured around the assets that can be transferred or controlled separately: brand, private assets, know-how, transition services, future development, deployment assets, commercial agreements and any other IP not already irrevocably licensed under MIT.

Legal counsel should validate the final transaction perimeter.

## Ideal strategic buyers / partners

- PACS and RIS vendors.
- Medical-imaging software companies.
- Tele-radiology operators.
- Hospital information-system vendors.
- Imaging-device manufacturers.
- Medical-AI companies seeking a viewer / workflow layer.
- Digital-health groups building multimodal clinical workspaces.

## 30-second pitch

> MedVision AI Pro is an installable browser-based medical-imaging workspace that combines DICOM visualization, local MPR, measurements, encrypted case storage and configurable vision AI in one lightweight product. It is already technically functional as a prototype and is designed to be integrated into a larger regulated imaging or hospital-software ecosystem.

## Commercial objective

Open discussions with strategic buyers or partners able to provide distribution, regulatory capability, clinical validation and integration into established healthcare workflows.

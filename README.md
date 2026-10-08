# MedVision AI Pro

**AI-assisted medical imaging workspace for the web — DICOM viewing, MPR reconstruction, measurements, encrypted local cases and provider-agnostic vision AI.**

[Live application](https://nikoju1977.github.io/medicalvisionproai/) · Version **17.1.5** · Created by **Nicolas Julienne — Studio Niko Design**

> MedVision AI Pro is a technical prototype for medical-imaging workflows. It is **not certified as a medical device** and is not intended to replace professional clinical judgement.

## Why MedVision

Medical imaging workflows are often fragmented between viewers, annotation tools, reporting utilities and external AI services. MedVision explores a lighter architecture: a browser-based workspace that keeps visualization and case storage local while allowing the user to connect the vision-AI provider of their choice.

The product is designed around three principles:

- **Fast access:** installable PWA, no heavyweight desktop client required.
- **Interoperability:** DICOM imaging tools plus standard image support and provider-agnostic AI routing.
- **Data control:** local encrypted case storage, explicit remote-analysis actions and no embedded vendor API key.

## Product capabilities

### Medical imaging
- DICOM CT/MR series import for supported uncompressed monochrome 8/16-bit transfer syntaxes.
- MPR reconstruction: axial, coronal and sagittal views.
- Synchronized crosshair, Window/Level, CT presets and axial cine.
- Hounsfield Unit reading when Rescale Slope / Intercept metadata are available.
- Zoom, calibrated measurements, annotations and regions of interest.
- Standard JPEG, PNG, WebP and BMP image viewing.

### AI-assisted analysis
- Mistral vision integration.
- Support for private OpenAI-compatible endpoints, including self-hosted model gateways.
- Provider catalogue discovery and model routing.
- Batch or series-oriented analysis workflows.
- Abort/cancellation controls for in-flight and queued requests.
- Separate non-medical standard-image analysis mode.

### Security and workflow
- AES-256-GCM encrypted local case storage in IndexedDB.
- Local persistence of image series, annotations, context and reports.
- API credentials remain on the local device in the current implementation.
- PDF report export.
- Installable PWA with controlled offline cache and update notifications.

## Architecture

MedVision is intentionally lightweight:

- **Client:** static web application / PWA.
- **Medical imaging module:** browser-side DICOM decoding and MPR reconstruction.
- **Storage:** encrypted IndexedDB.
- **AI layer:** remote provider selected by the user.
- **Deployment:** reproducible static build for GitHub Pages and Vercel.
- **Quality:** automated integration, regression, cache, production-routing and synthetic DICOM tests.

No AI provider key is shipped with the repository.

## Target strategic use cases

MedVision can serve as a foundation or demonstrator for:

- radiology and imaging software vendors;
- PACS / RIS ecosystem companies;
- tele-radiology platforms;
- hospital software providers;
- medical-device manufacturers exploring browser-based companion software;
- AI-imaging companies that need a lightweight multimodal viewing and annotation front end;
- research and proof-of-concept programs around locally controlled imaging workflows.

## What is differentiated

MedVision combines, in a single browser-based product:

1. **DICOM visualization + local MPR**
2. **provider-agnostic multimodal AI**
3. **encrypted local case persistence**
4. **PWA deployment**
5. **medical and standard-image modes kept separate**
6. **automated technical validation around imaging and routing logic**

The project deliberately avoids claiming diagnostic performance that has not been clinically validated.

## Demo path

For a concise commercial demonstration:

1. Open the application.
2. Import a synthetic or authorized DICOM CT series.
3. Show axial / coronal / sagittal reconstruction and synchronized crosshair.
4. Demonstrate Window/Level and HU reading.
5. Add an annotation or measurement.
6. Show the AI-provider configuration panel.
7. Run only an authorized demo analysis.
8. Save the case locally and export a PDF report.

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a 3-minute buyer presentation.

## Current maturity

**Technical prototype / pre-regulatory product.**

The software includes build, test and deployment tooling, but it has not undergone clinical validation or medical-device certification. Automated tests validate software behavior, not diagnostic safety or efficacy.

Known imaging limitation: compressed DICOM transfer syntaxes such as JPEG, JPEG-LS, JPEG2000, RLE and Deflated are not yet decoded locally and are explicitly rejected.

## Commercial discussion

The project may be relevant for:

- strategic acquisition;
- technology transfer;
- white-label integration;
- product / IP licensing;
- co-development;
- integration into an existing imaging, PACS, telemedicine or AI platform.

For a buyer-facing summary, see [COMMERCIAL_OVERVIEW.md](COMMERCIAL_OVERVIEW.md).

## Development

Requirements: Node.js 22+ and Python 3.

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run build
npm run validate:dist
python3 -m http.server 8080 --directory dist --bind 127.0.0.1
```

## Data and clinical safety

Image display and local case storage happen in the browser. When the user explicitly launches a remote AI analysis, the selected images and clinical context are transmitted to the configured provider.

The application does **not** guarantee de-identification of patient information embedded in image pixels. Demonstrations should use synthetic, anonymized or otherwise authorized data only.

## License

Current public source is distributed under the [MIT License](LICENSE).

© 2026 Nicolas Julienne — Studio Niko Design

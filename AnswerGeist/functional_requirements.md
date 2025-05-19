## Functional Requirements Specification

**Project Name:** Answergeist
**Stakeholders:**

* **Primary User:** A person analyzing questionnaire-type content from a separate screen (e.g., quiz solvers, test reviewers)
* **System Developer:** Responsible for implementing, configuring, and maintaining the system

**System Scope:**
Answergeist is a desktop software tool that captures screenshots of questionnaire content from a separate screen via a camera, performs OCR, analyzes the questions with AI, and visually displays results within a structured GUI.

---

## Functional Requirements (IREB-Style)

### F1 – Manual Image Capture via Trigger

* **Description:** The system shall allow the user to trigger a camera-based screenshot capture using a UI button or a designated hardware input (e.g., foot pedal).
* **Rationale:** Enables the user to initiate analysis on demand.
* **Fit Criterion:** Upon trigger, a new image is captured, processed, and visually added to the results area of the UI.

### F2 – Central Region OCR Extraction

* **Description:** The system shall isolate and extract text from the central region of the captured image using an OCR engine.
* **Rationale:** The questionnaire content is known to reside in the image’s central area.
* **Fit Criterion:** Text is successfully extracted from the middle 50–70% of the image height and width.

### F3 – AI-Based MCQ Analysis

* **Description:** The system shall send the extracted text to an AI model (remote OpenAI API or local equivalent) to evaluate all possible multiple-choice answers.
* **Rationale:** Provides intelligence to determine which answers are most likely correct.
* **Fit Criterion:** For each answer option:

  * A confidence score (e.g., 0–100%) is returned.
  * A one-sentence justification is generated.

### F4 – Configurable Processing Mode

* **Description:** The system shall offer a configuration option to choose between:

  * Remote processing via OpenAI API.
  * Local models for OCR and/or question analysis.
* **Rationale:** Supports both online (cloud-powered) and offline (privacy-sensitive or cost-optimized) use cases.
* **Fit Criterion:** User can select mode from a settings menu or config file.

### F5 – UI: Vertical Image Stack with Dynamic Cards

* **Description:** The system shall maintain a vertically scrollable list of result “cards,” each representing a single image capture session.
* **Rationale:** Provides a clear, chronological overview of previous captures and their associated results.
* **Fit Criterion:** Each card contains:

  * A scaled-down version of the captured image on the left.
  * A status indicator or result panel on the right (see F6–F7).

### F6 – UI: Real-Time Status Indicators

* **Description:** Each result card in the UI shall display a live status:

  * “Processing...” with a spinner if analysis is in progress.
  * “Error” if OCR or AI call fails.
  * “Complete” once the answer scores and explanations are available.
* **Rationale:** Keeps the user informed of the analysis progress.
* **Fit Criterion:** Status is updated dynamically per card, independent of others.

### F7 – UI: Result Display Panel

* **Description:** Upon completion of AI analysis, each result card shall display:

  * The list of answer options extracted.
  * For each option: a percentage (confidence level) and a one-sentence justification.
* **Rationale:** Allows the user to quickly assess the likelihood and reasoning of each answer.
* **Fit Criterion:** All options are shown in a visually grouped block beside the corresponding image.

### F8 – Concurrent Processing Queue

* **Description:** The system shall queue and process multiple captures asynchronously.
* **Rationale:** Allows the user to continue capturing while previous items are still processing.
* **Fit Criterion:** UI remains responsive, and result cards update independently.

### F9 – Screenshot Archive (Optional)

* **Description:** The system shall store a persistent archive of processed screenshots and results, optionally exportable.
* **Rationale:** Enables historical review or data export.
* **Fit Criterion:** Captures are saved to disk and can be reopened via the UI (optional feature toggle).

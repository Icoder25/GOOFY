# Goofy Product Backlog (Seed)

This backlog seeds the initial set of epics and user stories, organized by priority tiers (MVP → Priority 2 → Priority 3). Each story includes a short description and high-level acceptance criteria to guide implementation and testing.

## Legend

- **Priority:** P0 (critical), P1 (high), P2 (medium), P3 (future)
- **Status:** Idea → Ready → In Progress → Done

## Epic Overview

| Epic | Priority | Description |
| --- | --- | --- |
| E1 | P0 | Voice capture and transcription pipeline |
| E2 | P0 | Core command parsing and context management |
| E3 | P0 | Browser automation actions (tabs, windows, scrolling, clipboard) |
| E4 | P0 | Avatar feedback and control panel UX |
| E5 | P1 | Analytics, logging, and privacy controls |
| E6 | P1 | Advanced commands (multi-step, forms, productivity) |
| E7 | P1 | Backend AI orchestration and resilience |
| E8 | P2 | Context awareness and smart suggestions |
| E9 | P2 | Cross-device sync and preferences backup |
| E10 | P3 | Developer extensibility and custom scripting |

---

## MVP Stories (Priority 0 / 1)

### Story S1 – Push-to-Talk Voice Capture (E1, P0)
- **As a** user
- **I want** to hold a button in the extension and issue a command
- **So that** I can interact with the browser hands-free when needed
- **Acceptance Criteria:**
  1. Push-to-talk button shows listening state while pressed and closes when released.
  2. Transcription appears as interim text within 500 ms of speech start.
  3. If microphone permission is missing, user receives actionable prompt.
  4. Errors (e.g., no audio detected) surface via avatar and toast message.

### Story S2 – Regex Command Parsing for Navigation (E2, P0)
- **As a** power user
- **I want** common navigation commands to execute reliably without AI fallback
- **So that** I can move between tabs quickly
- **Acceptance Criteria:**
  1. Recognizes “open new tab”, “close this tab”, “switch to next tab”, “go back”.
  2. Parser unit tests cover at least 20 sample utterances per command.
  3. Confidence score ≥0.9 for canonical phrases; fallback invoked otherwise.
  4. Command history logs intent, parameters, and success/failure status.

### Story S3 – Scroll and Page Interaction Actions (E3, P0)
- **As a** user with limited mobility
- **I want** to scroll and jump within pages via voice
- **So that** I can consume content without touchpad or mouse
- **Acceptance Criteria:**
  1. Supports “scroll up/down”, “scroll to top/bottom”, “page down/up”.
  2. Content script executes actions within 200 ms of command receipt.
  3. Avatar confirms completion via animation + speech (“Scrolled down”).
  4. Errors (e.g., no scrollable element) reported and suggested remedy given.

### Story S4 – Clipboard Voice Operations (E3, P0)
- **As a** researcher
- **I want** to copy summaries and paste into forms by voice
- **So that** I can gather information rapidly while multitasking
- **Acceptance Criteria:**
  1. Commands: “copy selection”, “copy link”, “copy page title”, “paste here”.
  2. Requires explicit permission before first clipboard access.
  3. Clipboard history keeps last 5 items locally with timestamps.
  4. Privacy banner describes clipboard usage and opt-out.

### Story S5 – Avatar Feedback Loop (E4, P0)
- **As a** new user
- **I want** visual confirmation and personality from the assistant
- **So that** I feel confident and engaged while issuing commands
- **Acceptance Criteria:**
  1. Avatar shows distinct states: idle, listening, thinking, success, error.
  2. State transitions sync with command lifecycle and speech playback.
  3. Voice responses generated via Speech Synthesis API with adjustable persona.
  4. UX validated through usability test with ≥5 participants; feedback logged.

### Story S6 – Backend AI Fallback (E7, P1)
- **As a** casual user speaking naturally
- **I want** complex phrases to still work via AI understanding
- **So that** I do not need to memorize specific commands
- **Acceptance Criteria:**
  1. Extension sends transcripts to backend when regex parser confidence <0.5.
  2. Backend calls Gemini with sanitized context and returns structured intent.
  3. AI responses cached for 10 minutes to reduce repeated calls.
  4. Latency budget: AI fallback adds ≤1.2 seconds median to command execution.

### Story S7 – Command Telemetry & Privacy Controls (E5, P1)
- **As a** product owner
- **I want** anonymized telemetry about command success
- **So that** we can improve reliability and UX
- **Acceptance Criteria:**
  1. Firestore stores command metadata (intent, result, duration) without PII.
  2. Opt-in toggle for telemetry in settings with clear description.
  3. Users can purge their history, removing data both locally and in Firestore.
  4. Metrics dashboard displays success %, latency percentiles, error taxonomy.
- **Status:** Done (Phase 5 delivery – backend telemetry service, opt-in UI, export/purge actions, metrics endpoint).

### Story S8 – Beta Cohort Release Infrastructure (Cross-cutting, P1)
- **As a** release manager
- **I want** a gated beta channel
- **So that** we can iterate with select users before public launch
- **Acceptance Criteria:**
  1. Build pipeline produces signed beta package with watermarking.
  2. Beta users authenticated via Firebase Auth group or invite codes.
  3. Feature flags toggle experimental commands without redeploy.
  4. Feedback submission channel integrated within extension UI.

---

## Priority 2 Stories (Post-MVP Enhancements)

- **S9 – Multi-Step Command Sequencing (E6, P1):** Allow compound commands (“open Gmail and compose email”).
- **S10 – Form Field Mapping Assistant (E6, P1):** Voice-driven form filling with confirmation prompts.
- **S11 – Productivity Integrations (E6, P1):** Email, calendar, and note-taking automation.
- **S12 – Contextual Suggestions (E8, P2):** Predict next commands based on recent history and page content.
- **S13 – Page Summaries (E8, P2):** Generate concise summaries with highlight extraction.

Acceptance criteria for Priority 2 items will be elaborated when approaching implementation.

---

## Priority 3 / Future Ideas

- **S14 – Intelligent Tab Grouping (E9, P2)**
- **S15 – Cross-Device Sync & Backup (E9, P2)**
- **S16 – Custom Command Marketplace (E10, P3)**
- **S17 – Developer Scripting API (E10, P3)**

These initiatives require additional discovery and will be scheduled after public launch.

---

## Operational Tasks & Technical Debt

- Establish automation for audio-driven integration testing.
- Document ADR template and capture key architectural decisions.
- Implement usage analytics alerting (threshold breaches, anomaly detection).
- Create localization pipeline for strings and voice personas.

---

## Backlog Maintenance Process

- Weekly triage with PM, tech lead, and UX to refine upcoming stories.
- Definition of Ready includes: user value, acceptance criteria, design references, dependencies cleared.
- Definition of Done includes: code merged, tests passed, documentation updated, telemetry verified.

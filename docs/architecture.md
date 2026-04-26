# Goofy Architecture Overview

This document summarizes the planned system architecture for the Goofy voice browser assistant. It aligns with the roadmap and acts as the baseline for further design elaboration and Architecture Decision Records (ADRs).

## 1. System Context

```
+---------------------------+
|         End User          |
| (voice input & feedback)  |
+-------------+-------------+
              |
              v
+-------------+-------------+
|  Chrome Extension Client  |
|  (React, Manifest V3)     |
+-------------+-------------+
              |
              v
+-------------+-------------+        +-------------------+
|  Backend Services (API)   |<------>|  Third-Party APIs |
|  (FastAPI on Cloud Run)   |        |  (Gemini, GCP STT) |
+-------------+-------------+        +-------------------+
              |
              v
+-------------+-------------+
| Firebase (Firestore/Auth) |
+---------------------------+
```

## 2. Component Breakdown

### 2.1 Extension Shell
- **Service Worker (Background):** Manages hotword detection, always-on listening (where permitted), message routing, and alarm scheduling.
- **Popup / Control Panel (React):** Provides mic controls, history, settings, permissions, and onboarding.
- **Content Scripts:** Injected into active tabs to perform DOM-level actions (scrolling, clicking, form filling) and collect contextual metadata.
- **Avatar Renderer:** React component hosting Lottie animation states, synchronized with command lifecycle.

### 2.2 Voice Pipeline
- **Audio Capture:** Web Speech API streaming to browser; fallback audio capture for backend STT when higher accuracy needed.
- **Noise Calibration:** Adaptive filtering and thresholds stored in local profile.
- **Transcription Strategy:**
  - Primary: Web Speech API (on-device / browser-managed).
  - Fallback: Upload compressed audio chunk to backend -> Google Cloud Speech-to-Text.

### 2.3 Intent & Dialogue Layer
- **Command Router:** Decides between regex parser (fast path) and AI parser (Gemini).
- **Context Store:** Maintains conversation state, active tab metadata, and prior command results.
- **Disambiguation Prompts:** Creates clarifying questions when intent confidence falls below threshold.

### 2.4 Browser Automation Engine
- **Action Executor:** Maps structured commands into Chrome extension API calls (tabs, windows, bookmarks, downloads).
- **DOM Agent:** Content-script helpers for element targeting (semantic selectors, heuristics, ARIA roles) and form autofill.
- **Clipboard Manager:** Utilizes `navigator.clipboard` API with permission guards and fallback prompts.

### 2.5 Backend Services
- **API Gateway (FastAPI):** Secures requests from extension via OAuth2 device flow or signed tokens; routes to micro-modules.
- **AI Orchestration:** Handles Gemini prompts, caching, and safety filters. Applies rate limiting and prompt templates.
- **Analytics Processor:** Receives command logs, aggregates metrics, and writes to Firestore or BigQuery export.
- **Configuration Service:** Stores remote flags, experiment configs, and feature rollout controls.

### 2.6 Data Stores
- **Firestore:** Command history (anonymized), user preferences, beta cohort flags.
- **Local Storage / IndexedDB:** Offline-capable cache of preferences, audio calibration, and recent history.
- **Secret Management:** Backend secrets managed via Google Secret Manager; extension uses OAuth tokens with minimal scopes.

## 3. Data Flow (MVP Scenario)

1. User presses push-to-talk button within extension popup.
2. Audio stream captured and transcribed via Web Speech API; interim results displayed.
3. Transcript sent to command router:
   - Regex parser attempts match; if confidence high, create structured command.
   - Otherwise, call backend AI orchestration (Gemini) for intent resolution.
4. Context manager updates state and forwards structured command to action executor.
5. Action executor communicates with content script (if page interaction) or Chrome APIs (if tab/window/clipboard).
6. Result emitted back to user via avatar state changes and speech synthesis.
7. Command and telemetry sent (asynchronously) to backend analytics; Firestore stores sanitized log.

## 4. Technology Stack

| Layer | Technologies |
| --- | --- |
| UI & Rendering | React 18, Vite, Tailwind CSS, Lottie, React Spring |
| Speech & Audio | Web Speech API, Web Audio API, Google Cloud Speech-to-Text (fallback) |
| AI & NLP | Regex parser, Gemini API via FastAPI backend, context heuristics |
| Extension Platform | Chrome Manifest V3, service workers, Chrome Tabs/Windows/Bookmarks APIs |
| Backend | FastAPI, Uvicorn, Google Cloud Run, Firebase Admin SDK |
| Data & Analytics | Firebase Firestore, Cloud Logging, optional BigQuery export |
| DevOps | GitHub Actions (CI), Docker, Terraform (for infra as code - planned) |

## 5. Security & Privacy Considerations

- **Principle of Least Privilege:** Request minimal extension permissions; leverage optional permissions for high-risk features.
- **Secure Channels:** All extension ⇄ backend communication over HTTPS with signed JWTs and short-lived tokens.
- **Data Minimization:** Store only anonymized command metadata; sensitive content stripped or hashed.
- **Consent & Transparency:** Provide clear onboarding for telemetry opt-in, with user-accessible data export/delete controls.
- **Secret Handling:** Backend stores API keys in Secret Manager; extension never ships with raw keys.
- **Threat Detection:** Rate limiting for voice-to-backend calls, anomaly detection on command success rates.

## 6. Scalability & Reliability

- **Backend:** Stateless FastAPI services deployed on Cloud Run with auto-scaling; asynchronous tasks handled via Cloud Tasks if needed.
- **Caching:** Edge caching of AI prompt templates and parsed intent patterns to reduce latency.
- **Resilience:** Circuit breakers around third-party APIs; degrade gracefully to local regex parser when offline.
- **Monitoring:** Cloud Monitoring dashboards covering STT latency, Gemini usage, command success rates, error taxonomy.

## 7. Testing Strategy

- **Unit Tests:** Parser logic, context manager, backend API modules.
- **Integration Tests:** Simulated voice commands executed in headless Chrome via Puppeteer/Playwright.
- **End-to-End:** Voice-to-action scenarios using recorded utterances and WebDriver.
- **Performance:** Latency budgets for transcription, parsing, execution tracked in CI.
- **Accessibility Audits:** Leverage axe-core and manual screen reader passes.

## 8. Future Enhancements

- Multi-browser support (Firefox, Edge) via abstraction over browser APIs.
- Offline cache for frequent commands and summaries.
- Plugin marketplace for custom command packs.
- Edge-compute variant for on-device NLP when hardware permits.

## 9. Open Questions

- Will we support continuous listening on launch, or restrict to push-to-talk for privacy/regulatory reasons?
- Do we require on-premise data residency options for enterprise customers?
- Which analytics KPIs should be exposed in real-time dashboards versus offline reports?
- What governance model will we adopt for community-built command scripts?

> Decisions will be tracked in forthcoming ADR documents within `docs/adr/`.

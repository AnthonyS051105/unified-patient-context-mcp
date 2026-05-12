# Nova by NexusHealth — Unified Patient Context MCP Server

> **"Instant context. Better care."**

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that acts as the **living memory and intelligence layer** of a patient in a multi-agent healthcare AI ecosystem. It aggregates data from FHIR EHR, lab results, medication history, and clinical deterioration signals — and goes beyond aggregation to **think, adapt, alert proactively, and learn from patterns**.

**Platform:** [Prompt Opinion](https://promptopinion.ai) with SHARP context propagation  
**Marketplace:** [Nova on Prompt Opinion Marketplace](https://app.promptopinion.ai/marketplace/mcp/019e01d3-a04c-7c08-aa21-d4a30e98bef0) \
**Demonstration Video:** [Watch on YouTube](https://youtu.be/V1qbjtGSS4g)

---

## Why This Exists

Clinicians spend **36 minutes in the EHR per 30-minute patient visit**. Every AI agent operating in healthcare has to "interview" 5–10 different systems (EHR, lab system, pharmacy, wearable gateway) just to understand one patient. This creates latency, incomplete context, duplicate data, and missed deterioration signals.

Nova is the **intelligence layer** between agents and clinical data sources. Agents don't need to know FHIR, HL7, or OpenFDA exist. They call clinical tools and receive processed, AI-adapted, pattern-aware context — instantly.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROMPT OPINION PLATFORM                      │
│   Diagnosis Agent  │  Triage Agent  │  Medication Agent        │
└────────────────────┼────────────────┼─────────────────────────-┘
                     │  MCP Tool Calls + SHARP Context
                     │  (patient_id, ehr_token, role...)
                     ▼
         ┌─────────────────────────────────────────┐
         │     NOVA — UNIFIED PATIENT CONTEXT      │
         │     Python + FastMCP | Railway.app      │
         │                                         │
         │  ┌───────────────────────────────────┐  │
         │  │        SHARP MIDDLEWARE           │  │
         │  │   extract → validate → audit      │  │
         │  └──────────────┬────────────────────┘  │
         │                 │                       │
         │  ┌──────────────▼────────────────────┐  │
         │  │          10 MCP TOOLS             │  │
         │  │  Tools 1–6: Data retrieval        │  │
         │  │  Tool 7:    AI Synthesis ⭐        │  │
         │  │  Tool 8:    Ward Alerts 🆕         │  │
         │  │  Tool 9:    Meta-Orchestrator 🆕   │  │
         │  │  Tool 10:   Pattern Memory 🆕      │  │
         │  └────┬─────────────┬─────────────┬──┘  │
         │       │             │             │      │
         │  ┌────▼────┐  ┌─────▼─────┐ ┌────▼───┐  │
         │  │ NEWS2/  │  │ Gemini AI │ │Pattern │  │
         │  │ MEWS    │  │ Explainer │ │Memory  │  │
         │  │ Engine  │  │ + Persona │ │Store   │  │
         │  └─────────┘  └───────────┘ └────────┘  │
         └───────────────────┬─────────────────────┘
                             │
           ┌─────────────────┴──────────────────┐
           │  HAPI FHIR R4 Public Server        │
           │  OpenFDA Drug Interaction API      │
           │  Google Gemini API (2.5 Flash)     │
           └────────────────────────────────────┘
```

---

## 5 Advanced Features

### 1. Adaptive Clinical Persona

Every tool output is **restructured by clinician role** — not just filtered, but fundamentally reshaped. Same data, completely different output:

| Role         | Output Format                            | Focus                                           |
| ------------ | ---------------------------------------- | ----------------------------------------------- |
| `physician`  | Narrative + full medical terminology     | Differential reasoning, raw values              |
| `nurse`      | WATCH / ESCALATE IF / ACTION NOW bullets | Thresholds, escalation triggers                 |
| `pharmacist` | Drug-centric structured format           | Interactions, renal dosing, contraindications   |
| `patient`    | Plain language, 6th grade reading level  | What's happening, what's next, questions to ask |

Pass `role` as a parameter to any tool — or it propagates automatically via SHARP context.

### 2. Proactive Ward Alerts (`scan_ward_alerts`)

Nova doesn't wait to be asked. `scan_ward_alerts` scans an entire ward in parallel, ranks patients by clinical risk, and surfaces who needs attention — before a clinician thinks to ask.

### 3. Confidence-Weighted Evidence Trail

Every synthesis tool returns a transparent `evidence_trail` with:

- Which data sources were used and their recency
- Per-source confidence weights (0.0–1.0)
- What data is missing and why it matters
- Overall confidence label: `high / moderate / low / insufficient`

### 4. Clinical Pattern Memory (`get_pattern_insights`)

A session-scoped, **zero-PII pattern accumulation layer**. Nova stores cryptographic hashes of clinical condition combinations — never patient data — and surfaces context when a pattern recurs:

> _"This pattern (creatinine rising + new nephrotoxic agent + declining urine output) has appeared 3 times this session. In 2 of 3 cases, deterioration was subsequently detected within ~31 hours."_

Pattern store resets on server restart. No persistent storage of any kind.

### 5. Meta-Orchestrator (`orchestrate_context_from_sources`)

Nova can **call other MCP servers** as part of its context-building, making it a true interoperability hub across the multi-agent ecosystem.

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Google Gemini API key](https://ai.google.dev) (free tier supported)

### Installation

```bash
git clone https://github.com/AnthonyS051105/unified-context-patient-mcp
cd unified-context-patient-mcp

pip install -r requirements.txt

cp .env.example .env
# Edit .env — add GEMINI_API_KEY at minimum
```

### Run the Server

```bash
python main.py
# Server starts on http://0.0.0.0:8000
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python main.py
# Opens browser UI — all 10 tools will appear and are invokable
```

### Run Tests

```bash
pytest tests/ -v
# Expected: 148 passed
```

### Test SHARP Mock Mode (local dev)

```bash
MOCK_SHARP=true MOCK_PATIENT_ID=synthea-demo-patient MOCK_SHARP_ROLE=nurse python main.py
```

---

## Environment Variables

| Variable                       | Default                        | Description                                   |
| ------------------------------ | ------------------------------ | --------------------------------------------- |
| `GEMINI_API_KEY`               | _(required)_                   | Google Gemini API key for LLM calls           |
| `GEMINI_MODEL`                 | `gemini-2.0-flash`             | Gemini model to use                           |
| `FHIR_BASE_URL`                | `https://hapi.fhir.org/baseR4` | FHIR R4 server base URL                       |
| `OPENFDA_BASE_URL`             | `https://api.fda.gov/drug`     | OpenFDA API base URL                          |
| `MCP_HOST`                     | `0.0.0.0`                      | Server bind host                              |
| `MCP_PORT`                     | `8000`                         | Server port                                   |
| `LOG_LEVEL`                    | `INFO`                         | Logging level                                 |
| `MOCK_SHARP`                   | `false`                        | Set `true` to simulate SHARP context locally  |
| `MOCK_PATIENT_ID`              | `synthea-demo-patient`         | Patient ID used when `MOCK_SHARP=true`        |
| `MOCK_SHARP_ROLE`              | `physician`                    | Clinician role when `MOCK_SHARP=true`         |
| `MOCK_EXTERNAL_MCP`            | `true`                         | Use mock radiology/pharmacy MCP data for demo |
| `WARD_SCAN_MAX_PATIENTS`       | `20`                           | Max patients scanned per ward call            |
| `PATTERN_MEMORY_ENABLED`       | `true`                         | Enable Clinical Pattern Memory                |
| `PATTERN_SIMILARITY_THRESHOLD` | `0.8`                          | Minimum similarity for pattern match          |

---

## 10 Clinical Tools

### Tool 1: `get_patient_snapshot`

Unified snapshot of a patient's current clinical status: demographics, active conditions, medications, and allergies in one call. Always adapted to clinician role.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `role` | string | `physician` / `nurse` / `pharmacist` / `patient` |

**Example output (role="nurse"):**

```json
{
  "patient_id": "synthea-demo-patient",
  "name": "Eleanor M. Dawson",
  "age_years": 68,
  "gender": "female",
  "active_conditions": [
    { "display": "Type 2 Diabetes Mellitus", "clinical_status": "active" },
    {
      "display": "Chronic Kidney Disease, Stage 3",
      "clinical_status": "active"
    }
  ],
  "active_medications_count": 4,
  "allergies": [{ "substance": "Penicillin", "severity": "severe" }],
  "content_adapted": "WATCH: Blood sugar and kidney function. ESCALATE IF: urine output <30mL/hr...",
  "persona_applied": "nurse",
  "persona_format": "bullets",
  "sharp_metadata": { "role_context": "nurse", "sharp_propagated": false }
}
```

---

### Tool 2: `get_active_problems`

Active clinical problems prioritized by AI-assessed clinical urgency. Role-aware: physician focus = diagnosis; nurse focus = monitoring; pharmacist focus = medication implications.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `include_resolved` | boolean | Include resolved conditions (default: false) |
| `role` | string | Clinician role for output adaptation |

**Example output:**

```json
{
  "problems": [
    {
      "display": "Chronic Kidney Disease, Stage 3",
      "urgency_score": 4,
      "urgency_reasoning": "CKD Stage 3 with rising creatinine trend requires close GFR monitoring and medication dose review."
    },
    {
      "display": "Type 2 Diabetes Mellitus",
      "urgency_score": 3,
      "urgency_reasoning": "Chronic condition with interaction risk given CKD — metformin safety threshold approaching."
    }
  ],
  "total_count": 2,
  "persona_applied": "physician"
}
```

---

### Tool 3: `get_medication_timeline`

Medication history with OpenFDA drug interaction flags. Automatically deduplicates brand vs. generic names (e.g., "Glucophage" and "metformin hydrochloride" become one entry via semantic resolution).

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `days` | integer | Days of history (default: 90) |
| `role` | string | Clinician role — pharmacist gets detailed interaction explanations |

**Example output:**

```json
{
  "medications": [
    {
      "display_name": "metformin",
      "status": "active",
      "authored_on": "2026-02-10",
      "is_duplicate_merged": true,
      "interaction_flags": [
        {
          "drug_a": "metformin",
          "drug_b": "lisinopril",
          "severity": "moderate",
          "ai_explanation": "Given Stage 3 CKD, concurrent use warrants monitoring of renal function and lactate levels."
        }
      ]
    }
  ],
  "total_medications": 4,
  "interaction_pairs_checked": 6,
  "persona_applied": "pharmacist"
}
```

---

### Tool 4: `get_recent_abnormal_labs`

Abnormal lab results with trend analysis and AI-generated clinical significance explanations. Supports three thresholds: `critical`, `abnormal`, `borderline`.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `days` | integer | Days of history (default: 30) |
| `threshold` | string | `critical` / `abnormal` / `borderline` |
| `role` | string | Clinician role |

**Example output:**

```json
{
  "abnormal_labs": [
    {
      "display_name": "Creatinine",
      "loinc_code": "2160-0",
      "value": 2.1,
      "unit": "mg/dL",
      "reference_range": "0.7-1.2",
      "abnormality_level": "abnormal",
      "trend": {
        "direction": "rising",
        "previous_value": 1.5,
        "change_percent": 40.0
      },
      "ai_explanation": "Creatinine at 2.1 mg/dL represents a 40% rise over 48 hours — warrants urgent evaluation.",
      "evidence_trail": {
        "overall_confidence": 0.82,
        "confidence_label": "high"
      }
    }
  ],
  "total_abnormal": 1
}
```

---

### Tool 5: `detect_clinical_deterioration_signals`

Detect clinical deterioration using **NEWS2** (National Early Warning Score 2) and **MEWS** (Modified Early Warning Score) algorithms. Rule engine decides risk level — AI generates narrative. Always includes `confidence: "rule-based"` and `action_required_by: "clinician"`. Auto-records clinical pattern to Pattern Memory.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `hours_lookback` | integer | Vital sign history window (default: 72) |
| `role` | string | Clinician role |

**Example output:**

```json
{
  "news2": { "total_score": 7, "risk_level": "high" },
  "mews": { "total_score": 4, "risk_level": "medium" },
  "risk_level": "high",
  "triggered_rules": [
    "RR 22 /min — tachypnea (>20)",
    "SpO₂ 93% — hypoxemia (≤95%)",
    "NEWS2 score 7 — HIGH RISK: emergency response indicated"
  ],
  "recommendation": "Immediate emergency response required",
  "clinical_narrative": "The combination of elevated respiratory rate, reduced oxygen saturation, and tachycardia produces a NEWS2 score of 7 — HIGH risk category requiring immediate escalation.",
  "confidence": "rule-based",
  "action_required_by": "clinician",
  "evidence_trail": {
    "overall_confidence": 0.79,
    "confidence_label": "moderate"
  },
  "pattern_recorded": true,
  "persona_applied": "nurse"
}
```

**NEWS2 Risk Levels:**
| Score | Risk | Action |
|---|---|---|
| 0 | Low | Routine monitoring |
| 1–4 | Low-Medium | Increase monitoring frequency |
| 5–6 | Medium | Urgent clinical review |
| **7+** | **High** | **Emergency response** |

---

### Tool 6: `get_patient_context_delta`

What has changed for a patient in the last N hours across labs, medications, vitals, and conditions. AI generates a narrative change summary.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `since_hours` | integer | Lookback window in hours (default: 48) |
| `role` | string | Clinician role |

**Example output:**

```json
{
  "since_hours": 48,
  "no_changes": false,
  "new_labs": [{ "display_name": "Creatinine", "value": 2.1, "unit": "mg/dL" }],
  "changed_medications": [],
  "new_vitals": [{ "display_name": "Heart rate", "value": 96, "unit": "/min" }],
  "ai_narrative": "In the last 48 hours: creatinine rose to 2.1 mg/dL (above normal). Heart rate at 96 bpm. No medication changes or new conditions documented.",
  "persona_applied": "physician"
}
```

---

### Tool 7: `synthesize_cross_domain_insights` ⭐

**The AI Factor tool.** Answers a clinical question by simultaneously synthesizing lab trends, medication history, and vital sign patterns — something no SQL query or rule engine can do.

Rule engines can flag "creatinine high" and "metformin prescribed" separately. Only AI can connect: _"Creatinine rose 40% in 48h, coinciding with metformin initiation 3 days ago, alongside declining urine output — this pattern warrants evaluation for AKI."_

Calls Tools 4, 3, and 5 in parallel, then synthesizes across all three domains. Auto-records pattern to Clinical Pattern Memory.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `clinical_question` | string | Free-text clinical question |
| `role` | string | Clinician role — shapes synthesis framing |

**Example output:**

```json
{
  "clinical_question": "Is the elevated creatinine related to the new medication?",
  "synthesis_narrative": "The 40% rise in creatinine over 48 hours temporally correlates with metformin initiation 3 days ago. Combined with elevated respiratory rate and reduced SpO2, this pattern is consistent with declining renal clearance and warrants evaluation for medication-related nephrotoxicity. Action required by: clinician.",
  "confidence_level": "moderate",
  "confidence_reasoning": "Temporal correlation is strong but causation requires clinical judgment; baseline creatinine is unavailable.",
  "data_gaps": [
    "No baseline creatinine before metformin initiation",
    "eGFR not available"
  ],
  "cross_domain_patterns": [
    "Creatinine rising trend (labs) coincides with metformin start (medications)",
    "Elevated RR + reduced SpO2 (vitals) may reflect metabolic acidosis compensation"
  ],
  "evidence_trail": {
    "overall_confidence": 0.74,
    "confidence_label": "moderate",
    "evidence_items": [
      { "source": "Lab/Creatinine", "weight": 0.85, "quality": "complete" },
      {
        "source": "Medication/Metformin",
        "weight": 0.72,
        "quality": "complete"
      },
      { "source": "Vitals/SpO2", "weight": 0.61, "quality": "partial" }
    ],
    "missing_data": ["Baseline creatinine", "eGFR calculation"]
  },
  "action_required_by": "clinician",
  "ai_generated": true,
  "persona_applied": "physician"
}
```

---

### Tool 8: `scan_ward_alerts` 🆕

**Proactive ward-level scanning.** Nova doesn't wait to be asked. Scans all patients in a ward in parallel, scores each by clinical risk, and surfaces who needs attention — before the clinician thinks to ask.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `ward_id` | string | Ward or unit ID (e.g. `ICU-A`, `Ward-3B`) |
| `threshold` | string | Minimum alert level: `critical` / `high` / `medium` (default: `high`) |
| `max_patients` | integer | Max patients to scan (default: 20) |
| `role` | string | Clinician role — nurse gets actionable bullets, physician gets clinical detail |

**Example output:**

```json
{
  "ward_id": "ICU-A",
  "scan_timestamp": "2026-05-12T08:30:00Z",
  "patients_scanned": 18,
  "alerts_triggered": 2,
  "alerts": [
    {
      "patient_id": "synthea-demo-patient",
      "patient_name": "Eleanor M. Dawson",
      "alert_level": "high",
      "news2_score": 7,
      "primary_signal": "NEWS2=7 — emergency response indicated",
      "secondary_signals": [
        "Creatinine rising 40%",
        "Metformin interaction flag"
      ],
      "recommended_action": "Immediate clinical review",
      "evidence_trail": { "overall_confidence": 0.79 }
    }
  ],
  "summary_narrative": "2 of 18 patients require immediate attention. Patient Eleanor M. Dawson has NEWS2=7 (HIGH risk). Recommend immediate clinical review for both.",
  "persona_applied": "nurse"
}
```

---

### Tool 9: `orchestrate_context_from_sources` 🆕

**Meta-orchestrator.** Calls Nova's internal tools plus external MCP servers in parallel, then synthesizes a unified context from all sources. Makes Nova the only MCP server that is also a **true interoperability hub** — calling other MCP servers, not just receiving calls.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID |
| `sources` | list[string] | External MCP servers to query (e.g. `["radiology_mcp", "pharmacy_mcp"]`) |
| `role` | string | Clinician role |

**Example output:**

```json
{
  "sources_queried": ["nara_core", "radiology_mcp", "pharmacy_mcp"],
  "sources_available": 2,
  "sources_failed": ["pharmacy_mcp"],
  "unified_context": {
    "core_data": { "risk_level": "high", "news2_score": 7 },
    "radiology_findings": { "chest_xray": "No acute cardiopulmonary process" }
  },
  "synthesis": "Patient presents with HIGH deterioration risk (NEWS2=7). Radiology shows no acute chest pathology, suggesting the respiratory component may be non-pulmonary in origin. Warrants clinical reassessment.",
  "evidence_trail": { "overall_confidence": 0.71 },
  "persona_applied": "physician"
}
```

---

### Tool 10: `get_pattern_insights` 🆕 ⭐⭐

**Clinical Pattern Memory.** The most differentiating feature of Nova. Retrieves session-scoped pattern context for a set of clinical conditions — without storing any patient data.

Every call to Tools 5 and 7 automatically records a cryptographic hash of the clinical pattern encountered. `get_pattern_insights` queries this accumulation to surface context like:

> _"This pattern has appeared 3 times this session. In 2 of 3 cases, deterioration was detected within ~31 hours. Treat as a weak signal requiring clinical judgment."_

**Privacy architecture:**

- What is **NOT stored**: `"Patient Eleanor has creatinine 1.8"` ← PII
- What **IS stored**: `sha256("creatinine_rise_80pct|new_metformin|urine_decrease")` → outcome seen
- No way to reverse-engineer patient identity from hashes
- Pattern store is in-memory only — resets on server restart

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `patient_id` | string | FHIR Patient resource ID (used for fresh data, not stored) |
| `conditions` | list[string] | Clinical conditions to check (e.g. `["creatinine_rising", "new_metformin"]`) |
| `role` | string | Clinician role |

**Example output:**

```json
{
  "pattern_found": true,
  "conditions_checked": [
    "creatinine_rising_trend",
    "metformin_present",
    "urine_decreasing"
  ],
  "session_context": {
    "similar_patterns_seen": 3,
    "outcome_distribution": {
      "deterioration_detected": "67%",
      "stable_monitoring": "33%"
    },
    "median_time_to_change_hours": 31
  },
  "contextual_insight": "This pattern has appeared 3 times this session. In 2 of 3 cases, deterioration was subsequently detected within ~31 hours. Treat as a weak signal requiring clinical judgment.",
  "confidence": "low",
  "confidence_note": "Based on 3 session observations only — not a statistical claim.",
  "data_scope": "current_session_only",
  "session_reset_note": "Pattern store resets on server restart. No persistent storage of any kind.",
  "action_required_by": "clinician"
}
```

---

## SHARP Context Integration

SHARP (Structured Healthcare Agent Request Protocol) is the extension spec from Prompt Opinion that propagates EHR session credentials into MCP context.

When running on the Prompt Opinion platform, every tool call automatically receives:

| Header             | Description                                                   |
| ------------------ | ------------------------------------------------------------- |
| `sharp_patient_id` | Active patient in the current clinician session               |
| `sharp_ehr_token`  | EHR authentication token propagated from the session          |
| `sharp_session_id` | Session ID for zero-PII audit trail                           |
| `sharp_org_id`     | Healthcare organization ID                                    |
| `sharp_role`       | Clinician role: `physician`, `nurse`, `pharmacist`, `patient` |

When SHARP headers are present, `patient_id` and `role` are resolved automatically — the agent doesn't need to specify them. If SHARP is absent, both can be passed as explicit tool parameters.

### Testing SHARP Locally

```bash
# Simulate a nurse session with Eleanor M. Dawson
MOCK_SHARP=true MOCK_PATIENT_ID=synthea-demo-patient MOCK_SHARP_ROLE=nurse python main.py
```

---

## AI Factor — 6 Genuinely Irreplaceable Capabilities

| Capability                          | Why Rule-Based Systems Cannot Do This                                                                               |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Semantic Entity Resolution**      | Detects "Metformin HCl 500mg" = "Glucophage" without a hardcoded lookup table                                       |
| **Cross-Domain Clinical Synthesis** | Connects lab trends + medication timing + vital signs _simultaneously_ to answer a clinical question                |
| **Adaptive Clinical Persona**       | Reshapes output depth, format, and terminology based on who is reading — not just filters fields                    |
| **Proactive Pattern Detection**     | Scans an entire ward and surfaces risk without being asked                                                          |
| **Evidence-Weighted Reasoning**     | Calculates and displays confidence per data source with transparency notes                                          |
| **Clinical Pattern Memory**         | Recognizes anonymous patterns across patients in a session and surfaces context that only emerges from accumulation |

---

## Design Principles

| Principle                        | Implementation                                                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Stateless**                    | Zero persistent patient data. Every tool call is a fresh FHIR fetch.                                            |
| **AI as explainer, not decider** | Rule engines (NEWS2/MEWS) make clinical decisions. LLM generates language only.                                 |
| **Graceful degradation**         | FHIR timeout → informative error with `retry_suggested`. LLM failure → structured data without narrative.       |
| **Zero PII in logs**             | Patient IDs and session IDs are always `[REDACTED]` in application logs.                                        |
| **Pattern privacy**              | Pattern Memory stores only SHA-256 hashes of condition combinations — never patient IDs or raw clinical values. |
| **FHIR R4 only**                 | All resources use FHIR R4 format via HAPI public server.                                                        |
| **Async throughout**             | All network calls use `httpx.AsyncClient`. No blocking I/O.                                                     |
| **Persona transparency**         | Every response includes `persona_applied` field.                                                                |
| **Evidence transparency**        | All synthesis tools include `evidence_trail` with confidence weights and data gaps.                             |

---

## Safety & Compliance

- All AI-generated output includes `"ai_generated": true`
- Deterioration decisions always carry `"confidence": "rule-based"`
- Every response includes `"action_required_by": "clinician"`
- Tool 7 synthesis always includes a clinical disclaimer
- The words "diagnose", "diagnosis", and "prescribe" are never used in AI output
- Zero persistent storage of patient data (stateless by design)
- Patient IDs never appear in application logs
- Pattern Memory stores only anonymous hashes — zero PII, zero reversibility

---

## Project Structure

```
unified-patient-mcp/
├── main.py                      # Entry point
├── server.py                    # FastMCP init + 10 tools registered
│
├── tools/                       # One file per clinical domain
│   ├── patient_snapshot.py      # Tool 1: get_patient_snapshot
│   ├── active_problems.py       # Tool 2: get_active_problems
│   ├── medications.py           # Tool 3: get_medication_timeline
│   ├── lab_results.py           # Tool 4: get_recent_abnormal_labs
│   ├── deterioration.py         # Tool 5: detect_clinical_deterioration_signals
│   ├── context_delta.py         # Tool 6: get_patient_context_delta
│   ├── cross_domain_insights.py # Tool 7: synthesize_cross_domain_insights ⭐
│   ├── ward_alerts.py           # Tool 8: scan_ward_alerts 🆕
│   ├── orchestrate.py           # Tool 9: orchestrate_context_from_sources 🆕
│   └── pattern_insights.py      # Tool 10: get_pattern_insights 🆕
│
├── memory/                      # Clinical Pattern Memory engine
│   ├── store.py                 # ClinicalPatternMemory — SHA-256 keyed in-memory store
│   ├── signature.py             # PatternSignature — extracts generic conditions
│   ├── matcher.py               # PatternMatcher — similarity search
│   └── models.py                # PatternRecord, PatternInsight Pydantic models
│
├── persona/                     # Adaptive Clinical Persona engine
│   ├── adapter.py               # PersonaAdapter — LLM-driven output transformation
│   ├── profiles.py              # RoleProfile definitions per role
│   └── prompts.py               # Role-specific prompt templates
│
├── evidence/                    # Confidence-Weighted Evidence Trail engine
│   ├── scorer.py                # EvidenceScorer — weight per data source
│   ├── trail.py                 # EvidenceTrail builder
│   └── models.py                # EvidenceItem, EvidenceTrail Pydantic models
│
├── sharp/                       # SHARP protocol integration
│   ├── context.py               # SHARPContext + extract_sharp_context()
│   ├── middleware.py            # resolve_patient_id, build_sharp_metadata
│   └── audit.py                 # Zero-PII audit logging
│
├── integrations/
│   ├── fhir_client.py           # HAPI FHIR R4 async client
│   ├── openfda_client.py        # OpenFDA drug interaction client
│   ├── llm_client.py            # Gemini API wrapper
│   └── mcp_client.py            # MCP-to-MCP client for Meta-Orchestrator
│
├── engine/
│   ├── news2.py                 # NEWS2 scoring (RCP 2017)
│   ├── mews.py                  # MEWS 5-parameter scoring
│   └── deduplicator.py          # Brand/generic drug deduplication
│
├── models/                      # Pydantic v2 data contracts
│   ├── patient.py
│   ├── medication.py
│   ├── lab.py
│   ├── deterioration.py
│   └── advanced.py              # WardAlert, OrchestratedContext, PatternInsight
│
└── tests/                       # 148 tests, all passing
    ├── test_tools.py
    ├── test_news2.py
    ├── test_sharp.py
    ├── test_persona.py
    ├── test_evidence.py
    ├── test_ward_alerts.py
    └── test_pattern_memory.py
```

---

## Tech Stack

- **Python 3.11+** with **FastMCP** (`mcp` package)
- **httpx** — async HTTP client for FHIR and OpenFDA
- **Pydantic v2** — data validation and serialization
- **HAPI FHIR** public test server (R4) — `hapi.fhir.org/baseR4`
- **OpenFDA API** — drug interaction data
- **Google Gemini 2.0 Flash** — clinical explanation, synthesis, and persona adaptation
- **Railway.app** — deployment
- **pytest + pytest-asyncio** — 148 automated tests

---

## Deploy to Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up

# Set environment variables in Railway dashboard:
# GEMINI_API_KEY, FHIR_BASE_URL, OPENFDA_BASE_URL
```

**Live server:** `https://amiable-determination-production.up.railway.app`

**MCP endpoint** (register this in Prompt Opinion):

```
https://amiable-determination-production.up.railway.app/mcp
```

---

## How to Test

Nova is live and ready — no installation or account required to test the server directly.

**All synthetic data. No real PHI.** The demo patient (Eleanor M. Dawson, `synthea-demo-patient`) was generated with [Synthea](https://synthea.mitre.org) and uploaded to the HAPI FHIR public test server.

### Option 1: Prompt Opinion Marketplace (Recommended)

1. Open the [Nova listing on Prompt Opinion Marketplace](https://app.promptopinion.ai/marketplace/mcp/019e01d3-a04c-7c08-aa21-d4a30e98bef0)
2. Add Nova to your Prompt Opinion workspace
3. Create an agent and try these example prompts:

| What to test | Example prompt |
|---|---|
| Patient snapshot (nurse view) | *"Show me the patient snapshot for synthea-demo-patient as a nurse"* |
| Deterioration detection | *"Detect clinical deterioration signals for synthea-demo-patient"* |
| Cross-domain AI synthesis | *"Is the elevated creatinine related to the new medication? patient: synthea-demo-patient"* |
| Ward alert scan | *"Scan ward ICU-A for patient alerts"* |
| Clinical Pattern Memory | *"Get pattern insights for synthea-demo-patient with conditions: creatinine_rising, metformin_present"* |
| Role adaptation (pharmacist) | *"As a pharmacist, show me the medication timeline for synthea-demo-patient"* |

**To test Adaptive Clinical Persona:** ask the same question twice — once with *"as a nurse"* and once with *"as a physician"* — and compare the structure of the output.

### Option 2: MCP Inspector (Direct Tool Invocation)

```bash
npx @modelcontextprotocol/inspector
```

Connect to:
```
https://amiable-determination-production.up.railway.app/mcp
```

All 10 tools will appear in the inspector. Invoke any tool directly with:
- `patient_id`: `synthea-demo-patient`
- `role`: `physician`, `nurse`, `pharmacist`, or `patient`

**Recommended test sequence to demonstrate Pattern Memory:**
1. Call `detect_clinical_deterioration_signals` with `patient_id: synthea-demo-patient`
2. Call it 2 more times with the same patient
3. Call `get_pattern_insights` with `conditions: ["news2_medium_risk", "tachycardia"]`
4. You should see `pattern_found: true` and `similar_patterns_seen > 0`

### Option 3: Direct HTTP (curl)

```bash
# Step 1: Initialize session
SESSION=$(curl -s -X POST https://amiable-determination-production.up.railway.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -D - \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
  | grep -i "mcp-session-id" | awk '{print $2}' | tr -d '\r')

# Step 2: Call any tool
curl -s -X POST https://amiable-determination-production.up.railway.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_patient_snapshot","arguments":{"patient_id":"synthea-demo-patient","role":"nurse"}}}'
```

---

_Nova by NexusHealth — Proactive · Adaptive · Transparent · Pattern-aware · Interoperable._

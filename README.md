# Unified Patient Context MCP Server

> **"One call. Full context. Every agent."**

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that acts as the **living memory of a patient** in a multi-agent healthcare AI ecosystem. It aggregates data from FHIR EHR, lab results, medication history, and clinical deterioration signals into a single unified context object — queryable by any AI agent in real-time using clinical language, not technical queries.

**Hackathon:** Agents Assemble — The Healthcare AI Endgame (Devpost)  
**Track:** Option 1 — Build a Superpower (MCP Server)  
**Platform:** [Prompt Opinion](https://promptopinion.ai) with SHARP context propagation

---

## Why This Exists

Clinicians spend **36 minutes in the EHR per 30-minute patient visit**. Every AI agent operating in healthcare has to "interview" 5–10 different systems (EHR, lab system, pharmacy, wearable gateway) just to understand one patient. This creates latency, incomplete context, duplicate data, and missed deterioration signals.

This MCP server is the **intelligence layer** between agents and clinical data sources. Agents don't need to know FHIR, HL7, or OpenFDA exist. They call clinical tools and receive processed, deduplicated, AI-explained context.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  PROMPT OPINION PLATFORM                    │
│   Diagnosis Agent  │  Triage Agent  │  Medication Agent    │
└────────────────────┼────────────────┼─────────────────────-┘
                     │  MCP Tool Calls + SHARP Context        
                     │  (patient_id, ehr_token, role...)      
                     ▼
         ┌───────────────────────────────────┐
         │  UNIFIED PATIENT CONTEXT SERVER   │
         │  Python + FastMCP | Railway.app   │
         │                                   │
         │  ┌─────────────────────────────┐  │
         │  │     SHARP MIDDLEWARE        │  │
         │  │  extract → validate → audit │  │
         │  └──────────────┬──────────────┘  │
         │                 │                 │
         │  ┌──────────────▼──────────────┐  │
         │  │  7 MCP TOOLS               │  │
         │  │  Tools 1-6: Data retrieval  │  │
         │  │  Tool 7:    AI Synthesis ⭐ │  │
         │  └──────┬──────────┬───────────┘  │
         │         │          │              │
         │  ┌──────▼──┐ ┌─────▼──────┐      │
         │  │NEWS2/   │ │Claude Haiku│      │
         │  │MEWS Eng.│ │ Explainer  │      │
         │  └─────────┘ └────────────┘      │
         └───────────────────┬───────────────┘
                             │
           ┌─────────────────┴──────────────┐
           │  HAPI FHIR R4 Public Server    │
           │  OpenFDA Drug Interaction API  │
           │  Anthropic API (Claude Haiku)  │
           └────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com)

### Installation

```bash
git clone https://github.com/AnthonyS051105/unified-context-patient-mcp
cd unified-context-patient-mcp

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Run the Server

```bash
python main.py
# Server starts on http://0.0.0.0:8000
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python main.py
# Opens browser UI — all 7 tools will appear and are invokable
```

### Run Tests

```bash
pytest tests/ -v
# Expected: 69 passed
```

### Test SHARP Mock Mode (local dev)

```bash
MOCK_SHARP=true MOCK_PATIENT_ID=test-patient-123 MOCK_SHARP_ROLE=physician python main.py
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | API key for Gemini 2.0 Flash LLM calls |
| `FHIR_BASE_URL` | `https://hapi.fhir.org/baseR4` | FHIR R4 server base URL |
| `OPENFDA_BASE_URL` | `https://api.fda.gov/drug` | OpenFDA API base URL |
| `MCP_HOST` | `0.0.0.0` | Server bind host |
| `MCP_PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MOCK_SHARP` | `false` | Set `true` to simulate SHARP context locally |
| `MOCK_PATIENT_ID` | `synthea-001` | Patient ID used when `MOCK_SHARP=true` |
| `MOCK_SHARP_ROLE` | `physician` | Clinician role when `MOCK_SHARP=true` |

---

## 7 Clinical Tools

### Tool 1: `get_patient_snapshot`

Retrieve a unified snapshot of a patient's current clinical status. Aggregates demographics, active conditions, medications, and allergies in one call.

**Input:**
```json
{
  "patient_id": "592941"
}
```

**Output:**
```json
{
  "patient_id": "592941",
  "name": "John Smith",
  "birth_date": "1965-03-14",
  "age_years": 61,
  "gender": "male",
  "active_conditions": [
    {
      "condition_id": "cond-001",
      "display": "Type 2 Diabetes Mellitus",
      "code": "44054006",
      "code_system": "http://snomed.info/sct",
      "clinical_status": "active",
      "severity": "moderate",
      "onset_date": "2018-06-01"
    }
  ],
  "active_medications_count": 4,
  "allergies": [
    {
      "substance": "Penicillin",
      "reaction": "Anaphylaxis",
      "severity": "severe",
      "status": "active"
    }
  ],
  "ai_summary": "John Smith is a 61-year-old male with moderate Type 2 Diabetes Mellitus and 3 other active conditions, currently on 4 medications with a severe penicillin allergy.",
  "ai_generated": true,
  "data_sources": ["FHIR/Patient", "FHIR/Condition", "FHIR/MedicationRequest", "FHIR/AllergyIntolerance"],
  "last_updated": "2026-05-05T10:23:41Z",
  "server_version": "1.0.0",
  "sharp_metadata": {
    "sharp_propagated": false,
    "role_context": null
  }
}
```

---

### Tool 2: `get_active_problems`

List active clinical problems prioritized by clinical urgency using AI reasoning (not static weights). Role-aware: physician focus = diagnosis; nurse focus = monitoring; pharmacist focus = medication implications.

**Input:**
```json
{
  "patient_id": "592941",
  "include_resolved": false
}
```

**Output:**
```json
{
  "patient_id": "592941",
  "problems": [
    {
      "condition_id": "cond-002",
      "display": "Chronic kidney disease, stage 3",
      "clinical_status": "active",
      "onset_date": "2022-01-15",
      "urgency_score": 4,
      "urgency_reasoning": "Stage 3 CKD requires close monitoring of GFR trend and medication dose adjustments; risk of progression to stage 4 is clinically significant."
    },
    {
      "condition_id": "cond-001",
      "display": "Type 2 Diabetes Mellitus",
      "clinical_status": "active",
      "onset_date": "2018-06-01",
      "urgency_score": 3,
      "urgency_reasoning": "Chronic but requires ongoing glycemic management; interaction with CKD complicates medication choices."
    }
  ],
  "total_count": 2,
  "ai_generated": true,
  "sharp_metadata": { "sharp_propagated": false }
}
```

---

### Tool 3: `get_medication_timeline`

Fetch medication history with drug interaction flags from OpenFDA. Automatically deduplicates brand vs. generic names (e.g., "Glucophage" and "metformin hydrochloride" become one entry). Role-aware: pharmacist receives more detailed interaction explanations.

**Input:**
```json
{
  "patient_id": "592941",
  "days": 90
}
```

**Output:**
```json
{
  "patient_id": "592941",
  "medications": [
    {
      "medication_id": "med-001",
      "display_name": "metformin",
      "original_name": "Metformin HCl 500mg",
      "status": "active",
      "authored_on": "2026-02-10",
      "is_duplicate_merged": true,
      "interaction_flags": [
        {
          "drug_a": "metformin",
          "drug_b": "lisinopril",
          "severity": "moderate",
          "description": "Concurrent use may increase risk of lactic acidosis in patients with renal impairment.",
          "ai_explanation": "Given the patient's Stage 3 CKD, the combination of metformin and lisinopril warrants careful monitoring of renal function and lactate levels.",
          "source": "OpenFDA"
        }
      ]
    }
  ],
  "total_medications": 4,
  "interaction_pairs_checked": 6,
  "ai_generated": true,
  "sharp_metadata": { "sharp_propagated": false }
}
```

---

### Tool 4: `get_recent_abnormal_labs`

Retrieve recent abnormal lab results with trend analysis and AI-generated clinical significance explanations. Supports three thresholds: `critical`, `abnormal`, `borderline`.

**Input:**
```json
{
  "patient_id": "592941",
  "days": 30,
  "threshold": "abnormal"
}
```

**Output:**
```json
{
  "patient_id": "592941",
  "abnormal_labs": [
    {
      "observation_id": "obs-001",
      "display_name": "Creatinine [Mass/volume] in Serum or Plasma",
      "loinc_code": "2160-0",
      "value": 2.1,
      "unit": "mg/dL",
      "reference_range": "0.7-1.2",
      "abnormality_level": "abnormal",
      "effective_date": "2026-05-03T08:00:00Z",
      "trend": {
        "direction": "rising",
        "previous_value": 1.5,
        "change_percent": 40.0,
        "data_points": 2
      },
      "ai_explanation": "Creatinine at 2.1 mg/dL (reference 0.7-1.2) represents a 40% rise over 48 hours, suggesting acute deterioration of kidney function that warrants urgent clinical evaluation."
    }
  ],
  "total_abnormal": 1,
  "days_analyzed": 30,
  "threshold": "abnormal",
  "ai_generated": true,
  "sharp_metadata": { "sharp_propagated": false }
}
```

---

### Tool 5: `detect_clinical_deterioration_signals`

Detect clinical deterioration using **NEWS2** (National Early Warning Score 2) and **MEWS** (Modified Early Warning Score) algorithms. Rule engine decides — AI explains. Always includes `confidence: "rule-based"` and `action_required_by: "clinician"`.

**Input:**
```json
{
  "patient_id": "592941",
  "hours_lookback": 72
}
```

**Output:**
```json
{
  "patient_id": "592941",
  "news2": {
    "total_score": 7,
    "risk_level": "high",
    "components": {
      "respiratory_rate": 2,
      "oxygen_saturation": 2,
      "systolic_bp": 0,
      "heart_rate": 1,
      "consciousness": 0,
      "temperature": 1,
      "supplemental_o2": 1
    }
  },
  "mews": {
    "total_score": 4,
    "risk_level": "medium"
  },
  "risk_level": "high",
  "triggered_rules": [
    "RR 22 bpm (score 2: 21-24 range)",
    "SpO2 93% (score 2: 92-93% range)",
    "Supplemental O2 in use (score 1)",
    "Temperature 38.4°C (score 1: 38.1-39.0 range)",
    "Heart rate 96 bpm (score 1: 91-110 range)"
  ],
  "recommendation": "Urgent clinical review required. NEWS2 score ≥7 indicates HIGH risk.",
  "clinical_narrative": "The patient's vital signs show a combination of elevated respiratory rate, reduced oxygen saturation requiring supplemental oxygen, and low-grade fever. Together these findings indicate a NEWS2 score of 7, placing the patient in the HIGH risk category requiring urgent clinical escalation.",
  "confidence": "rule-based",
  "action_required_by": "clinician",
  "ai_generated": true,
  "data_window_hours": 72,
  "vital_signs_count": 8,
  "sharp_metadata": { "sharp_propagated": false }
}
```

**NEWS2 Risk Levels:**
- 0: Low (routine monitoring)
- 1–4: Low-Medium (increased monitoring frequency)
- 5–6: Medium (urgent review)
- **7+: High (emergency response)**

---

### Tool 6: `get_patient_context_delta`

Show what has changed for a patient in the last N hours across labs, medications, vitals, and conditions. AI generates a narrative summary.

**Input:**
```json
{
  "patient_id": "592941",
  "since_hours": 48
}
```

**Output:**
```json
{
  "patient_id": "592941",
  "since_hours": 48,
  "no_changes": false,
  "new_labs": [
    {
      "display_name": "Creatinine",
      "value": 2.1,
      "unit": "mg/dL",
      "effective_date": "2026-05-03T08:00:00Z"
    }
  ],
  "changed_medications": [],
  "new_vitals": [
    {
      "display_name": "Heart rate",
      "value": 96,
      "unit": "/min",
      "effective_date": "2026-05-03T06:30:00Z"
    }
  ],
  "new_conditions": [],
  "ai_narrative": "In the last 48 hours, one new lab result was recorded: creatinine at 2.1 mg/dL (above normal range). Vital sign monitoring shows heart rate at 96 bpm. No medication changes or new conditions were documented.",
  "ai_generated": true,
  "sharp_metadata": { "sharp_propagated": false }
}
```

---

### Tool 7: `synthesize_cross_domain_insights` ⭐

**The AI Factor tool.** Answers a clinical question by simultaneously synthesizing lab trends, medication history, and vital sign patterns — something no SQL query or rule engine can do.

Rule engines can flag "creatinine high" and "metformin prescribed" separately. Only AI can connect: *"Creatinine rose 40% in 48h, coinciding with metformin initiation 3 days ago, alongside declining urine output — this pattern warrants evaluation for AKI."*

**Input:**
```json
{
  "patient_id": "592941",
  "clinical_question": "Is the elevated creatinine related to the new medication?"
}
```

**Output:**
```json
{
  "patient_id": "592941",
  "clinical_question": "Is the elevated creatinine related to the new medication?",
  "synthesis_narrative": "The 40% rise in creatinine over 48 hours (1.5 → 2.1 mg/dL) is temporally correlated with the initiation of metformin 3 days ago. Combined with the elevated respiratory rate and reduced SpO2 seen in the vital signs — which may reflect early metabolic compensation — this pattern is consistent with declining renal clearance and warrants evaluation for medication-related nephrotoxicity or AKI. Metformin is contraindicated when eGFR falls below 30 mL/min/1.73m², making current renal function a critical parameter. Action required by: clinician.",
  "confidence_level": "moderate",
  "confidence_reasoning": "Temporal correlation is strong but causation requires clinical judgment; baseline creatinine prior to medication is unavailable.",
  "data_gaps": [
    "No baseline creatinine before metformin initiation",
    "eGFR not available in FHIR data",
    "Urine output measurements absent"
  ],
  "cross_domain_patterns": [
    "Creatinine rising trend (labs) coincides with metformin start (medications)",
    "Elevated RR + reduced SpO2 (vitals) may reflect metabolic acidosis compensation",
    "NEWS2 score 7 (high risk) corroborates clinical urgency suggested by lab trend"
  ],
  "supporting_data": {
    "labs_referenced": 3,
    "medications_referenced": 4,
    "vitals_referenced": 8,
    "news2_score": 7,
    "overall_risk": "high"
  },
  "action_required_by": "clinician",
  "ai_generated": true,
  "disclaimer": "This synthesis is generated by an AI clinical decision support tool for informational purposes only. It does not constitute a diagnosis, clinical recommendation, or prescription. All clinical decisions must be made by a qualified healthcare professional.",
  "sharp_metadata": { "sharp_propagated": false }
}
```

**Role-aware output (via SHARP context):**
- `physician`: Full clinical reasoning with medical terminology and differential considerations
- `nurse`: Actionable summary focused on what to monitor and escalate
- `pharmacist`: Medication-focused synthesis highlighting drug-lab-vital interactions

---

## SHARP Context Integration

SHARP (Structured Healthcare Agent Request Protocol) is the extension spec from Prompt Opinion that propagates EHR session credentials into MCP context.

When running on the Prompt Opinion platform, every tool call automatically receives:

| Header | Description |
|---|---|
| `sharp_patient_id` | Active patient in the current clinician session |
| `sharp_ehr_token` | EHR authentication token propagated from the session |
| `sharp_session_id` | Session ID for zero-PII audit trail |
| `sharp_org_id` | Healthcare organization ID |
| `sharp_role` | Clinician role: `physician`, `nurse`, `pharmacist` |

**What this means in practice:** When a clinician opens a patient chart in Prompt Opinion and asks an agent a question, the agent calls this MCP server — and the server *automatically knows which patient and what role* without the agent needing to specify them. The agent doesn't need to know FHIR exists.

### Testing SHARP Locally

```bash
# Simulate a physician session with a specific patient
MOCK_SHARP=true MOCK_PATIENT_ID=592941 MOCK_SHARP_ROLE=physician python main.py
```

When `MOCK_SHARP=true`, all tool calls will automatically use `MOCK_PATIENT_ID` as the effective patient ID and `MOCK_SHARP_ROLE` as the clinician role — even if you don't pass `patient_id` in the tool call.

---

## AI Factor — Why This Is Genuinely Irreplaceable

Three capabilities that rule-based software fundamentally cannot replicate:

### 1. Semantic Entity Resolution
Detects that "Metformin HCl 500mg", "Glucophage", and "metformin hydrochloride" are the same drug — without a hardcoded lookup table. The deduplicator uses a 50+ drug mapping as a base, and the LLM explanation layer synthesizes meaning from context.

### 2. Cross-Domain Clinical Synthesis (Tool 7)
Connects abnormal labs + medication changes + vital sign trends *simultaneously* to answer a clinical question. No SQL query can join these three streams and produce a narrative that explains their temporal and causal relationships.

### 3. Adaptive Context Prioritization
Uses the clinician's role from SHARP context to determine *what matters most* — a nurse gets actionable monitoring steps, a physician gets full differential reasoning, a pharmacist gets drug-centric analysis. Static weights cannot adapt to clinical context this way.

---

## Seeding Test Patients

To test with realistic synthetic patients:

```bash
# Download Synthea FHIR R4 bundles from synthea.mitre.org/downloads
# Extract to a local directory, then:

python scripts/seed_synthea.py --dir /path/to/fhir_r4/ --count 5

# Patient IDs are saved to tests/fixtures/test_patients.json
```

You can then use any saved patient ID to test tools against real FHIR data on the HAPI public server.

---

## Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

railway login
railway init
railway up

# Set environment variables in Railway dashboard:
# ANTHROPIC_API_KEY, FHIR_BASE_URL, OPENFDA_BASE_URL
```

Your server will be accessible at `https://amiable-determination-production.up.railway.app`.

**MCP Endpoint URL** (use this when registering with Prompt Opinion):
```
https://amiable-determination-production.up.railway.app/mcp
```

To register with Prompt Opinion: add the URL above as an MCP server endpoint in the Prompt Opinion marketplace settings.

---

## Design Principles

| Principle | Implementation |
|---|---|
| **Stateless** | No patient data stored. Every tool call is a fresh FHIR fetch. |
| **AI as explainer, not decider** | Rule engines (NEWS2/MEWS) make clinical decisions. LLM generates language only. |
| **Graceful degradation** | FHIR timeout → informative error with `retry_suggested`. LLM failure → structured data without AI narrative. |
| **Zero PII in logs** | Patient IDs and session IDs are always `[REDACTED]` in application logs. |
| **FHIR R4 only** | All resources use FHIR R4 format via HAPI public server. |
| **Async throughout** | All network calls use `httpx.AsyncClient`. No blocking I/O. |

---

## Project Structure

```
unified-patient-mcp/
├── main.py                      # Entry point — starts MCP server
├── server.py                    # FastMCP init + 7 tools registered
│
├── tools/                       # One file per clinical domain
│   ├── patient_snapshot.py      # get_patient_snapshot
│   ├── active_problems.py       # get_active_problems
│   ├── medications.py           # get_medication_timeline
│   ├── lab_results.py           # get_recent_abnormal_labs
│   ├── deterioration.py         # detect_clinical_deterioration_signals
│   ├── context_delta.py         # get_patient_context_delta
│   └── cross_domain_insights.py # synthesize_cross_domain_insights ⭐
│
├── sharp/                       # SHARP protocol integration
│   ├── context.py               # SHARPContext + extract_sharp_context()
│   ├── middleware.py            # resolve_patient_id, build_sharp_metadata
│   └── audit.py                 # Zero-PII audit logging
│
├── integrations/
│   ├── fhir_client.py           # HAPI FHIR R4 async client
│   ├── openfda_client.py        # OpenFDA drug interaction client
│   └── llm_client.py           # Claude Haiku wrapper
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
│   └── deterioration.py
│
└── tests/                       # 69 tests, all passing
    ├── test_news2.py            # 15 NEWS2/MEWS unit tests
    ├── test_fhir_client.py      # 9 FHIR client tests
    ├── test_tools.py            # 15 tool/parser unit tests
    ├── test_sharp.py            # 19 SHARP integration tests
    └── test_cross_domain.py     # 11 Tool 7 tests
```

---

## Tech Stack

- **Python 3.11+** with **FastMCP** (`mcp` package)
- **httpx** — async HTTP client for FHIR and OpenFDA
- **Pydantic v2** — data validation and serialization
- **HAPI FHIR** public test server (R4) — `hapi.fhir.org/baseR4`
- **OpenFDA API** — drug interaction data
- **Gemini 2.0 Flash** (`gemini-2.0-flash`) — clinical explanation and synthesis
- **Railway.app** — deployment
- **pytest + pytest-asyncio** — 69 automated tests

---

## Safety & Compliance

- All AI-generated output includes `"ai_generated": true`
- Deterioration decisions always carry `"confidence": "rule-based"`
- Every response includes `"action_required_by": "clinician"`
- Tool 7 synthesis always includes a clinical disclaimer
- The words "diagnose", "diagnosis", and "prescribe" are never used in AI output
- Zero persistent storage of patient data (stateless by design)
- Patient IDs never appear in application logs

---

*Built for the Agents Assemble hackathon. SHARP-compliant | FHIR R4 | Stateless | Privacy-safe.*

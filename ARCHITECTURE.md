# ARCHITECTURE.md — System Architecture

# Unified Patient Context MCP Server

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROMPT OPINION PLATFORM                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Diagnosis   │  │   Triage     │  │  Medication Management   │  │
│  │    Agent     │  │    Agent     │  │         Agent            │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│         │                 │                        │                │
│         └─────────────────┼────────────────────────┘                │
│                           │ MCP Tool Calls + SHARP Context          │
│                           │ (sharp_patient_id, ehr_token, role...)  │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
            ┌───────────────▼──────────────────────┐
            │    UNIFIED PATIENT CONTEXT MCP SERVER │
            │    (Python + FastMCP, Railway.app)    │
            │                                      │
            │  ┌──────────────────────────────────┐ │
            │  │     SHARP MIDDLEWARE LAYER       │ │
            │  │  extract_sharp_context()         │ │
            │  │  validate + propagate to tools   │ │
            │  │  audit trail (zero-PII logging)  │ │
            │  └────────────────┬─────────────────┘ │
            │                   │                   │
            │  ┌────────────────▼────────────────┐  │
            │  │          MCP TOOL LAYER         │  │
            │  │  Tools 1-6: Data retrieval      │  │
            │  │  Tool 7: AI Synthesis ⭐         │  │
            │  └─────┬──────────┬────────────────┘  │
            │        │          │                   │
            │  ┌─────▼───┐ ┌────▼────┐              │
            │  │Clinical │ │   LLM   │              │
            │  │Rule Eng.│ │Explainer│              │
            │  │NEWS2/   │ │+Synthesis              │
            │  │MEWS     │ │Engine   │              │
            │  └─────────┘ └─────────┘              │
            └──────────────────────┬────────────────┘
                                   │
               ┌───────────────────┘
               │
    ┌──────────▼──────────┐         ┌───────────────────────┐
    │   EXTERNAL APIs     │         │   Anthropic API        │
    │                     │         │   (Claude Haiku)       │
    │  ┌───────────────┐  │         │                        │
    │  │  HAPI FHIR R4 │  │         │  Tool 1-6: explain    │
    │  │  Public Server│  │         │  Tool 7: synthesize   │
    │  └───────────────┘  │         │  cross-domain insight  │
    │  ┌───────────────┐  │         └───────────────────────┘
    │  │  OpenFDA API  │  │
    │  └───────────────┘  │
    └─────────────────────┘
```

---

## 2. Layer Architecture

### Layer 0: SHARP Middleware (`sharp/`) — BARU

Bertanggung jawab untuk:

- Mengekstrak SHARP context dari setiap incoming MCP tool call
- Menyediakan `SHARPContext` object ke semua tool handlers
- Menjalankan zero-PII audit logging per session
- Graceful fallback ke explicit parameters saat SHARP tidak ada

```python
# sharp/context.py
@dataclass
class SHARPContext:
    patient_id: Optional[str] = None   # auto-injected oleh Prompt Opinion
    ehr_token: Optional[str] = None    # EHR auth token dari sesi klinisi
    session_id: Optional[str] = None   # untuk audit trail
    org_id: Optional[str] = None       # organisasi healthcare
    role: Optional[str] = None         # physician|nurse|pharmacist|admin
    is_present: bool = False           # True = request dari Prompt Opinion platform
```

Bertanggung jawab untuk:

- Menerima MCP tool calls dari agents via HTTP/SSE transport
- Routing ke tool handler yang tepat
- Serialisasi/deserialisasi Pydantic models ke JSON
- Error handling dan formatting MCP error responses

```python
# server.py — struktur utama
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="unified-patient-context",
    version="1.0.0",
    description="Aggregates patient data from FHIR and clinical databases into unified context for AI agents"
)

# Tools didaftarkan via import
from tools.patient_snapshot import get_patient_snapshot
from tools.medications import get_medication_timeline
# ... dst
```

### Layer 2: Tool Layer (`tools/`)

Setiap tool adalah async function yang:

1. Menerima input yang sudah divalidasi Pydantic
2. Memanggil integration clients
3. Memanggil rule engine jika perlu
4. Memanggil LLM explainer untuk natural language output
5. Mengembalikan Pydantic model (auto-serialized ke JSON)

```python
# Pola standar setiap tool
@mcp.tool()
async def get_patient_snapshot(patient_id: str) -> PatientSnapshot:
    """
    Ambil ringkasan lengkap kondisi pasien saat ini.

    Args:
        patient_id: FHIR Patient resource ID

    Returns:
        PatientSnapshot dengan data dari FHIR dan AI-generated summary
    """
    # 1. Fetch dari FHIR
    fhir_data = await fhir_client.get_patient_bundle(patient_id)

    # 2. Transform ke Pydantic models
    snapshot = build_snapshot(fhir_data)

    # 3. Generate AI explanation
    snapshot.ai_summary = await llm.explain_patient_context(snapshot)

    return snapshot
```

### Layer 3: Integration Layer (`integrations/`)

Stateless HTTP clients yang handle:

- Connection pooling via httpx AsyncClient
- Retry logic dengan exponential backoff
- Response parsing dan error handling
- Rate limiting compliance

```python
# integrations/fhir_client.py — pola utama
class FHIRClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def search(self, resource_type: str, params: dict) -> dict:
        """Generic FHIR search dengan retry."""
        ...

    async def get_patient_bundle(self, patient_id: str) -> dict:
        """Ambil semua resource terkait pasien dalam satu operasi."""
        ...
```

### Layer 4: Engine Layer (`engine/`)

Pure Python, no external dependencies, fully testable:

- **NEWS2:** Implementasi algoritma National Early Warning Score 2
- **MEWS:** Implementasi algoritma Modified Early Warning Score
- **Deduplicator:** Fuzzy matching untuk brand vs generic drug names

### Layer 5: Model Layer (`models/`)

Pydantic v2 models sebagai kontrak data antara semua layers.

---

## 3. Data Flow per Tool

### Flow: `detect_clinical_deterioration_signals`

```
Agent Call
    │
    ▼
[FastMCP] validate patient_id, hours_lookback
    │
    ▼
[FHIRClient] GET /Observation?patient={id}&category=vital-signs
             &date=gt{72h ago}&_sort=-date
    │
    ▼
[VitalSigns Parser] extract: HR, RR, SpO2, BP, Temp, AVPU, consciousness
    │
    ▼
[NEWS2 Engine] calculate score dari 7 parameters
[MEWS Engine]  calculate score dari 5 parameters
    │
    ▼
[Rule Evaluator] map score → risk level → triggered rules
    │
    ▼
[LLM Explainer] generate clinical narrative dari structured rules
    │
    ▼
[Response Builder] assemble DeteriorationReport
    {
      "news2_score": 7,
      "mews_score": 4,
      "risk_level": "high",
      "triggered_rules": ["HR > 110", "SpO2 < 95%", "RR > 20"],
      "recommendation": "Escalate to clinical review",
      "clinical_narrative": "Patient shows signs of...",
      "confidence": "rule-based",
      "action_required_by": "clinician",
      "ai_generated": true,
      "data_window_hours": 72,
      "vital_signs_count": 12
    }
    │
    ▼
Agent Receives Response
```

### Flow: `synthesize_cross_domain_insights` ⭐ (AI FACTOR UTAMA)

```
Agent Call (patient_id, clinical_question, ctx+SHARP)
    │
    ▼
[SHARP Middleware] extract role, session_id, effective patient_id
    │
    ▼
[Parallel Sub-calls via asyncio.gather()]
    ├── get_recent_abnormal_labs(patient_id, days=30)
    ├── get_medication_timeline(patient_id, days=90)
    └── detect_clinical_deterioration_signals(patient_id, hours=72)
    │
    ▼
[Context Assembler] merge semua hasil menjadi satu structured context dict
    {
      "abnormal_labs": [...],
      "medications": [...],
      "deterioration": {...},
      "clinical_question": "Is the elevated creatinine related to new medication?"
    }
    │
    ▼
[LLM Synthesis] Prompt ke Claude Haiku:
    "Kamu adalah clinical decision support AI. JANGAN buat diagnosis.
     Berdasarkan data berikut: {context}
     Jawab pertanyaan klinis: {clinical_question}
     Role klinisi: {sharp.role}
     Format output: narrative + confidence + data_gaps + disclaimer"
    │
    ▼
[Response Builder] assemble ClinicalInsight
    {
      "clinical_question": "Is the elevated creatinine...",
      "synthesis_narrative": "The creatinine elevation correlates temporally with
                              metformin initiation 3 days ago. Combined with the
                              declining urine output trend in vitals and the 40%
                              rise over 48h in labs, this pattern warrants clinical
                              evaluation for early AKI...",
      "confidence_level": "moderate",
      "data_gaps": ["No urine output measurements in FHIR", "Missing baseline creatinine"],
      "supporting_data": {
        "labs_referenced": 3,
        "medications_referenced": 2,
        "vitals_referenced": 8
      },
      "action_required_by": "clinician",
      "ai_generated": true,
      "disclaimer": "This synthesis is for clinical decision support only...",
      "sharp_metadata": { "role": "physician", "session_id": "[REDACTED]" }
    }
    │
    ▼
Agent Receives Response — reasoning yang tidak bisa dilakukan SQL manapun
```

```
Agent Call (patient_id, days=90)
    │
    ▼
[FHIRClient] GET /MedicationRequest?patient={id}&authoredon=gt{90d ago}
    │
    ▼
[Deduplicator] merge brand/generic duplicates
    │
    ▼
[OpenFDAClient] untuk setiap kombinasi obat:
    GET /drug/label.json?search=openfda.generic_name:{drug_a}+AND+{drug_b}
    │
    ▼
[Interaction Analyzer] flag severe interactions
    │
    ▼
[LLM Explainer] plain language warning per interaction
    │
    ▼
Response: List[MedicationEntry] dengan interaction_flags populated
```

---

## 4. FHIR Resource Mapping

| Tool                     | FHIR Resources                                            | Key Parameters                                  |
| ------------------------ | --------------------------------------------------------- | ----------------------------------------------- |
| get_patient_snapshot     | Patient, Condition, MedicationRequest, AllergyIntolerance | patient={id}                                    |
| get_active_problems      | Condition                                                 | patient={id}&clinical-status=active             |
| get_medication_timeline  | MedicationRequest                                         | patient={id}&authoredon=gt{date}                |
| get_recent_abnormal_labs | Observation                                               | patient={id}&category=laboratory&date=gt{date}  |
| detect_deterioration     | Observation                                               | patient={id}&category=vital-signs&date=gt{date} |
| get_context_delta        | All above                                                 | \_lastUpdated=gt{date}                          |

### FHIR Vital Signs LOINC Codes (untuk NEWS2/MEWS)

```python
VITAL_SIGNS_LOINC = {
    "heart_rate":          "8867-4",
    "respiratory_rate":    "9279-1",
    "oxygen_saturation":   "59408-5",
    "systolic_bp":         "8480-6",
    "diastolic_bp":        "8462-4",
    "body_temperature":    "8310-5",
    "consciousness_avpu":  "67775-7",
    "gcs_total":           "9269-2"
}
```

---

## 5. NEWS2 Algorithm Implementation Spec

Implementasikan sesuai Royal College of Physicians guideline (2017):

| Parameter        | Range     | Score |
| ---------------- | --------- | ----- |
| Respiratory Rate | ≤8        | 3     |
|                  | 9–11      | 1     |
|                  | 12–20     | 0     |
|                  | 21–24     | 2     |
|                  | ≥25       | 3     |
| SpO2 Scale 1     | ≤91       | 3     |
|                  | 92–93     | 2     |
|                  | 94–95     | 1     |
|                  | ≥96       | 0     |
| Systolic BP      | ≤90       | 3     |
|                  | 91–100    | 2     |
|                  | 101–110   | 1     |
|                  | 111–219   | 0     |
|                  | ≥220      | 3     |
| Heart Rate       | ≤40       | 3     |
|                  | 41–50     | 1     |
|                  | 51–90     | 0     |
|                  | 91–110    | 1     |
|                  | 111–130   | 2     |
|                  | ≥131      | 3     |
| Consciousness    | Alert     | 0     |
|                  | CVPU      | 3     |
| Temperature      | ≤35.0     | 3     |
|                  | 35.1–36.0 | 1     |
|                  | 36.1–38.0 | 0     |
|                  | 38.1–39.0 | 1     |
|                  | ≥39.1     | 2     |

**Risk Levels:**

- 0: Low (routine monitoring)
- 1-4: Low-Medium (increased frequency monitoring)
- 5-6: Medium (urgent review)
- 7+: High (emergency response)

---

## 6. Deployment Architecture

```
GitHub Repository
    │
    │ (auto-deploy on push)
    ▼
Railway.app
    │
    ├── Environment: Python 3.11
    ├── Start command: python main.py
    ├── Port: 8000 (auto-detected)
    └── Env vars: set via Railway dashboard
    │
    ▼
Public URL: https://unified-patient-mcp.railway.app
    │
    ▼
Prompt Opinion Platform
    └── Register MCP server URL di marketplace
```

### `railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python main.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

---

## 7. Error Response Format

Semua errors harus mengikuti format standar ini:

```python
class MCPError(BaseModel):
    error: str                    # machine-readable error code
    message: str                  # human-readable description
    suggestion: str | None        # apa yang harus dilakukan agent/user
    retry_suggested: bool = False
    data_partial: dict | None     # data yang berhasil diambil (jika partial success)
```

Contoh:

```json
{
  "error": "FHIR_TIMEOUT",
  "message": "Could not reach FHIR server within 10 seconds",
  "suggestion": "Retry in 30 seconds or check FHIR server status",
  "retry_suggested": true,
  "data_partial": null
}
```

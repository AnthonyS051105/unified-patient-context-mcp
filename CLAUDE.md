# CLAUDE.md — Master Instruction File

# Nara by NexusHealth — Unified Patient Context MCP Server

# Hackathon: Agents Assemble — The Healthcare AI Endgame (Devpost)

# Version: 3.0 — Clinical Pattern Memory Edition

## 🎯 MISI PROYEK

Bangun sebuah MCP (Model Context Protocol) server bernama **"Nara"** oleh **NexusHealth** yang menjadi
**"memori hidup dan intelligence layer"** seorang pasien di ekosistem multi-agent healthcare AI.

Tagline: _"One call. Full picture."_

Server ini tidak hanya mengaggregasi data — ia **berpikir, beradaptasi, berproaktif, dan belajar**:

- Mengaggregasi data dari FHIR EHR, lab, obat, dan sinyal deteriorasi klinis
- Menyesuaikan output secara cerdas berdasarkan role klinisi (Adaptive Clinical Persona)
- Memberikan peringatan ward-level secara proaktif tanpa harus ditanya (Proactive Alert)
- Mengorkestrasi MCP server lain untuk data yang lebih kaya (Meta-Orchestrator)
- Menyertakan jejak bukti yang transparan di setiap insight (Confidence-Weighted Evidence Trail)
- **Mengenali pola klinis dari session dan memberikan konteks historis anonim (Clinical Pattern Memory)** 🆕

Tujuan akhir: **Memenangkan hackathon Agents Assemble ($7,500 Grand Prize)**

---

## 📋 KRITERIA JURI (SELALU INGAT INI)

1. **AI Factor** — AI HARUS melakukan sesuatu yang TIDAK BISA dilakukan rule-based software biasa.
   Di proyek ini, AI berperan dalam ENAM cara yang genuinely irreplaceable:
   - **Semantic Entity Resolution**: Mendeteksi "Metformin HCl 500mg" = "Glucophage" tanpa lookup table
   - **Cross-Domain Clinical Synthesis**: Menghubungkan lab + obat + vitals secara bersamaan
   - **Adaptive Clinical Persona**: Mengubah depth, prioritas, dan format output berdasarkan role
   - **Proactive Pattern Detection**: Mendeteksi pasien berisiko di seluruh ward tanpa diminta
   - **Evidence-Weighted Reasoning**: Menghitung dan menampilkan confidence per sumber data
   - **Clinical Pattern Memory**: Mengenali pola klinis anonim dari session dan mengkontekstualisasikan insight baru berdasarkan pola historis yang sudah terlihat 🆕

2. **Potential Impact** — Solusi menyentuh SETIAP interaksi klinisi-pasien, bukan edge case.
   Dokter menghabiskan 36 menit di EHR per kunjungan 30 menit. Nara memotong ini menjadi detik.

3. **Feasibility** — Semua data dari public APIs. Stateless by design. Zero PII. SHARP-compliant.
   Setiap fitur bisa berjalan di sistem healthcare nyata hari ini.

---

## 🏗️ STACK TEKNOLOGI

- **Language:** Python 3.11+
- **MCP Framework:** FastMCP (dari package `mcp`)
- **HTTP Client:** httpx (async)
- **Data Validation:** Pydantic v2
- **FHIR Server:** HAPI FHIR Public Test Server (https://hapi.fhir.org/baseR4)
- **Drug Database:** OpenFDA API (https://api.fda.gov/drug)
- **Synthetic Patients:** Synthea-generated FHIR bundles (Eleanor M. Dawson sudah ada)
- **Clinical Rules:** NEWS2 + MEWS (pure Python, no ML)
- **Transport:** Streamable HTTP (untuk Prompt Opinion platform)
- **Deploy:** Railway.app — https://amiable-determination-production.up.railway.app
- **Testing:** pytest + pytest-asyncio (69 tests sudah pass)
- **Linting:** ruff

---

## 📁 STRUKTUR PROJECT (DIUPDATE v2.0)

```
unified-patient-mcp/
├── CLAUDE.md                    # file ini
├── README.md                    # dokumentasi publik
├── PRD.md                       # product requirements
├── ARCHITECTURE.md              # system architecture
│
├── main.py                      # entry point — jalankan MCP server
├── server.py                    # inisialisasi FastMCP + register semua tools
│
├── tools/                       # setiap file = satu domain tool
│   ├── __init__.py
│   ├── patient_snapshot.py      # tool 1: get_patient_snapshot
│   ├── active_problems.py       # tool 2: get_active_problems
│   ├── medications.py           # tool 3: get_medication_timeline
│   ├── lab_results.py           # tool 4: get_recent_abnormal_labs
│   ├── deterioration.py         # tool 5: detect_clinical_deterioration_signals
│   ├── context_delta.py         # tool 6: get_patient_context_delta
│   ├── cross_domain_insights.py # tool 7: synthesize_cross_domain_insights ⭐
│   ├── ward_alerts.py           # tool 8: scan_ward_alerts 🆕 PROACTIVE
│   ├── orchestrate.py           # tool 9: orchestrate_context_from_sources 🆕 META
│   └── pattern_insights.py      # tool 10: get_pattern_insights 🆕 MEMORY
│
├── memory/                      # 🆕 Clinical Pattern Memory engine
│   ├── __init__.py
│   ├── store.py                 # ClinicalPatternMemory — in-memory pattern store
│   ├── signature.py             # PatternSignature — hashing clinical patterns
│   ├── matcher.py               # PatternMatcher — find similar past patterns
│   └── models.py                # PatternInsight, PatternRecord Pydantic models
│
├── persona/                     # 🆕 Adaptive Clinical Persona engine
│   ├── __init__.py
│   ├── adapter.py               # PersonaAdapter — transform output by role
│   ├── profiles.py              # RoleProfile definitions per role
│   └── prompts.py               # Role-specific LLM prompt templates
│
├── evidence/                    # 🆕 Confidence-Weighted Evidence Trail engine
│   ├── __init__.py
│   ├── scorer.py                # EvidenceScorer — weight per data source
│   ├── trail.py                 # EvidenceTrail builder
│   └── models.py                # EvidenceItem, EvidenceTrail Pydantic models
│
├── sharp/                       # SHARP Extension Specs integration (WAJIB)
│   ├── __init__.py
│   ├── context.py               # SHARPContext + extract_sharp_context() ✅
│   ├── middleware.py            # SHARP validation middleware ✅
│   └── audit.py                 # Audit trail logging (zero-PII) ✅
│
├── integrations/                # koneksi ke sistem eksternal
│   ├── __init__.py
│   ├── fhir_client.py           # HAPI FHIR R4 client ✅
│   ├── openfda_client.py        # OpenFDA drug interaction client ✅
│   ├── llm_client.py            # Anthropic API client ✅
│   └── mcp_client.py            # 🆕 MCP-to-MCP client untuk Meta-Orchestrator
│
├── engine/                      # rule-based clinical logic
│   ├── __init__.py
│   ├── news2.py                 # NEWS2 scoring ✅
│   ├── mews.py                  # MEWS scoring ✅
│   └── deduplicator.py          # semantic deduplication ✅
│
├── models/                      # Pydantic data models
│   ├── __init__.py
│   ├── patient.py               # PatientSnapshot, ActiveProblem ✅
│   ├── medication.py            # MedicationEntry, InteractionFlag ✅
│   ├── lab.py                   # LabResult, AbnormalLab ✅
│   ├── deterioration.py         # DeteriorationReport ✅
│   └── advanced.py              # 🆕 WardAlert, OrchestratedContext, EvidenceTrail
│
├── tests/
│   ├── __init__.py
│   ├── test_tools.py            # 69 tests sudah pass ✅
│   ├── test_news2.py            # unit tests NEWS2 ✅
│   ├── test_sharp.py            # 19 tests SHARP ✅
│   ├── test_persona.py          # 🆕 unit tests Adaptive Persona
│   ├── test_evidence.py         # 🆕 unit tests Evidence Trail
│   ├── test_ward_alerts.py      # 🆕 unit tests Ward Alerts
│   ├── test_pattern_memory.py   # 🆕 unit tests Clinical Pattern Memory
│   └── fixtures/
│       ├── synthea_patient.json # Eleanor M. Dawson bundle ✅
│       └── test_patients.json   # patient IDs ✅
│
├── scripts/
│   └── seed_synthea.py          # upload Synthea patients ✅
│
├── requirements.txt
├── pyproject.toml
├── .env.example
├── Dockerfile
└── railway.json
```

---

## 🔐 SHARP INTEGRATION (SUDAH SELESAI ✅)

SHARP sudah diimplementasikan dengan 19 test cases passing. Semua tools sudah:

- Mengekstrak SHARP context via `extract_sharp_context(ctx)`
- Memprioritaskan `sharp.patient_id` di atas parameter eksplisit
- Menyertakan `sharp_metadata` di setiap response
- Support `MOCK_SHARP=true` untuk testing lokal

---

## 🆕 4 FITUR ADVANCED (TARGET v2.0)

### FITUR 1: Adaptive Clinical Persona

**File:** `persona/adapter.py`, `persona/profiles.py`, `persona/prompts.py`

Nara bukan hanya mengubah bahasa — ia mengubah **seluruh struktur output** berdasarkan role klinisi.

```
sharp.role = "physician"   → Full clinical reasoning + differential + medical terminology
                              Format: narrative panjang + data lengkap + confidence scores
                              Contoh: "Creatinine elevation of 1.8 mg/dL represents 80%
                                       increase from baseline, temporally correlating with..."

sharp.role = "nurse"       → Actionable summary + tanda monitoring + eskalasi kapan
                              Format: bullet points pendek + threshold angka konkret
                              Contoh: "WATCH: Creatinine rising. Monitor urine output
                                       hourly. Escalate if <30mL/hr."

sharp.role = "pharmacist"  → Medication-focused + interaksi + dosis adjustment
                              Format: drug-centric, interaction severity, renal dosing
                              Contoh: "Metformin CONTRAINDICATED with eGFR <30.
                                       Current creatinine suggests eGFR ~25. Review urgently."

sharp.role = "patient"     → Plain language + no jargon + next steps sederhana
                              Format: FAQ-style, 6th grade reading level
                              Contoh: "Your kidney numbers have gone up recently.
                                       Your doctor will want to check your medicines."
```

**Implementasi:**

```python
# persona/adapter.py
class PersonaAdapter:
    def adapt(self, raw_output: dict, role: str) -> dict:
        profile = RoleProfile.get(role)
        return {
            "content": self._reshape_content(raw_output, profile),
            "format": profile.output_format,      # narrative|bullets|table|simple
            "depth": profile.depth,               # full|summary|medication|simple
            "terminology": profile.terminology,   # medical|nursing|pharmacy|plain
            "persona_applied": role,
            "original_available": True            # physician bisa minta raw jika perlu
        }
```

**Kenapa ini memenangkan AI Factor:**
Rule-based system bisa filter field. Tapi HANYA AI yang bisa mengubah _cara berpikir_ tentang
data yang sama — menyoroti hal berbeda, menggunakan framing berbeda, dan memprioritaskan
tindakan berbeda untuk audience yang berbeda.

---

### FITUR 2: Proactive Ward Alert Tool

**File:** `tools/ward_alerts.py`, `models/advanced.py`

**Tool baru: `scan_ward_alerts(ward_id, threshold, max_patients)`**

Nara tidak hanya menjawab pertanyaan — ia **memindai seluruh ward** dan memberi tahu siapa
yang butuh perhatian segera, tanpa harus ditanya satu per satu.

```
Input:
  ward_id: str          — ID ward/unit di FHIR (misalnya "ICU-A", "Ward-3B")
  threshold: str        — "critical" | "high" | "medium" (default: "high")
  max_patients: int     — maksimal pasien yang discan (default: 20)
  ctx (SHARP)           — session dokter/perawat yang sedang jaga

Output: WardAlertReport
  {
    "ward_id": "ICU-A",
    "scan_timestamp": "2026-05-09T14:30:00Z",
    "patients_scanned": 18,
    "alerts": [
      {
        "patient_id": "synthea-001",
        "patient_name": "Eleanor Dawson",   # hanya diisi jika SHARP authorized
        "alert_level": "critical",
        "primary_signal": "NEWS2=9, rising trend",
        "secondary_signals": ["Creatinine up 80%", "New metformin interaction"],
        "recommended_action": "Immediate clinical review",
        "time_since_last_assessment": "4h 23m",
        "evidence_trail": {...}
      }
    ],
    "summary_narrative": "2 of 18 patients require immediate attention...",
    "persona_applied": "nurse",
    "sharp_metadata": {...}
  }
```

**Implementasi (flow):**

```
scan_ward_alerts(ward_id="ICU-A", threshold="high")
    │
    ▼
[FHIR] GET /Patient?location={ward_id} → list patient IDs
    │
    ▼
[asyncio.gather() — parallel untuk semua pasien]
    ├── detect_deterioration(patient_1) → NEWS2/MEWS
    ├── detect_deterioration(patient_2) → NEWS2/MEWS
    └── ... (max_patients concurrent)
    │
    ▼
[Alert Ranker] sort by risk score descending, filter by threshold
    │
    ▼
[PersonaAdapter] format berdasarkan sharp.role
    (nurse = actionable bullets, physician = clinical detail)
    │
    ▼
[EvidenceTrail] tambahkan confidence weights per alert
    │
    ▼
Return WardAlertReport
```

**Kenapa ini game-changer untuk Impact score:**
Menggeser Nara dari _reactive_ (tunggu pertanyaan) ke _proactive_ (beri peringatan).
Ini menyentuh **workflow shift** — bukan hanya tool baru, tapi paradigma baru dalam
bagaimana klinisi berinteraksi dengan AI di healthcare.

---

### FITUR 3: Confidence-Weighted Evidence Trail

**File:** `evidence/scorer.py`, `evidence/trail.py`, `evidence/models.py`

Setiap insight dari Nara kini dilengkapi **jejak bukti transparan** yang menunjukkan:

- Data apa yang digunakan
- Seberapa besar kontribusi setiap sumber
- Apa yang hilang (data gaps)
- Seberapa yakin Nara dengan output-nya

```python
# evidence/models.py
class EvidenceItem(BaseModel):
    source: str           # "Lab/Creatinine", "Medication/Metformin", "Vitals/HR"
    data_points: int      # jumlah data points yang digunakan
    recency_hours: float  # seberapa baru data ini
    weight: float         # 0.0 - 1.0, kontribusi ke confidence keseluruhan
    quality: str          # "complete" | "partial" | "estimated"
    raw_values: list      # nilai aktual yang dirujuk

class EvidenceTrail(BaseModel):
    overall_confidence: float        # 0.0 - 1.0
    confidence_label: str            # "high" | "moderate" | "low" | "insufficient"
    evidence_items: list[EvidenceItem]
    missing_data: list[str]          # apa yang seharusnya ada tapi tidak
    recommendation_strength: str     # "strong" | "moderate" | "weak" | "insufficient"
    transparency_note: str           # penjelasan plain language kenapa confidence ini
```

**Contoh output Evidence Trail:**

```json
{
  "overall_confidence": 0.74,
  "confidence_label": "moderate",
  "evidence_items": [
    {
      "source": "Lab/Creatinine",
      "data_points": 3,
      "recency_hours": 6.5,
      "weight": 0.85,
      "quality": "complete",
      "raw_values": [1.0, 1.4, 1.8]
    },
    {
      "source": "Medication/Metformin",
      "data_points": 1,
      "recency_hours": 72,
      "weight": 0.72,
      "quality": "complete",
      "raw_values": ["Metformin 500mg, started 3 days ago"]
    },
    {
      "source": "Vitals/UrineOutput",
      "data_points": 2,
      "recency_hours": 12,
      "weight": 0.61,
      "quality": "partial",
      "raw_values": ["35mL/hr", "28mL/hr"]
    }
  ],
  "missing_data": [
    "Baseline creatinine (pre-admission) not in FHIR",
    "eGFR calculation not available"
  ],
  "recommendation_strength": "moderate",
  "transparency_note": "Confidence is moderate because urine output data is incomplete
                         and baseline creatinine is unavailable for comparison."
}
```

**Kenapa ini kritis untuk Feasibility score:**
Juri dari FDA/regulatory background akan langsung menghargai ini. Regulasi FDA 2026
menuntut AI yang transparan dan reproducible. Evidence Trail adalah implementasi
langsung dari prinsip tersebut — sesuatu yang hampir tidak ada submission lain yang pikirkan.

---

### FITUR 5: Clinical Pattern Memory 🆕

**File:** `memory/store.py`, `memory/signature.py`, `memory/matcher.py`, `tools/pattern_insights.py`

**Tool baru: `get_pattern_insights(patient_id, conditions)`**

Ini adalah fitur yang paling membedakan Nara secara fundamental dari semua submission lain.
Seluruh Nara v1.0 dan v2.0 bersifat stateless — setiap call fresh fetch, tidak ada yang diingat.
Pattern Memory menambahkan **lapisan memori anonim session-level** yang menyimpan _pola klinis_,
bukan data pasien. Perbedaan krusial yang tidak bisa diserang dari sisi privasi:

```
Yang TIDAK disimpan:  "Pasien Eleanor punya kreatinin 1.8"   ← PII
Yang DISIMPAN:        hash("creatinine_rise_80pct|new_metformin|urine_decrease")
                      → outcome_seen: "deterioration" (3x dalam session)
```

**Prinsip Privasi yang Tidak Bisa Diserang:**

- Pattern store adalah **in-memory only** — reset setiap server restart
- Kunci store adalah **cryptographic hash** dari kombinasi kondisi klinis, bukan ID pasien
- Tidak ada cara untuk reverse-engineer siapa pasien dari hash tersebut
- Sepenuhnya stateless dari perspektif persistent storage
- Sesuai penuh dengan syarat kompetisi (zero real PHI)

**Flow Kerja Pattern Memory:**

```
Setiap kali Tool 5 atau 7 dijalankan pada pasien:
    │
    ▼
[PatternSignature] ekstrak kondisi klinis → buat signature hash
  conditions = ["creatinine_rise_80pct", "new_metformin", "urine_decrease"]
  signature  = sha256(sorted(conditions).join("|")) → "a3f7b2c1..."
    │
    ▼
[PatternMatcher] cari signature serupa yang sudah pernah disimpan
  → Match found: 2 pola serupa, outcome = "deterioration"
    │
    ▼
[ClinicalPatternMemory.record()] simpan pola baru ke in-memory store
    │
    ▼
[get_pattern_insights()] kembalikan konteks historis session ke agent
```

**Output Tool:**

```json
{
  "current_pattern": {
    "signature": "a3f7b2c1...",
    "conditions": [
      "creatinine_rise_80pct",
      "new_metformin",
      "urine_decreasing"
    ],
    "pattern_label": "Renal stress with nephrotoxic exposure"
  },
  "session_context": {
    "similar_patterns_seen": 3,
    "outcome_distribution": {
      "deterioration_detected": "67%",
      "stable_monitoring": "33%"
    },
    "median_time_to_change_hours": 31,
    "confidence": "low",
    "confidence_note": "Based on 3 session observations only — not a statistical claim"
  },
  "contextual_insight": "This pattern has appeared 3 times this session. In 2 of 3 cases, deterioration was subsequently detected within ~31 hours. Treat as a weak signal requiring clinical judgment.",
  "data_scope": "current_session_only",
  "session_reset_note": "Pattern store resets on server restart. No persistent storage of any kind.",
  "action_required_by": "clinician",
  "ai_generated": true
}
```

**Integrasi ke Tool 7 — Pattern auto-recorded saat synthesis berjalan:**

```python
# Di synthesize_cross_domain_insights(), setelah synthesis selesai:
signature = pattern_signature.create(labs=labs, meds=medications, vitals=vitals)
past_context = pattern_memory.query_similar(signature)
pattern_memory.record(signature, outcome_hint="deterioration_signals_present")
insight.pattern_context = past_context  # null jika belum ada pattern serupa
```

**Kenapa ini Genuinely Irreplaceable:**
Rule engine bisa flag pola pada satu pasien. Tapi HANYA AI + Pattern Memory yang bisa berkata:
_"Pola ini terlihat 3 kali hari ini pada pasien berbeda — ini bukan anomali satu orang,
ini kemungkinan pola ward-level yang perlu perhatian sistemik."_
Ini insight yang hanya muncul dari akumulasi observasi lintas pasien dalam satu shift.

---

### FITUR 4: Meta-Orchestrator Tool

**File:** `tools/orchestrate.py`, `integrations/mcp_client.py`

**Tool baru: `orchestrate_context_from_sources(patient_id, sources)`**

Nara bisa **memanggil MCP server lain** sebagai bagian dari context-building, menjadikannya
satu-satunya submission yang benar-benar mengimplementasikan _interoperabilitas antar MCP servers_
— sesuai tema inti kompetisi: "Build Interoperable Healthcare Agents."

```
Input:
  patient_id: str
  sources: list[str]  — MCP server mana yang diquery
                        ["radiology_mcp", "pharmacy_mcp", "scheduling_mcp"]
  ctx (SHARP)

Output: OrchestratedContext
  {
    "patient_id": "synthea-001",
    "sources_queried": ["nara_core", "radiology_mcp", "pharmacy_mcp"],
    "sources_available": 2,  # dari 3 yang diminta
    "sources_failed": ["scheduling_mcp"],
    "unified_context": {
      "core_data": {...},          # dari Nara tools 1-7
      "radiology_findings": {...}, # dari radiology MCP (jika tersedia)
      "pharmacy_records": {...}    # dari pharmacy MCP (jika tersedia)
    },
    "synthesis": "...",          # AI synthesis dari semua sumber
    "evidence_trail": {...},
    "persona_applied": "physician"
  }
```

**Implementasi MCP Client:**

```python
# integrations/mcp_client.py
class MCPClient:
    """Client untuk memanggil MCP server lain sebagai sub-orchestration."""

    async def call_tool(self, server_url: str, tool_name: str, params: dict) -> dict:
        """
        Panggil tool dari MCP server eksternal via HTTP.
        Graceful failure jika server tidak tersedia.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{server_url}/mcp/tools/{tool_name}",
                    json=params,
                    headers={"Content-Type": "application/json"}
                )
                return response.json()
        except Exception as e:
            return {"error": str(e), "available": False}
```

**Mock servers untuk demo (jika MCP server lain tidak tersedia):**

```python
# Gunakan MOCK_EXTERNAL_MCP=true di .env untuk demo
# Server radiology dan pharmacy di-mock dengan synthetic data
MOCK_RADIOLOGY_FINDINGS = {
    "chest_xray": "No acute cardiopulmonary process",
    "findings_date": "2026-05-08"
}
```

**Kenapa ini differentiating:**
Tema kompetisi adalah **"interoperability"**. Submission lain membuat server yang
menerima panggilan. Nara adalah satu-satunya yang juga **mengorkestrasi** server lain —
menjadikannya true interoperability hub, bukan hanya endpoint.

---

## 🔧 TOOLS LENGKAP NARA v3.0 (12 Tools Total)

| #   | Tool                                             | Status   | Fitur Advanced                                                |
| --- | ------------------------------------------------ | -------- | ------------------------------------------------------------- |
| 1   | `get_patient_snapshot`                           | ✅ Done  | + Persona + Evidence Trail                                    |
| 2   | `get_active_problems`                            | ✅ Done  | + Persona (role-aware prioritization)                         |
| 3   | `get_medication_timeline`                        | ✅ Done  | + Persona + Evidence Trail                                    |
| 4   | `get_recent_abnormal_labs`                       | ✅ Done  | + Evidence Trail                                              |
| 5   | `detect_clinical_deterioration_signals`          | ✅ Done  | + Persona + Evidence Trail + Pattern Record                   |
| 6   | `get_patient_context_delta`                      | ✅ Done  | + Persona                                                     |
| 7   | `synthesize_cross_domain_insights`               | ✅ Done  | + Persona + Evidence Trail + Pattern Record + Pattern Context |
| 8   | `scan_ward_alerts`                               | 🆕 Build | Proactive Alert (Ward-level)                                  |
| 9   | `orchestrate_context_from_sources`               | 🆕 Build | Meta-Orchestrator                                             |
| 10  | `get_pattern_insights`                           | 🆕 Build | Clinical Pattern Memory ⭐⭐                                  |
| 11  | _(persona sudah embedded di semua tools)_        | 🆕 Build | Adaptive Clinical Persona                                     |
| 12  | _(evidence trail sudah embedded di semua tools)_ | 🆕 Build | Evidence Trail                                                |

---

## 🔒 PRINSIP ARSITEKTUR (TIDAK BOLEH DILANGGAR)

1. **Stateless by design** — Zero persistent storage pasien data
2. **AI sebagai explainer, bukan decider** — Rule-based decide, AI explain
3. **Graceful degradation** — Jika apapun gagal, return informative error
4. **FHIR R4 only** — Base URL: https://hapi.fhir.org/baseR4
5. **Zero PII di logs** — Gunakan [PATIENT_REDACTED] di semua logs
6. **Async throughout** — httpx AsyncClient, asyncio.gather untuk parallel calls
7. **Persona transparency** — Selalu sertakan `persona_applied` di response
8. **Evidence transparency** — Selalu sertakan `evidence_trail` di synthesis tools
9. **Pattern privacy** — Pattern Memory hanya simpan hash anonim, TIDAK PERNAH simpan patient_id atau nilai klinis mentah 🆕

---

## 📦 ENVIRONMENT VARIABLES (DIUPDATE)

```
ANTHROPIC_API_KEY=           # wajib — LLM explanations & synthesis
FHIR_BASE_URL=https://hapi.fhir.org/baseR4
OPENFDA_BASE_URL=https://api.fda.gov/drug
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO
MOCK_SHARP=false
MOCK_PATIENT_ID=synthea-demo-patient
MOCK_SHARP_ROLE=physician
MOCK_EXTERNAL_MCP=true       # 🆕 mock radiology/pharmacy MCP untuk demo
WARD_SCAN_MAX_PATIENTS=20    # 🆕 batas scan per ward
EVIDENCE_MIN_DATAPOINTS=2    # 🆕 minimum data points untuk high confidence
PATTERN_MEMORY_ENABLED=true  # 🆕 aktifkan Clinical Pattern Memory
PATTERN_SIMILARITY_THRESHOLD=0.8  # 🆕 minimum similarity untuk pattern match
```

---

## ✅ DEFINITION OF DONE v2.0

**Existing (sudah done):**

- [x] 7 tools berjalan, 69 tests pass
- [x] SHARP integration complete
- [x] Railway deployed & Prompt Opinion registered

**Advanced features (target baru):**

- [ ] `persona/` module complete — adapt() berfungsi untuk 4 roles
- [ ] `evidence/` module complete — EvidenceTrail populated di tools 4,5,7
- [ ] `scan_ward_alerts` tool berfungsi dengan ≥3 synthetic patients
- [ ] `orchestrate_context_from_sources` berfungsi (dengan mock external MCPs)
- [ ] `memory/` module complete — PatternMemory store, signature, matcher berfungsi
- [ ] `get_pattern_insights` tool berfungsi dan pattern terakumulasi saat tool 5 & 7 dijalankan
- [ ] Semua tools 1-7 sudah embed Persona + Evidence Trail
- [ ] Tool 5 & 7 auto-record pattern ke memory saat dijalankan
- [ ] pytest semua advanced tests pass (target: 100+ total tests)
- [ ] Demo video diupdate untuk menampilkan semua 5 fitur advanced

---

## 🎬 SKENARIO DEMO v2.0 (3 MENIT — DIUPDATE)

1. (0:00-0:20) Problem — 36 menit di EHR. Data tersebar. AI tidak tahu siapa yang butuh perhatian.
2. (0:20-0:45) **scan_ward_alerts** → "2 pasien butuh perhatian segera" — PROAKTIF tanpa diminta
3. (0:45-1:15) **synthesize_cross_domain_insights** + **Evidence Trail** →
   "Is creatinine related to metformin?" → AI synthesis + confidence 0.74 + data gaps
4. (1:15-1:40) **get_pattern_insights** — KLIMAKS BARU ⭐ →
   "Pola ini terlihat 3 kali hari ini pada pasien berbeda — kemungkinan pola ward-level"
   Highlight: "Nara belajar dari shift ini tanpa menyimpan satu pun data pasien."
5. (1:40-2:05) **Adaptive Persona** side-by-side →
   Query sama, role physician vs nurse → output berbeda secara fundamental
6. (2:05-2:35) **orchestrate_context_from_sources** →
   Unified context dari 2 MCP servers berbeda dalam satu call
7. (2:35-3:00) Closing — "Nara by NexusHealth. Proactive. Adaptive. Transparent. Pattern-aware."
   Tagline: SHARP-compliant | FHIR R4 | Evidence-based | Multi-MCP | Pattern Memory

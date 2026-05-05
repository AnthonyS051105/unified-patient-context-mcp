# CLAUDE.md — Master Instruction File

# Unified Patient Context MCP Server

# Hackathon: Agents Assemble — The Healthcare AI Endgame (Devpost)

## 🎯 MISI PROYEK

Bangun sebuah MCP (Model Context Protocol) server bernama **"Unified Patient Context Server"** yang menjadi
**"memori hidup" seorang pasien** di ekosistem multi-agent healthcare AI. Server ini mengaggregasi data dari
FHIR EHR, hasil lab, riwayat obat, dan sinyal deteriorasi klinis ke dalam satu living context object yang
bisa di-query oleh agent manapun secara real-time dengan tools yang berbahasa klinis — bukan teknis.

Tujuan akhir: **Memenangkan hackathon Agents Assemble ($7,500 Grand Prize)** dengan solusi yang memenuhi
ketiga kriteria juri: AI Factor, Potential Impact, dan Feasibility.

---

## 📋 KRITERIA JURI (SELALU INGAT INI)

1. **AI Factor** — AI HARUS melakukan sesuatu yang TIDAK BISA dilakukan rule-based software biasa.
   Di proyek ini, AI berperan dalam TIGA cara yang genuinely irreplaceable:
   - **Semantic Entity Resolution**: Mendeteksi bahwa "Metformin HCl 500mg", "Glucophage", dan
     "metformin hydrochloride" adalah obat yang sama — tanpa hardcoded lookup table.
   - **Cross-Domain Clinical Synthesis**: Menghubungkan lab abnormal + perubahan obat + vital signs
     trend secara bersamaan untuk menghasilkan narrative yang koheren — sesuatu yang tidak bisa
     dilakukan oleh query SQL atau rule engine manapun.
   - **Adaptive Context Prioritization**: Menentukan informasi mana yang PALING RELEVAN untuk
     konteks klinis spesifik (triage vs. discharge vs. ICU) menggunakan reasoning, bukan static weights.

2. **Potential Impact** — Solusi menyentuh SETIAP interaksi klinisi-pasien, bukan edge case.
   Dokter menghabiskan 36 menit di EHR per kunjungan 30 menit. Solusi ini memotong waktu itu.

3. **Feasibility** — Semua data dari public APIs (HAPI FHIR, OpenFDA, Synthea). Stateless by design.
   Zero PII. Arsitektur bisa berjalan di healthcare nyata hari ini. SHARP-compliant.

---

## 🏗️ STACK TEKNOLOGI

- **Language:** Python 3.11+
- **MCP Framework:** FastMCP (dari package `mcp`)
- **HTTP Client:** httpx (async)
- **Data Validation:** Pydantic v2
- **FHIR Server:** HAPI FHIR Public Test Server (https://hapi.fhir.org/baseR4)
- **Drug Database:** OpenFDA API (https://api.fda.gov/drug)
- **Synthetic Patients:** Synthea-generated FHIR bundles
- **Clinical Rules:** NEWS2 score + MEWS score (implemented as pure Python, no ML)
- **Transport:** Streamable HTTP (untuk deploy ke Prompt Opinion platform)
- **Deploy:** Railway.app (dari GitHub, free tier)
- **Testing:** pytest + pytest-asyncio
- **Linting:** ruff

---

## 📁 STRUKTUR PROJECT (WAJIB DIIKUTI)

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
│   ├── patient_snapshot.py      # tool: get_patient_snapshot
│   ├── medications.py           # tool: get_medication_timeline
│   ├── lab_results.py           # tool: get_recent_abnormal_labs
│   ├── deterioration.py         # tool: detect_clinical_deterioration_signals
│   ├── context_delta.py         # tool: get_patient_context_delta
│   ├── active_problems.py       # tool: get_active_problems
│   └── cross_domain_insights.py # tool: synthesize_cross_domain_insights ⭐
│
├── sharp/                       # SHARP Extension Specs integration (WAJIB)
│   ├── __init__.py
│   ├── context.py               # SHARPContext dataclass + extract_sharp_context()
│   ├── middleware.py            # SHARP validation middleware
│   └── audit.py                 # Audit trail logging (zero-PII)
│
├── integrations/                # koneksi ke sistem eksternal
│   ├── __init__.py
│   ├── fhir_client.py           # HAPI FHIR R4 client (async httpx)
│   └── openfda_client.py        # OpenFDA drug interaction client (async httpx)
│
├── engine/                      # rule-based clinical logic
│   ├── __init__.py
│   ├── news2.py                 # NEWS2 scoring algorithm
│   ├── mews.py                  # MEWS scoring algorithm
│   └── deduplicator.py          # semantic deduplication logic
│
├── models/                      # Pydantic data models
│   ├── __init__.py
│   ├── patient.py               # PatientSnapshot, ActiveProblem, etc.
│   ├── medication.py            # MedicationEntry, InteractionFlag, etc.
│   ├── lab.py                   # LabResult, AbnormalLab, etc.
│   └── deterioration.py        # DeteriorationSignal, ClinicalScore, etc.
│
├── tests/
│   ├── __init__.py
│   ├── test_tools.py            # integration tests semua tools
│   ├── test_news2.py            # unit tests NEWS2 scoring
│   ├── test_fhir_client.py      # tests FHIR client dengan mock
│   └── fixtures/
│       └── synthea_patient.json # sample Synthea patient bundle
│
├── scripts/
│   └── seed_synthea.py          # upload Synthea patients ke HAPI FHIR
│
├── requirements.txt
├── pyproject.toml
├── .env.example
├── Dockerfile
└── railway.json
```

---

## 🔐 SHARP INTEGRATION (WAJIB — SYARAT KOMPETISI)

SHARP (Structured Healthcare Agent Request Protocol) adalah extension spec dari Prompt Opinion
yang menjembatani EHR session credentials ke dalam konteks MCP. Ini adalah syarat wajib kompetisi
dan harus diimplementasikan dengan benar agar submission tidak didiskualifikasi.

### Apa itu SHARP Context?

Setiap tool call dari Prompt Opinion platform akan membawa SHARP context header berisi:

- `sharp_patient_id` — ID pasien yang sedang aktif di sesi klinisi
- `sharp_ehr_token` — Token autentikasi EHR yang dipropagasi dari sesi klinisi
- `sharp_session_id` — ID sesi untuk audit trail
- `sharp_org_id` — ID organisasi healthcare
- `sharp_role` — Role klinisi yang memanggil (physician, nurse, pharmacist, dst.)

### Cara Mengekstrak SHARP Context di FastMCP

```python
# sharp/context.py — BUAT FILE INI
from dataclasses import dataclass
from typing import Optional

@dataclass
class SHARPContext:
    patient_id: Optional[str] = None
    ehr_token: Optional[str] = None
    session_id: Optional[str] = None
    org_id: Optional[str] = None
    role: Optional[str] = None
    is_present: bool = False

def extract_sharp_context(ctx) -> SHARPContext:
    """
    Ekstrak SHARP context dari MCP request context.
    SHARP headers dipropagasi oleh Prompt Opinion platform secara otomatis.
    Saat testing lokal (MCP Inspector), context akan kosong — ini normal.
    """
    try:
        meta = ctx.request_context.meta if hasattr(ctx, 'request_context') else {}
        sharp = SHARPContext(
            patient_id=meta.get("sharp_patient_id"),
            ehr_token=meta.get("sharp_ehr_token"),
            session_id=meta.get("sharp_session_id"),
            org_id=meta.get("sharp_org_id"),
            role=meta.get("sharp_role"),
            is_present=bool(meta.get("sharp_patient_id"))
        )
        return sharp
    except Exception:
        return SHARPContext()  # Graceful fallback untuk local testing
```

### Cara Menggunakan SHARP Context di Setiap Tool

```python
# Pola standar SEMUA tools — WAJIB diikuti
@mcp.tool()
async def get_patient_snapshot(patient_id: str, ctx=None) -> PatientSnapshot:
    """..."""
    # 1. Ekstrak SHARP context
    sharp = extract_sharp_context(ctx)

    # 2. Prioritaskan patient_id dari SHARP context jika tersedia
    # (Saat berjalan di Prompt Opinion, agent tidak perlu pass patient_id manual)
    effective_patient_id = sharp.patient_id or patient_id

    # 3. Gunakan SHARP token untuk autentikasi FHIR jika tersedia
    fhir_token = sharp.ehr_token  # None saat pakai HAPI public server

    # 4. Log session untuk audit trail (tanpa PII)
    if sharp.session_id:
        logger.info(f"Tool call via SHARP session [REDACTED] for role: {sharp.role}")

    # 5. Jalankan logika tool seperti biasa
    result = await fhir_client.get_patient_bundle(
        effective_patient_id,
        auth_token=fhir_token
    )
    # ...
```

### SHARP Context dalam Output Response

Setiap tool response HARUS menyertakan SHARP metadata:

```python
# Tambahkan ke semua Pydantic response models
class SHARPMetadata(BaseModel):
    session_id: Optional[str] = None
    org_id: Optional[str] = None
    role_context: Optional[str] = None
    sharp_propagated: bool = False  # True jika request datang via Prompt Opinion

# Semua response models inherit dari base ini:
class BaseToolResponse(BaseModel):
    sharp_metadata: SHARPMetadata = SHARPMetadata()
    data_timestamp: str  # ISO 8601
    server_version: str = "1.0.0"
```

### Testing SHARP Integration

Saat testing lokal dengan MCP Inspector, SHARP context tidak tersedia — ini normal.
Gunakan environment variable `MOCK_SHARP=true` untuk simulasi SHARP context di dev:

```python
# Tambahkan ke extract_sharp_context()
if os.getenv("MOCK_SHARP") == "true":
    return SHARPContext(
        patient_id=os.getenv("MOCK_PATIENT_ID", "synthea-001"),
        role="physician",
        session_id="dev-session-001",
        org_id="test-org",
        is_present=True
    )
```

### Struktur Folder Tambahan untuk SHARP

```
unified-patient-mcp/
├── sharp/
│   ├── __init__.py
│   ├── context.py       # SHARPContext dataclass + extract_sharp_context()
│   ├── middleware.py    # SHARP validation middleware
│   └── audit.py        # Audit trail logging (zero-PII)
```

---

## 🔧 7 MCP TOOLS YANG HARUS DIBUAT (DIUPDATE)

### Tool 1: `get_patient_snapshot`

```
Input:  patient_id: str, ctx (SHARP context auto-injected)
Output: PatientSnapshot — nama, usia, jenis kelamin, kondisi aktif,
        obat aktif, alergi, last_updated, data_sources, sharp_metadata
Sumber: HAPI FHIR (Patient + Condition + MedicationRequest + AllergyIntolerance)
AI role: Generate 1-sentence plain language summary dari kondisi pasien
SHARP:  Gunakan sharp.patient_id sebagai effective_patient_id jika tersedia
```

### Tool 2: `get_active_problems`

```
Input:  patient_id: str, include_resolved: bool = False, ctx (SHARP)
Output: List[ActiveProblem] — kondisi klinis aktif dengan onset date,
        severity, dan status
Sumber: HAPI FHIR Condition resource
AI role: Prioritize problems by clinical urgency menggunakan LLM reasoning
         (bukan static weight — ini yang membedakan dari rule-based system)
SHARP:  Role klinisi dari sharp.role mempengaruhi prioritization angle
        (physician fokus diagnosis, nurse fokus monitoring, pharmacist fokus obat)
```

### Tool 3: `get_medication_timeline`

```
Input:  patient_id: str, days: int = 90, ctx (SHARP)
Output: List[MedicationEntry] dengan flag interaksi dari OpenFDA
Sumber: HAPI FHIR MedicationRequest + OpenFDA drug interaction API
AI role: Semantic entity resolution — deteksi brand/generic same drug via LLM
         + plain-language explanation setiap interaksi berbahaya
SHARP:  sharp.role="pharmacist" → lebih detail di interaction explanation
```

### Tool 4: `get_recent_abnormal_labs`

```
Input:  patient_id: str, days: int = 30, threshold: str = "abnormal", ctx (SHARP)
Output: List[AbnormalLab] dengan nilai, reference range, dan trend
Sumber: HAPI FHIR Observation (category=laboratory)
AI role: Explain clinical significance dalam 1-2 kalimat per lab
SHARP:  patient_id dari context jika tidak di-pass eksplisit
```

### Tool 5: `detect_clinical_deterioration_signals`

```
Input:  patient_id: str, hours_lookback: int = 72, ctx (SHARP)
Output: DeteriorationReport — NEWS2 score, MEWS score, triggered_rules,
        trend_analysis, recommendation, confidence="rule-based"
Sumber: HAPI FHIR Observation (vital signs) dalam window waktu tertentu
AI role: Generate natural language explanation dari rules yang ter-trigger
PENTING: AI TIDAK predict. Rule engine yang decide. AI yang explain.
Output harus selalu include: "action_required_by": "clinician"
SHARP:  sharp.role mempengaruhi bahasa output (lebih teknis untuk physician,
        lebih actionable untuk nurse)
```

### Tool 6: `get_patient_context_delta`

```
Input:  patient_id: str, since_hours: int = 48, ctx (SHARP)
Output: ContextDelta — apa yang berubah dalam N jam terakhir:
        new_labs, changed_medications, new_vitals, new_conditions
Sumber: HAPI FHIR (semua resource dengan lastUpdated filter)
AI role: Summarize delta dalam narrative "Dalam 48 jam terakhir, ..."
SHARP:  session_id untuk audit trail perubahan
```

### Tool 7: `synthesize_cross_domain_insights` ⭐ (AI FACTOR UTAMA)

```
Input:  patient_id: str, clinical_question: str, ctx (SHARP)
        Contoh clinical_question: "Is this patient safe for discharge?"
                                  "What is driving the elevated creatinine?"
                                  "Should we adjust the insulin dose?"

Output: ClinicalInsight — narrative synthesis yang menghubungkan:
        - Lab trends + medication changes + vital patterns SECARA BERSAMAAN
        - Jawaban terhadap clinical_question berdasarkan data aktual
        - Confidence level + data gaps yang perlu diisi klinisi
        - Flag: "action_required_by": "clinician" selalu ada

Kenapa ini TIDAK BISA dilakukan rule-based software:
  Rule engine bisa flag "creatinine high" dan "metformin prescribed" secara terpisah.
  Tapi HANYA AI yang bisa menghubungkan: "Creatinine naik 40% dalam 48 jam,
  bersamaan dengan dimulainya metformin 3 hari lalu, dan urine output menurun
  berdasarkan vital signs — ini pola AKI yang perlu evaluasi segera."

AI role: Cross-domain synthesis menggunakan semua tools lain sebagai sub-calls,
         lalu reasoning over combined context untuk jawab clinical_question
SHARP:  sharp.role critical — physician dapat full synthesis, nurse dapat
        actionable summary saja, pharmacist dapat medication-focused synthesis
```

---

## 🔒 PRINSIP ARSITEKTUR (TIDAK BOLEH DILANGGAR)

1. **Stateless by design** — Server TIDAK menyimpan state pasien apapun. Setiap tool call
   adalah fresh fetch dari sumber data. Tidak ada database lokal pasien.

2. **AI sebagai explainer, bukan decider** — Semua keputusan klinis dari rule-based engine.
   LLM hanya dipanggil untuk generate natural language output. Selalu ada flag
   `"ai_generated": true` dan `"confidence": "rule-based"` di output yang relevan.

3. **Graceful degradation** — Jika FHIR server tidak bisa diakses, return error yang informatif
   dengan `"suggestion"` field. Jangan crash.

4. **FHIR R4 only** — Gunakan HAPI FHIR public test server. Base URL: https://hapi.fhir.org/baseR4
   Semua resource menggunakan FHIR R4 format.

5. **Zero PII di logs** — Jangan pernah log patient_id atau data klinis ke stdout/stderr.
   Gunakan placeholder seperti `[PATIENT_REDACTED]` jika perlu log.

6. **Async throughout** — Semua network calls menggunakan httpx AsyncClient. Jangan pakai
   requests library (blocking).

---

## 🤖 CARA MEMANGGIL LLM DARI DALAM TOOLS

Untuk generate natural language explanation, gunakan Anthropic API langsung:

```python
import httpx
import os

async def generate_clinical_explanation(context: dict, prompt_template: str) -> str:
    """Panggil Claude untuk generate plain-language clinical explanation."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",  # gunakan Haiku untuk speed + cost
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt_template.format(**context)}]
            },
            timeout=10.0
        )
        data = response.json()
        return data["content"][0]["text"]
```

Gunakan `claude-haiku-4-5-20251001` untuk semua LLM calls — cukup cerdas untuk explanation,
jauh lebih cepat dan murah dari Sonnet/Opus.

---

## 🧪 SYNTHEA TEST DATA

Gunakan script `scripts/seed_synthea.py` untuk upload synthetic patients ke HAPI FHIR.
Download Synthea bundles dari: https://synthea.mitre.org/downloads
Pilih "100 Sample Synthetic Patient Records, FHIR R4" (file: synthea_sample_data_fhir_r4.zip)

Patient IDs yang dipakai untuk testing harus didokumentasikan di `tests/fixtures/README.md`
setelah seeding berhasil.

---

## 🚀 CARA MENJALANKAN

```bash
# Development
pip install -r requirements.txt
cp .env.example .env
# isi ANTHROPIC_API_KEY di .env
python main.py

# Test dengan MCP Inspector
npx @modelcontextprotocol/inspector python main.py

# Run tests
pytest tests/ -v

# Deploy ke Railway
railway login
railway init
railway up
```

---

## 📦 ENVIRONMENT VARIABLES

```
ANTHROPIC_API_KEY=        # wajib — untuk LLM explanations & AI synthesis
FHIR_BASE_URL=https://hapi.fhir.org/baseR4   # bisa diganti FHIR server lain
OPENFDA_BASE_URL=https://api.fda.gov/drug
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO
MOCK_SHARP=false          # set true untuk simulasi SHARP context di dev/testing
MOCK_PATIENT_ID=synthea-001  # patient ID untuk MOCK_SHARP mode
```

---

## ✅ DEFINITION OF DONE

Project dianggap selesai jika:

- [ ] Semua 7 tools berjalan tanpa error dengan Synthea test patients
- [ ] `detect_clinical_deterioration_signals` menghasilkan NEWS2 score yang benar
- [ ] `get_medication_timeline` mendeteksi drug interaction via OpenFDA
- [ ] `synthesize_cross_domain_insights` menghasilkan narrative yang koheren untuk clinical question
- [ ] SHARP context diekstrak dengan benar (dengan graceful fallback saat tidak ada)
- [ ] Semua tools propagate SHARP metadata di response output
- [ ] Semua tools terdaftar di MCP Inspector dan bisa di-invoke
- [ ] Server bisa dijalankan via HTTP transport (bukan hanya stdio)
- [ ] README.md lengkap dengan cara setup dan contoh output setiap tool
- [ ] Dockerfile berfungsi untuk deploy
- [ ] pytest menjalankan minimal 12 test cases dan semua pass

---

## 🎬 SKENARIO DEMO (3 MENIT)

Untuk video submission hackathon — tampilkan di dalam Prompt Opinion platform:

1. (0:00-0:30) Problem statement — dokter menghabiskan 36 menit di EHR per kunjungan 30 menit.
   Tampilkan statistik nyata ini di layar.
2. (0:30-1:00) Demo: Agent memanggil `get_patient_snapshot` via Prompt Opinion →
   SHARP context auto-inject patient ID → full context dalam 2 detik.
   Highlight: "Agent tidak perlu tahu FHIR exists."
3. (1:00-1:40) Demo: `detect_clinical_deterioration_signals` → NEWS2=7 (High Risk) →
   AI generates narrative explanation → "action_required_by: clinician"
4. (1:40-2:15) Demo: `synthesize_cross_domain_insights` dengan clinical_question:
   "Is the elevated creatinine related to the new medication?" →
   AI cross-references lab trend + medication timeline + vitals →
   Narrative synthesis yang tidak bisa dilakukan query SQL manapun.
   Ini adalah KLIMAKS demo — paling differentiating.
5. (2:15-2:45) Demo: `get_medication_timeline` → drug interaction detected →
   plain language warning untuk klinisi.
6. (2:45-3:00) Closing — "Satu MCP server. Tujuh tools. Konteks penuh. Untuk semua agent."
   Tampilkan: SHARP-compliant | FHIR R4 | Stateless | Privacy-safe

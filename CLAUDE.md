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
1. **AI Factor** — AI digunakan untuk semantic deduplication + natural language explanation. AI TIDAK
   mendiagnosis. Rule-based engine (NEWS2/MEWS) yang trigger alert, AI yang explain.
2. **Potential Impact** — Solusi menyentuh SETIAP interaksi klinisi-pasien, bukan edge case.
3. **Feasibility** — Semua data dari public APIs (HAPI FHIR, OpenFDA, Synthea). Stateless by design.
   Zero PII. Arsitektur bisa berjalan di healthcare nyata hari ini.

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
│   └── active_problems.py       # tool: get_active_problems
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

## 🔧 6 MCP TOOLS YANG HARUS DIBUAT

### Tool 1: `get_patient_snapshot`
```
Input:  patient_id: str
Output: PatientSnapshot — nama, usia, jenis kelamin, kondisi aktif,
        obat aktif, alergi, last_updated, data_sources
Sumber: HAPI FHIR (Patient + Condition + MedicationRequest + AllergyIntolerance)
AI role: Generate 1-sentence plain language summary dari kondisi pasien
```

### Tool 2: `get_active_problems`
```
Input:  patient_id: str, include_resolved: bool = False
Output: List[ActiveProblem] — kondisi klinis aktif dengan onset date,
        severity, dan status
Sumber: HAPI FHIR Condition resource
AI role: Prioritize problems by clinical urgency (gunakan LLM scoring)
```

### Tool 3: `get_medication_timeline`
```
Input:  patient_id: str, days: int = 90
Output: List[MedicationEntry] dengan flag interaksi dari OpenFDA
Sumber: HAPI FHIR MedicationRequest + OpenFDA drug interaction API
AI role: Generate plain-language explanation jika ada interaksi berbahaya
Dedup:  Obat yang sama tapi nama berbeda (brand vs generic) di-merge
```

### Tool 4: `get_recent_abnormal_labs`
```
Input:  patient_id: str, days: int = 30, threshold: str = "abnormal"
        threshold options: "critical" | "abnormal" | "borderline"
Output: List[AbnormalLab] dengan nilai, reference range, dan trend
Sumber: HAPI FHIR Observation (category=laboratory)
AI role: Explain clinical significance dalam 1-2 kalimat per lab
```

### Tool 5: `detect_clinical_deterioration_signals`
```
Input:  patient_id: str, hours_lookback: int = 72
Output: DeteriorationReport — NEWS2 score, MEWS score, triggered_rules,
        trend_analysis, recommendation, confidence="rule-based"
Sumber: HAPI FHIR Observation (vital signs) dalam window waktu tertentu
AI role: Generate natural language explanation dari rules yang ter-trigger
PENTING: AI TIDAK predict. Rule engine yang decide. AI yang explain.
Output harus selalu include: "action_required_by": "clinician"
```

### Tool 6: `get_patient_context_delta`
```
Input:  patient_id: str, since_hours: int = 48
Output: ContextDelta — apa yang berubah dalam N jam terakhir:
        new_labs, changed_medications, new_vitals, new_conditions
Sumber: HAPI FHIR (semua resource dengan lastUpdated filter)
AI role: Summarize delta dalam narrative "Dalam 48 jam terakhir, ..."
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
ANTHROPIC_API_KEY=        # wajib — untuk LLM explanations
FHIR_BASE_URL=https://hapi.fhir.org/baseR4   # bisa diganti FHIR server lain
OPENFDA_BASE_URL=https://api.fda.gov/drug
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO
```

---

## ✅ DEFINITION OF DONE

Project dianggap selesai jika:
- [ ] Semua 6 tools berjalan tanpa error dengan Synthea test patients
- [ ] `detect_clinical_deterioration_signals` menghasilkan NEWS2 score yang benar
- [ ] `get_medication_timeline` mendeteksi drug interaction via OpenFDA
- [ ] Semua tools terdaftar di MCP Inspector dan bisa di-invoke
- [ ] Server bisa dijalankan via HTTP transport (bukan hanya stdio)
- [ ] README.md lengkap dengan cara setup dan contoh output setiap tool
- [ ] Dockerfile berfungsi untuk deploy
- [ ] pytest menjalankan minimal 10 test cases dan semua pass

---

## 🎬 SKENARIO DEMO (3 MENIT)

Untuk video submission hackathon:
1. (0:00-0:30) Problem statement — fragmented patient data, klinisi berpindah 10 sistem
2. (0:30-1:30) Demo: Agent memanggil `get_patient_snapshot` → full context dalam 2 detik
3. (1:30-2:15) Demo: `detect_clinical_deterioration_signals` → NEWS2 alert + AI explanation
4. (2:15-2:45) Demo: `get_medication_timeline` → drug interaction detected + plain language warning
5. (2:45-3:00) Closing — "Satu MCP server, konteks penuh, untuk semua agent di ekosistem"

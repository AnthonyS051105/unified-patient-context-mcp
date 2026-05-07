# SPRINT_PLAN.md — Execution Roadmap

# Nara by NexusHealth — Unified Patient Context MCP Server

# Version: 2.0 — Advanced Features Edition

## Instruksi untuk Claude Code

Baca CLAUDE.md, PRD.md, dan ARCHITECTURE.md terlebih dahulu sebelum memulai.
Phase 1-4 sudah SELESAI. Mulai langsung dari Phase 5.
Jangan sentuh kode yang sudah berjalan kecuali untuk menambahkan integrasi baru.
Jalankan `pytest tests/ -v` sebelum dan sesudah setiap sub-task untuk pastikan tidak ada regresi.

---

## STATUS EXISTING (SUDAH SELESAI ✅)

### PHASE 1: Foundation — ✅ SELESAI

- [x] Project setup, requirements.txt, pyproject.toml, Dockerfile, railway.json
- [x] SHARP integration (19 tests pass): context.py, middleware.py, audit.py
- [x] Pydantic models: patient.py, medication.py, lab.py, deterioration.py
- [x] FHIR client (hapi.fhir.org/baseR4 verified live)
- [x] OpenFDA client
- [x] LLM client (Anthropic API)
- [x] NEWS2 + MEWS engines
- [x] Deduplicator (50+ brand→generic mappings)

### PHASE 2: Core Tools — ✅ SELESAI

- [x] Tool 1: get_patient_snapshot
- [x] Tool 2: get_active_problems
- [x] Tool 3: get_medication_timeline
- [x] Tool 4: get_recent_abnormal_labs

### PHASE 3: Intelligence Layer — ✅ SELESAI

- [x] Tool 5: detect_clinical_deterioration_signals (NEWS2 + MEWS)
- [x] Tool 6: get_patient_context_delta
- [x] Tool 7: synthesize_cross_domain_insights ⭐

### PHASE 4: Deploy & Polish — ✅ SEBAGIAN SELESAI

- [x] README.md lengkap
- [x] Synthea patient (Eleanor M. Dawson) di HAPI FHIR
- [x] Railway deployment: https://amiable-determination-production.up.railway.app
- [x] Prompt Opinion: org NexusHealth, server registered, 7 tools detected
- [x] End-to-end test 7/7 tools PASS
- [x] 69 tests total pass
- [ ] Demo video (belum direkam — tunggu Phase 5-6 selesai)
- [ ] Publish ke Marketplace (butuh Publisher Profile)

---

## PHASE 5: Advanced Features 🆕 (Target: 3 Hari)

### ⚠️ PRIORITAS EKSEKUSI

Karena deadline 11 Mei sangat dekat, urutan prioritas:

1. **Evidence Trail** — paling cepat diimplementasi, impact besar di AI Factor
2. **Adaptive Persona** — high value, moderate effort
3. **Ward Alerts** — high impact, moderate effort
4. **Meta-Orchestrator** — jika waktu mencukupi

---

### PHASE 5.1 — Evidence Trail Engine (Hari 1, Prioritas #1)

**Target: evidence/ module selesai + terintegrasi ke tools 5, 7**

#### Step 1: Buat `models/advanced.py`

Tambahkan Pydantic models baru (jangan hapus models lama):

```python
# Tambahkan ke models/advanced.py:
# - EvidenceItem
# - EvidenceTrail
# - PatientAlert
# - WardAlertReport
# - ExternalSourceResult
# - OrchestratedContext
```

Lihat ARCHITECTURE.md section "Pydantic Models Baru" untuk definisi lengkap.

#### Step 2: Buat `evidence/` module

```
evidence/
├── __init__.py
├── scorer.py    # EvidenceScorer class
├── trail.py     # EvidenceTrail builder helpers
└── models.py    # re-export dari models/advanced.py
```

**`evidence/scorer.py` — implementasi:**

```python
class EvidenceScorer:
    def score(self, data_sources: list) -> EvidenceTrail:
        # Hitung weight per source:
        # recency_score = max(0, 1 - (recency_hours / 168))  # decay 1 minggu
        # completeness_score = min(1, data_points / 5)        # max di 5 points
        # quality_score = {"complete":1.0, "partial":0.6, "estimated":0.3}[quality]
        # weight = (recency*0.4) + (completeness*0.4) + (quality*0.2)
        #
        # overall_confidence = weighted average semua weights
        # confidence_label: >0.8=high, 0.5-0.8=moderate, <0.5=low
        pass

    def _find_gaps(self, sources: list) -> list[str]:
        # Deteksi data yang seharusnya ada tapi tidak tersedia
        # Contoh: jika tidak ada urine output, tambahkan ke missing_data
        pass
```

#### Step 3: Integrasi ke Tool 5 (`tools/deterioration.py`)

Tambahkan evidence trail ke output DeteriorationReport:

```python
# Di akhir detect_clinical_deterioration_signals():
data_sources = [
    DataSource("Vitals/HeartRate", hr_values, recency_h, "complete"),
    DataSource("Vitals/SpO2", spo2_values, recency_h, "complete"),
    # ... semua vital signs yang berhasil diambil
]
evidence = evidence_scorer.score(data_sources)
report.evidence_trail = evidence
```

#### Step 4: Integrasi ke Tool 7 (`tools/cross_domain_insights.py`)

Tambahkan evidence trail ke ClinicalInsight output:

```python
# Di synthesize_cross_domain_insights():
data_sources = [
    DataSource("Lab", lab_values, lab_recency, lab_quality),
    DataSource("Medication", med_values, med_recency, "complete"),
    DataSource("Vitals", vital_values, vital_recency, vital_quality),
]
evidence = evidence_scorer.score(data_sources)
insight.evidence_trail = evidence
```

#### Step 5: Tulis tests `tests/test_evidence.py`

```python
# Minimal test scenarios:
def test_high_confidence_complete_recent_data():
    # 5 data points, <6h old, complete → confidence >0.8

def test_low_confidence_sparse_old_data():
    # 1 data point, >120h old, estimated → confidence <0.5

def test_missing_data_detection():
    # source tanpa urine_output → "urine output" ada di missing_data

def test_transparency_note_generated():
    # moderate confidence → transparency_note tidak kosong
```

**Verifikasi Phase 5.1 selesai:**

```bash
pytest tests/test_evidence.py -v  # semua pass
pytest tests/ -v  # tidak ada regresi (tetap 69+ pass)
```

---

### PHASE 5.2 — Adaptive Clinical Persona (Hari 1-2, Prioritas #2)

**Target: persona/ module selesai + terintegrasi ke SEMUA tools**

#### Step 1: Buat `persona/` module

```
persona/
├── __init__.py
├── profiles.py    # RoleConfig dan RoleProfile definitions
├── adapter.py     # PersonaAdapter class
└── prompts.py     # LLM prompt templates per role
```

**`persona/profiles.py`:**

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class RoleConfig:
    format: Literal["narrative", "bullets", "structured", "simple"]
    depth: Literal["full", "summary", "medication-focused", "simplified"]
    terminology: Literal["medical", "nursing", "pharmacy", "plain"]
    priority_fields: list[str]
    max_length: int | None

class RoleProfile:
    PROFILES = {
        "physician": RoleConfig(
            format="narrative",
            depth="full",
            terminology="medical",
            priority_fields=["clinical_reasoning", "differential", "raw_values", "evidence"],
            max_length=None
        ),
        "nurse": RoleConfig(
            format="bullets",
            depth="summary",
            terminology="nursing",
            priority_fields=["monitoring_thresholds", "escalation_triggers", "immediate_actions"],
            max_length=300
        ),
        "pharmacist": RoleConfig(
            format="structured",
            depth="medication-focused",
            terminology="pharmacy",
            priority_fields=["drug_interactions", "renal_dosing", "contraindications", "alternatives"],
            max_length=400
        ),
        "patient": RoleConfig(
            format="simple",
            depth="simplified",
            terminology="plain",
            priority_fields=["what_is_happening", "next_steps", "questions_for_doctor"],
            max_length=200
        )
    }

    @classmethod
    def get(cls, role: str) -> RoleConfig:
        return cls.PROFILES.get(role.lower(), cls.PROFILES["physician"])
```

**`persona/prompts.py` — prompt templates:**

```python
PERSONA_PROMPTS = {
    "physician": """
You are adapting clinical information for a physician.
Use full medical terminology. Include clinical reasoning and differential.
Show all data including raw values. Be comprehensive.
Clinical data: {data}
Adapt this for a physician:""",

    "nurse": """
You are adapting clinical information for a bedside nurse.
Use clear nursing language. Focus on:
- What to MONITOR (with specific numbers/thresholds)
- When to ESCALATE (specific triggers)
- What ACTION to take NOW
Keep it under 300 words. Use bullet points.
Clinical data: {data}
Adapt this for a nurse:""",

    "pharmacist": """
You are adapting clinical information for a clinical pharmacist.
Focus on:
- Drug interactions (severity: major/moderate/minor)
- Renal dosing adjustments needed
- Contraindications based on current labs
- Alternative medications if needed
Clinical data: {data}
Adapt this for a pharmacist:""",

    "patient": """
You are adapting clinical information for a patient.
Rules:
- Use 6th grade reading level (no medical jargon)
- Explain WHAT is happening in simple terms
- Tell them WHAT WILL HAPPEN NEXT
- Give them QUESTIONS to ask their doctor
- Be reassuring but honest
- Maximum 200 words
Clinical data: {data}
Adapt this for a patient:"""
}
```

**`persona/adapter.py`:**

```python
class PersonaAdapter:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def adapt(self, raw_output: dict, role: str) -> dict:
        if not role or role not in RoleProfile.PROFILES:
            role = "physician"

        profile = RoleProfile.get(role)
        prompt = PERSONA_PROMPTS[role].format(data=str(raw_output))

        adapted = await self.llm.explain(
            prompt=prompt,
            max_tokens=profile.max_length or 600
        )

        return {
            **raw_output,
            "content_adapted": adapted,
            "persona_applied": role,
            "persona_format": profile.format,
            "persona_depth": profile.depth,
            "original_available": True
        }
```

#### Step 2: Integrasi Persona ke semua 7 tools yang sudah ada

Pola integrasi yang sama untuk SETIAP tool:

```python
# Di akhir setiap tool handler:
if sharp.role:  # hanya adapt jika role diketahui
    output = await persona_adapter.adapt(output.model_dump(), sharp.role)
    return EnhancedOutput(**output)
return output
```

**Urutan integrasi (dari yang paling impactful):**

1. Tool 7 (`cross_domain_insights.py`) — synthesis, paling terlihat
2. Tool 5 (`deterioration.py`) — clinical urgency, nurse-critical
3. Tool 1 (`patient_snapshot.py`) — first impression
4. Tool 3 (`medications.py`) — pharmacist-critical
5. Tool 2, 4, 6 — complete coverage

#### Step 3: Tulis tests `tests/test_persona.py`

```python
@pytest.mark.asyncio
async def test_physician_gets_full_narrative():
    # output physician = narrative panjang dengan medical terms

@pytest.mark.asyncio
async def test_nurse_gets_actionable_bullets():
    # output nurse mengandung bullet points dan thresholds angka

@pytest.mark.asyncio
async def test_pharmacist_gets_medication_focus():
    # output pharmacist menyebutkan interaction/renal dosing

@pytest.mark.asyncio
async def test_patient_gets_plain_language():
    # output patient tidak ada kata-kata medis sulit

@pytest.mark.asyncio
async def test_unknown_role_defaults_to_physician():
    # role=None atau role="unknown" → default physician

def test_persona_applied_always_in_response():
    # persona_applied field selalu ada di response
```

**Verifikasi Phase 5.2 selesai:**

```bash
pytest tests/test_persona.py -v  # semua pass
pytest tests/ -v  # tidak ada regresi
```

---

### PHASE 5.3 — Proactive Ward Alert Tool (Hari 2, Prioritas #3)

**Target: `scan_ward_alerts` tool berfungsi dengan synthetic patients**

#### Step 1: Tambahkan FHIR method untuk ward queries

Di `integrations/fhir_client.py`, tambahkan:

```python
async def get_patients_by_location(self, ward_id: str, max_count: int = 20) -> list:
    """
    Get all patients in a ward/location.
    Uses FHIR Patient?_has:Encounter:patient:location={ward_id}
    atau simulasi dengan Patient?_count={max_count} jika location filter tidak tersedia.
    """
    # Coba location-based query dulu
    # Fallback: ambil N patients dan filter manually
    # Untuk demo: return synthetic patients dari test_patients.json
    pass
```

**Fallback untuk demo (jika FHIR location query tidak bisa):**

```python
# Jika ward_id tidak dikenali, gunakan semua patients dari fixtures
# Ini acceptable untuk demo karena kita demonstrasikan konsep, bukan real EHR
DEMO_WARD_PATIENTS = {
    "ICU-A": ["synthea-demo-patient"],  # Eleanor Dawson
    # Tambah 2-3 patient lagi dengan skenario berbeda untuk demo
}
```

#### Step 2: Buat minimal 3 synthetic patients dengan skenario berbeda

Di `scripts/seed_additional_patients.py`:

```python
# Patient 2: High NEWS2 (critical) — untuk trigger critical alert
# Patient 3: Medium NEWS2 — untuk baseline comparison
# Upload ke HAPI FHIR dan simpan IDs ke test_patients.json
```

#### Step 3: Buat `tools/ward_alerts.py`

Implementasi `scan_ward_alerts` sesuai spec di ARCHITECTURE.md section "Flow: scan_ward_alerts".

Key points:

- asyncio.gather untuk parallel scan (critical untuk performance)
- timeout per patient: 3 detik (jangan block karena satu patient)
- Evidence Trail per alert (reuse evidence_scorer dari Phase 5.1)
- Persona Adapter untuk summary (default: nurse)

#### Step 4: Register tool di `server.py`

```python
from tools.ward_alerts import scan_ward_alerts
```

#### Step 5: Tulis `tests/test_ward_alerts.py`

```python
@pytest.mark.asyncio
async def test_scan_returns_prioritized_alerts():
    # mock 3 patients: NEWS2=9, NEWS2=4, NEWS2=7
    # threshold="high" → return 2 alerts (NEWS2>=5)
    # urutan: NEWS2=9 dulu, NEWS2=7 kedua

@pytest.mark.asyncio
async def test_scan_applies_persona_to_summary():
    # SHARP role="nurse" → summary format bullets

@pytest.mark.asyncio
async def test_scan_handles_empty_ward():
    # ward kosong → no_alerts_found=true, bukan error

@pytest.mark.asyncio
async def test_scan_respects_max_patients_limit():
    # max_patients=5, ward punya 10 → hanya 5 yang discan

@pytest.mark.asyncio
async def test_each_alert_has_evidence_trail():
    # setiap PatientAlert.evidence_trail tidak None
```

**Verifikasi Phase 5.3 selesai:**

```bash
pytest tests/test_ward_alerts.py -v
pytest tests/ -v  # regresi check
# MCP Inspector: scan_ward_alerts terlihat sebagai tool ke-8
```

---

### PHASE 5.4 — Meta-Orchestrator (Hari 3, Prioritas #4)

**Target: `orchestrate_context_from_sources` berfungsi dengan mock external MCPs**

#### Step 1: Buat `integrations/mcp_client.py`

Implementasi MCPClient dengan mock support.
Lihat ARCHITECTURE.md section "Layer 3: Integration Layer" untuk kode lengkap.

#### Step 2: Tambahkan env vars ke `.env.example`

```
MOCK_EXTERNAL_MCP=true
MCP_URL_RADIOLOGY_MCP=  # kosong = gunakan mock
MCP_URL_PHARMACY_MCP=   # kosong = gunakan mock
```

#### Step 3: Buat `tools/orchestrate.py`

Implementasi `orchestrate_context_from_sources` sesuai ARCHITECTURE.md.

Penting:

- Semua external calls via asyncio.gather (parallel)
- Setiap failed external call → masuk ke `sources_failed`, bukan error
- Synthesis LLM tetap berjalan meski ada sources yang gagal
- Evidence Trail mencakup semua sources (termasuk mock data)

#### Step 4: Register tool di `server.py`

```python
from tools.orchestrate import orchestrate_context_from_sources
```

#### Step 5: Tulis `tests/test_orchestrate.py`

```python
@pytest.mark.asyncio
async def test_orchestrate_with_mock_servers():
    # MOCK_EXTERNAL_MCP=true
    # sources=["nara_core","radiology_mcp","pharmacy_mcp"]
    # → sources_available=3, unified_context punya semua data

@pytest.mark.asyncio
async def test_orchestrate_graceful_with_unavailable_server():
    # sources=["nara_core","nonexistent_mcp"]
    # → sources_failed=["nonexistent_mcp"], tapi tetap return hasil

@pytest.mark.asyncio
async def test_orchestrate_synthesis_includes_all_sources():
    # synthesis narrative menyebut data dari semua sources yang available

@pytest.mark.asyncio
async def test_orchestrate_evidence_trail_includes_external_sources():
    # evidence_trail.evidence_items include radiology dan pharmacy source
```

**Verifikasi Phase 5.4 selesai:**

```bash
pytest tests/test_orchestrate.py -v
pytest tests/ -v  # target: 90+ tests pass
# MCP Inspector: 9 tools terlihat
```

---

## PHASE 6: Integration, Polish & Demo (Hari 4-5)

### Phase 6.1 — Full Integration Test

```bash
# 1. Jalankan server lokal
MOCK_SHARP=true MOCK_PATIENT_ID=synthea-demo-patient MOCK_SHARP_ROLE=physician \
MOCK_EXTERNAL_MCP=true python main.py

# 2. MCP Inspector — verify semua 9 tools (atau 11 jika persona+evidence dihitung terpisah)
npx @modelcontextprotocol/inspector python main.py

# 3. Test setiap fitur advanced satu per satu:
# Tool 8: scan_ward_alerts(ward_id="ICU-A", threshold="high")
# Tool 9: orchestrate_context_from_sources(patient_id="synthea-demo-patient",
#          sources=["nara_core","radiology_mcp"])
# Tool 1 dengan role="nurse" → lihat persona adaptation
# Tool 7 → lihat evidence_trail di response

# 4. Deploy update ke Railway
git add . && git commit -m "feat: advanced features v2.0" && git push
# Railway auto-deploy, verify di URL live
```

### Phase 6.2 — Update Prompt Opinion Registration

- Login ke Prompt Opinion → Studio → update server description
- Tambahkan ke description: mention Adaptive Persona, Ward Alerts, Evidence Trail, Meta-Orchestrator
- Complete Publisher Profile → Publish ke Marketplace (ini wajib untuk submission!)
- Test 9 tools via Prompt Opinion Launchpad dengan real agent

### Phase 6.3 — Demo Video Recording v2.0

**Script demo 3 menit (DIUPDATE untuk fitur advanced):**

```
[0:00-0:20] PROBLEM STATEMENT (slide + narasi)
  "Dokter menghabiskan 36 menit di EHR per kunjungan 30 menit.
   AI yang ada bersifat reaktif dan memberikan output yang sama
   untuk semua orang. Nara hadir untuk mengubah itu."

[0:20-0:50] FITUR 1: PROACTIVE WARD ALERT
  Ketik di Prompt Opinion: "Siapa yang perlu perhatian di ward ICU-A sekarang?"
  Agent calls: scan_ward_alerts(ward_id="ICU-A", threshold="high")
  Tunjukkan: 2 patients diprioritaskan dalam format nurse-friendly (bullets)
  Highlight: "Tanpa diminta, Nara sudah tahu siapa yang butuh perhatian."

[0:50-1:30] FITUR 2: AI SYNTHESIS + EVIDENCE TRAIL (KLIMAKS)
  Ketik: "Apakah kreatinin Eleanor berhubungan dengan obat barunya?"
  Agent calls: synthesize_cross_domain_insights + evidence_trail
  Tunjukkan: narrative synthesis + confidence 0.74 + data gaps
  Highlight: "Nara tidak hanya menjawab — ia menunjukkan MENGAPA ia yakin."

[1:30-2:00] FITUR 3: ADAPTIVE PERSONA (SIDE BY SIDE)
  Tunjukkan query yang sama, dua role berbeda:
  - Role=physician → narrative klinis panjang
  - Role=nurse → bullet points + thresholds angka
  Highlight: "Output berbeda secara fundamental, bukan hanya bahasanya."

[2:00-2:30] FITUR 4: META-ORCHESTRATOR
  Ketik: "Berikan saya gambaran lengkap Eleanor dari semua sistem"
  Agent calls: orchestrate_context_from_sources(sources=["nara_core","radiology_mcp"])
  Tunjukkan: unified context dari 2 MCP servers berbeda
  Highlight: "Satu-satunya MCP server yang mengorkestrasi server lain."

[2:30-3:00] CLOSING
  Tampilkan: 9 tools di Prompt Opinion Marketplace
  Narasi: "Nara by NexusHealth.
           Proactive. Adaptive. Transparent. Interoperable.
           One call. Full picture."
  Tagline: SHARP-compliant | FHIR R4 | Evidence-based | Multi-MCP
```

### Phase 6.4 — Update Devpost Submission

Update description di Devpost untuk mencakup:

- Semua 4 fitur advanced (Adaptive Persona, Ward Alert, Evidence Trail, Meta-Orchestrator)
- Tambahkan: "Unlike other submissions, Nara is the only MCP server that orchestrates other
  MCP servers, proactively detects at-risk patients, adapts output for each clinical role,
  and provides transparent evidence trails for every insight."
- Link ke Railway URL dan GitHub repo
- Link ke demo video YouTube

---

## Checklist Final Sebelum Submit (v2.0)

**Existing (sudah done):**

- [x] 7 core tools berjalan, 69 tests pass
- [x] SHARP integration complete
- [x] Railway deployed & Prompt Opinion registered

**Advanced features (target):**

- [ ] `evidence/` module complete + terintegrasi ke tools 5, 7
- [ ] `persona/` module complete + terintegrasi ke semua 7 tools
- [ ] `scan_ward_alerts` (tool 8) berfungsi dengan ≥2 synthetic patients
- [ ] `orchestrate_context_from_sources` (tool 9) berfungsi dengan mock MCPs
- [ ] pytest: ≥90 tests pass, tidak ada regresi
- [ ] Semua 9 tools terlihat di MCP Inspector
- [ ] Railway redeployed dengan env vars baru (MOCK_EXTERNAL_MCP, WARD_SCAN_MAX_PATIENTS)
- [ ] Prompt Opinion: 9 tools verified di platform, Published ke Marketplace
- [ ] Demo video v2.0 direkam (3 menit, 4 fitur advanced terlihat)
- [ ] Devpost submission form updated (description, video link, marketplace URL)
- [ ] README.md updated dengan 9 tools + advanced features dokumentasi

**Hard deadline:** 11 Mei 2026 23:00 EDT = 12 Mei 2026 10:00 WIB

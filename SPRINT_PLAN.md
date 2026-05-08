# SPRINT_PLAN.md — Execution Roadmap

# Nara by NexusHealth — Unified Patient Context MCP Server

# Version: 3.0 — Clinical Pattern Memory Edition

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

### PHASE 5.5 — Clinical Pattern Memory (Hari 3-4, Prioritas #5) 🆕

**Target: `memory/` module + `get_pattern_insights` tool berfungsi, auto-record di tools 5 & 7**

**Estimasi effort: ~4-6 jam** — ini adalah fitur paling compact secara implementasi karena tidak butuh FHIR call, tidak butuh external API. Pure Python in-memory logic.

#### Step 1: Buat `memory/` module

```
memory/
├── __init__.py
├── store.py        # ClinicalPatternMemory singleton
├── signature.py    # PatternSignature extractor
├── matcher.py      # PatternMatcher (optional — bisa merge ke store.py)
└── models.py       # PatternRecord, PatternInsight Pydantic models
```

**`memory/store.py` — implementasi lengkap:**

```python
import hashlib
from threading import Lock
from datetime import datetime, timezone
from models.advanced import PatternRecord

class ClinicalPatternMemory:
    """
    Thread-safe in-memory pattern store.
    Singleton — satu instance per server process.

    PRIVACY GUARANTEES:
    - Keys are SHA-256 hashes of generic conditions, NEVER patient IDs
    - Values are outcome counts ONLY, no clinical values stored
    - Store resets on every server restart (no persistence)
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._store = {}
                    cls._instance._store_lock = Lock()
        return cls._instance

    def record(self, conditions: list[str], outcome: str) -> str:
        """Record a new pattern observation. Non-blocking. Returns signature."""
        if not conditions:
            return ""
        signature = self._make_signature(conditions)
        with self._store_lock:
            if signature not in self._store:
                self._store[signature] = PatternRecord(
                    signature=signature,
                    conditions=sorted(conditions),
                    outcome_counts={},
                    first_seen=datetime.now(timezone.utc).isoformat(),
                    last_seen="",
                    total_observations=0
                )
            record = self._store[signature]
            record.outcome_counts[outcome] = record.outcome_counts.get(outcome, 0) + 1
            record.total_observations += 1
            record.last_seen = datetime.now(timezone.utc).isoformat()
        return signature

    def query_similar(self, conditions: list[str]) -> PatternRecord | None:
        """Query for exact pattern match. Returns None if not found."""
        if not conditions:
            return None
        signature = self._make_signature(conditions)
        with self._store_lock:
            return self._store.get(signature)

    def get_stats(self) -> dict:
        """Return store statistics for debugging (no patient data)."""
        with self._store_lock:
            return {
                "total_patterns": len(self._store),
                "total_observations": sum(r.total_observations for r in self._store.values())
            }

    def _make_signature(self, conditions: list[str]) -> str:
        canonical = "|".join(sorted(c.lower().strip() for c in conditions if c))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

# Singleton instance — import ini di semua tools yang butuh pattern memory
pattern_memory = ClinicalPatternMemory()
```

**`memory/signature.py` — ekstrak conditions dari clinical data:**

```python
class PatternSignature:
    """
    Ekstrak kondisi GENERIK dari clinical data untuk Pattern Memory.

    ATURAN KRITIS:
    - Ekstrak KATEGORI, bukan nilai numerik spesifik
    - BOLEH: "creatinine_rising_trend", "news2_high_risk"
    - TIDAK BOLEH: "creatinine=1.8", "news2=7", "patient_p001"
    """

    def from_news2_result(self, score: int, triggered_rules: list[str]) -> list[str]:
        conditions = []
        if score >= 7:
            conditions.append("news2_high_risk")
        elif score >= 5:
            conditions.append("news2_medium_risk")
        elif score >= 1:
            conditions.append("news2_low_medium_risk")
        else:
            conditions.append("news2_low_risk")

        # Normalize triggered rules ke generic labels
        for rule in triggered_rules:
            normalized = self._normalize_rule(rule)
            if normalized:
                conditions.append(normalized)
        return conditions

    def from_synthesis_context(self, labs: list, meds: list, vitals_summary: dict) -> list[str]:
        conditions = []

        # Labs — kategorisasi trend, bukan nilai
        for lab in labs:
            name_lower = lab.name.lower() if hasattr(lab, 'name') else ""
            if "creatinine" in name_lower:
                trend = getattr(lab, 'trend', None)
                if trend == "rising":
                    conditions.append("creatinine_rising_trend")
                elif trend == "falling":
                    conditions.append("creatinine_falling_trend")
            if "hemoglobin" in name_lower or "hgb" in name_lower:
                conditions.append("abnormal_hemoglobin")

        # Medications — kehadiran, bukan dosis
        for med in meds:
            name_lower = med.name.lower() if hasattr(med, 'name') else ""
            if "metformin" in name_lower:
                conditions.append("metformin_present")
            if "warfarin" in name_lower or "coumadin" in name_lower:
                conditions.append("anticoagulant_present")
            flags = getattr(med, 'interaction_flags', [])
            if flags:
                conditions.append("active_drug_interaction")

        return list(set(conditions))  # deduplicate

    def _normalize_rule(self, rule: str) -> str | None:
        rule_lower = rule.lower()
        mappings = {
            "heart rate": "elevated_heart_rate",
            "respiratory": "elevated_respiratory_rate",
            "spo2": "low_oxygen_saturation",
            "oxygen": "low_oxygen_saturation",
            "blood pressure": "abnormal_blood_pressure",
            "temperature": "abnormal_temperature",
            "consciousness": "altered_consciousness",
        }
        for keyword, label in mappings.items():
            if keyword in rule_lower:
                return label
        return None

# Singleton instance
pattern_signature = PatternSignature()
```

#### Step 2: Tambahkan PatternRecord dan PatternInsight ke `models/advanced.py`

```python
# Tambahkan ke models/advanced.py:

class PatternRecord(BaseModel):
    """Internal — tidak di-expose langsung ke agent."""
    signature: str
    conditions: list[str]
    outcome_counts: dict
    first_seen: str
    last_seen: str
    total_observations: int

class PatternInsight(BaseModel):
    """Response model untuk get_pattern_insights tool."""
    pattern_found: bool
    conditions_checked: list[str] = []
    signature: str | None = None
    similar_patterns_seen: int = 0
    outcome_distribution: dict = {}
    contextual_insight: str = ""
    data_scope: str = "current_session_only"
    session_reset_note: str = "Pattern store resets on server restart. No persistent storage."
    confidence: Literal["low", "moderate", "none"] = "none"
    confidence_note: str = "Session-scoped context only — not a statistical claim"
    action_required_by: str = "clinician"
    ai_generated: bool = True
    sharp_metadata: SHARPMetadata = SHARPMetadata()
```

#### Step 3: Integrasi auto-record ke Tool 5 (`tools/deterioration.py`)

```python
# Tambahkan import di atas file:
from memory.store import pattern_memory
from memory.signature import pattern_signature
import asyncio

# Di akhir detect_clinical_deterioration_signals(), sebelum return:
# Auto-record pattern (non-blocking, background)
if os.getenv("PATTERN_MEMORY_ENABLED", "true") == "true":
    try:
        conditions = pattern_signature.from_news2_result(
            score=report.news2_score,
            triggered_rules=report.triggered_rules
        )
        outcome = "deterioration_high_risk" if report.news2_score >= 7 else \
                  "deterioration_medium_risk" if report.news2_score >= 5 else "stable"
        pattern_memory.record(conditions, outcome)
        # Tambahkan ke report untuk transparansi
        report.pattern_recorded = True
        report.pattern_conditions = conditions
    except Exception:
        pass  # Pattern recording TIDAK BOLEH block atau error main flow
```

#### Step 4: Integrasi auto-record ke Tool 7 (`tools/cross_domain_insights.py`)

```python
# Di akhir synthesize_cross_domain_insights(), sebelum return:
if os.getenv("PATTERN_MEMORY_ENABLED", "true") == "true":
    try:
        conditions = pattern_signature.from_synthesis_context(
            labs=abnormal_labs,
            meds=medications,
            vitals_summary={"deterioration_level": deterioration.risk_level}
        )
        outcome = "cross_domain_concern" if insight.confidence_level != "low" else "monitoring"
        pattern_memory.record(conditions, outcome)
        insight.pattern_recorded = True
    except Exception:
        pass  # Non-blocking
```

#### Step 5: Buat `tools/pattern_insights.py`

```python
# tools/pattern_insights.py
from mcp.server.fastmcp import FastMCP
from memory.store import pattern_memory
from memory.signature import pattern_signature
from models.advanced import PatternInsight
from sharp.context import extract_sharp_context, resolve_patient_id, build_sharp_metadata
from integrations.llm_client import llm_client
import os

@mcp.tool()
async def get_pattern_insights(
    patient_id: str,
    conditions: list[str] | None = None,
    ctx=None
) -> PatternInsight:
    """
    Query Clinical Pattern Memory for anonymous session-scoped historical context.

    Returns pattern observations from current session only.
    No patient data is stored — only anonymous clinical condition hashes.
    Store resets on server restart.

    Args:
        patient_id: FHIR Patient resource ID (used to fetch conditions if not provided)
        conditions: Optional list of generic clinical conditions to query.
                    If not provided, will be derived from patient's latest deterioration data.
    """
    sharp = extract_sharp_context(ctx)

    if not os.getenv("PATTERN_MEMORY_ENABLED", "true") == "true":
        return PatternInsight(
            pattern_found=False,
            message="Pattern Memory is disabled on this server.",
            conditions_checked=[]
        )

    # Gunakan conditions yang di-pass, atau derive dari FHIR
    effective_conditions = conditions
    if not effective_conditions:
        # Ambil dari deterioration report pasien ini
        try:
            from integrations.fhir_client import fhir_client as fc
            effective_id = resolve_patient_id(sharp, patient_id)
            vitals = await fc.get_observations(effective_id, category="vital-signs", days=3)
            # Parse minimal untuk dapat NEWS2 approximation
            effective_conditions = ["current_patient_pattern"]  # fallback generic
        except Exception:
            effective_conditions = []

    if not effective_conditions:
        return PatternInsight(
            pattern_found=False,
            conditions_checked=[],
            contextual_insight="No conditions available to query pattern memory.",
            sharp_metadata=build_sharp_metadata(sharp)
        )

    # Query memory
    past = pattern_memory.query_similar(effective_conditions)

    if not past or past.total_observations == 0:
        return PatternInsight(
            pattern_found=False,
            conditions_checked=effective_conditions,
            contextual_insight="No similar patterns observed in current session yet. This is the first occurrence.",
            sharp_metadata=build_sharp_metadata(sharp)
        )

    # Hitung distribusi outcome
    total = past.total_observations
    distribution = {k: f"{(v/total*100):.0f}%" for k, v in past.outcome_counts.items()}

    # Generate LLM explanation
    insight_text = await llm_client.explain(
        prompt=f"""You are a clinical decision support AI analyzing session pattern data.

Pattern observed: {past.conditions}
Times seen this session: {total}
Outcome distribution: {distribution}

Write 2-3 sentences explaining this pattern context for a clinician.
Rules:
- NEVER say "diagnose" or "diagnosis"
- ALWAYS note this is session-scoped context only
- ALWAYS note clinician judgment is required
- Keep it factual and hedged appropriately""",
        max_tokens=150
    )

    confidence = "moderate" if total >= 5 else "low"

    return PatternInsight(
        pattern_found=True,
        conditions_checked=effective_conditions,
        signature=past.signature,
        similar_patterns_seen=total,
        outcome_distribution=distribution,
        contextual_insight=insight_text or f"This pattern has been observed {total} time(s) this session.",
        data_scope="current_session_only",
        session_reset_note="Pattern store resets on server restart. No persistent storage of any kind.",
        confidence=confidence,
        confidence_note=f"Based on {total} session observation(s) only — not a validated statistical claim.",
        action_required_by="clinician",
        ai_generated=True,
        sharp_metadata=build_sharp_metadata(sharp)
    )
```

#### Step 6: Register tool di `server.py`

```python
from tools.pattern_insights import get_pattern_insights
```

#### Step 7: Tulis `tests/test_pattern_memory.py`

```python
# tests/test_pattern_memory.py
import pytest
from memory.store import ClinicalPatternMemory
from memory.signature import PatternSignature

# Reset singleton state sebelum setiap test
@pytest.fixture(autouse=True)
def reset_memory():
    memory = ClinicalPatternMemory()
    memory._store.clear()
    yield
    memory._store.clear()

def test_record_and_query_exact_match():
    memory = ClinicalPatternMemory()
    conditions = ["news2_high_risk", "creatinine_rising_trend"]
    memory.record(conditions, "deterioration")
    result = memory.query_similar(conditions)
    assert result is not None
    assert result.total_observations == 1
    assert result.outcome_counts["deterioration"] == 1

def test_record_accumulates_multiple_observations():
    memory = ClinicalPatternMemory()
    conditions = ["creatinine_rising_trend", "metformin_present"]
    memory.record(conditions, "deterioration")
    memory.record(conditions, "deterioration")
    memory.record(conditions, "stable")
    result = memory.query_similar(conditions)
    assert result.total_observations == 3
    assert result.outcome_counts["deterioration"] == 2
    assert result.outcome_counts["stable"] == 1

def test_query_returns_none_if_no_match():
    memory = ClinicalPatternMemory()
    result = memory.query_similar(["nonexistent_condition"])
    assert result is None

def test_signature_is_order_independent():
    memory = ClinicalPatternMemory()
    sig = PatternSignature()
    conditions_a = ["creatinine_rising_trend", "metformin_present"]
    conditions_b = ["metformin_present", "creatinine_rising_trend"]
    # Urutan berbeda → hash yang sama
    assert memory._make_signature(conditions_a) == memory._make_signature(conditions_b)

def test_no_patient_data_in_store():
    memory = ClinicalPatternMemory()
    memory.record(["news2_high_risk"], "deterioration")
    # Pastikan tidak ada nilai yang menyerupai PII di store
    for sig, record in memory._store.items():
        assert "patient" not in sig.lower()
        for condition in record.conditions:
            assert "=" not in condition  # tidak ada "creatinine=1.8"
            assert any(char.isalpha() for char in condition)  # bukan angka murni

def test_singleton_shared_across_instances():
    memory_a = ClinicalPatternMemory()
    memory_b = ClinicalPatternMemory()
    memory_a.record(["test_condition"], "outcome_a")
    result = memory_b.query_similar(["test_condition"])
    assert result is not None  # same instance

def test_pattern_signature_from_news2():
    sig = PatternSignature()
    conditions = sig.from_news2_result(score=8, triggered_rules=["HR > 110", "SpO2 < 95%"])
    assert "news2_high_risk" in conditions
    assert "elevated_heart_rate" in conditions
    assert "low_oxygen_saturation" in conditions

def test_pattern_signature_no_numeric_values():
    sig = PatternSignature()
    conditions = sig.from_news2_result(score=7, triggered_rules=["RR > 25"])
    for condition in conditions:
        assert "7" not in condition  # score numerik tidak masuk ke condition
        assert ">" not in condition  # operator tidak masuk

@pytest.mark.asyncio
async def test_get_pattern_insights_returns_not_found_if_empty():
    from tools.pattern_insights import get_pattern_insights
    # Memory kosong → pattern_found=False
    result = await get_pattern_insights(
        patient_id="test-patient",
        conditions=["very_rare_condition_xyz"]
    )
    assert result.pattern_found == False

@pytest.mark.asyncio
async def test_get_pattern_insights_returns_context_after_recording():
    from memory.store import pattern_memory
    from tools.pattern_insights import get_pattern_insights
    # Seed memory dulu
    pattern_memory.record(["creatinine_rising_trend", "metformin_present"], "deterioration")
    pattern_memory.record(["creatinine_rising_trend", "metformin_present"], "deterioration")

    result = await get_pattern_insights(
        patient_id="test-patient",
        conditions=["creatinine_rising_trend", "metformin_present"]
    )
    assert result.pattern_found == True
    assert result.similar_patterns_seen == 2
    assert result.action_required_by == "clinician"
    assert result.data_scope == "current_session_only"

def test_get_stats_returns_no_pii():
    memory = ClinicalPatternMemory()
    memory.record(["test_condition"], "test_outcome")
    stats = memory.get_stats()
    assert "total_patterns" in stats
    assert "total_observations" in stats
    # Stats tidak mengandung data pasien
    assert "patient" not in str(stats)
```

**Verifikasi Phase 5.5 selesai:**

```bash
pytest tests/test_pattern_memory.py -v  # semua 10+ tests pass
pytest tests/ -v  # target: 100+ tests total, tidak ada regresi

# Verify auto-recording bekerja:
# 1. Jalankan server: MOCK_SHARP=true python main.py
# 2. Panggil tool 5 beberapa kali via MCP Inspector
# 3. Panggil get_pattern_insights → harus muncul "similar_patterns_seen > 0"

# MCP Inspector: 10 tools terlihat (tools 1-9 + get_pattern_insights)
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

### Phase 6.3 — Demo Video Recording v3.0

**Script demo 3 menit (DIUPDATE — 5 fitur advanced):**

```
[0:00-0:20] PROBLEM STATEMENT
  "Dokter menghabiskan 36 menit di EHR per kunjungan 30 menit.
   AI yang ada reaktif, tidak belajar, dan memberi output yang sama untuk semua orang."

[0:20-0:45] FITUR 1: PROACTIVE WARD ALERT
  "Siapa yang perlu perhatian di ward ICU-A sekarang?"
  → scan_ward_alerts → 2 patients diprioritaskan
  Highlight: "Proaktif tanpa diminta."

[0:45-1:15] FITUR 2: AI SYNTHESIS + EVIDENCE TRAIL
  "Apakah kreatinin Eleanor berhubungan dengan obat barunya?"
  → synthesize_cross_domain_insights → narrative + confidence 0.74 + data gaps
  Highlight: "Transparan — Nara menunjukkan mengapa ia yakin."

[1:15-1:45] FITUR 3: CLINICAL PATTERN MEMORY ⭐ KLIMAKS BARU
  "Apakah pola ini pernah terlihat hari ini?"
  → get_pattern_insights → "Pola ini terlihat 3 kali session ini. 67% menuju deterioration."
  Highlight: "Nara belajar dari shift ini tanpa menyimpan satu pun data pasien.
              Keys adalah hash anonim. Store reset setiap restart."

[1:45-2:10] FITUR 4: ADAPTIVE PERSONA
  Query sama, physician vs nurse → output berbeda secara fundamental
  Highlight: "Adaptif — bukan hanya bahasa, tapi seluruh struktur informasi."

[2:10-2:40] FITUR 5: META-ORCHESTRATOR
  → orchestrate_context_from_sources → unified context dari 2 MCP servers
  Highlight: "Satu-satunya MCP server yang mengorkestrasi server lain."

[2:40-3:00] CLOSING
  "Nara by NexusHealth.
   Proactive. Adaptive. Transparent. Pattern-aware. Interoperable.
   One call. Full picture."
  Tagline: SHARP-compliant | FHIR R4 | Evidence-based | Pattern Memory | Multi-MCP
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

## Checklist Final Sebelum Submit (v3.0)

**Existing (sudah done):**

- [x] 7 core tools berjalan, 69 tests pass
- [x] SHARP integration complete
- [x] Railway deployed & Prompt Opinion registered

**Advanced features (target):**

- [ ] `evidence/` module complete + terintegrasi ke tools 5, 7
- [ ] `persona/` module complete + terintegrasi ke semua 7 tools
- [ ] `scan_ward_alerts` (tool 8) berfungsi dengan ≥2 synthetic patients
- [ ] `orchestrate_context_from_sources` (tool 9) berfungsi dengan mock MCPs
- [ ] `memory/` module complete — store, signature, PatternRecord, PatternInsight
- [ ] `get_pattern_insights` (tool 10) berfungsi — query returns hasil setelah beberapa tool 5/7 calls
- [ ] Tool 5 & 7 auto-record pattern ke memory (non-blocking)
- [ ] pytest: ≥100 tests pass, tidak ada regresi
- [ ] Semua 10 tools terlihat di MCP Inspector
- [ ] Railway redeployed dengan env vars baru (MOCK_EXTERNAL_MCP, PATTERN_MEMORY_ENABLED, dll.)
- [ ] Prompt Opinion: 10 tools verified di platform, Published ke Marketplace
- [ ] Demo video v3.0 direkam (3 menit, 5 fitur advanced terlihat termasuk Pattern Memory)
- [ ] Devpost submission form updated (description mention Pattern Memory + privacy guarantee)
- [ ] README.md updated dengan 10 tools + semua advanced features dokumentasi

**Hard deadline:** 11 Mei 2026 23:00 EDT = 12 Mei 2026 10:00 WIB

# ARCHITECTURE.md — System Architecture

# Nara by NexusHealth — Unified Patient Context MCP Server

# Version: 3.0 — Clinical Pattern Memory Edition

---

## 1. High-Level Architecture (v2.0)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PROMPT OPINION PLATFORM                           │
│                                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ Diagnosis  │  │  Triage    │  │ Medication │  │   Ward Monitor     │ │
│  │   Agent    │  │   Agent    │  │   Agent    │  │      Agent         │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────────┬───────────┘ │
│        └───────────────┼───────────────┼─────────────────-┘             │
│                        │   MCP Tool Calls + SHARP Context                │
└────────────────────────┼─────────────────────────────────────────────────┘
                         │
         ┌───────────────▼──────────────────────────────────┐
         │          NARA BY NEXUSHEALTH — MCP SERVER        │
         │      https://amiable-determination-production     │
         │              .up.railway.app/mcp                  │
         │                                                   │
         │  ┌────────────────────────────────────────────┐  │
         │  │           SHARP MIDDLEWARE LAYER           │  │
         │  │  extract_sharp_context() → role, patient   │  │
         │  │  zero-PII audit logging                    │  │
         │  └──────────────────┬─────────────────────────┘  │
         │                     │                            │
         │  ┌──────────────────▼─────────────────────────┐  │
         │  │        ADAPTIVE CLINICAL PERSONA 🆕         │  │
         │  │  PersonaAdapter.adapt(output, role)         │  │
         │  │  physician | nurse | pharmacist | patient   │  │
         │  └──────────────────┬─────────────────────────┘  │
         │                     │                            │
         │  ┌──────────────────▼─────────────────────────┐  │
         │  │              MCP TOOL LAYER                 │  │
         │  │  Tools 1-7: Data retrieval (✅ Done)         │  │
         │  │  Tool 8: scan_ward_alerts 🆕                │  │
         │  │  Tool 9: orchestrate_context 🆕             │  │
         │  │  Tool 10: get_pattern_insights 🆕           │  │
         │  └────┬──────────────┬──────────────┬──────────┘  │
         │       │              │              │             │
         │  ┌────▼────┐  ┌──────▼───┐  ┌───────▼──────────┐ │
         │  │Clinical │  │   LLM    │  │ Evidence Trail 🆕│ │
         │  │Rule Eng.│  │Explainer │  │  EvidenceScorer  │ │
         │  │NEWS2/   │  │+Synthesis│  │  weight per src  │ │
         │  │MEWS     │  │+Persona  │  │  confidence calc │ │
         │  └─────────┘  └──────────┘  └──────────────────┘ │
         │                                                   │
         │  ┌────────────────────────────────────────────┐  │
         │  │     CLINICAL PATTERN MEMORY 🆕 NEW         │  │
         │  │  In-memory only — resets on restart        │  │
         │  │  Keys: SHA-256 hash of clinical conditions │  │
         │  │  Values: outcome counts (NO patient data)  │  │
         │  │  Auto-populated by Tool 5 & Tool 7         │  │
         │  └────────────────────────────────────────────┘  │
         └─────────────────────────┬────────────────────────┘
                                   │
          ┌────────────────────────┼───────────────────────┐
          │                        │                       │
┌─────────▼──────────┐  ┌──────────▼──────┐  ┌────────────▼──────────────┐
│   EXTERNAL APIs    │  │  Anthropic API  │  │  EXTERNAL MCP SERVERS 🆕  │
│                    │  │  (Claude Haiku) │  │                           │
│  HAPI FHIR R4      │  │                 │  │  radiology_mcp (mock)     │
│  OpenFDA API       │  │  Explain+       │  │  pharmacy_mcp (mock)      │
│                    │  │  Synthesize+    │  │  [future: real servers]   │
│                    │  │  Persona adapt  │  │                           │
└────────────────────┘  └─────────────────┘  └───────────────────────────┘
```

---

## 2. Layer Architecture (v2.0)

### Layer 0: SHARP Middleware (`sharp/`) — ✅ DONE

_(tidak berubah dari v1.0 — sudah selesai)_

### Layer 0.5: Adaptive Clinical Persona (`persona/`) — 🆕 NEW

Bertanggung jawab untuk mentransformasi **seluruh struktur output** berdasarkan role klinisi.
Bukan sekadar mengubah bahasa — mengubah format, depth, prioritas konten, dan terminologi.

```python
# persona/profiles.py
class RoleProfile:
    PROFILES = {
        "physician": RoleConfig(
            format="narrative",
            depth="full",
            terminology="medical",
            priority_fields=["differential", "clinical_reasoning", "raw_values"],
            max_length=None  # no limit for physician
        ),
        "nurse": RoleConfig(
            format="bullets",
            depth="summary",
            terminology="nursing",
            priority_fields=["monitoring_thresholds", "escalation_triggers", "actions"],
            max_length=300
        ),
        "pharmacist": RoleConfig(
            format="structured",
            depth="medication-focused",
            terminology="pharmacy",
            priority_fields=["drug_interactions", "renal_dosing", "contraindications"],
            max_length=400
        ),
        "patient": RoleConfig(
            format="simple",
            depth="simplified",
            terminology="plain",
            priority_fields=["next_steps", "what_to_watch", "questions_for_doctor"],
            max_length=200
        )
    }

# persona/adapter.py
class PersonaAdapter:
    async def adapt(self, raw_output: dict, role: str, llm_client) -> dict:
        profile = RoleProfile.PROFILES.get(role, RoleProfile.PROFILES["physician"])
        adapted_content = await llm_client.adapt_for_persona(raw_output, profile)
        return {
            **raw_output,
            "content_adapted": adapted_content,
            "persona_applied": role,
            "persona_format": profile.format,
            "original_available": True
        }
```

### Layer 0.6: Evidence Trail Engine (`evidence/`) — 🆕 NEW

Bertanggung jawab untuk menghitung confidence secara transparan berdasarkan kualitas data.

```python
# evidence/scorer.py
class EvidenceScorer:
    def score(self, data_sources: list[DataSource]) -> EvidenceTrail:
        items = []
        for source in data_sources:
            weight = self._calculate_weight(source)
            items.append(EvidenceItem(
                source=source.name,
                data_points=len(source.values),
                recency_hours=source.recency_hours,
                weight=weight,
                quality=source.quality,
                raw_values=source.values
            ))

        overall = self._weighted_average([i.weight for i in items])
        return EvidenceTrail(
            overall_confidence=overall,
            confidence_label=self._label(overall),
            evidence_items=items,
            missing_data=self._find_gaps(data_sources),
            recommendation_strength=self._strength(overall),
            transparency_note=self._explain(overall, items)
        )

    def _calculate_weight(self, source: DataSource) -> float:
        recency_score = max(0, 1 - (source.recency_hours / 168))  # decay over 1 week
        completeness_score = min(1, source.data_points / 5)        # max at 5 points
        quality_score = {"complete": 1.0, "partial": 0.6, "estimated": 0.3}[source.quality]
        return (recency_score * 0.4) + (completeness_score * 0.4) + (quality_score * 0.2)
```

### Layer 0.7: Clinical Pattern Memory (`memory/`) — 🆕 NEW

Bertanggung jawab untuk mengakumulasi pola klinis anonim selama server session berlangsung,
memberikan konteks historis kepada tools tanpa menyimpan satu pun data pasien.

**Prinsip desain yang tidak bisa dikompromikan:**

- Store hidup **hanya di RAM** — tidak ada file, tidak ada database, tidak ada disk write
- Setiap key adalah **SHA-256 hash** dari kondisi klinis yang sudah di-sort dan di-join
- Tidak ada patient_id, nama, atau nilai raw yang disimpan di store
- Reset otomatis setiap server restart — ini adalah fitur, bukan bug

```python
# memory/store.py
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

@dataclass
class PatternRecord:
    signature: str          # SHA-256 hash
    conditions: list[str]   # kondisi yang membentuk hash (untuk display saja)
    outcome_counts: dict = field(default_factory=dict)  # {"deterioration": 2, "stable": 1}
    first_seen: str = ""
    last_seen: str = ""
    total_observations: int = 0

class ClinicalPatternMemory:
    """
    Thread-safe in-memory pattern store.
    Hanya simpan pola anonim — zero patient data.
    """
    def __init__(self):
        self._store: dict[str, PatternRecord] = {}
        self._lock = Lock()

    def record(self, conditions: list[str], outcome: str) -> str:
        """Simpan observasi pattern baru. Return signature hash."""
        signature = self._make_signature(conditions)
        with self._lock:
            if signature not in self._store:
                self._store[signature] = PatternRecord(
                    signature=signature,
                    conditions=conditions  # kondisi generik, bukan nilai pasien spesifik
                )
            record = self._store[signature]
            record.outcome_counts[outcome] = record.outcome_counts.get(outcome, 0) + 1
            record.total_observations += 1
        return signature

    def query_similar(self, conditions: list[str]) -> PatternRecord | None:
        """Cari pattern serupa di store. Return None jika belum ada."""
        signature = self._make_signature(conditions)
        with self._lock:
            return self._store.get(signature)

    def _make_signature(self, conditions: list[str]) -> str:
        """SHA-256 hash dari sorted conditions. Deterministic dan anonymous."""
        canonical = "|".join(sorted(c.lower().strip() for c in conditions))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]  # 16 char prefix
```

```python
# memory/signature.py
class PatternSignature:
    """
    Mengekstrak kondisi klinis generik dari data FHIR untuk dipakai sebagai pattern key.
    PENTING: Ekstrak KATEGORI, bukan nilai numerik spesifik pasien.
    """

    CREATININE_THRESHOLDS = [
        (0.5, "creatinine_low"), (1.2, "creatinine_normal"),
        (2.0, "creatinine_elevated"), (float("inf"), "creatinine_critical")
    ]

    def from_deterioration_report(self, report: DeteriorationReport) -> list[str]:
        conditions = []
        if report.news2_score >= 7:
            conditions.append("news2_high_risk")
        elif report.news2_score >= 5:
            conditions.append("news2_medium_risk")
        for rule in report.triggered_rules:
            conditions.append(self._normalize_rule(rule))
        return conditions

    def from_synthesis(self, labs, medications, vitals) -> list[str]:
        conditions = []
        # Kategorisasi lab values ke bucket generik
        for lab in labs:
            if lab.trend == "rising" and "creatinine" in lab.name.lower():
                conditions.append("creatinine_rising_trend")
        # Cek medication flags
        for med in medications:
            if med.interaction_flags:
                conditions.append("active_drug_interaction")
            if "metformin" in med.name.lower():
                conditions.append("metformin_present")
        return conditions

    def _normalize_rule(self, rule: str) -> str:
        """Normalisasi triggered rule ke format generik."""
        rule_lower = rule.lower()
        if "heart rate" in rule_lower or "hr" in rule_lower:
            return "elevated_heart_rate"
        if "respiratory" in rule_lower or "rr" in rule_lower:
            return "elevated_respiratory_rate"
        if "spo2" in rule_lower or "oxygen" in rule_lower:
            return "low_oxygen_saturation"
        return rule_lower.replace(" ", "_")[:30]
```

**Tool 10: `get_pattern_insights`**

```python
# tools/pattern_insights.py
@mcp.tool()
async def get_pattern_insights(
    patient_id: str,
    conditions: list[str] | None = None,
    ctx=None
) -> PatternInsight:
    """
    Query Clinical Pattern Memory untuk konteks historis anonim.
    Jika conditions tidak di-pass, gunakan kondisi terbaru dari tool 5 & 7.

    PENTING: Output selalu menyertakan disclaimer bahwa ini session-scoped context,
    bukan statistical claim, dan action_required_by selalu "clinician".
    """
    sharp = extract_sharp_context(ctx)
    effective_id = resolve_patient_id(sharp, patient_id)

    # Jika conditions tidak di-pass, generate dari data FHIR pasien ini
    if not conditions:
        report = await detect_deterioration_internal(effective_id)
        conditions = pattern_signature.from_deterioration_report(report)

    # Query memory
    past = pattern_memory.query_similar(conditions)

    if not past:
        return PatternInsight(
            pattern_found=False,
            message="No similar patterns observed in current session yet.",
            conditions_checked=conditions
        )

    # Hitung distribusi outcome
    total = past.total_observations
    distribution = {k: f"{v/total*100:.0f}%" for k, v in past.outcome_counts.items()}

    return PatternInsight(
        pattern_found=True,
        signature=past.signature,
        conditions=past.conditions,
        similar_patterns_seen=total,
        outcome_distribution=distribution,
        contextual_insight=await llm_client.explain_pattern(past, distribution),
        data_scope="current_session_only",
        session_reset_note="Pattern store resets on server restart. No persistent storage.",
        confidence="low" if total < 5 else "moderate",
        action_required_by="clinician",
        ai_generated=True,
        sharp_metadata=build_sharp_metadata(sharp)
    )
```

### Layer 1: MCP Protocol Layer (`server.py`) — ✅ DONE

### Layer 2: Tool Layer (`tools/`) — Diperbarui

Tools 1-7 sudah ada. Tiga tool baru ditambahkan:

**Tool 8: `scan_ward_alerts`**

```python
@mcp.tool()
async def scan_ward_alerts(
    ward_id: str,
    threshold: str = "high",  # critical|high|medium
    max_patients: int = 20,
    ctx=None
) -> WardAlertReport:
    """
    Proactively scan all patients in a ward and return prioritized alerts.
    No need to ask about each patient individually.
    """
    sharp = extract_sharp_context(ctx)

    # 1. Get all patients in ward
    patients = await fhir_client.get_patients_by_location(ward_id)
    patients = patients[:max_patients]

    # 2. Parallel deterioration scan
    tasks = [detect_deterioration_internal(p.id) for p in patients]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Filter & rank by threshold
    alerts = rank_alerts(results, threshold)

    # 4. Apply Evidence Trail per alert
    for alert in alerts:
        alert.evidence_trail = evidence_scorer.score(alert.data_sources)

    # 5. Apply Adaptive Persona to summary
    summary = await persona_adapter.adapt(
        {"alerts": alerts, "ward_id": ward_id},
        role=sharp.role or "nurse"  # default nurse for ward scanning
    )

    return WardAlertReport(
        ward_id=ward_id,
        patients_scanned=len(patients),
        alerts=alerts,
        summary_narrative=summary["content_adapted"],
        persona_applied=sharp.role or "nurse",
        sharp_metadata=build_sharp_metadata(sharp)
    )
```

**Tool 9: `orchestrate_context_from_sources`**

```python
@mcp.tool()
async def orchestrate_context_from_sources(
    patient_id: str,
    sources: list[str],  # ["nara_core", "radiology_mcp", "pharmacy_mcp"]
    ctx=None
) -> OrchestratedContext:
    """
    Orchestrate patient context from multiple MCP servers.
    Nara calls other MCP servers and synthesizes unified context.
    """
    sharp = extract_sharp_context(ctx)
    effective_id = resolve_patient_id(sharp, patient_id)

    # 1. Always include core Nara data
    core_task = get_patient_snapshot_internal(effective_id)

    # 2. Call external MCPs in parallel
    external_tasks = [
        mcp_client.call_tool(SOURCE_URLS[src], "get_patient_data", {"patient_id": effective_id})
        for src in sources if src != "nara_core"
    ]

    core_data, *external_results = await asyncio.gather(
        core_task, *external_tasks, return_exceptions=True
    )

    # 3. Merge all results
    unified = merge_context(core_data, external_results, sources)

    # 4. Evidence Trail across all sources
    evidence = evidence_scorer.score_multi_source(unified)

    # 5. LLM synthesis of everything
    synthesis = await llm_client.synthesize_orchestrated(unified, sharp.role)

    # 6. Adaptive Persona
    output = await persona_adapter.adapt(
        {"synthesis": synthesis, "unified_context": unified},
        role=sharp.role or "physician"
    )

    return OrchestratedContext(
        patient_id=effective_id,
        sources_queried=sources,
        sources_available=len([r for r in external_results if not isinstance(r, Exception)]) + 1,
        unified_context=unified,
        synthesis=output["content_adapted"],
        evidence_trail=evidence,
        persona_applied=sharp.role or "physician"
    )
```

### Layer 3: Integration Layer — Diperbarui

**Baru: `integrations/mcp_client.py`**

```python
class MCPClient:
    """MCP-to-MCP HTTP client untuk Meta-Orchestrator."""

    # Mock server URLs (MOCK_EXTERNAL_MCP=true)
    MOCK_SERVERS = {
        "radiology_mcp": {
            "get_patient_data": lambda pid: {
                "imaging_findings": "No acute cardiopulmonary process on CXR",
                "last_imaging_date": "2026-05-08",
                "available": True
            }
        },
        "pharmacy_mcp": {
            "get_patient_data": lambda pid: {
                "dispensing_records": ["Metformin 500mg — dispensed 3 days ago"],
                "refill_due": "2026-05-20",
                "available": True
            }
        }
    }

    async def call_tool(self, server_id: str, tool_name: str, params: dict) -> dict:
        if os.getenv("MOCK_EXTERNAL_MCP") == "true":
            mock = self.MOCK_SERVERS.get(server_id, {})
            handler = mock.get(tool_name)
            return handler(params.get("patient_id")) if handler else {"available": False}

        # Real HTTP call untuk production
        server_url = os.getenv(f"MCP_URL_{server_id.upper()}", "")
        if not server_url:
            return {"available": False, "error": "Server URL not configured"}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{server_url}/tools/{tool_name}",
                    json=params
                )
                return {**response.json(), "available": True}
        except Exception as e:
            return {"available": False, "error": str(e)}
```

---

## 3. Data Flow per Tool (Diperbarui)

### Flow: `scan_ward_alerts` 🆕

```
Agent Call (ward_id="ICU-A", threshold="high", ctx+SHARP)
    │
    ▼
[SHARP Middleware] extract role="nurse", session_id
    │
    ▼
[FHIR] GET /Patient?location=ICU-A → [patient_1, patient_2, ..., patient_18]
    │
    ▼
[asyncio.gather() — PARALLEL untuk semua pasien]
    ├── detect_deterioration(patient_1) → NEWS2=9 ← CRITICAL
    ├── detect_deterioration(patient_2) → NEWS2=4 ← medium
    ├── detect_deterioration(patient_3) → NEWS2=7 ← HIGH
    └── ... (18 patients total)
    │
    ▼
[Alert Ranker] sort by score, filter threshold="high"
    → Alert list: [patient_1 (NEWS2=9), patient_3 (NEWS2=7)]
    │
    ▼
[Evidence Trail] score per alert → confidence per patient
    │
    ▼
[Persona Adapter] role="nurse" → actionable bullets
    "⚠ 2 patients need attention:
     1. Eleanor Dawson — NEWS2=9 CRITICAL. Immediate review.
     2. John Smith — NEWS2=7 HIGH. Clinical review within 30min."
    │
    ▼
Return WardAlertReport
    {
      "ward_id": "ICU-A",
      "patients_scanned": 18,
      "alerts": [
        {"patient_id": "p1", "alert_level": "critical", "news2": 9,
         "recommended_action": "Immediate clinical review",
         "evidence_trail": {"overall_confidence": 0.89, ...}},
        {"patient_id": "p3", "alert_level": "high", "news2": 7, ...}
      ],
      "summary_narrative": "2 of 18 patients require attention...",
      "persona_applied": "nurse"
    }
```

### Flow: `orchestrate_context_from_sources` 🆕

```
Agent Call (patient_id, sources=["nara_core","radiology_mcp","pharmacy_mcp"], ctx+SHARP)
    │
    ▼
[SHARP Middleware] extract role="physician"
    │
    ▼
[asyncio.gather() — PARALLEL]
    ├── get_patient_snapshot("synthea-001")         → core clinical context
    ├── mcp_client.call("radiology_mcp", ...)       → imaging findings
    └── mcp_client.call("pharmacy_mcp", ...)        → dispensing records
    │
    ▼
[Context Merger] unified_context = {core + radiology + pharmacy}
    {
      "core": {snapshot, labs, meds, vitals},
      "radiology": {"findings": "No acute CXR process"},
      "pharmacy": {"last_dispensed": "Metformin 3 days ago"}
    }
    │
    ▼
[Evidence Scorer] score per source (core=high, radiology=moderate, pharmacy=complete)
    │
    ▼
[LLM Synthesis] "Considering all available data across 3 systems..."
    │
    ▼
[Persona Adapter] role="physician" → full clinical narrative
    │
    ▼
Return OrchestratedContext
    {
      "sources_queried": ["nara_core", "radiology_mcp", "pharmacy_mcp"],
      "sources_available": 3,
      "synthesis": "Full clinical narrative...",
      "evidence_trail": {"overall_confidence": 0.81, ...},
      "persona_applied": "physician"
    }
```

### Flow: Adaptive Clinical Persona (embedded di semua tools) 🆕

```
Setiap tool response melewati PersonaAdapter sebelum dikembalikan:

Raw Output dari tool
    │
    ▼
[PersonaAdapter.adapt(raw, sharp.role)]
    │
    ├── role = "physician" → narrative panjang + full data
    ├── role = "nurse"     → bullets pendek + thresholds
    ├── role = "pharmacist"→ medication-focused structured
    └── role = "patient"   → plain language simple
    │
    ▼
Enhanced Output
    {
      ...original fields...,
      "content_adapted": "...",  ← role-specific version
      "persona_applied": "nurse",
      "persona_format": "bullets",
      "original_available": true
    }
```

### Flow: Evidence Trail (embedded di synthesis tools) 🆕

```
Tools 4, 5, 7, 9 menambahkan Evidence Trail sebelum return:

Structured Data dari tool
    │
    ▼
[EvidenceScorer.score(data_sources)]
    │
    ├── Lab Creatinine: recency=6h, points=3, quality=complete → weight=0.85
    ├── Medication/Metformin: recency=72h, points=1, quality=complete → weight=0.72
    └── Vitals/UrineOutput: recency=12h, points=2, quality=partial → weight=0.61
    │
    ▼
    overall_confidence = weighted_avg([0.85, 0.72, 0.61]) = 0.74
    confidence_label = "moderate"
    missing_data = ["baseline creatinine", "eGFR"]
    │
    ▼
Response dengan Evidence Trail
    {
      ...original fields...,
      "evidence_trail": {
        "overall_confidence": 0.74,
        "confidence_label": "moderate",
        "evidence_items": [...],
        "missing_data": [...],
        "transparency_note": "Confidence is moderate because..."
      }
    }
```

### Flow: Clinical Pattern Memory 🆕 (auto-recorded + on-demand query)

```
═══ FASE 1: AUTO-RECORD (terjadi setiap Tool 5 & 7 dijalankan) ═══

Tool 5 atau Tool 7 selesai menghasilkan insight
    │
    ▼
[PatternSignature.from_deterioration_report() / from_synthesis()]
  Ekstrak kondisi GENERIK (bukan nilai pasien):
  ["news2_high_risk", "creatinine_rising_trend", "metformin_present"]
    │
    ▼
[ClinicalPatternMemory.record(conditions, outcome)]
  signature = sha256("creatinine_rising_trend|metformin_present|news2_high_risk")
             = "a3f7b2c1..." (hash anonim)
  store["a3f7b2c1..."].outcome_counts["deterioration_signals"] += 1
    │
    ▼
  Pattern tersimpan di RAM — zero disk write, zero patient data

═══ FASE 2: ON-DEMAND QUERY (via get_pattern_insights tool) ═══

Agent Call (patient_id, optional conditions, ctx+SHARP)
    │
    ▼
[SHARP Middleware] extract role, effective_patient_id
    │
    ▼
[Jika conditions=None] → fetch deterioration report untuk pasien ini
[PatternSignature] → ekstrak conditions dari report
    │
    ▼
[ClinicalPatternMemory.query_similar(conditions)]
  → Cari hash yang cocok di store
  → Temukan: 3 observasi, 2x deterioration, 1x stable
    │
    ▼
[LLM Explainer] generate contextual insight dari pattern counts
  Input: {"similar": 3, "outcomes": {"deterioration": 2, "stable": 1}}
  Output: "This pattern has been observed 3 times this session..."
    │
    ▼
Return PatternInsight
    {
      "pattern_found": true,
      "similar_patterns_seen": 3,
      "outcome_distribution": {"deterioration_detected": "67%", "stable": "33%"},
      "contextual_insight": "This pattern has appeared 3 times this session...",
      "data_scope": "current_session_only",
      "confidence": "low",
      "confidence_note": "Session-scoped context only — not a statistical claim",
      "action_required_by": "clinician"
    }
```

---

## 4. Pydantic Models Baru (`models/advanced.py`) 🆕

```python
# models/advanced.py

class EvidenceItem(BaseModel):
    source: str
    data_points: int
    recency_hours: float
    weight: float
    quality: Literal["complete", "partial", "estimated"]
    raw_values: list

class EvidenceTrail(BaseModel):
    overall_confidence: float
    confidence_label: Literal["high", "moderate", "low", "insufficient"]
    evidence_items: list[EvidenceItem]
    missing_data: list[str]
    recommendation_strength: Literal["strong", "moderate", "weak", "insufficient"]
    transparency_note: str

class PatientAlert(BaseModel):
    patient_id: str
    patient_name: str | None = None  # hanya jika SHARP authorized
    alert_level: Literal["critical", "high", "medium"]
    news2_score: int
    mews_score: int
    primary_signal: str
    secondary_signals: list[str]
    recommended_action: str
    time_since_last_assessment: str
    evidence_trail: EvidenceTrail
    sharp_metadata: SHARPMetadata

class WardAlertReport(BaseModel):
    ward_id: str
    scan_timestamp: str
    patients_scanned: int
    alerts: list[PatientAlert]
    summary_narrative: str
    persona_applied: str
    sharp_metadata: SHARPMetadata

class ExternalSourceResult(BaseModel):
    source_id: str
    available: bool
    data: dict | None = None
    error: str | None = None

class OrchestratedContext(BaseModel):
    patient_id: str
    sources_queried: list[str]
    sources_available: int
    sources_failed: list[str]
    unified_context: dict
    synthesis: str
    evidence_trail: EvidenceTrail
    persona_applied: str
    sharp_metadata: SHARPMetadata

# 🆕 Clinical Pattern Memory models
class PatternRecord(BaseModel):
    """Internal store record — tidak pernah di-expose langsung ke agent."""
    signature: str           # SHA-256 hash (16 char prefix)
    conditions: list[str]    # kondisi generik, bukan nilai pasien
    outcome_counts: dict     # {"deterioration": 2, "stable": 1}
    total_observations: int

class PatternInsight(BaseModel):
    """Response model untuk get_pattern_insights tool."""
    pattern_found: bool
    signature: str | None = None
    conditions: list[str] = []
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

---

## 3. Data Flow per Tool (Diperbarui)

## 5. FHIR Resource Mapping (Diperbarui)

| Tool                        | FHIR Resources                                            | Key Parameters                      |
| --------------------------- | --------------------------------------------------------- | ----------------------------------- |
| get_patient_snapshot        | Patient, Condition, MedicationRequest, AllergyIntolerance | patient={id}                        |
| get_active_problems         | Condition                                                 | patient={id}&clinical-status=active |
| get_medication_timeline     | MedicationRequest                                         | patient={id}&authoredon=gt{date}    |
| get_recent_abnormal_labs    | Observation                                               | patient={id}&category=laboratory    |
| detect_deterioration        | Observation                                               | patient={id}&category=vital-signs   |
| get_context_delta           | All above                                                 | \_lastUpdated=gt{date}              |
| **scan_ward_alerts** 🆕     | **Patient, Observation**                                  | **location={ward_id}**              |
| **orchestrate_context** 🆕  | **All above + external**                                  | **patient={id} + MCP calls**        |
| **get_pattern_insights** 🆕 | **None — in-memory store only**                           | **No FHIR call needed**             |

---

## 6. Deployment Architecture (Diperbarui)

Railway.app deployment sudah berjalan:

- URL: `https://amiable-determination-production.up.railway.app`
- MCP endpoint: `.../mcp`
- Auto-deploy dari GitHub push

**Environment variables baru yang perlu ditambahkan di Railway:**

```
MOCK_EXTERNAL_MCP=true
WARD_SCAN_MAX_PATIENTS=20
EVIDENCE_MIN_DATAPOINTS=2
PATTERN_MEMORY_ENABLED=true
PATTERN_SIMILARITY_THRESHOLD=0.8
```

---

## 7. Error Response Format (Tidak Berubah)

_(sama seperti v1.0)_

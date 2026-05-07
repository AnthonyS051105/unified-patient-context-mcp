# SPRINT_PLAN.md — Execution Roadmap
# Unified Patient Context MCP Server

## Instruksi untuk Claude Code

Ikuti sprint ini secara berurutan. Jangan skip fase. Setiap fase harus selesai dan
berfungsi sebelum lanjut ke fase berikutnya. Jalankan tests di akhir setiap fase.

> **Lihat PROGRESS.md untuk status lengkap dan cara resume di session baru.**

---

## PHASE 1: Foundation (Hari 1-3) — ✅ SELESAI

### 1.1 Project Setup — ✅
- [x] `requirements.txt` (mcp, httpx, pydantic, anthropic, pytest, ruff)
- [x] `pyproject.toml` (pytest asyncio=auto, ruff config)
- [x] `.env.example` (termasuk `MOCK_SHARP`, `MOCK_PATIENT_ID`, `MOCK_SHARP_ROLE`)
- [x] `.gitignore`
- [x] `Dockerfile`
- [x] `railway.json`

### 1.2 SHARP Integration — ✅ SELESAI

File: `sharp/context.py`, `sharp/middleware.py`, `sharp/audit.py`

- [x] `SHARPContext` dataclass
- [x] `extract_sharp_context(ctx)` dengan graceful fallback (ctx=None, exception → empty SHARPContext)
- [x] `MOCK_SHARP=true` mode berfungsi dengan `MOCK_PATIENT_ID` dan `MOCK_SHARP_ROLE`
- [x] `resolve_patient_id()` — SHARP patient_id override explicit param
- [x] `build_sharp_metadata()` — never includes ehr_token or patient_id
- [x] `role_is()` — case-insensitive role check
- [x] Zero-PII audit logging (session_id selalu `[REDACTED]` di logs)
- [x] 19 test cases pass

### 1.3 Pydantic Models (`models/`) — ✅
- [x] `models/patient.py` — PatientSnapshot, ActiveProblem, Allergy
- [x] `models/medication.py` — MedicationEntry, InteractionFlag, MedicationTimeline
- [x] `models/lab.py` — LabResult, AbnormalLab, LabTrend
- [x] `models/deterioration.py` — VitalSign, ClinicalScore, DeteriorationReport, ContextDelta

### 1.4 FHIR Client (`integrations/fhir_client.py`) — ✅
- [x] `get_patient()`, `get_conditions()`, `get_medications()`, `get_observations()`
- [x] `get_allergies()`, `get_all_since()` (lastUpdated filter)
- [x] `FHIRError` dengan retry_suggested + to_dict()
- [x] Connectivity verified: `hapi.fhir.org/baseR4` live dan accessible

### 1.5 OpenFDA Client (`integrations/openfda_client.py`) — ✅
- [x] `check_interaction(drug_a, drug_b)` → InteractionFlag | None
- [x] `get_drug_info(drug_name)` — tries generic then brand name
- [x] Severity estimation (major/moderate/minor) dari keyword matching

### 1.6 LLM Client (`integrations/llm_client.py`) — ✅
- [x] `explain()` — base method, graceful None if no API key
- [x] `synthesize()` — Tool 7, max_tokens=600
- [x] `patient_summary()`, `prioritize_problems()` (role-aware)
- [x] `explain_interaction()` (detailed=True for pharmacist)
- [x] `explain_abnormal_lab()`, `explain_deterioration()` (role-aware nurse/physician)
- [x] `explain_context_delta()`

### 1.7 Clinical Engine — ✅
- [x] `engine/news2.py` — NEWS2 per RCP 2017, verified with known scenarios
- [x] `engine/mews.py` — MEWS 5-parameter
- [x] `engine/deduplicator.py` — 50+ brand→generic mappings

### 1.8 Synthea Seeding Script — ✅
- [x] `scripts/seed_synthea.py` — upload bundles, save patient IDs ke JSON
- [ ] **TODO PHASE 4**: Jalankan script dengan actual Synthea bundles

---

## PHASE 2: Core Tools (Hari 4-8) — ✅ SELESAI (dikerjakan dalam Phase 1)

### 2.1 Tool 1: `get_patient_snapshot` — ✅
- [x] asyncio.gather: Patient + Condition + MedicationRequest + AllergyIntolerance
- [x] SHARP: resolve_patient_id, build_sharp_metadata dalam response
- [x] AI: 1-sentence patient summary
- [x] Graceful degradation jika partial FHIR data unavailable

### 2.2 Tool 2: `get_active_problems` — ✅
- [x] SHARP: role-aware urgency prioritization (nurse/physician/pharmacist angle)
- [x] AI: urgency scoring 1-5 dengan reasoning per condition
- [x] Sort by urgency score descending

### 2.3 Tool 3: `get_medication_timeline` — ✅
- [x] Dedup brand/generic via deduplicator.py
- [x] OpenFDA interaction check per drug pair (max 20 pairs)
- [x] SHARP: pharmacist role → detailed interaction explanation
- [x] sharp_metadata di response

### 2.4 Tool 4: `get_recent_abnormal_labs` — ✅
- [x] threshold: critical/abnormal/borderline
- [x] Trend calculation (rising/falling/stable) jika ≥2 data points
- [x] AI: clinical significance explanation per lab
- [x] SHARP: resolve_patient_id + sharp_metadata

---

## PHASE 3: Intelligence Layer (Hari 9-11) — ✅ SELESAI

### 3.1 NEWS2 Engine — ✅
- [x] Semua parameter: RR, SpO2, SBP, HR, Consciousness, Temperature, Supplemental O2
- [x] Risk levels: low/low-medium/medium/high
- [x] Test scenario low risk: score=0 ✓
- [x] Test scenario high risk: score=15, risk=high ✓

### 3.2 MEWS Engine — ✅
- [x] 5 parameter: RR, HR, SBP, Consciousness (AVPU), Temperature
- [x] AVPU scoring A=0, V=1, P=2, U=3

### 3.3 Deduplicator — ✅
- [x] 50+ brand→generic mappings
- [x] `deduplicate_medications()` — merge dan set is_duplicate_merged=True

### 3.4 Tool 5: `detect_clinical_deterioration_signals` — ✅
- [x] LOINC code mapping untuk 10 vital sign types
- [x] BP component extraction (systolic dari composite resource)
- [x] GCS→AVPU conversion
- [x] Triggered rules generation
- [x] SHARP: role-aware narrative (nurse=actionable, physician=technical)
- [x] `confidence="rule-based"`, `action_required_by="clinician"` SELALU ada

### 3.5 Tool 6: `get_patient_context_delta` — ✅
- [x] 4 kategori: labs, meds, vitals, conditions
- [x] AI narrative "In the last X hours, ..."
- [x] `no_changes=true` jika tidak ada perubahan

### 3.6 Tool 7: `synthesize_cross_domain_insights` ⭐ — ✅
- [x] Parallel sub-calls: labs + meds + deterioration via asyncio.gather
- [x] Role-aware LLM prompt (physician/nurse/pharmacist)
- [x] JSON-structured output: synthesis_narrative, confidence_level, data_gaps, cross_domain_patterns
- [x] Sub-call failure handling (graceful, error masuk ke data_gaps)
- [x] Disclaimer + action_required_by="clinician" ALWAYS
- [x] SHARP metadata di response
- [x] 11 test cases pass (termasuk 3 clinical question scenarios)

---

## PHASE 4: Deploy & Polish (Hari 12-13) — ✅ SEBAGIAN SELESAI

### 4.1 README.md — ✅ SELESAI
- [x] Quick start guide
- [x] 7 tools dengan contoh input/output JSON
- [x] ASCII architecture diagram
- [x] SHARP context explanation + how to use with Prompt Opinion
- [x] Design principles, tech stack, project structure

### 4.2 Synthea Seeding & Integration Test — ✅ SELESAI
- [x] Synthetic FHIR R4 bundle dibuat dengan 23 resources (realistic clinical scenario)
- [x] Uploaded ke HAPI FHIR sebagai `synthea-demo-patient` (Eleanor M. Dawson)
- [x] Patient IDs disimpan ke `tests/fixtures/test_patients.json`
- [x] End-to-end test 7/7 tools PASS dengan real patient ID
- [x] Bug fix: `fhir_client.get_medications()` client-side date filtering

### 4.3 Server HTTP Transport — ✅ (sudah done di main.py)
```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

### 4.4 Railway Deployment — ✅ SELESAI
- [x] `railway login && railway init && railway up` — deployed
- [x] Set GEMINI_API_KEY, GEMINI_MODEL, FHIR_BASE_URL, OPENFDA_BASE_URL, FASTMCP_HOST di Railway
- [x] Public URL: https://amiable-determination-production.up.railway.app
- [x] MCP endpoint: https://amiable-determination-production.up.railway.app/mcp
- [x] Status: Online (verified responding, HTTP 406 = normal)

### 4.5 Prompt Opinion Registration & Testing — ✅ SELESAI
- [x] Buat akun di promptopinion.ai (org: NexusHealth)
- [x] Register MCP server "Unified Patient Context Server" di Marketplace Studio
- [x] 7 tools terdeteksi oleh platform
- [x] Buat BYO Agent "Clinical Context Assistant" dengan system prompt klinis
- [x] Import synthetic patient (Edward499 Balistreri607) ke Prompt Opinion
- [x] Test via Launchpad → Patient scope → chat berhasil
- [x] `get_patient_snapshot` berhasil fetch Eleanor M. Dawson dari HAPI FHIR
- [x] Agent merespons dalam Bahasa Indonesia dengan data klinis akurat
- [ ] **TODO**: Publish MCP server ke Marketplace (butuh isi Publisher Profile dulu)

### 4.6 Demo Video Recording — ⏳ TODO (butuh Prompt Opinion account)
Script (3 menit) dengan demo patient `synthea-demo-patient`:
1. (0:00-0:30) Problem statement — 36 menit di EHR per kunjungan 30 menit
2. (0:30-1:00) `get_patient_snapshot` → Eleanor Dawson, T2DM + CKD + HTN
3. (1:00-1:40) `detect_clinical_deterioration_signals` → NEWS2=6 (medium) → AI narrative
4. (1:40-2:15) `synthesize_cross_domain_insights` → "Is creatinine related to new medication?" → KLIMAKS
5. (2:15-2:45) `get_medication_timeline` → metformin + lisinopril interaction
6. (2:45-3:00) Closing tagline

---

## Checklist Final Sebelum Submit

- [x] Semua 7 tools terdaftar dan `server.py` bisa diimport tanpa error
- [x] SHARP context diekstrak tanpa error (test dengan `MOCK_SHARP=true`)
- [x] SHARP metadata muncul di response semua tools
- [x] `synthesize_cross_domain_insights` menghasilkan narrative koheren
- [x] `pytest tests/ -v` → 69 tests pass
- [x] HTTP transport (`streamable-http`) dikonfigurasi di `main.py`
- [x] `Dockerfile` dan `railway.json` siap
- [x] README.md lengkap (quick start, 7 tools JSON examples, SHARP, arsitektur)
- [x] Demo patient `synthea-demo-patient` di HAPI FHIR (7/7 tools verified)
- [ ] `npx @modelcontextprotocol/inspector python main.py` → 7 tools terlihat
- [ ] Railway deployment online dan responding
- [ ] Semua tools registered di Prompt Opinion Marketplace
- [ ] Demo video direkam DI DALAM Prompt Opinion platform
- [ ] Devpost submission form: repo link, demo video, description (mention SHARP + AI Factor)

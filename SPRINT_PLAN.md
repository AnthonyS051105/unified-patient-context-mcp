# SPRINT_PLAN.md — Execution Roadmap
# Unified Patient Context MCP Server

## Instruksi untuk Claude Code
Ikuti sprint ini secara berurutan. Jangan skip fase. Setiap fase harus selesai dan
berfungsi sebelum lanjut ke fase berikutnya. Jalankan tests di akhir setiap fase.

---

## PHASE 1: Foundation (Hari 1-3)

### 1.1 Project Setup
```bash
mkdir unified-patient-mcp && cd unified-patient-mcp
python -m venv venv && source venv/bin/activate
pip install mcp httpx pydantic python-dotenv pytest pytest-asyncio ruff
```

Buat file-file berikut (kosong dulu, isi nanti):
- `requirements.txt` (dengan semua dependencies + versi)
- `pyproject.toml` (konfigurasi pytest dan ruff)
- `.env.example`
- `.gitignore`
- `Dockerfile`
- `railway.json`

### 1.2 Pydantic Models (models/)
Urutan pembuatan:
1. `models/patient.py` — PatientSnapshot, ActiveProblem, Allergy
2. `models/medication.py` — MedicationEntry, InteractionFlag, MedicationTimeline
3. `models/lab.py` — LabResult, AbnormalLab, LabTrend
4. `models/deterioration.py` — VitalSign, ClinicalScore, DeteriorationReport, ContextDelta

### 1.3 FHIR Client (integrations/fhir_client.py)
Implementasikan methods:
- `async get_patient(patient_id)` → dict
- `async get_conditions(patient_id, status="active")` → list
- `async get_medications(patient_id, days=90)` → list
- `async get_observations(patient_id, category, days=30)` → list
- `async get_allergies(patient_id)` → list
- `async get_all_since(patient_id, hours)` → dict (semua resource dengan lastUpdated filter)

Test dengan: `https://hapi.fhir.org/baseR4/Patient?_count=5` (pastikan bisa diakses)

### 1.4 OpenFDA Client (integrations/openfda_client.py)
Implementasikan methods:
- `async check_interaction(drug_a: str, drug_b: str)` → InteractionFlag | None
- `async get_drug_info(drug_name: str)` → dict

### 1.5 Synthea Seeding (scripts/seed_synthea.py)
- Download Synthea sample FHIR R4 bundles
- Upload beberapa patients ke HAPI FHIR public server
- Simpan patient IDs ke `tests/fixtures/test_patients.json`

---

## PHASE 2: Core Tools (Hari 4-8)

### 2.1 Tool: get_patient_snapshot
File: `tools/patient_snapshot.py`
- Fetch Patient + Condition + MedicationRequest + AllergyIntolerance parallel (asyncio.gather)
- Build PatientSnapshot Pydantic model
- Call LLM untuk ai_summary
- Register ke server.py

Test: Panggil dengan patient ID dari Synthea, pastikan semua fields populated

### 2.2 Tool: get_active_problems
File: `tools/active_problems.py`
- Fetch Condition dengan clinical-status=active
- Sort by onset_date (terbaru dulu)
- Optional: include resolved
- AI: prioritize by urgency (1-3 sentence reasoning per condition)

### 2.3 Tool: get_medication_timeline
File: `tools/medications.py`
- Fetch MedicationRequest dalam date range
- Deduplicate brand/generic via deduplicator.py
- Check interactions via OpenFDA untuk setiap pair obat
- AI: explain each interaction dalam 1-2 kalimat

### 2.4 Tool: get_recent_abnormal_labs
File: `tools/lab_results.py`
- Fetch Observation category=laboratory
- Filter berdasarkan interpretationCode (H/HH/L/LL) atau bandingkan dengan referenceRange
- Calculate trend jika ≥2 datapoints tersedia
- AI: clinical significance explanation per abnormal result

---

## PHASE 3: Intelligence Layer (Hari 9-11)

### 3.1 NEWS2 Engine (engine/news2.py)
- Implementasikan scoring table sesuai ARCHITECTURE.md
- Input: dict of vital signs values
- Output: `{"score": int, "risk_level": str, "parameter_scores": dict}`
- WAJIB: unit test dengan known clinical scenarios

Test scenarios (dari literatur):
```python
# Scenario 1: Low risk patient
vitals = {"rr": 16, "spo2": 97, "sbp": 120, "hr": 75, "temp": 37.0, "consciousness": "A"}
assert news2_score(vitals) == {"score": 0, "risk_level": "low"}

# Scenario 2: High risk patient
vitals = {"rr": 26, "spo2": 90, "sbp": 88, "hr": 115, "temp": 38.5, "consciousness": "V"}
assert news2_score(vitals)["risk_level"] == "high"
```

### 3.2 MEWS Engine (engine/mews.py)
Scoring: RR, HR, Systolic BP, Consciousness, Temperature
Mirip NEWS2 tapi 5 parameter.

### 3.3 Deduplicator (engine/deduplicator.py)
- Mapping common brand → generic names (hardcoded dict + fuzzy match)
- `def deduplicate_medications(med_list: list) -> list`

### 3.4 Tool: detect_clinical_deterioration_signals
File: `tools/deterioration.py`
- Fetch vital signs dari FHIR (hours_lookback)
- Run NEWS2 + MEWS
- Map scores ke triggered_rules
- AI: generate clinical_narrative berdasarkan rules (BUKAN berdasarkan prediksi bebas)
- WAJIB: output selalu ada `confidence: "rule-based"` dan `action_required_by: "clinician"`

### 3.5 Tool: get_patient_context_delta
File: `tools/context_delta.py`
- Query semua resources dengan `_lastUpdated=gt{since_hours ago}`
- Categorize changes: new_labs, changed_medications, new_vitals, new_conditions
- AI: generate narrative "Dalam X jam terakhir, ..."

---

## PHASE 4: Deploy & Polish (Hari 12-13)

### 4.1 Server HTTP Transport
Update `main.py` untuk support Streamable HTTP:
```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

### 4.2 Test Suite Lengkap
`tests/test_tools.py`:
- Test setiap tool dengan Synthea patient IDs
- Test graceful degradation (mock FHIR server down)
- Test LLM fallback (mock Anthropic API error)

### 4.3 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
```

### 4.4 README.md
Wajib ada:
- Quick start guide
- Semua 6 tools dengan contoh input dan output (JSON)
- Architecture diagram (ASCII)
- How to register di Prompt Opinion platform
- Link ke demo video

### 4.5 Deploy ke Railway
```bash
railway login && railway init && railway up
```
Set environment variables di Railway dashboard.

### 4.6 Register di Prompt Opinion
- Buat akun di promptopinion.ai
- Register MCP server URL
- Test via platform interface

---

## Checklist Final Sebelum Submit

- [ ] `npx @modelcontextprotocol/inspector python main.py` → semua 6 tools terlihat dan bisa di-invoke
- [ ] `pytest tests/ -v` → minimal 10 tests pass
- [ ] Railway deployment online dan responding
- [ ] Semua tools registered di Prompt Opinion Marketplace
- [ ] README.md dengan contoh output setiap tool
- [ ] Demo video 3 menit sesuai script di CLAUDE.md
- [ ] Devpost submission form lengkap dengan: repo link, demo video, description

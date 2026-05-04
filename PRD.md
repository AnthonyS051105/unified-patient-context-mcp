# PRD — Product Requirements Document
# Unified Patient Context MCP Server
# Hackathon: Agents Assemble — The Healthcare AI Endgame

---

## 1. Executive Summary

**Nama Produk:** Unified Patient Context MCP Server  
**Tagline:** *"One call. Full context. Every agent."*  
**Tipe Submission:** Option 1 — Build a Superpower (MCP Server)  
**Target Pengguna:** AI agents yang beroperasi di dalam platform Prompt Opinion untuk membantu klinisi  

### Problem Statement
Di ekosistem healthcare AI saat ini, setiap agent harus "wawancara" 5-10 sistem berbeda (EHR, lab system,
pharmacy system, wearable gateway) hanya untuk memahami kondisi satu pasien. Ini menciptakan:
- **Latency tinggi** — agent lambat karena harus query banyak sistem
- **Konteks tidak lengkap** — agent bertindak berdasarkan informasi parsial
- **Duplikasi data** — obat yang sama dari dua sumber dianggap dua entry berbeda
- **Risiko klinis** — deteriorasi pasien tidak terdeteksi karena data tersebar

### Solution Statement
MCP server ini menjadi **intelligence layer** di antara agents dan sumber data klinis. Agent tidak perlu
tahu FHIR, HL7, atau OpenFDA exists. Mereka cukup memanggil tools berbahasa klinis dan mendapat
konteks pasien yang sudah diproses, dideduplikasi, dan dijelaskan dalam bahasa natural.

---

## 2. Goals & Success Metrics

### Hackathon Goals
| Goal | Metric | Target |
|---|---|---|
| Semua tools berfungsi | Tools bisa di-invoke via MCP Inspector | 6/6 tools |
| Clinical accuracy | NEWS2 score sesuai algoritma resmi | 100% |
| Drug interaction detection | OpenFDA integration berjalan | ≥1 interaksi terdeteksi di demo |
| Response time | Latency per tool call | < 3 detik |
| Demo quality | Video 3 menit menunjukkan semua tools | Complete |

### Impact Goals (Post-Hackathon Vision)
- Mengurangi waktu yang dihabiskan klinisi untuk mengumpulkan konteks pasien dari rata-rata 8 menit → < 30 detik
- Menjadi foundational MCP tool yang digunakan oleh 10+ specialized agents di Prompt Opinion Marketplace

---

## 3. User Stories

### Primary User: Healthcare AI Agent
```
SEBAGAI sebuah diagnosis agent di Prompt Opinion platform,
SAYA INGIN memanggil satu tool untuk mendapat konteks lengkap pasien,
AGAR SAYA bisa memberikan rekomendasi yang akurat tanpa query manual ke FHIR.
```

```
SEBAGAI sebuah triage agent,
SAYA INGIN mengetahui apakah ada sinyal deteriorasi pada pasien saat ini,
AGAR SAYA bisa memprioritaskan eskalasi ke klinisi yang tepat waktu.
```

```
SEBAGAI sebuah medication management agent,
SAYA INGIN melihat seluruh timeline obat pasien beserta flag interaksi,
AGAR SAYA bisa mendeteksi potensi medication error sebelum dispensing.
```

### Secondary User: Klinisi (via agent intermediary)
```
SEBAGAI seorang dokter jaga,
SAYA INGIN agent saya bisa memberi briefing pasien dalam hitungan detik,
AGAR SAYA bisa fokus pada keputusan klinis, bukan pengumpulan data.
```

---

## 4. Functional Requirements

### FR-01: get_patient_snapshot
- **HARUS** mengambil data dari FHIR resources: Patient, Condition, MedicationRequest, AllergyIntolerance
- **HARUS** menghasilkan AI-generated 1-sentence summary kondisi pasien
- **HARUS** mencantumkan `data_sources` (list FHIR resources yang diquery)
- **HARUS** mencantumkan `last_updated` timestamp
- **BOLEH** mengembalikan partial data jika sebagian resource tidak tersedia (graceful degradation)

### FR-02: get_active_problems
- **HARUS** hanya mengembalikan Condition dengan status "active" secara default
- **HARUS** include `onset_date` jika tersedia di FHIR
- **HARUS** include `severity` jika tersedia
- **BOLEH** include resolved conditions jika `include_resolved=True`

### FR-03: get_medication_timeline
- **HARUS** query MedicationRequest dari FHIR dalam window `days` terakhir
- **HARUS** query OpenFDA untuk setiap pasangan obat (drug interaction check)
- **HARUS** melakukan deduplication brand vs generic name
- **HARUS** mengembalikan `interaction_flags` jika ada interaksi terdeteksi
- **HARUS** AI-generated explanation untuk setiap interaction flag

### FR-04: get_recent_abnormal_labs
- **HARUS** query FHIR Observation dengan category=laboratory
- **HARUS** filter berdasarkan `threshold`: critical/abnormal/borderline
- **HARUS** menghitung trend (naik/turun/stabil) jika ada ≥2 data points
- **HARUS** AI-generated clinical significance explanation per abnormal lab

### FR-05: detect_clinical_deterioration_signals
- **HARUS** mengimplementasikan NEWS2 scoring algorithm secara akurat
- **HARUS** mengimplementasikan MEWS scoring algorithm secara akurat
- **HARUS** query vital signs dari FHIR Observation dalam window `hours_lookback`
- **HARUS** output selalu menyertakan `confidence: "rule-based"` dan `action_required_by: "clinician"`
- **HARUS** AI-generated explanation dalam bahasa yang bisa dipahami klinisi non-spesialis
- **TIDAK BOLEH** output mengandung kata "diagnose", "diagnosis", atau "prescribe"

### FR-06: get_patient_context_delta
- **HARUS** menggunakan FHIR `_lastUpdated` filter untuk efisiensi
- **HARUS** mengembalikan perubahan dalam 4 kategori: labs, medications, vitals, conditions
- **HARUS** AI-generated narrative summary: "Dalam X jam terakhir, ..."
- **HARUS** mengembalikan `no_changes: true` dengan explanation jika tidak ada perubahan

---

## 5. Non-Functional Requirements

### NFR-01: Performance
- Response time per tool call: < 3 detik (P95)
- Concurrent requests: server harus handle minimal 10 simultaneous tool calls

### NFR-02: Reliability
- Jika FHIR server timeout: return error dengan `retry_suggested: true`
- Jika OpenFDA tidak tersedia: return medication list tanpa interaction flags, dengan warning
- Jika LLM API gagal: return structured data tanpa AI explanation, dengan flag `ai_explanation: null`

### NFR-03: Security & Privacy
- Zero persistent storage pasien data
- API keys disimpan di environment variables, tidak pernah di-hardcode
- Patient ID tidak boleh muncul di application logs

### NFR-04: Maintainability
- Setiap tool harus punya docstring yang menjelaskan input, output, dan data sources
- Semua integration clients harus mockable untuk testing
- Coverage minimal 70% untuk engine/ dan integrations/

---

## 6. Out of Scope (untuk hackathon)

- Autentikasi OAuth2 SMART on FHIR (disimulasikan dengan HAPI public server)
- Real EHR integration (Epic, Cerner) — gunakan HAPI FHIR
- Real-time streaming vital signs dari wearable hardware
- Multi-tenant / multi-organization support
- Persistent audit logging (HIPAA-grade)
- Front-end UI (MCP server adalah backend tool, bukan aplikasi)

---

## 7. Timeline

| Fase | Durasi | Deliverable |
|---|---|---|
| Phase 1: Foundation | 3 hari | Project setup, FHIR client, Pydantic models, Synthea seeding |
| Phase 2: Core Tools | 5 hari | Tools 1-4 berfungsi dan tested |
| Phase 3: Intelligence | 3 hari | Tool 5 (NEWS2/MEWS) + Tool 6 (delta) + LLM integration |
| Phase 4: Deploy & Demo | 2 hari | Railway deploy, README, demo video recording |
| **Total** | **~13 hari** | **Submission-ready** |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| HAPI FHIR public server down | Medium | High | Cache last-known state, dokumentasikan alternatif (SMART Health IT sandbox) |
| OpenFDA rate limiting | Low | Medium | Implement exponential backoff, cache drug interaction results |
| NEWS2 algorithm error | Low | High | Test dengan known clinical scenarios dari literatur medis |
| LLM explanation hallucination | Medium | High | Prompt engineering ketat, selalu berdasarkan structured data, bukan opini bebas |
| Prompt Opinion platform integration issues | Medium | High | Test via MCP Inspector dulu, dokumentasikan troubleshooting |

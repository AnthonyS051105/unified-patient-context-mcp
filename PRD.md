# PRD — Product Requirements Document

# Nara by NexusHealth — Unified Patient Context MCP Server

# Version: 3.0 — Clinical Pattern Memory Edition

# Hackathon: Agents Assemble — The Healthcare AI Endgame

---

## 1. Executive Summary

**Nama Produk:** Nara by NexusHealth
**Tagline:** _"One call. Full picture."_
**Tipe Submission:** Option 1 — Build a Superpower (MCP Server)
**Target Pengguna:** AI agents di Prompt Opinion platform yang membantu klinisi

### Problem Statement (Diperbarui)

Di ekosistem healthcare AI saat ini, tiga masalah fundamental belum terpecahkan:

1. **Fragmentasi data** — Agent harus query 5-10 sistem hanya untuk satu pasien
2. **Output satu ukuran untuk semua** — Dokter, perawat, apoteker, dan pasien mendapat
   informasi yang sama padahal kebutuhan mereka sangat berbeda
3. **AI yang reaktif** — Agent hanya menjawab saat ditanya; tidak ada yang memindai
   keseluruhan ward untuk mendeteksi pasien berisiko secara proaktif
4. **Black box reasoning** — Klinisi tidak tahu _mengapa_ AI menghasilkan rekomendasi tertentu
5. **Silo antar MCP servers** — Setiap MCP server bekerja sendiri; tidak ada yang mengorkestrasi data lintas server
6. **Amnesia per-call** — Setiap AI call bersifat stateless total; tidak ada akumulasi pola dari shift/session sehingga insight tidak semakin kaya seiring waktu

### Solution Statement (Diperbarui)

Nara adalah **proactive, adaptive, transparent, pattern-aware intelligence layer** untuk healthcare AI:

- **Proactive:** Memindai ward dan memberi alert tanpa harus diminta
- **Adaptive:** Menyesuaikan output secara fundamental berdasarkan role klinisi
- **Transparent:** Menyertakan evidence trail yang menjelaskan confidence dan sumber data
- **Interoperable:** Mengorkestrasi MCP server lain untuk unified cross-system context
- **Pattern-aware:** Mengakumulasi pola klinis anonim selama session dan memberikan konteks historis 🆕

---

## 2. Goals & Success Metrics

### Hackathon Goals (v2.0)

| Goal                       | Metric                                 | Target                                     |
| -------------------------- | -------------------------------------- | ------------------------------------------ |
| Core tools berfungsi       | 7 tools invocable                      | ✅ Done (69 tests)                         |
| SHARP integration          | Context diekstrak & dipropagasi        | ✅ Done                                    |
| Adaptive Clinical Persona  | Output berbeda per 4 roles             | persona_applied di semua tools             |
| Proactive Ward Alert       | scan_ward_alerts berjalan              | ≥3 patients di demo                        |
| Evidence Trail             | Confidence + weights di synthesis      | evidence_trail di tools 4,5,7,9            |
| Meta-Orchestrator          | Call ke external MCP berhasil          | ≥1 mock server integration                 |
| Clinical Pattern Memory 🆕 | Pattern terakumulasi & query berfungsi | ≥3 patterns tercatat dalam demo session    |
| Total tests                | pytest pass                            | ≥100 tests                                 |
| Demo quality               | 3 menit di Prompt Opinion              | Complete — semua 4 fitur advanced terlihat |

### Impact Goals (Diperbarui)

- Mengurangi waktu pengumpulan konteks pasien: 8 menit → <30 detik
- Mengurangi waktu klinisi memilah informasi: tambahan 5 menit → 0 (Adaptive Persona)
- Memungkinkan deteksi proaktif pasien berisiko di ward tanpa rounding manual

---

## 3. User Stories (Diperbarui)

### Existing User Stories (tetap berlaku)

_(semua user story v1.0 tetap berlaku)_

### 🆕 User Stories Advanced Features

```
SEBAGAI seorang perawat yang sedang jaga malam di ICU,
SAYA INGIN bisa tanya "siapa yang butuh perhatian sekarang?"
dan mendapat daftar prioritas pasien berdasarkan sinyal klinis aktual,
AGAR SAYA bisa mengalokasikan waktu dengan tepat tanpa harus cek
setiap pasien satu per satu.
[→ Proactive Ward Alert]
```

```
SEBAGAI seorang apoteker yang menerima order obat baru,
SAYA INGIN Nara menjelaskan situasi pasien dalam konteks medication —
bukan dalam bahasa diagnosa dokter,
AGAR SAYA bisa langsung fokus pada drug interaction dan renal dosing
tanpa harus mentranslate informasi klinis.
[→ Adaptive Clinical Persona]
```

```
SEBAGAI dokter yang akan membuat keputusan klinis penting,
SAYA INGIN tahu seberapa yakin Nara dengan insight-nya dan data apa
yang digunakan sebagai dasarnya,
AGAR SAYA bisa mengevaluasi rekomendasi dengan kritis dan tahu
data apa yang perlu saya cari tambahan.
[→ Confidence-Weighted Evidence Trail]
```

```
SEBAGAI sistem multi-agent di Prompt Opinion,
SAYA INGIN Nara bisa mengambil data dari radiology MCP dan pharmacy MCP
sekaligus dalam satu panggilan,
AGAR SAYA tidak perlu mengkoordinasikan multiple tool calls sendiri.
[→ Meta-Orchestrator]
```

```
SEBAGAI sebuah clinical reasoning agent yang menangani banyak pasien dalam satu shift,
SAYA INGIN tahu apakah pola klinis yang saya lihat pada pasien ini
juga terlihat pada pasien lain hari ini,
AGAR SAYA bisa mendeteksi kemungkinan pola ward-level dan mengeskalasi
ke perhatian sistemik — bukan hanya individual.
[→ Clinical Pattern Memory]
```

---

## 4. Functional Requirements (v2.0)

### FR-00 hingga FR-07 (tetap berlaku dari v1.0)

_(semua requirements sebelumnya tetap berlaku dan sudah implemented)_

---

### FR-08: Adaptive Clinical Persona Engine

- **HARUS** mengimplementasikan `persona/adapter.py` dengan `PersonaAdapter` class
- **HARUS** mendefinisikan 4 `RoleProfile` di `persona/profiles.py`:
  - `physician`: full clinical reasoning, medical terminology, complete data
  - `nurse`: actionable bullets, monitoring thresholds, escalation triggers
  - `pharmacist`: medication-centric, interaction severity, renal dosing flags
  - `patient`: plain language, 6th grade level, next steps only
- **HARUS** mengubah TIGA aspek output sekaligus (bukan hanya bahasa):
  - `format`: narrative | bullets | table | simple
  - `depth`: full | summary | medication-focused | simplified
  - `content_priority`: what gets surfaced first based on role
- **HARUS** menyertakan `persona_applied` field di setiap response
- **HARUS** menyertakan `original_available: true` untuk physician (bisa minta raw data)
- **BOLEH** default ke `physician` jika role tidak diketahui
- **TIDAK BOLEH** membuang data klinis penting meski di mode `patient` — hanya sederhanakan

**Contoh transformasi untuk query yang sama (`get_patient_snapshot`):**

```
physician output:
  "68yo female presenting with T2DM (HbA1c 8.2%), stage 3 CKD (eGFR ~25),
   and hypertension on ACE inhibitor therapy. Creatinine trending upward
   at 1.8 mg/dL — 80% above baseline..."

nurse output:
  "⚠ Eleanor Dawson, 68F
   WATCH: Kidney numbers rising (creatinine 1.8, was 1.0)
   MONITOR: Urine output hourly (target >30mL/hr)
   ESCALATE if: <30mL/hr, or creatinine >2.0"

pharmacist output:
  "MEDICATION REVIEW NEEDED
   Metformin 500mg: CONTRAINDICATED if eGFR <30
   Estimated eGFR: ~25 based on current creatinine
   ACTION: Hold metformin pending nephrologist review"

patient output:
  "Hello! Here's what we know about your health right now:
   Your kidneys need some extra attention. Your doctor will
   review your medicines to make sure they're still right for you."
```

---

### FR-09: Proactive Ward Alert Tool (`scan_ward_alerts`)

- **HARUS** menerima `ward_id` sebagai FHIR Location ID atau string identifier
- **HARUS** query semua pasien di ward via FHIR `Patient?location={ward_id}`
- **HARUS** menjalankan `detect_clinical_deterioration_signals` parallel untuk semua pasien
- **HARUS** mengurutkan hasil berdasarkan risk score descending
- **HARUS** filter berdasarkan `threshold`: "critical" | "high" | "medium"
- **HARUS** menyertakan `time_since_last_assessment` per patient (dari FHIR lastUpdated)
- **HARUS** apply Adaptive Clinical Persona berdasarkan `sharp.role`
- **HARUS** menyertakan Evidence Trail per alert
- **HARUS** return `patients_scanned` dan `scan_timestamp`
- **HARUS** gracefully handle jika ward kosong (`no_alerts_found: true`)
- **BOLEH** limit ke `max_patients` untuk performance (default: 20)
- **TIDAK BOLEH** exceed 10 detik total response time untuk 20 pasien

---

### FR-10: Confidence-Weighted Evidence Trail

- **HARUS** mengimplementasikan `evidence/scorer.py` dengan `EvidenceScorer`
- **HARUS** menghitung `weight` (0.0-1.0) per sumber data berdasarkan:
  - Recency: data lebih baru = weight lebih tinggi
  - Completeness: data point lebih banyak = weight lebih tinggi
  - Quality: "complete" > "partial" > "estimated"
- **HARUS** menghasilkan `overall_confidence` sebagai weighted average
- **HARUS** memetakan confidence ke label: "high" (>0.8) | "moderate" (0.5-0.8) | "low" (<0.5)
- **HARUS** menyertakan `missing_data` list — data apa yang seharusnya ada
- **HARUS** menyertakan `transparency_note` dalam bahasa natural yang menjelaskan confidence
- **HARUS** diintegrasikan ke tools: 4 (labs), 5 (deterioration), 7 (synthesis), 9 (orchestrate)
- **TIDAK BOLEH** generate confidence yang menyesatkan — lebih baik "low" dari "high" palsu

---

### FR-11: Meta-Orchestrator Tool (`orchestrate_context_from_sources`)

- **HARUS** mengimplementasikan `integrations/mcp_client.py` sebagai MCP-to-MCP HTTP client
- **HARUS** menerima `sources` parameter: list of MCP server identifiers
- **HARUS** memanggil tools dari setiap MCP server secara parallel via asyncio.gather
- **HARUS** gracefully handle jika external server tidak tersedia (`available: false` di response)
- **HARUS** menyertakan `sources_queried`, `sources_available`, `sources_failed`
- **HARUS** mensintesis data dari semua sumber via LLM ke dalam unified narrative
- **HARUS** menyertakan Evidence Trail yang mencakup semua sumber
- **HARUS** apply Adaptive Clinical Persona ke unified output
- **BOLEH** menggunakan mock servers (`MOCK_EXTERNAL_MCP=true`) untuk demo
- **Mock servers yang harus tersedia:**
  - `radiology_mcp`: returns synthetic imaging findings
  - `pharmacy_mcp`: returns dispensing records

---

### FR-12: Clinical Pattern Memory (`get_pattern_insights`) 🆕

- **HARUS** mengimplementasikan `memory/store.py` dengan `ClinicalPatternMemory` sebagai singleton in-memory store
- **HARUS** mengimplementasikan `memory/signature.py` dengan `PatternSignature` yang mengekstrak kondisi GENERIK (bukan nilai numerik pasien)
- **HARUS** menggunakan SHA-256 hash dari sorted conditions sebagai kunci store
- **TIDAK BOLEH** menyimpan patient_id, nama pasien, atau nilai klinis numerik mentah di store
- **TIDAK BOLEH** melakukan disk write atau database call apapun — pure in-memory
- **HARUS** auto-record pattern setiap kali Tool 5 dan Tool 7 dijalankan (background, non-blocking)
- **HARUS** menyediakan tool `get_pattern_insights(patient_id, conditions?)` untuk query manual
- **HARUS** menyertakan di setiap response:
  - `data_scope: "current_session_only"` — selalu ada
  - `session_reset_note` — menjelaskan bahwa store reset saat restart
  - `confidence: "low"` jika observations < 5, `"moderate"` jika ≥ 5
  - `confidence_note` — disclaimer bahwa ini bukan statistical claim
  - `action_required_by: "clinician"` — selalu ada
- **HARUS** gracefully return `pattern_found: false` jika belum ada pattern serupa dalam session
- **BOLEH** dinonaktifkan via `PATTERN_MEMORY_ENABLED=false` environment variable
- **Contoh kondisi generik yang boleh disimpan:**
  - `"news2_high_risk"`, `"creatinine_rising_trend"`, `"metformin_present"`, `"active_drug_interaction"`
- **Contoh yang TIDAK BOLEH disimpan:**
  - `"creatinine=1.8"` (nilai spesifik), `"patient_eleanor"` (identitas), `"ward_icu_a_bed_3"` (lokasi)

---

## 5. Non-Functional Requirements (Diperbarui)

### NFR-01: Performance (Diperbarui)

- Response time per tool call: < 3 detik (P95)
- `scan_ward_alerts` untuk 20 pasien: < 10 detik (parallel execution)
- `orchestrate_context_from_sources` dengan 3 sources: < 8 detik

### NFR-02: Reliability (tetap)

_(sama seperti v1.0)_

### NFR-03: Security & Privacy (tetap)

_(sama seperti v1.0)_

### NFR-04: Maintainability (Diperbarui)

- Coverage minimal 70% untuk semua module baru (persona/, evidence/)
- Semua mock servers harus terdokumentasi dengan jelas
- PersonaAdapter harus bisa di-extend tanpa modifikasi existing code

### NFR-05: Transparency (Baru) 🆕

- Setiap response dari tools 4, 5, 7, 9 HARUS menyertakan `evidence_trail`
- `persona_applied` HARUS selalu ada di setiap response
- AI-generated content HARUS selalu ditandai `"ai_generated": true`

---

## 6. Out of Scope (Diperbarui)

- Real external MCP server integration (gunakan mocks untuk demo)
- Real-time streaming data
- Persistent storage
- Front-end UI
- OAuth2 SMART on FHIR
- Production-grade HIPAA compliance (demo uses synthetic data)

---

## 7. Timeline (Diperbarui)

| Fase                           | Status     | Durasi       | Deliverable                               |
| ------------------------------ | ---------- | ------------ | ----------------------------------------- |
| Phase 1: Foundation            | ✅ Done    | 3 hari       | Project setup, FHIR client, models        |
| Phase 2: Core Tools            | ✅ Done    | 5 hari       | Tools 1-4                                 |
| Phase 3: Intelligence          | ✅ Done    | 3 hari       | Tools 5-7, NEWS2/MEWS                     |
| Phase 4: Deploy & Demo         | ✅ Partial | 2 hari       | Railway, Prompt Opinion                   |
| **Phase 5: Advanced Features** | 🆕 TODO    | **3 hari**   | **Persona, Evidence, Ward, Orchestrator** |
| **Phase 5.5: Pattern Memory**  | 🆕 TODO    | **1 hari**   | **Clinical Pattern Memory + Tool 10**     |
| Phase 6: Integration & Demo    | 🆕 TODO    | 2 hari       | Update demo video, final testing          |
| **Total**                      |            | **~19 hari** | **Submission-ready v3.0**                 |

### Phase 5 Detail Breakdown:

| Hari   | Target                                                              |
| ------ | ------------------------------------------------------------------- |
| Hari 1 | `evidence/` module + integrasikan ke tools 5 & 7                    |
| Hari 2 | `persona/` module + integrasikan ke semua tools                     |
| Hari 3 | `scan_ward_alerts` + `orchestrate_context_from_sources` + mock MCPs |
| Hari 4 | Integration testing semua fitur, bug fixes                          |
| Hari 5 | Demo video recording v2.0, update README & Devpost description      |

---

## 8. Risks & Mitigations (Diperbarui)

| Risk                                          | Likelihood | Impact | Mitigation                                                                        |
| --------------------------------------------- | ---------- | ------ | --------------------------------------------------------------------------------- |
| HAPI FHIR server down                         | Medium     | High   | Cache last-known state                                                            |
| OpenFDA rate limiting                         | Low        | Medium | Exponential backoff                                                               |
| Ward scan timeout (>20 patients)              | Medium     | Medium | max_patients cap + timeout per patient                                            |
| External MCP unavailable                      | High       | Low    | Mock servers sudah direncanakan                                                   |
| Persona output terlalu berbeda (inconsistent) | Medium     | Medium | Prompt templates yang ketat per role                                              |
| Evidence weights tidak akurat secara klinis   | Medium     | High   | Validasi dengan known clinical scenarios                                          |
| Persona output terlalu berbeda (inconsistent) | Medium     | Medium | Prompt templates yang ketat per role                                              |
| Evidence weights tidak akurat secara klinis   | Medium     | High   | Validasi dengan known clinical scenarios                                          |
| Pattern Memory mengakumulasi terlalu lambat   | Medium     | Medium | Seed dengan 3+ synthetic patients di awal demo session                            |
| Juri salah mengira Pattern Memory simpan PII  | Low        | High   | Disclaimer eksplisit di setiap response + dokumentasi arsitektur yang jelas       |
| Deadline terlalu mepet (11 Mei)               | High       | High   | Pattern Memory scope terkecil — implementasi terakhir, bisa skip jika waktu habis |

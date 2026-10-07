# Pipeline Technical Documentation & Architecture Deep-Dive

This document provides detailed technical documentation for the Generalized Data Cleaning & Entity Resolution Pipeline.

---

## 1. System Philosophy & Boundaries

As formulated in [DataCleaning_Schema.md](DataCleaning_Schema.md) and [Generalization.md](Generalization.md):
- **Deterministic Cleaning**: Applied to data fields where zero distortion can be tolerated (Names, Saudi Phones, Emails, Dates, Academic Levels).
- **Stochastic / AI Assistance**: Applied to Schema Contracting, Header Grouping, and Fuzzy Entity Linkage.
- **Master Data Management (MDM)**: Entity resolution creates deterministic UUIDv5 identifiers internally to link participants across batches and sheets, while final business exports retain clean, natural columns.

---

## 2. Module-by-Module Specification

### A. [`pipeline/schema.py`](../pipeline/schema.py)
Defines standard Pydantic models:
1. `CleanPerson`:
   - Dimension entity in `dim_persons`.
   - Primary key: `person_id` generated via `uuid.uuid5(PIPELINE_NAMESPACE, canonical_key)`.
   - Attributes: `canonical_email`, `canonical_phone_e164`, `full_name_ar`, `full_name_en`, `first_name`, `father_name`, `family_name`, `clean_display_name`.
2. `FactRegistration`:
   - Transactional registration event in `fact_registrations`.
   - Links to `dim_persons` via `person_id`.
   - Stores core workshop metadata + dynamic survey answers in `raw_metadata` (JSONB).
3. `QuarantineRecord`:
   - Dead-letter record capturing source file, sheet name, row index, raw payload, and machine-readable rejection codes.
4. `AuditSummary`:
   - Governance record capturing total rows, valid rows, quarantine count, duplicate merge count, and pipeline health status.

---

### B. [`pipeline/name_parser.py`](../pipeline/name_parser.py)
Provides compound-aware Arabic and English name parsing:
1. **Honorific Stripping**:
   - Arabic: `م.`, `د.`, `أ.`, `أ.د.`, `دكتور`, `مهندس`, `أستاذ`, `الشيخ`.
   - English: `Dr.`, `Eng.`, `Prof.`, `Mr.`, `Ms.`, `Mrs.`
2. **Compound Bonding (`bond_arabic_tokens`)**:
   - Theophoric prefixes that bond to the next word: `عبد`, `سيف`, `نور`, `شمس`, `علاء`, `جمال`, `صلاح`, `حسام`, `تقي`, `ضياء`, `محي`, `عماد`, `شرف`, `بدر`, `نجم`.
   - Example: `['عبد', 'الله']` $\rightarrow$ `['عبدالله']`.
3. **Patronymic / Clan Particle Preservation**:
   - Particles preserved with space: `آل`, `ابن`, `بن`, `أبو`, `أبي`, `أم`, `با`.
   - Example: `['أحمد', 'بن', 'إبراهيم', 'آل', 'سعود']` $\rightarrow$ `['أحمد', 'بن إبراهيم', 'آل سعود']`.
4. **Tri-part Decomposition**:
   - Extracted into: `First Name`, `Father Name`, `Family Name`.
5. **Inverted English Parsing**:
   - Inverted comma format: `Al-Harbi, Salman` $\rightarrow$ First: `Salman`, Family: `Al-Harbi`.
6. **Key Normalization for Entity Matching (`normalize_for_matching`)**:
   - Hamzas normalized: `[إأآا]` $\rightarrow$ `ا`.
   - Taa Marbuta normalized: `ة` $\rightarrow$ `ه`.
   - Alif Maqsura normalized: `ى` $\rightarrow$ `ي`.
   - Harakat / Diacritics stripped.

---

### C. [`pipeline/normalizers.py`](../pipeline/normalizers.py)

#### 1. `PhoneNormalizer`
- **Region**: Saudi Arabia (`SA` / `+966`).
- **Excel Drop-Zero Repair**: Detects 9-digit numbers starting with `5` (e.g. `508889900` or numeric float `508889900.0`) and prepends `0` before parsing.
- **Double Zero Prefix**: Replaces leading `00` with `+` (`00966...` $\rightarrow$ `+966...`).
- **Redundant Local Zero**: Fixes `+96605...` or `96605...` $\rightarrow$ `+9665...`.
- **Output**: Strict E.164 standard format (`+9665XXXXXXXX`).

#### 2. `EmailNormalizer`
- **Cleanup**: Trims whitespace, strips `mailto:` prefix, converts to lowercase.
- **Typo Domain Healing**:
  - `gmaill.com`, `gamil.com`, `gmial.com` $\rightarrow$ `gmail.com`
  - `hotmaill.com`, `hotmial.com` $\rightarrow$ `hotmail.com`
  - `outloo.com` $\rightarrow$ `outlook.com`
  - `yaho.com` $\rightarrow$ `yahoo.com`
- **Syntax**: Verified against standard email regex; invalid syntax returns `None`.

#### 3. `DateTimeNormalizer`
- **Excel Numeric Serials**: Floating point serials (e.g., `46266.6125`) are converted using the Excel epoch (`1899-12-30`) to UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`).
- **Heterogeneous Strings**: Tries 12 common date/time formats with 12h AM/PM and 24h notations.

#### 4. `CategoricalNormalizer`
- **Boolean Evaluation**:
  - True: `{"نعم", "موافق", "أوافق", "yes", "true", "1", "حضر", "حاضر", "attended", "present"}` $\rightarrow$ `True`.
  - False: `{"لا", "غير موافق", "no", "false", "0", "غائب", "لم يحضر", "absent"}` $\rightarrow$ `False`.
- **Multi-Select Normalization**:
  - Splits delimited strings by `[,;،\n]`.
  - Trims, deduplicates, and rejoins cleanly with standard delimiter.
- **Native Saudi Academic Level Vocabulary**:
  - Mapped directly to higher education stages:
    - Preparatory: `سنة تحضيرية`
    - Years 1-5: `بكالوريوس - سنة 1` to `بكالوريوس - سنة 5`
    - Internship Year: `سنة امتياز`
    - Postgrad / Graduation: `خريج`, `ماجستير`, `دكتوراه`
  - **Zero Pseudo-Normalization**: Preserves unlisted academic descriptions without destructive translation.
- **University Acronyms**:
  - Maps `UJ`, `KSU`, `PNU`, `KFUPM`, `KAU`, `IMSIU`, `IAU` to their official full Arabic names.

---

### D. [`pipeline/contract_generator.py`](../pipeline/contract_generator.py)
Automated schema contractor and classifier:
- Evaluates raw column headers and 3-5 sample values per column.
- Automatically assigns each column to one of the 4 Schema Groups:
  - `Identity`
  - `Structured/MetaData`
  - `Categorical/MultiSelect`
  - `Free-Form`
- Assigns canonical target fields (`full_name_ar`, `full_name_en`, `email`, `phone`, `registered_at`, `major`, `university`, etc.).
- Saves contract to `config/<dataset_id>_contract.yaml`.

---

### E. [`pipeline/entity_resolver.py`](../pipeline/entity_resolver.py)
Internal Master Data Management (MDM) entity resolution:
1. **Indexing**: In-memory hash indexing on canonical E.164 phone and lowercase email.
2. **Probabilistic Linkage**: Jaro-Winkler string similarity on normalized name keys with threshold `0.88`.
3. **Deterministic UUIDv5**: Reproducible ID derived from primary natural key (phone $\rightarrow$ email $\rightarrow$ clean name).
4. **Survivorship Rules**:
   - **Completeness Union**: Merges missing email/phone from later submissions into the golden record.
   - **Recency**: Retains newest timestamp for registration events.
   - **Affirmative Attendance**: Retains `attended_flag = True` if the participant attended in any submission.

---

### F. [`pipeline/quarantine.py`](../pipeline/quarantine.py)
Dead-letter store isolating invalid rows before pipeline processing:
- `MISSING_REQUIRED_NAME`: Row has no valid Arabic or English name.
- `MISSING_IDENTIFIER_RECORD_CANNOT_BE_LINKED`: Row has neither a valid phone nor a valid email.
- `SPAM_OR_DUMMY_VALUES_DETECTED`: Row contains test dummy text (`test test`, phone `12345`).
- Computes `quarantine_rate_pct` and flags `ALERT_THRESHOLD_EXCEEDED` if above threshold (default 15%).

---

### G. [`pipeline/runner.py`](../pipeline/runner.py) & [`pipeline/storage.py`](../pipeline/storage.py)
- Multi-sheet reader discovering all tabular sheets in `.xlsx`.
- Emits clean Excel workbooks:
  - Tab 1: `Cleaned_Data` (Pruned, natural business columns, deduplicated).
  - Tab 2: `quarantine_records` (Dead-letter store with rejection codes).
  - Tab 3: `audit_summary` (Batch governance metrics).
  - Tab 4: `dim_persons` (Internal golden entity table).
- Dual persistence into SQLite database (`dim_persons`, `fact_registrations`, `quarantine_records`, `audit_runs`).

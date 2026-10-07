# Dataset Generation Specification & Guidelines

This document defines the schema, column definitions, and dirty-data injection rules for generating realistic synthetic test datasets to benchmark and validate the Generalized Data Cleaning Pipeline.

---

## 1. Objectives of Synthetic Data Generation

To properly test whether the pipeline is truly **generalized**, deterministic where required, and robust against real-world data corruption, the generator must produce datasets with controlled anomalies across both narrow and wide schemas:
1. **Narrow Schema (13 Columns)**: Single-event workshop registration (`Distraction_Era`).
2. **Wide Schema (55 Columns)**: Complex multi-role application survey (`نموذج طلب الانضمام إلى لجنة المطورين لعام 2026`).
3. **Cross-Dataset Entity Linkage**: Common participants registering in both events with slight variations (e.g., using English vs. Arabic names, missing country code, or alternative emails) to verify Master Data Management (MDM) entity resolution.

---

## 2. Controlled Dirty-Data Injections & Anomalies

The synthetic generator must introduce realistic dirty-data edge cases across all 4 column groups:

### A. Identity Anomalies (Strict Normalization Target)
- **Saudi Phone Numbers**:
  - Excel dropping leading zeros (e.g., `508889900` instead of `0508889900` -> Target: `+966508889900`).
  - Double zero prefix (e.g., `00966531122334` -> Target: `+966531122334`).
  - Redundant local prefix appended to international (e.g., `+9660554975066` -> Target: `+966554975066`).
  - Formatting noise with spaces, dashes, parentheses (`+966 (054) 321-7890`).
  - Malformed short numbers (`0501234`) -> Sent to Quarantine.
- **Email Addresses**:
  - Trailing and leading whitespace, mixed upper/lower case (`  FAHAD@HOTMAIL.COM  `).
  - Common domain typos (`@gmaill.com`, `@hotmial.com`, `@yaho.com`, `@outloo.com`).
  - Missing `@` or invalid syntax (`amal.sudairy.gmail.com`) -> Sent to Quarantine if no other valid identifier.
- **Arabic Names**:
  - Honorific titles (`د.`, `م.`, `أستاذ`, `المهندس`).
  - Unbonded theophoric / compound prefixes (`عبد الله` -> `عبدالله`, `سيف الدين`, `نور الهدى`).
  - Patronymic clan particles (`آل سعود`, `بن باز`).
  - Harakat / Diacritics (`مُحَمَّد`).
- **English Names**:
  - Inverted Lastname-Firstname notation (`Al-Harbi, Salman` -> First: Salman, Family: Al-Harbi).
  - Mixed case and honorifics (`DR. JOHN DOE`).

### B. Structured / MetaData Anomalies
- **Timestamps**:
  - Excel numeric floating serial numbers (`46266.6125` -> `2026-09-01T14:42:00Z`).
  - Mixed datetime string formats (`DD/MM/YYYY HH:MM:SS`, `MM/DD/YYYY HH:MM AM/PM`, `YYYY-MM-DD`).
- **Universities**:
  - Acronyms and informal names (`UJ` -> `جامعة جدة`, `KSU` -> `جامعة الملك سعود`, `PNU` -> `جامعة الأميرة نورة`, `KFUPM` -> `جامعة الملك فهد للبترول والمعادن`).
- **Academic Levels**:
  - Numeric levels (`1`, `2.0`, `سنة أولى`, `Junior`, `خريج`).

### C. Categorical & MultiSelect Anomalies
- **Booleans & Consents**:
  - Arabic and English affirmative values (`نعم`, `موافق`, `yes`, `true`, `1`, `حضر`).
  - Negative values (`لا`, `غير موافق`, `no`, `0`, `غائب`).
- **Multi-Select Skills & Tools**:
  - Comma-separated or semicolon-separated lists.

### D. Free-Form Text Anomalies
- Unsanitized strings, excess whitespace, quotes, and punctuation.

### E. Governance & Deduplication Cases
- **Intra-File Duplicate Submissions**: Same person submitting multiple times. The pipeline must keep the latest timestamp and affirmative attendance.
- **Cross-File Duplicate Registrations**: A participant present in both the workshop and the committee form.
- **Spam / Test Rows**: Records with dummy names (`test test`, `asdf`) or phone (`12345`) which must be routed to Quarantine.

---

## 3. Dataset 1: Workshop "Distraction_Era" (13 Columns)

Target File: `RawData/Distraction_Era_Workshop_Dataset.xlsx`

| # | Column Header (Raw) | Target Canonical Field | Group | Data Type |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `Full Name (Ar)` | `full_name_ar` | Identity | String |
| 2 | `Full Name (En)` | `full_name_en` | Identity | String |
| 3 | `Email` | `email` | Identity | Email |
| 4 | `Phone` | `phone` | Identity | Phone (+966) |
| 5 | `College` | `major` | Structured/MetaData | String |
| 6 | `Uni` | `university` | Structured/MetaData | String |
| 7 | `Academic lvl` | `academic_lvl` | Structured/MetaData | Enum |
| 8 | `Where did you hear about the workshop` | `source_channel` | Categorical/MultiSelect | String |
| 9 | `What to expect from the workshop` | `expectations` | Free-Form | Text |
| 10 | `your biggest source of distraction` | `biggest_distraction` | Free-Form | Text |
| 11 | `Agree to being photographed` | `consent_photo` | Categorical/MultiSelect | Boolean |
| 12 | `Attendance` | `attendance` | Categorical/MultiSelect | Boolean |
| 13 | `TimeStamp` | `registered_at` | Structured/MetaData | DateTime (UTC ISO) |

---

## 4. Dataset 2: Developers Committee 2026 Responses (55 Columns)

Target File: `RawData/Developers_Committee_2026_Responses.xlsx`  
Contract: `config/developers_committee_contract.yaml`

| # | Column Header (Raw) | Target Canonical Field / Classification | Group |
| :--- | :--- | :--- | :--- |
| 1 | `Timestamp` | `registered_at` | Structured/MetaData |
| 2 | `الاسم الثلاثي بالعربي` | `full_name_ar` | Identity |
| 3 | `الاسم الثلاثي بالانجليزي` | `full_name_en` | Identity |
| 4 | `الجنس` | `gender` | Structured/MetaData |
| 5 | `رقم الجوال` | `phone` | Identity |
| 6 | `البريد الإلكتروني (Gmail)` | `email` | Identity |
| 7 | `البريد الإلكتروني (الجامعي)` | `academic_email` | Identity |
| 8 | `الفرع` | `branch` | Structured/MetaData |
| 9 | `التخصص الجامعي` | `major` | Structured/MetaData |
| 10 | `هل أنت/ي عضو في مجتمع قوقل؟` | `is_gdsc_member` | Categorical/MultiSelect |
| 11 | `اذا نعم، ماهي لجنتك؟` | `gdsc_committee` | Categorical/MultiSelect |
| 12 | `شاركنا حسابك في (LinkedIn)` | `linkedin_url` | Structured/MetaData |
| 13 | `اختر اللجنة الفرعية التي ترغب بالعمل عليها داخل لجنة المطورين` | `subcommittee_choice` | Categorical/MultiSelect |
| 14 | `اختر الدور الذي تراه مناسبًا لك داخل اللجنة` | `role_choice_1` | Categorical/MultiSelect |
| 15 | `كيف تقيّم مستواك الحالي في هذا المجال؟` | `skill_level_1` | Categorical/MultiSelect |
| 16 | `كم ساعة تستطيع الالتزام بها أسبوعيًا؟` | `weekly_hours_1` | Structured/MetaData |
| 17 | `ما الذي يدفعك للعمل على هذا المشروع تحديدا؟` | `motivation_1` | Free-Form |
| 18 | `ما هي مهاراتك التقنية ذات الصلة؟` | `technical_skills` | Free-Form |
| 19 | `صف بإيجاز أي مشروع او خبرة سابقة لك في هذا المجال` | `past_experience_1` | Free-Form |
| 20 | `لماذا ترغب في العمل على هذا المشروع، وما القيمة التي يمكنك إضافتها للفريق؟` | `value_add_1` | Free-Form |
| 21 | `ما التحدي الأكبر الذي قد تواجهه؟` | `biggest_challenge_1` | Free-Form |
| 22 | `اختر الدور الذي تراه مناسبًا لك داخل اللجنة 2` | `role_choice_2` | Categorical/MultiSelect |
| 23 | `كيف تقيّم مستواك الحالي في هذا المجال؟ 2` | `skill_level_2` | Categorical/MultiSelect |
| 24 | `كم ساعة تستطيع الالتزام بها أسبوعيًا؟ 2` | `weekly_hours_2` | Structured/MetaData |
| 25 | `هل درست أي مقرر له علاقة بتحليل البيانات؟ (قواعد بيانات، Python، Data Science، إحصاء)` | `studied_data_course` | Categorical/MultiSelect |
| 26 | `ما الأدوات أو اللغات التي لديك معرفة بها؟` | `known_tools_languages` | Free-Form |
| 27 | `برأيك، ما دور تحليل البيانات في أي مشروع؟` | `data_role_opinion` | Free-Form |
| 28 | `هل سبق لك العمل على مشروع تحليلي (جامعي أو شخصي)؟` | `worked_data_project` | Categorical/MultiSelect |
| 29 | `إذا نعم، صفه باختصار` | `data_project_desc` | Free-Form |
| 30 | `لو كان لدينا بيانات حضور فعاليات، ما أول شيء تحب تحليله ولماذا؟` | `attendance_analysis_idea` | Free-Form |
| 31 | `لماذا ترغب في العمل على هذا المشروع، وما القيمة التي يمكنك إضافتها للفريق؟ 2` | `value_add_2` | Free-Form |
| 32 | `ما التحدي الأكبر الذي قد تواجهه؟2` | `biggest_challenge_2` | Free-Form |
| 33 | `اختر الدور الذي تراه مناسبًا لك داخل اللجنة3` | `role_choice_3` | Categorical/MultiSelect |
| 34 | `كيف تقيّم مستواك الحالي في هذا المجال؟ 3` | `skill_level_3` | Categorical/MultiSelect |
| 35 | `3 كم ساعة تستطيع الالتزام بها أسبوعيًا؟` | `weekly_hours_3` | Structured/MetaData |
| 36 | `هل شاركت في مشروع تقني جماعي؟ اوصف دورك` | `team_project_role` | Free-Form |
| 37 | `هل سبق لك العمل على تصميم الواجهات؟` | `worked_ui_design` | Categorical/MultiSelect |
| 38 | `اذا نعم، ايش الادوات اللي استخدمتها؟` | `ui_tools_used` | Free-Form |
| 39 | `؟ CSS / HTML / JavaScript هل لديك معرفة بـ` | `knows_web_basics` | Categorical/MultiSelect |
| 40 | `هل استخدمت React؟` | `used_react` | Categorical/MultiSelect |
| 41 | `هل اشتغلت على ربط API سابقا؟` | `used_apis` | Categorical/MultiSelect |
| 42 | `هل استخدمت OpenAI?` | `used_openai` | Categorical/MultiSelect |
| 43 | `لماذا ترغب في العمل على هذا المشروع، وما القيمة التي يمكنك إضافتها للفريق؟ 3` | `value_add_3` | Free-Form |
| 44 | `ما التحدي الأكبر الذي قد تواجهه؟` | `biggest_challenge_3` | Free-Form |
| 45 | `اختر الدور الذي تراه مناسبًا لك داخل اللجنة 4` | `role_choice_4` | Categorical/MultiSelect |
| 46 | `كيف تقيّم مستواك الحالي في هذا المجال؟ 4` | `skill_level_4` | Categorical/MultiSelect |
| 47 | `كم ساعة تستطيع الالتزام بها أسبوعيًا؟` | `weekly_hours_4` | Structured/MetaData |
| 48 | `4هل سبق لك إنشاء سير عمل مؤتمت؟ ماهي المنصات التي استخدمتها؟` | `automated_workflows` | Free-Form |
| 49 | `صف بإيجاز ما قمت بإنشائه` | `automated_workflow_desc` | Free-Form |
| 50 | `هل سبق لك العمل مع Ai agents or LLM tools ؟` | `worked_ai_agents` | Categorical/MultiSelect |
| 51 | `ماهي المحفزات/الإجراءات التي استخدمتها؟` | `ai_triggers_actions` | Free-Form |
| 52 | `إذا كانت الأجابة نعم، إذا ما الذي قمت به باستخدامها؟` | `ai_tools_desc` | Free-Form |
| 53 | `قيم مدى ارتياحك لتصميم prompts لضمان اتساق التقييم (من 1 إلى 5)` | `prompt_design_comfort` | Categorical/MultiSelect |
| 54 | `لماذا ترغب في العمل على هذا المشروع، وما القيمة التي يمكنك إضافتها للفريق؟ 4` | `value_add_4` | Free-Form |
| 55 | `ما التحدي الأكبر الذي قد تواجهه؟3` | `biggest_challenge_4` | Free-Form |

import os
import yaml
import tempfile
import pytest
from pipeline.contract_generator import AutoContractGenerator
from pipeline.contract_engine import ContractEngine, ColumnMapping

# =====================================================================
# 1. 4-Group Column Classifier Tests (AutoContractGenerator)
# =====================================================================

def test_classifier_identity_arabic_names():
    headers = ["اسم المشارك بالعربي", "الاسم الثلاثي", "الاسم الكامل", "fullname_ar", "اسم الطالب"]
    for h in headers:
        res = AutoContractGenerator.classify_column(h)
        assert res["group"] == "Identity", f"Failed for {h}"
        assert res["target_field"] == "full_name_ar", f"Failed for {h}"
        assert "normalize_full_name_ar" in res["transformers"] or "normalize_arabic_name" in res["transformers"]

def test_classifier_identity_english_names():
    headers = ["Participant English Name", "FullName (En)", "Name in English", "English Name"]
    for h in headers:
        res = AutoContractGenerator.classify_column(h)
        assert res["group"] == "Identity", f"Failed for {h}"
        assert res["target_field"] == "full_name_en", f"Failed for {h}"

def test_classifier_identity_contact_info():
    phone_headers = ["رقم الجوال", "هاتف", "mobile", "رقم الواتساب للتواصل", "phone number"]
    for h in phone_headers:
        res = AutoContractGenerator.classify_column(h)
        assert res["group"] == "Identity"
        assert res["target_field"] == "phone"
        assert res["type"] == "phone"

    email_headers = ["البريد الإلكتروني", "Email Address", "ايميل الشخصي"]
    for h in email_headers:
        res = AutoContractGenerator.classify_column(h)
        assert res["group"] == "Identity"
        assert res["target_field"] == "email"
        assert res["type"] == "email"

    academic_email = ["البريد الجامعي", "Student Academic Email"]
    for h in academic_email:
        res = AutoContractGenerator.classify_column(h)
        assert res["group"] == "Identity"
        assert res["target_field"] == "academic_email"

def test_classifier_structured_metadata():
    test_cases = [
        ("الرقم الجامعي", "student_id", "string"),
        ("اسم الجامعة", "university", "string"),
        ("التخصص الأكاديمي", "major", "string"),
        ("المستوى الدراسي", "academic_lvl", "string"),
        ("وقت التسجيل", "registered_at", "datetime"),
        ("مدينة الإقامة", "branch", "string"),
        ("حساب لينكد إن", "linkedin_url", "string"),
    ]
    for h, expected_target, expected_type in test_cases:
        res = AutoContractGenerator.classify_column(h)
        assert res["group"] == "Structured/MetaData", f"Failed for {h}"
        assert res["target_field"] == expected_target, f"Failed for {h}"
        assert res["type"] == expected_type, f"Failed for {h}"

def test_classifier_structured_datetime_samples():
    # When header is ambiguous (e.g., 'تاريخ'), sample values confirm datetime
    res = AutoContractGenerator.classify_column("تاريخ", sample_values=["2026-09-01 10:00:00", "2026-09-02"])
    assert res["group"] == "Structured/MetaData"
    assert res["target_field"] == "registered_at"
    assert res["type"] == "datetime"

def test_classifier_categorical_booleans():
    # Boolean headers
    res1 = AutoContractGenerator.classify_column("هل توافق على الشروط والأحكام؟")
    assert res1["group"] == "Categorical/MultiSelect"
    assert res1["type"] == "boolean"

    res2 = AutoContractGenerator.classify_column("موافقة على التصوير")
    assert res2["group"] == "Categorical/MultiSelect"
    assert res2["type"] == "boolean"

    # Ambiguous header classified as boolean via sample values
    res3 = AutoContractGenerator.classify_column("حالة التسجيل", sample_values=["نعم", "لا", "نعم"])
    assert res3["group"] == "Categorical/MultiSelect"
    assert res3["type"] == "boolean"

def test_classifier_categorical_multiselect_samples():
    # Samples with Arabic comma, standard comma, semicolon
    res = AutoContractGenerator.classify_column("المهارات التقنية", sample_values=["Python، Docker", "SQL, Pandas", "Java; C++"])
    assert res["group"] == "Categorical/MultiSelect"
    assert "normalize_multiselect" in res["transformers"]

def test_classifier_free_form_questions_and_long_text():
    # Free-form questions with question words
    q_headers = [
        "لماذا ترغب بالانضمام إلى هذا المعسكر؟",
        "ما هي التحديات التي واجهتها سابقاً؟",
        "صف تجربتك في تحليل البيانات",
    ]
    for h in q_headers:
        res = AutoContractGenerator.classify_column(h)
        assert res["group"] == "Free-Form", f"Failed for {h}"
        assert res["type"] == "text"

    # Generic header with long text samples (> 5 words)
    res_samples = AutoContractGenerator.classify_column(
        "ملاحظات إضافية",
        sample_values=["أرغب في حضور ورش العمل للاستفادة وتطوير المهارات في مجال الذكاء الاصطناعي"]
    )
    assert res_samples["group"] == "Free-Form"
    assert res_samples["type"] == "text"

# =====================================================================
# 2. AutoContractGenerator End-to-End Contract Generation & Persistence
# =====================================================================

def test_contract_generation_structure():
    headers = [
        "الاسم الكامل",
        "رقم الجوال",
        "البريد الإلكتروني",
        "الجامعة",
        "التخصص",
        "هل توافق على الحضور؟",
        "تطلعاتك من البرنامج"
    ]
    contract = AutoContractGenerator.generate_contract(headers=headers, dataset_id="event_2026")
    
    assert contract["version"] == 1.0
    assert contract["dataset_id"] == "event_2026"
    assert contract["quarantine_threshold_pct"] == 15.0
    assert contract["unmapped_columns_strategy"] == "store_jsonb"
    assert len(contract["canonical_mappings"]) == len(headers)

    # Check required fields
    required_targets = [m["target_field"] for m in contract["canonical_mappings"] if m.get("required")]
    assert "full_name_ar" in required_targets
    assert "phone" in required_targets
    assert "email" in required_targets

def test_contract_generation_disambiguation():
    # Two columns that classify to 'email'
    headers = ["البريد الإلكتروني الأول", "البريد الإلكتروني البديل"]
    contract = AutoContractGenerator.generate_contract(headers=headers)
    targets = [m["target_field"] for m in contract["canonical_mappings"]]
    assert len(targets) == len(set(targets)), "Target fields must be unique"
    assert targets[0] == "email"
    assert targets[1].startswith("email_")

def test_contract_slug_determinism():
    # The slug for non-ASCII headers must produce identical results across multiple calls
    header = "ما هي أكبر المعوقات التي تواجهك؟"
    slug1 = AutoContractGenerator._slugify(header)
    slug2 = AutoContractGenerator._slugify(header)
    assert slug1 == slug2
    assert slug1.startswith("col_")

def test_contract_yaml_file_persistence():
    headers = ["اسم المشارك", "رقم الهاتف", "البريد"]
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_path = os.path.join(tmpdir, "generated_contract.yaml")
        contract_dict = AutoContractGenerator.generate_contract(
            headers=headers,
            dataset_id="test_persist",
            output_yaml_path=yaml_path
        )
        assert os.path.exists(yaml_path)
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        
        assert loaded["dataset_id"] == "test_persist"
        assert len(loaded["canonical_mappings"]) == 3

# =====================================================================
# 3. ContractEngine Dynamic Header Resolution & Semantic Heuristics
# =====================================================================

@pytest.fixture
def sample_contract_engine():
    contract_data = {
        "dataset_id": "test_suite",
        "quarantine_threshold_pct": 15.0,
        "canonical_mappings": [
            {
                "target_field": "full_name_ar",
                "group": "Identity",
                "type": "string",
                "aliases": ["الاسم بالعربي", "اسم المشارك", "FullName(AR)"]
            },
            {
                "target_field": "full_name_en",
                "group": "Identity",
                "type": "string",
                "aliases": ["الاسم بالإنجليزي", "English Name", "FullName(En)"]
            },
            {
                "target_field": "phone",
                "group": "Identity",
                "type": "phone",
                "aliases": ["الجوال", "رقم الجوال", "Phone"]
            },
            {
                "target_field": "email",
                "group": "Identity",
                "type": "email",
                "aliases": ["البريد الإلكتروني", "Email"]
            },
            {
                "target_field": "academic_email",
                "group": "Identity",
                "type": "email",
                "aliases": ["البريد الجامعي"]
            },
            {
                "target_field": "student_id",
                "group": "Structured/MetaData",
                "type": "string",
                "aliases": ["الرقم الجامعي", "Student ID"]
            },
            {
                "target_field": "university",
                "group": "Structured/MetaData",
                "type": "string",
                "aliases": ["الجامعة", "University"]
            }
        ]
    }
    return ContractEngine(contract_data)

def test_engine_exact_and_alias_resolution(sample_contract_engine):
    raw_headers = ["FullName(AR)", "FullName(En)", "Phone", "Email", "University"]
    resolved, unmapped = sample_contract_engine.resolve_headers(raw_headers)
    assert resolved["FullName(AR)"] == "full_name_ar"
    assert resolved["FullName(En)"] == "full_name_en"
    assert resolved["Phone"] == "phone"
    assert resolved["Email"] == "email"
    assert resolved["University"] == "university"
    assert len(unmapped) == 0

def test_engine_semantic_heuristics_disambiguation(sample_contract_engine):
    # Test disambiguation between Arabic vs English names
    raw = ["الاسم الثلاثي (بالعربي)", "الاسم بالانجليزي"]
    resolved, _ = sample_contract_engine.resolve_headers(raw)
    assert resolved["الاسم الثلاثي (بالعربي)"] == "full_name_ar"
    assert resolved["الاسم بالانجليزي"] == "full_name_en"

    # Test disambiguation between Student ID vs University Name
    raw_ids = ["الرقم الجامعي للطالب", "اسم الجامعة المقيد بها"]
    resolved_ids, _ = sample_contract_engine.resolve_headers(raw_ids)
    assert resolved_ids["الرقم الجامعي للطالب"] == "student_id"
    assert resolved_ids["اسم الجامعة المقيد بها"] == "university"

    # Test personal email vs academic email
    raw_emails = ["إيميل تواصل شخصي", "ايميلك الجامعي الرسمي"]
    resolved_emails, _ = sample_contract_engine.resolve_headers(raw_emails)
    assert resolved_emails["إيميل تواصل شخصي"] == "email"
    assert resolved_emails["ايميلك الجامعي الرسمي"] == "academic_email"

def test_engine_noise_and_punctuation_tolerance(sample_contract_engine):
    # Extra whitespace, brackets, diacritics
    raw = ["  رقم الجوال :  ", "الجامعة! (الحالية)"]
    resolved, unmapped = sample_contract_engine.resolve_headers(raw)
    assert resolved["  رقم الجوال :  "] == "phone"
    assert resolved["الجامعة! (الحالية)"] == "university"
    assert len(unmapped) == 0

def test_engine_unmapped_columns_captured(sample_contract_engine):
    raw = ["رقم الجوال", "سؤال غير معروف تماماً", "حقل_مخصص_123"]
    resolved, unmapped = sample_contract_engine.resolve_headers(raw)
    assert resolved["رقم الجوال"] == "phone"
    assert "سؤال غير معروف تماماً" in unmapped
    assert "حقل_مخصص_123" in unmapped

# =====================================================================
# 4. Canonical Row Extraction & JSONB Metadata Strategy
# =====================================================================

def test_engine_extract_canonical_row_clean(sample_contract_engine):
    raw_row = {
        "FullName(AR)": "فهد الدوسري",
        "Phone": "0501234567",
        "Email": "fahad@example.com",
        "حقل_إضافي": "قيمة تجريبية"
    }
    resolved_map, unmapped = sample_contract_engine.resolve_headers(list(raw_row.keys()))
    canonical, metadata = sample_contract_engine.extract_canonical_row(raw_row, resolved_map, unmapped)

    assert canonical["full_name_ar"] == "فهد الدوسري"
    assert canonical["phone"] == "0501234567"
    assert canonical["email"] == "fahad@example.com"
    assert "حقل_إضافي" in metadata
    assert metadata["حقل_إضافي"] == "قيمة تجريبية"

def test_engine_extract_canonical_row_duplicate_mappings_safety(sample_contract_engine):
    # Two raw headers that both map to 'full_name_ar'
    raw_row = {
        "FullName(AR)": "عبدالله السالم",
        "اسم المشارك": "عبدالله محمد السالم",
        "Phone": "0559988776"
    }
    resolved_map, unmapped = sample_contract_engine.resolve_headers(list(raw_row.keys()))
    canonical, metadata = sample_contract_engine.extract_canonical_row(raw_row, resolved_map, unmapped)

    # First non-empty value should be kept in canonical data
    assert canonical["full_name_ar"] == "عبدالله السالم"
    assert canonical["phone"] == "0559988776"
    # Secondary conflicting column should be preserved in metadata, NOT lost
    assert "اسم المشارك" in metadata
    assert metadata["اسم المشارك"] == "عبدالله محمد السالم"

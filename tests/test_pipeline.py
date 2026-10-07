import os
import pytest
from pipeline.name_parser import ArabicNameParser
from pipeline.normalizers import PhoneNormalizer, EmailNormalizer, DateTimeNormalizer, CategoricalNormalizer
from pipeline.schema import generate_deterministic_person_uuid
from pipeline.runner import PipelineRunner
from pipeline.contract_generator import AutoContractGenerator

def test_arabic_name_compound_bonding():
    # Test that 'عبد الله' is bonded and not split
    parsed = ArabicNameParser.parse_arabic_name("عبد الله محمد السالم")
    assert parsed.first_name == "عبدالله"
    assert parsed.father_name == "محمد"
    assert parsed.family_name == "السالم"
    assert parsed.full_clean == "عبدالله محمد السالم"

def test_arabic_name_patronymic_clan():
    # Test 'آل سعود' and 'بن باز'
    parsed = ArabicNameParser.parse_arabic_name("أحمد بن إبراهيم آل سعود")
    assert parsed.first_name == "أحمد"
    assert "إبراهيم" in parsed.father_name
    assert parsed.family_name == "آل سعود"

def test_english_inverted_name():
    # Test 'Al-Harbi, Salman'
    parsed = ArabicNameParser.parse_english_name("Al-Harbi, Salman")
    assert parsed.first_name == "Salman"
    assert parsed.family_name == "Al-Harbi"
    assert parsed.full_clean == "Salman Al-Harbi"

def test_phone_normalization_and_excel_bug():
    # Test standard local 05
    assert PhoneNormalizer.normalize("0507788990") == "+966507788990"
    
    # Test Excel stripped leading zero (508889900 -> +966508889900)
    assert PhoneNormalizer.normalize("508889900") == "+966508889900"
    assert PhoneNormalizer.normalize(508889900) == "+966508889900"
    
    # Test double zero prefix (00966...)
    assert PhoneNormalizer.normalize("00966531122334") == "+966531122334"
    
    # Test redundant +96605...
    assert PhoneNormalizer.normalize("+9660554975066") == "+966554975066"
    
    # Test hyphens & spaces
    assert PhoneNormalizer.normalize("+966-54-321-7890") == "+966543217890"
    
    # Test invalid short phone
    assert PhoneNormalizer.normalize("0501234") is None

def test_email_normalization_and_typo_fix():
    # Test uppercase and extra whitespace
    assert EmailNormalizer.normalize("  DEMOUSER@HOTMAIL.COM  ") == "demouser@hotmail.com"
    
    # Test domain typo fix (@gmaill.com -> @gmail.com)
    assert EmailNormalizer.normalize("demotest@gmaill.com") == "demotest@gmail.com"
    assert EmailNormalizer.normalize("demorecord@hotmial.com") == "demorecord@hotmail.com"
    
    # Test malformed email without @
    assert EmailNormalizer.normalize("amal.sudairy.gmail.com") is None

def test_datetime_excel_serial():
    # Test Excel serial number float (46266.6125)
    iso_date = DateTimeNormalizer.normalize("46266.6125")
    assert "2026-09-01" in iso_date

def test_academic_level_native_normalization():
    # Test native Saudi terms (NO pseudo-normalization hallucination!)
    assert CategoricalNormalizer.normalize_academic_level("سنة أولى") == "بكالوريوس - سنة 1"
    assert CategoricalNormalizer.normalize_academic_level("1") == "بكالوريوس - سنة 1"
    assert CategoricalNormalizer.normalize_academic_level("سنة ثانية") == "بكالوريوس - سنة 2"
    assert CategoricalNormalizer.normalize_academic_level("سنة رابعة") == "بكالوريوس - سنة 4"
    assert CategoricalNormalizer.normalize_academic_level("خريج") == "خريج"
    assert CategoricalNormalizer.normalize_academic_level("سنة امتياز") == "سنة امتياز"
    
    # Non-standard term should be preserved trimmed WITHOUT hallucinating pseudo categories
    assert CategoricalNormalizer.normalize_academic_level("طالب زائر") == "طالب زائر"

def test_categorical_boolean_and_multiselect():
    # Booleans
    assert CategoricalNormalizer.parse_boolean("نعم") is True
    assert CategoricalNormalizer.parse_boolean("حاضر") is True
    assert CategoricalNormalizer.parse_boolean("موافق") is True
    assert CategoricalNormalizer.parse_boolean("لا") is False
    assert CategoricalNormalizer.parse_boolean("غائب") is False
    assert CategoricalNormalizer.parse_boolean(None) is None

    # Multi-select list splitting & deduplication
    skills = "Python, SQL, Python, Pandas، Docker; SQL"
    clean_skills = CategoricalNormalizer.normalize_multiselect(skills)
    assert clean_skills == "Python, SQL, Pandas, Docker"

def test_uuidv5_deterministic_consistency():
    # UUIDv5 produces identical outputs across calls
    uuid1 = generate_deterministic_person_uuid("+966501234567")
    uuid2 = generate_deterministic_person_uuid("+966501234567")
    uuid_diff = generate_deterministic_person_uuid("+966559876543")

    assert uuid1 == uuid2
    assert uuid1 != uuid_diff
    assert len(uuid1) == 36

def test_auto_contract_generator():
    headers = ["الاسم الكامل", "رقم الجوال", "البريد الإلكتروني", "المستوى الدراسي", "هل توافق على الشروط؟", "لماذا ترغب بالانضمام؟"]
    contract = AutoContractGenerator.generate_contract(headers=headers, dataset_id="test_contract")
    mappings = {m["aliases"][0]: m["group"] for m in contract["canonical_mappings"]}
    
    assert mappings["الاسم الكامل"] == "Identity"
    assert mappings["رقم الجوال"] == "Identity"
    assert mappings["البريد الإلكتروني"] == "Identity"
    assert mappings["المستوى الدراسي"] == "Structured/MetaData"
    assert mappings["هل توافق على الشروط؟"] == "Categorical/MultiSelect"
    assert mappings["لماذا ترغب بالانضمام؟"] == "Free-Form"

def test_end_to_end_workshop_dataset(tmp_path):
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]

    dataset_file = (
        project_root
        / "RawData"
        / "Distraction_Era_Workshop_Dataset.xlsx"
    )

    contract_file = (
        project_root
        / "config"
        / "workshop_contract.yaml"
    )

    test_db = tmp_path / "test_workshop.db"
    test_output_excel = tmp_path / "test_workshop_cleaned.xlsx"

    runner = PipelineRunner(
        contract_path=str(contract_file),
        db_path=str(test_db),
    )

    summary = runner.run(
        input_file_path=str(dataset_file),
        output_excel_path=str(test_output_excel),
    )

    assert summary.total_rows == 40
    assert summary.quarantined_rows == 3
    assert summary.valid_rows == 37
    assert summary.duplicate_events_merged >= 2
    assert summary.status == "HEALTHY"
    assert test_db.exists()
    assert test_output_excel.exists()

def test_end_to_end_developers_committee_55_columns(tmp_path):
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]

    dataset_file = (
        project_root
        / "RawData"
        / "Developers_Committee_2026_Responses.xlsx"
    )

    contract_file = (
        project_root
        / "config"
        / "developers_committee_contract.yaml"
    )

    test_db = tmp_path / "test_committee.db"
    test_output_excel = tmp_path / "test_committee_cleaned.xlsx"

    runner = PipelineRunner(
        contract_path=str(contract_file),
        db_path=str(test_db),
    )

    summary = runner.run(
        input_file_path=str(dataset_file),
        output_excel_path=str(test_output_excel),
    )

    assert summary.total_rows == 23
    assert summary.quarantined_rows == 1
    assert summary.valid_rows == 22
    assert summary.status == "HEALTHY"
    assert test_db.exists()
    assert test_output_excel.exists()
def test_multisheet_excel_processing_and_cross_sheet_dedup(tmp_path):
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]

    dataset_file = (
        project_root
        / "RawData"
        / "MultiSheet_Workshop_Batches.xlsx"
    )

    test_db = tmp_path / "test_multisheet.db"
    test_output_excel = tmp_path / "test_multisheet_cleaned.xlsx"

    runner = PipelineRunner(
        contract_path=None,
        db_path=str(test_db),
    )

    summary = runner.run(
        input_file_path=str(dataset_file),
        output_excel_path=str(test_output_excel),
    )

    assert summary.total_rows == 5
    assert summary.valid_rows == 5
    assert "Morning_Session" in summary.sheet_name
    assert "Evening_Session" in summary.sheet_name
    assert summary.unique_persons_resolved == 4
    assert summary.duplicate_events_merged >= 1
    assert test_db.exists()
    assert test_output_excel.exists()
def test_entity_resolver_name_similarity_match():
    from pipeline.entity_resolver import HybridEntityResolver, jaro_winkler_similarity
    from pipeline.name_parser import ArabicNameParser

    resolver = HybridEntityResolver()

    parsed_name_1 = ArabicNameParser.parse_english_name(
        "Mohammed Ahmed Ali"
    )

    person1, is_duplicate1 = resolver.resolve_person(
        phone_e164=None,
        email=None,
        parsed_name_ar=None,
        parsed_name_en=parsed_name_1,
        university="KSU",
    )

    parsed_name_2 = ArabicNameParser.parse_english_name(
    "Mohamad Khaled Omar"
)

    similarity = jaro_winkler_similarity(
        person1.full_name_en.casefold(),
        parsed_name_2.normalized_key.casefold(),
    )

    assert similarity < 0.88

    person2, is_duplicate2 = resolver.resolve_person(
        phone_e164=None,
        email=None,
        parsed_name_ar=None,
        parsed_name_en=parsed_name_2,
        university="KSU",
    )

    assert person1.person_id != person2.person_id

def test_registration_event_merges_metadata_even_when_new_event_is_older():
    from pipeline.entity_resolver import HybridEntityResolver
    from pipeline.schema import FactRegistration

    resolver = HybridEntityResolver()

    registration1 = FactRegistration(
        registration_id="registration-1",
        person_id="person-1",
        dataset_id="dataset-1",
        sheet_name="Morning",
        attended_flag=False,
        registered_at="2026-09-15T10:00:00",
        raw_metadata={
            "source": "morning",
            "role": "student",
        },
    )

    registration2 = FactRegistration(
        registration_id="registration-2",
        person_id="person-1",
        dataset_id="dataset-1",
        sheet_name="Evening",
        attended_flag=False,
        registered_at="2026-09-15T09:00:00",
        raw_metadata={
            "location": "Jeddah",
        },
    )

    resolver.add_registration_event(registration1)
    resolver.add_registration_event(registration2)

    stored_registration = resolver.registrations[0]

    assert len(resolver.registrations) == 1
    assert resolver.merged_duplicate_count == 1

    assert stored_registration.raw_metadata["source"] == "morning"
    assert stored_registration.raw_metadata["role"] == "student"
    assert stored_registration.raw_metadata["location"] == "Jeddah"

    assert stored_registration.registered_at == "2026-09-15T10:00:00"

def test_storage_enforces_foreign_key_integrity(tmp_path):
    import sqlite3

    from pipeline.schema import AuditSummary, FactRegistration
    from pipeline.storage import StorageManager

    db_path = tmp_path / "foreign_key_test.db"

    storage = StorageManager(db_path=str(db_path))

    registration = FactRegistration(
        person_id="non-existent-person",
        dataset_id="dataset-1",
        sheet_name="Sheet1",
        registered_at="2026-09-16T10:00:00",
    )

    summary = AuditSummary(
        source_file="test.xlsx",
        sheet_name="Sheet1",
        total_rows=1,
        valid_rows=1,
        quarantined_rows=0,
        unique_persons_resolved=0,
        duplicate_events_merged=0,
        quarantine_rate_pct=0.0,
        status="HEALTHY",
    )

    try:
        storage.save_to_sqlite(
            persons=[],
            registrations=[registration],
            quarantine=[],
            summary=summary,
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError(
            "Foreign key constraint was not enforced."
        )
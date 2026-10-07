import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Dict, Any, List, Optional

from pydantic import BaseModel, Field, field_validator


# Reject blank text without trimming or changing accepted values.
_NonBlankStr = Annotated[str, Field(min_length=1, pattern=r"\S")]

# Fixed namespace UUID for deterministic UUIDv5 generation across batches.
PIPELINE_NAMESPACE = uuid.UUID("e7b3992b-8b54-4a27-a06f-47dc08e1bf9a")


def generate_deterministic_person_uuid(primary_key: str) -> str:
    """
    Generates a consistent, reproducible UUIDv5 from a canonical natural key
    (such as an E.164 phone number or lowercase email).
    """
    clean_key = str(primary_key).strip().lower()

    if not clean_key:
        raise ValueError("primary_key cannot be blank")

    return str(uuid.uuid5(PIPELINE_NAMESPACE, clean_key))


class CleanPerson(BaseModel):
    """
    Dimension model representing a unique real-world individual in dim_persons.
    Used strictly for internal Master Data Management (MDM) deduplication and clustering.
    """

    person_id: _NonBlankStr
    canonical_email: Optional[str] = None
    canonical_phone_e164: Optional[str] = None
    full_name_ar: Optional[str] = None
    full_name_en: Optional[str] = None
    first_name: Optional[str] = None
    father_name: Optional[str] = None
    family_name: Optional[str] = None
    clean_display_name: _NonBlankStr
    created_at: _NonBlankStr = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: _NonBlankStr = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @field_validator("canonical_email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

        if not re.fullmatch(email_pattern, value):
            raise ValueError("canonical_email must be a valid email address")

        return value

    @field_validator("canonical_phone_e164")
    @classmethod
    def validate_phone_e164(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        # E.164: + followed by a non-zero country code and up to 15 digits total.
        if not re.fullmatch(r"^\+[1-9]\d{1,14}$", value):
            raise ValueError(
                "canonical_phone_e164 must be a valid E.164 number"
            )

        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_person_datetime(cls, value: str) -> str:
        _validate_iso_datetime(value)
        return value


class FactRegistration(BaseModel):
    """
    Transactional event record representing a registration/submission
    linked to dim_persons.
    """

    registration_id: _NonBlankStr = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    person_id: _NonBlankStr
    sheet_name: _NonBlankStr = "default_sheet"
    dataset_id: _NonBlankStr = "default_dataset"
    attended_flag: bool = False
    consent_photo: bool = False
    major: Optional[str] = None
    university: Optional[str] = None
    academic_lvl: Optional[str] = None
    registered_at: _NonBlankStr
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("registered_at")
    @classmethod
    def validate_registered_at(cls, value: str) -> str:
        _validate_iso_datetime(value)
        return value


class QuarantineRecord(BaseModel):
    """
    Dead-letter store record for rows failing contract assertions.
    Captures exact raw row data and specific programmatic failure codes.
    """

    quarantine_id: _NonBlankStr = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    source_file: _NonBlankStr
    sheet_name: _NonBlankStr
    row_index: int = Field(ge=0)
    raw_payload: Dict[str, Any]
    rejection_codes: List[_NonBlankStr] = Field(min_length=1)
    quarantined_at: _NonBlankStr = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @field_validator("quarantined_at")
    @classmethod
    def validate_quarantined_at(cls, value: str) -> str:
        _validate_iso_datetime(value)
        return value


class AuditSummary(BaseModel):
    """
    Observability & governance summary for a batch ingestion run.
    """

    source_file: _NonBlankStr
    sheet_name: _NonBlankStr
    total_rows: int = Field(ge=0)
    valid_rows: int = Field(ge=0)
    quarantined_rows: int = Field(ge=0)
    unique_persons_resolved: int = Field(ge=0)
    duplicate_events_merged: int = Field(ge=0)
    quarantine_rate_pct: float = Field(ge=0, le=100)
    status: _NonBlankStr


def _validate_iso_datetime(value: str) -> None:
    """
    Validates that a string contains a valid ISO-8601 datetime.
    Validation only: the original value is not modified.
    """
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("value must be a valid ISO-8601 datetime") from exc
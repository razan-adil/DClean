import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Dict, List, Set
import phonenumbers
from pipeline.lookup_data import (
    COLLEGE_LOOKUP,
    UNIVERSITY_LOOKUP,
    ACADEMIC_LEVEL_LOOKUP,
    MAJOR_LOOKUP,
)

class PhoneNormalizer:
    """
    Deterministic Phone Normalizer with Saudi Arabia heuristics.
    Strips noise, fixes Excel dropped leading zeros, and outputs E.164.
    """
    @staticmethod
    def normalize(raw_val: Any, default_region: str = "SA") -> Optional[str]:
        if raw_val is None:
            return None
        
        # Handle float representation from Excel (e.g. 966558536903.0)
        if isinstance(raw_val, float):
            try:
                raw_val = int(raw_val)
            except (ValueError, OverflowError):
                pass

        val_str = str(raw_val).strip()
        if val_str.endswith(".0"):
            val_str = val_str[:-2]

        if val_str.lower() in ["none", "nan", "null", "", "n/a", "لا يوجد"]:
            return None

        # Clean string: keep only digits and leading plus
        cleaned = re.sub(r"[^\d+]", "", val_str)

        # Fix double zero international prefix (00966... -> +966...)
        if cleaned.startswith("00"):
            cleaned = "+" + cleaned[2:]

        # Fix redundant country code followed by local 05: e.g. 9665 0554975066 -> +966554975066
        # or +96605XXXXXXXX / 96605XXXXXXXX -> +9665XXXXXXXX
        if re.match(r"^\+?9665?05\d{8}$", cleaned):
            cleaned = "+966" + cleaned[-9:]
        elif re.match(r"^\+?96605\d{8}$", cleaned):
            cleaned = "+966" + cleaned[-9:]

        # Fix Excel dropped leading zero bug (e.g. 508889900 -> 0508889900)
        # Saudi numbers without country code have 9 digits starting with 5
        if re.match(r"^5\d{8}$", cleaned):
            cleaned = "0" + cleaned

        # Fix local Saudi format without +: 9665XXXXXXXX -> +9665XXXXXXXX
        if re.match(r"^9665\d{8}$", cleaned):
            cleaned = "+" + cleaned

        try:
            parsed = phonenumbers.parse(cleaned, default_region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass

        return None

class EmailNormalizer:
    """
    Deterministic Email Normalizer.
    Trims, lowercases, fixes common domain typos, and validates syntax.
    """
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    
    TYPO_DOMAINS = {
        "gmaill.com": "gmail.com",
        "gamil.com": "gmail.com",
        "gmial.com": "gmail.com",
        "hotmaill.com": "hotmail.com",
        "hotmial.com": "hotmail.com",
        "outloo.com": "outlook.com",
        "yaho.com": "yahoo.com"
    }

    @classmethod
    def normalize(cls, raw_val: Any) -> Optional[str]:
        if raw_val is None:
            return None
        val_str = str(raw_val).strip().lower()
        # Strip invisible Unicode control, zero-width, and directional characters (RTL/LTR marks)
        val_str = re.sub(r"[\u200B-\u200F\u202A-\u202E\uFEFF]", "", val_str).strip()
        if val_str in ["none", "nan", "null", "", "n/a"]:
            return None

        # Strip mailto: prefix often added by spreadsheet hyperlinks
        val_str = re.sub(r"^mailto:\s*", "", val_str)

        # Fix common domain typos and missing dot before TLD
        if "@" in val_str:
            parts = val_str.rsplit("@", 1)
            if len(parts) == 2:
                local, domain = parts
                # Heal missing dots like @gmailcom -> @gmail.com
                for tld in ["com", "edu.sa", "net", "org", "gov.sa", "sa"]:
                    if domain.endswith(tld) and not domain.endswith(f".{tld}"):
                        prefix = domain[:-len(tld)]
                        if prefix in ["gmail", "hotmail", "yahoo", "outlook", "icloud"]:
                            domain = f"{prefix}.{tld}"
                domain = cls.TYPO_DOMAINS.get(domain, domain)
                val_str = f"{local}@{domain}"

        if cls.EMAIL_REGEX.match(val_str):
            return val_str
        return None

class DateTimeNormalizer:
    """
    Deterministic DateTime Normalizer.
    Converts heterogeneous dates, 12h AM/PM strings, and Excel serial floats to UTC ISO-8601.
    """
    EXCEL_EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)

    @classmethod
    def normalize(cls, raw_val: Any) -> Optional[str]:
        if raw_val is None:
            return None

        # Check if raw_val is already a native Python datetime/date object
        if isinstance(raw_val, datetime):
            if raw_val.tzinfo is None:
                raw_val = raw_val.replace(tzinfo=timezone.utc)
            return raw_val.strftime("%Y-%m-%dT%H:%M:%SZ")

        val_str = str(raw_val).strip()
        if val_str.lower() in ["none", "nan", "null", "", "n/a"]:
            return None

        # Check if it's an Excel numeric serial float (e.g. 46266.6125)
        try:
            float_val = float(val_str)
            # Excel serial dates in the 2020-2035 era range between ~43000 and ~50000
            if 30000 <= float_val <= 60000:
                days = int(float_val)
                frac = float_val - days
                dt = cls.EXCEL_EPOCH + timedelta(days=days, seconds=int(round(frac * 86400)))
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

        # Try various known datetime string formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %I:%M %p",
            "%d/%m/%Y %I:%M:%S %p",
            "%d/%m/%Y %I:%M %p",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ"
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(val_str, fmt)
                dt = dt.replace(tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue

        return val_str

class CategoricalNormalizer:
    """
    Normalizes categorical, boolean, multi-select, university, and academic level fields.
    Adheres strictly to the guidelines: zero pseudo-normalization hallucination!
    """
    TRUE_VALUES = {"نعم", "موافق", "أوافق", "yes", "true", "1", "حضر", "حاضر", "attended", "present"}
    FALSE_VALUES = {"لا", "غير موافق", "no", "false", "0", "غائب", "لم يحضر", "absent"}

    @staticmethod
    def normalize_lookup_key(value: Any) -> str:
        """
        Normalize the lookup key without changing the canonical value.
        """

        if value is None:
            return ""

        key = str(value).strip().lower()

        # Remove Arabic diacritics
        key = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", key)

        # Normalize common Arabic letter variations
        key = re.sub(r"[إأآا]", "ا", key)
        key = key.replace("ى", "ي")

        # Normalize Arabic taa marbuta / haa variations
        key = key.replace("ة", "ه")

        # Normalize repeated whitespace
        key = re.sub(r"\s+", " ", key)

        return key.strip()
    
    @classmethod
    def normalize_lookup(
        cls,
        raw_val: Any,
        lookup: Dict[str, str]
    ) -> Optional[str]:
        """
        Generic deterministic normalization using an explicit lookup table.

        Unknown values are preserved instead of being guessed or invented.
        """
        if raw_val is None:
            return None

        val_str = str(raw_val).strip()

        if not val_str or val_str.lower() in ["none", "nan", "null", "n/a"]:
            return None

        key = cls.normalize_lookup_key(val_str)

        normalized_lookup = {
            cls.normalize_lookup_key(k): v
            for k, v in lookup.items()
        }

        return normalized_lookup.get(key, val_str)

    @classmethod
    def parse_boolean(cls, raw_val: Any) -> Optional[bool]:
        if raw_val is None:
            return None
        if isinstance(raw_val, bool):
            return raw_val
        val_str = str(raw_val).strip().lower()
        if val_str in cls.TRUE_VALUES:
            return True
        if val_str in cls.FALSE_VALUES:
            return False
        return None

    @classmethod
    def normalize_multiselect(cls, raw_val: Any, delimiter: str = ", ") -> Optional[str]:
        """
        Splits delimited options (by comma, Arabic comma, semicolon, newline),
        strips whitespace, removes duplicates, and re-joins cleanly.
        """
        if raw_val is None:
            return None
        val_str = str(raw_val).strip()
        if not val_str or val_str.lower() in ["none", "nan", "null"]:
            return None

        # Split on commas, Arabic commas, semicolons, or newlines
        parts = re.split(r"[,;،\n]+", val_str)
        seen: Set[str] = set()
        clean_tokens: List[str] = []

        for p in parts:
            cleaned = p.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                clean_tokens.append(cleaned)

        return delimiter.join(clean_tokens) if clean_tokens else val_str

    @classmethod
    def normalize_academic_level(cls, raw_val: Any) -> Optional[str]:
        if raw_val is None:
            return None

        value = str(raw_val).strip()

        if not value:
            return None

        # Handle Excel-style numeric values such as 1.0
        if value.endswith(".0"):
            value = value[:-2]

        return cls.normalize_lookup(value, ACADEMIC_LEVEL_LOOKUP)
    
    @classmethod
    def normalize_college(cls, raw_val: Any) -> Optional[str]:
        return cls.normalize_lookup(raw_val, COLLEGE_LOOKUP)

    
    @classmethod
    def normalize_university(cls, raw_val: Any) -> Optional[str]:
        return cls.normalize_lookup(raw_val, UNIVERSITY_LOOKUP)
    
    @classmethod
    def normalize_major(cls, raw_val: Any) -> Optional[str]:
        return cls.normalize_lookup(raw_val, MAJOR_LOOKUP)

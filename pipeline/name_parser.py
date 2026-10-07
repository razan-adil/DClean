import re
from typing import Dict, Any, List, Optional


class ParsedName:
    def __init__(
        self,
        full_clean: str,
        first_name: Optional[str] = None,
        father_name: Optional[str] = None,
        family_name: Optional[str] = None,
        normalized_key: str = "",
    ):
        self.full_clean = full_clean
        self.first_name = first_name
        self.father_name = father_name
        self.family_name = family_name
        self.normalized_key = normalized_key

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_clean": self.full_clean,
            "first_name": self.first_name,
            "father_name": self.father_name,
            "family_name": self.family_name,
            "normalized_key": self.normalized_key,
        }


class ArabicNameParser:
    """
    Compound-aware Arabic & English Name Parser.
    Understands tri-part names (First - Father - Family) and correctly bonds
    theophoric/compound names ('عبد الله', 'سيف الدين', 'آل سعود', 'بن باز', 'أبو بكر')
    so they are not fragmented by naive whitespace splitting.
    """

    # Honorifics & titles to strip
    AR_HONORIFICS = re.compile(
        r"^(م\.|د\.|أ\.|أ\.د\.|دكتور|دكتورة|مهندس|مهندسة|أستاذ|أستاذة|الشيخ|المهندس|الدكتور)\s+",
        re.IGNORECASE,
    )
    EN_HONORIFICS = re.compile(
        r"^(dr\.|dr|eng\.|eng|prof\.|prof|mr\.|mr|ms\.|ms|mrs\.|mrs)\s+", re.IGNORECASE
    )

    # Prefixes that bond to the next word into a single theophoric token
    COMPOUND_NAMES = {
        "نور": {"الهدى", "الدين"},
        "سيف": {"الدين"},
        "شمس": {"الدين"},
        "علاء": {"الدين"},
        "جمال": {"الدين"},
        "صلاح": {"الدين"},
        "حسام": {"الدين"},
        "تقي": {"الدين"},
        "ضياء": {"الدين"},
        "محي": {"الدين"},
        "عماد": {"الدين"},
        "شرف": {"الدين"},
        "بدر": {"الدين"},
        "نجم": {"الدين"},
    }

    # Patronymic and clan particles preserved with space
    PATRONYMIC_PREFIXES = {
        "آل",
        "ابن",
        "بن",
        "أبو",
        "ابو",
        "أبي",
        "ابي",
        "أم",
        "ام",
        "با",
    }

    # Diacritics / Harakat regex
    AR_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")

    @classmethod
    def clean_raw_string(cls, raw: Any) -> str:
        if raw is None:
            return ""
        s = str(raw).strip()
        if s.lower() in ["none", "nan", "null", "n/a", ""]:
            return ""
        # Remove zero-width spaces and normalize whitespace
        s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    @classmethod
    def is_arabic(cls, text: str) -> bool:
        return bool(re.search(r"[\u0600-\u06FF]", text))

    @classmethod
    def bond_arabic_tokens(cls, raw_text: str) -> List[str]:
        """
        Tokenizes an Arabic name and bonds compounds into single tokens.
        Example: ['عبد', 'الله', 'محمد', 'آل', 'سعود'] -> ['عبدالله', 'محمد', 'آل سعود']
        """
        cleaned = cls.AR_HONORIFICS.sub("", raw_text).strip()
        tokens = cleaned.split()
        if not tokens:
            return []

        bonded = []
        i = 0
        n = len(tokens)
        while i < n:
            current = tokens[i]
            # Strip harakat from token for check
            check_token = cls.AR_DIACRITICS.sub("", current)
            
            if check_token in {"أم", "ام", "أبو", "ابو", "أبي", "ابي"} and i + 2 < n:
                next_token = tokens[i + 1]
                next_clean = cls.AR_DIACRITICS.sub("", next_token)
                third_token = tokens[i + 2]
                third_clean = cls.AR_DIACRITICS.sub("", third_token)

                if next_clean == "عبد" and third_clean in {"الله", "الرحمن", "العزيز"}:
                    combined = f"{current} {next_token}{third_token}"
                    bonded.append(combined)
                    i += 3
                    continue
                
            if check_token == "عبد" and (i + 1) < n:
                next_token = tokens[i + 1]
                combined = f"{current}{next_token}"
                bonded.append(combined)
                i += 2

            elif check_token in cls.COMPOUND_NAMES and (i + 1) < n:
                next_token = tokens[i + 1]
                next_clean = cls.AR_DIACRITICS.sub("", next_token)

                if next_clean in cls.COMPOUND_NAMES[check_token]:
                    combined = f"{current} {next_token}"
                    bonded.append(combined)
                    i += 2
                else:
                    bonded.append(current)
                    i += 1

            # Check if current token is a patronymic/clan particle (e.g. 'آل سعود', 'بن باز', 'أبو بكر')
            elif check_token in cls.PATRONYMIC_PREFIXES and (i + 1) < n:
                next_token = tokens[i + 1]
                combined = f"{current} {next_token}"
                bonded.append(combined)
                i += 2
            else:
                bonded.append(current)
                i += 1

        return bonded

    @classmethod
    def normalize_for_matching(cls, text: str) -> str:
        """
        Produces a normalized key for probabilistic string distance comparison.
        Normalizes Hamzas (أ, إ, آ -> ا), Taa Marbuta (ة -> ه), Alif Maqsura (ى -> ي).
        """
        if not text:
            return ""
        s = cls.clean_raw_string(text).lower()
        s = cls.AR_HONORIFICS.sub("", s)
        s = cls.EN_HONORIFICS.sub("", s)
        s = cls.AR_DIACRITICS.sub("", s)
        # Normalize Arabic characters
        s = re.sub(r"[إأآا]", "ا", s)
        s = re.sub(r"ة", "ه", s)
        s = re.sub(r"ى", "ي", s)
        # Normalize compound spaces for key match (e.g. 'عبد الله' -> 'عبدالله')
        s = re.sub(r"\bعبد\s+", "عبد", s)
        s = re.sub(r"[^\w\s]", "", s)
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def parse_arabic_name(cls, raw_name: str) -> ParsedName:
        """
        Parses an Arabic name string into Tri-part structure:
        First Name, Father Name, Family Name.
        """
        cleaned = cls.clean_raw_string(raw_name)
        if not cleaned:
            return ParsedName(full_clean="", normalized_key="")

        # Strip honorifics
        cleaned = cls.AR_HONORIFICS.sub("", cleaned).strip()
        tokens = cls.bond_arabic_tokens(cleaned)

        if not tokens:
            return ParsedName(
                full_clean=cleaned, normalized_key=cls.normalize_for_matching(cleaned)
            )

        first = tokens[0]
        father = None
        family = None

        if len(tokens) == 1:
            first = tokens[0]

        elif len(tokens) == 2:
            first = tokens[0]

            if tokens[1].split()[0] in {"بن", "ابن"}:
                father = tokens[1]
            else:
                family = tokens[1]

        elif len(tokens) == 3:
            first = tokens[0]
            father = tokens[1]
            family = tokens[2]

        else:  # 4 or more tokens
            first = tokens[0]
            father = " ".join(tokens[1:-1])
            family = tokens[-1]

        full_clean = " ".join(tokens)
        key = cls.normalize_for_matching(full_clean)

        return ParsedName(
            full_clean=full_clean,
            first_name=first,
            father_name=father,
            family_name=family,
            normalized_key=key,
        )

    @classmethod
    def parse_english_name(cls, raw_name: str) -> ParsedName:
        """
        Parses an English name string.
        Handles inverted formats like 'Al-Harbi, Salman' -> First: Salman, Family: Al-Harbi.
        """
        cleaned = cls.clean_raw_string(raw_name)
        if not cleaned:
            return ParsedName(full_clean="", normalized_key="")

        # Check for inverted comma format: "Lastname, Firstname"
        if "," in cleaned:
            parts = [p.strip() for p in cleaned.split(",", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                family_cand = parts[0]
                first_cand = parts[1]
                cleaned = f"{first_cand} {family_cand}"

        cleaned = cls.EN_HONORIFICS.sub("", cleaned).strip()
        tokens = [t.strip().title() for t in cleaned.split() if t.strip()]

        if not tokens:
            return ParsedName(
                full_clean=cleaned.title(),
                normalized_key=cls.normalize_for_matching(cleaned),
            )

        first = tokens[0]
        father = None
        family = None

        if len(tokens) == 1:
            first = tokens[0]
        elif len(tokens) == 2:
            first = tokens[0]
            family = tokens[1]
        elif len(tokens) == 3:
            first = tokens[0]
            father = tokens[1]
            family = tokens[2]
        else:
            first = tokens[0]
            father = " ".join(tokens[1:-1])
            family = tokens[-1]

        full_clean = " ".join(tokens)
        key = cls.normalize_for_matching(full_clean)

        return ParsedName(
            full_clean=full_clean,
            first_name=first,
            father_name=father,
            family_name=family,
            normalized_key=key,
        )

    @classmethod
    def parse_any_name(cls, raw_name: str) -> ParsedName:
        """
        Auto-detects language and returns structured parsed name.
        """
        cleaned = cls.clean_raw_string(raw_name)
        if cls.is_arabic(cleaned):
            return cls.parse_arabic_name(cleaned)
        return cls.parse_english_name(cleaned)

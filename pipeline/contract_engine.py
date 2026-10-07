import re
import yaml
import difflib
from typing import Dict, Any, List, Optional, Tuple

class ColumnMapping:
    def __init__(
        self,
        target_field: str,
        group: str,
        data_type: str,
        aliases: List[str],
        required: bool = False,
        default_region: str = "SA"
    ):
        self.target_field = target_field
        self.group = group
        self.data_type = data_type
        self.aliases = aliases
        self.required = required
        self.default_region = default_region

class ContractEngine:
    """
    Dynamic Contract & Header Resolution Engine.
    Eliminates hardcoded column names by matching arbitrary incoming headers
    against declarative YAML contracts, and preserving dynamic unmapped columns
    into a JSONB-ready payload.
    """
    def __init__(self, contract_path_or_dict: Any, similarity_threshold: Optional[float] = None):
        if isinstance(contract_path_or_dict, str):
            self.contract_path = contract_path_or_dict
            with open(contract_path_or_dict, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            self.contract_path = "dynamic_contract"
            self.config = contract_path_or_dict

        self.dataset_id = self.config.get("dataset_id", "default_dataset")
        self.quarantine_threshold_pct = float(self.config.get("quarantine_threshold_pct", 15.0))
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else float(self.config.get("similarity_threshold", 0.82))
        self.mappings: List[ColumnMapping] = []
        self._load_mappings()

    def _load_mappings(self):
        for m in self.config.get("canonical_mappings", []):
            mapping = ColumnMapping(
                target_field=m["target_field"],
                group=m.get("group", "Structured/MetaData"),
                data_type=m.get("type", "string"),
                aliases=m.get("aliases", []),
                required=m.get("required", False),
                default_region=m.get("default_region", "SA")
            )
            self.mappings.append(mapping)

    @staticmethod
    def _normalize_header(header: str) -> str:
        s = str(header).strip().lower()
        s = re.sub(r"[^\w\s]", "", s)
        return re.sub(r"\s+", " ", s).strip()

    def resolve_headers(self, raw_headers: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Dynamically matches raw headers to canonical target fields using:
        1. Exact normalized match against target fields and aliases.
        2. Substring containment against registered aliases.
        3. Semantic domain heuristics for survey questions.
        """
        resolved_map = {}
        unmapped_headers = []

        for raw_h in raw_headers:
            norm_h = self._normalize_header(raw_h)
            matched_field = None

            # Pass 1: Exact match against target_field or registered aliases
            for m in self.mappings:
                if norm_h == self._normalize_header(m.target_field):
                    matched_field = m.target_field
                    break
                for alias in m.aliases:
                    if norm_h == self._normalize_header(alias):
                        matched_field = m.target_field
                        break
                if matched_field:
                    break

            # Pass 2: High-priority semantic domain heuristics
            if not matched_field:
                # Distinguish Arabic vs English names accurately
                if ("arabic" in norm_h or "عربي" in norm_h or "بالعربي" in norm_h) and ("name" in norm_h or "اسم" in norm_h):
                    matched_field = "full_name_ar"
                elif ("english" in norm_h or "انجليزي" in norm_h or "إنجليزي" in norm_h or "بالانجليزي" in norm_h) and ("name" in norm_h or "اسم" in norm_h):
                    matched_field = "full_name_en"
                elif any(k in norm_h for k in ["phone", "mobile", "جوال", "هاتف", "whatsapp", "واتساب", "رقم تواصل", "وسيلة تواصل"]):
                    matched_field = "phone"
                elif any(k in norm_h for k in ["رقم جامعي", "الرقم الجامعي", "رقم الطالب", "student id", "academic id", "الرقم الاكاديمي"]):
                    matched_field = "student_id"
                elif any(k in norm_h for k in ["university", "جامعة", "uni"]) and not any(k in norm_h for k in ["رقم", "id", "طالب", "student"]):
                    matched_field = "university"
                elif "جامعي" in norm_h and any(k in norm_h for k in ["email", "بريد", "ايميل", "إيميل"]):
                    matched_field = "academic_email"
                elif any(k in norm_h for k in ["email", "بريد", "ايميل", "إيميل", "gmail"]):
                    matched_field = "email"
                elif any(k in norm_h for k in ["distract", "تشتت"]):
                    matched_field = "biggest_distraction"
                elif any(k in norm_h for k in ["expect", "توقع", "أهدافك", "اهدافك"]):
                    matched_field = "expectations"
                elif any(k in norm_h for k in ["photograph", "تصوير", "تغطية إعلامية", "تغطيه اعلاميه"]):
                    matched_field = "consent_photo"
                elif any(k in norm_h for k in ["college", "كلية"]):
                    matched_field = "college"
                elif any(k in norm_h for k in ["major", "تخصص", "قسم"]):
                    matched_field = "major"
                elif any(k in norm_h for k in ["academic", "مستوى", "سنة دراسية", "level"]):
                    matched_field = "academic_lvl"
                elif any(k in norm_h for k in ["attend", "حضور"]):
                    matched_field = "attendance"
                elif any(k in norm_h for k in ["timestamp", "وقت", "تاريخ", "submission time"]):
                    matched_field = "registered_at"
                elif any(k in norm_h for k in ["hear", "سمعت", "مصدر المعرفة"]):
                    matched_field = "source_channel"

            # Pass 3: Secondary substring match (minimum 5 chars)
            if not matched_field:
                for m in self.mappings:
                    for alias in m.aliases:
                        norm_alias = self._normalize_header(alias)
                        if len(norm_alias) >= 5 and (norm_alias in norm_h or norm_h in norm_alias):
                            matched_field = m.target_field
                            break
                    if matched_field:
                        break

            # Pass 4: Fuzzy typo-tolerant similarity match
            if not matched_field:
                best_ratio = 0.0
                best_candidate = None
                for m in self.mappings:
                    # Compare against target_field
                    target_norm = self._normalize_header(m.target_field)
                    r = difflib.SequenceMatcher(None, norm_h, target_norm).ratio()
                    if r > best_ratio:
                        best_ratio = r
                        best_candidate = m.target_field
                    # Compare against aliases
                    for alias in m.aliases:
                        alias_norm = self._normalize_header(alias)
                        r = difflib.SequenceMatcher(None, norm_h, alias_norm).ratio()
                        if r > best_ratio:
                            best_ratio = r
                            best_candidate = m.target_field

                if best_ratio >= self.similarity_threshold:
                    matched_field = best_candidate

            if matched_field:
                resolved_map[raw_h] = matched_field
            else:
                unmapped_headers.append(raw_h)

        return resolved_map, unmapped_headers

    def extract_canonical_row(
        self,
        raw_row: Dict[str, Any],
        resolved_map: Dict[str, str],
        unmapped_headers: List[str]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extracts mapped canonical fields and stores unmapped/wide columns into raw_metadata.
        Returns:
            canonical_data: {target_field: raw_value}
            metadata: {unmapped_header: raw_value}
        """
        canonical_data = {}
        metadata = {}

        for raw_col, val in raw_row.items():
            if raw_col in resolved_map:
                canon_field = resolved_map[raw_col]
                # Avoid overwriting already populated canonical field
                if canon_field not in canonical_data or canonical_data[canon_field] is None or canonical_data[canon_field] == "":
                    canonical_data[canon_field] = val
                else:
                    metadata[raw_col] = val
            else:
                metadata[raw_col] = val

        return canonical_data, metadata

    def diff_headers(self, raw_headers: List[str]) -> Dict[str, Any]:
        """
        Audits raw headers against contract schema requirements.
        Returns:
            resolved_count: int
            unmapped_count: int
            resolved_map: {raw_header: canonical_field}
            unmapped_headers: [raw_headers]
            missing_required: [target_fields]
            is_compliant: bool
        """
        resolved, unmapped = self.resolve_headers(raw_headers)
        resolved_targets = set(resolved.values())

        missing_required = [
            m.target_field for m in self.mappings
            if m.required and m.target_field not in resolved_targets
        ]

        return {
            "resolved_count": len(resolved),
            "unmapped_count": len(unmapped),
            "resolved_map": resolved,
            "unmapped_headers": unmapped,
            "missing_required": missing_required,
            "is_compliant": len(missing_required) == 0
        }

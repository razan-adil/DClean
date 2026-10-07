import os
import re
import openpyxl
import csv
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional, Tuple

from pipeline.schema import CleanPerson, FactRegistration, QuarantineRecord, AuditSummary
from pipeline.contract_generator import AutoContractGenerator
from pipeline.contract_engine import ContractEngine
from pipeline.name_parser import ArabicNameParser
from pipeline.normalizers import PhoneNormalizer, EmailNormalizer, DateTimeNormalizer, CategoricalNormalizer
from pipeline.quarantine import QuarantineManager
from pipeline.entity_resolver import HybridEntityResolver
from pipeline.storage import StorageManager

class PipelineRunner:
    """
    Generalized Pipeline Runner with:
    - Multi-sheet Excel workbook processing.
    - Automated or declarative contract schema support.
    - Deterministic normalization (zero pseudo-normalization).
    - Internal MDM probabilistic entity resolution & deduplication.
    - Clean natural dataset export (no synthetic IDs forced onto business users).
    """
    def __init__(self, contract_path: Optional[str] = None, db_path: str = "cleaned_database.db"):
        self.contract_path = contract_path
        self.contract_engine: Optional[ContractEngine] = ContractEngine(contract_path) if contract_path and os.path.exists(contract_path) else None
        self.quarantine_manager = QuarantineManager()
        self.resolver = HybridEntityResolver()
        self.storage = StorageManager(db_path=db_path)

    @staticmethod
    def _score_header_alignment(headers: List[str], sample_rows: List[List[Any]]) -> int:
        score = 0
        for row in sample_rows:
            for h, val in zip(headers, row):
                if val is None:
                    continue
                h_lower = str(h).strip().lower()
                val_str = str(val).strip()
                if not val_str:
                    continue

                # Email check
                if any(k in h_lower for k in ["بريد", "email"]):
                    if "@" in val_str:
                        score += 6
                    else:
                        score -= 4
                # Phone check
                elif any(k in h_lower for k in ["جوال", "phone", "هاتف"]):
                    clean_phone = re.sub(r"[\s\-\+]", "", val_str)
                    if re.match(r"^(?:966|05)\d{8}$", clean_phone) or (clean_phone.isdigit() and len(clean_phone) in [9, 10, 12]):
                        score += 5
                    else:
                        score -= 3
                # Gender check
                elif any(k in h_lower for k in ["جنس", "gender"]):
                    if val_str in ["ذكر", "أنثى", "male", "female", "m", "f"]:
                        score += 4
                    else:
                        score -= 2
                # Timestamp check
                elif any(k in h_lower for k in ["timestamp", "تاريخ", "وقت"]):
                    if isinstance(val, (datetime, date)) or (any(c in val_str for c in [":", "-", "/"]) and any(c.isdigit() for c in val_str)):
                        score += 4
                    else:
                        score -= 4
                # Student ID / Numeric ID check
                elif any(k in h_lower for k in ["رقم", "id", "student"]) and not any(k in h_lower for k in ["جوال", "phone"]):
                    clean_num = val_str.replace(".0", "").strip()
                    if clean_num.isdigit():
                        score += 3
                # Arabic / Person Name check
                elif any(k in h_lower for k in ["اسم", "name"]) and not any(k in h_lower for k in ["جامع", "university"]):
                    if not any(c.isdigit() for c in val_str) and len(val_str) > 2:
                        score += 3
        return score

    def _read_excel_sheets(self, file_path: str) -> List[Tuple[str, List[str], List[Dict[str, Any]]]]:
        """
        Reads all valid tabular sheets from an Excel workbook (.xlsx).
        Robustly detects genuine header rows (>= 2 domain matches with short titles),
        intelligently aligns candidate headers for headless sheets using statistical scoring,
        and automatically skips duplicate/repeated header rows (e.g. from page breaks).
        """
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheets_data = []
        valid_header_candidates: List[List[str]] = []

        # Pass 1: Discover sheets and identify genuine header rows
        sheet_candidates = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            if ws.max_row < 2 or ws.max_column < 2:
                continue

            header_row_idx = None
            max_matches = 0
            for r in range(1, min(6, ws.max_row + 1)):
                row_vals = [str(ws.cell(r, c).value or "").strip() for c in range(1, ws.max_column + 1)]
                matches = sum(
                    1 for v in row_vals
                    if 0 < len(v) <= 45 and any(k in v.lower() for k in ["name", "email", "phone", "اسم", "جوال", "بريد", "timestamp", "وقت", "تخصص", "جامع"])
                )
                if matches > max_matches:
                    max_matches = matches
                    header_row_idx = r

            sheet_candidates.append({
                "name": sheet_name,
                "ws": ws,
                "header_idx": header_row_idx,
                "matches": max_matches
            })

            # Record genuine header rows (>= 2 domain matches)
            if max_matches >= 2 and header_row_idx is not None:
                headers = [str(ws.cell(header_row_idx, c).value or "").strip() for c in range(1, ws.max_column + 1)]
                while headers and not headers[-1]:
                    headers.pop()
                if headers and headers not in valid_header_candidates:
                    valid_header_candidates.append(headers)

        # Pass 2: Extract rows for each sheet
        for sc in sheet_candidates:
            ws = sc["ws"]
            sheet_name = sc["name"]
            header_idx = sc["header_idx"]
            matches = sc["matches"]

            if matches >= 2 and header_idx is not None:
                raw_headers = [str(ws.cell(header_idx, c).value or "").strip() for c in range(1, ws.max_column + 1)]
                while raw_headers and not raw_headers[-1]:
                    raw_headers.pop()
                data_start_row = header_idx + 1
            elif valid_header_candidates:
                # Sheet lacks genuine headers; check if row 1 is generic (Column1, Column2...)
                row1_vals = [str(ws.cell(1, c).value or "").strip() for c in range(1, ws.max_column + 1)]
                is_row1_generic = any(re.match(r"^column\d+$", v.lower()) for v in row1_vals if v)
                data_start_row = 2 if is_row1_generic else 1

                # Sample non-empty data rows to test alignment
                sample_rows = []
                for r in range(data_start_row, min(data_start_row + 4, ws.max_row + 1)):
                    row_vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
                    if any(v is not None and str(v).strip() for v in row_vals):
                        sample_rows.append(row_vals)

                # Score all candidate header sets to find the best match
                best_cand = None
                best_score = -999
                for cand in valid_header_candidates:
                    sc_score = self._score_header_alignment(cand, sample_rows)
                    if sc_score > best_score:
                        best_score = sc_score
                        best_cand = cand

                if best_cand:
                    raw_headers = list(best_cand[:ws.max_column])
                    # If sheet has more columns than candidate headers, pad
                    while len(raw_headers) < ws.max_column:
                        col_idx = len(raw_headers) + 1
                        cell_val = str(ws.cell(1, col_idx).value or f"Col_{col_idx}").strip()
                        raw_headers.append(cell_val if not re.match(r"^column\d+$", cell_val.lower()) else f"Col_{col_idx}")
                else:
                    raw_headers = [str(ws.cell(1, c).value or f"Col_{c}").strip() for c in range(1, ws.max_column + 1)]
            else:
                raw_headers = [str(ws.cell(1, c).value or f"Col_{c}").strip() for c in range(1, ws.max_column + 1)]
                data_start_row = 2

            if len(raw_headers) < 2:
                continue

            rows = []
            for r in range(data_start_row, ws.max_row + 1):
                # Detect and skip repeated header rows (e.g. from page breaks or table concatenation)
                header_matches = sum(
                    1 for c_idx, h in enumerate(raw_headers, 1)
                    if str(ws.cell(r, c_idx).value or "").strip().lower() == h.lower()
                )
                if header_matches >= 3:
                    continue

                row_dict = {}
                is_empty = True
                for c_idx, h in enumerate(raw_headers, 1):
                    val = ws.cell(r, c_idx).value
                    if val is not None and str(val).strip():
                        is_empty = False
                    row_dict[h] = val
                if not is_empty:
                    rows.append(row_dict)

            if rows:
                sheets_data.append((sheet_name, raw_headers, rows))

        return sheets_data

    def _read_csv(self, file_path: str) -> List[Tuple[str, List[str], List[Dict[str, Any]]]]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
        return [("CSV_Default", headers, rows)]

    def run(self, input_file_path: str, output_excel_path: Optional[str] = None) -> AuditSummary:
        ext = os.path.splitext(input_file_path)[1].lower()
        if ext in [".xlsx", ".xlsm"]:
            sheets_data = self._read_excel_sheets(input_file_path)
        elif ext in [".csv", ".tsv"]:
            sheets_data = self._read_csv(input_file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}. Only .xlsx and .csv are supported.")

        if not sheets_data:
            raise ValueError(f"No valid tabular data found in {input_file_path}")

        total_rows_all = 0
        valid_rows_all = 0
        cleaned_dataset_rows = []
        final_headers_order = []
        sheet_names_list = []

        # Deduplication tracker by resolved person_id to keep latest clean row
        person_latest_clean_row: Dict[str, Dict[str, Any]] = {}

        for sheet_name, raw_headers, raw_rows in sheets_data:
            sheet_names_list.append(sheet_name)
            total_rows_all += len(raw_rows)

            if not final_headers_order:
                final_headers_order = list(raw_headers)

            # Resolve or auto-generate contract for this sheet
            if self.contract_engine:
                engine = self.contract_engine
            else:
                contract_dict = AutoContractGenerator.generate_contract(
                    headers=raw_headers,
                    sample_rows=raw_rows,
                    dataset_id=os.path.splitext(os.path.basename(input_file_path))[0]
                )
                engine = ContractEngine(contract_dict)

            resolved_map, unmapped_headers = engine.resolve_headers(raw_headers)

            for row_idx, raw_row in enumerate(raw_rows, start=1):
                canon_data, extra_meta = engine.extract_canonical_row(raw_row, resolved_map, unmapped_headers)

                # 1. Deterministic Name Parsing
                raw_ar_name = canon_data.get("full_name_ar")
                raw_en_name = canon_data.get("full_name_en")
                parsed_ar = ArabicNameParser.parse_arabic_name(str(raw_ar_name)) if raw_ar_name else None
                parsed_en = ArabicNameParser.parse_english_name(str(raw_en_name)) if raw_en_name else None

                # 2. Deterministic Phone & Email
                clean_phone = PhoneNormalizer.normalize(canon_data.get("phone"), default_region="SA")
                clean_email = EmailNormalizer.normalize(canon_data.get("email"))

                # 3. Check for spam / dummy row
                all_text_concat = " ".join(str(v).lower() for v in raw_row.values() if v)
                is_spam = "test test" in all_text_concat or (str(canon_data.get("phone")).strip() == "12345")

                has_valid_name = bool((parsed_ar and parsed_ar.full_clean) or (parsed_en and parsed_en.full_clean))
                has_phone = clean_phone is not None
                has_email = clean_email is not None

                # 4. Quarantine Assertion Check
                quarantine_record = self.quarantine_manager.evaluate_record(
                    source_file=os.path.basename(input_file_path),
                    sheet_name=sheet_name,
                    row_index=row_idx,
                    raw_payload=raw_row,
                    has_name=has_valid_name,
                    has_phone=has_phone,
                    has_email=has_email,
                    is_spam=is_spam
                )

                if quarantine_record:
                    continue

                valid_rows_all += 1

                # 5. Deterministic Normalization for Structured & Categorical fields
                clean_uni = CategoricalNormalizer.normalize_university(canon_data.get("university"))
                clean_college = CategoricalNormalizer.normalize_college(canon_data.get("college"))
                clean_academic = CategoricalNormalizer.normalize_academic_level(canon_data.get("academic_lvl"))
                clean_major = CategoricalNormalizer.normalize_major(canon_data.get("major"))
                clean_timestamp = DateTimeNormalizer.normalize(canon_data.get("registered_at"))

                consent = CategoricalNormalizer.parse_boolean(canon_data.get("consent_photo"))
                attendance = CategoricalNormalizer.parse_boolean(canon_data.get("attendance"))

                # 6. Entity Resolution & Survivorship
                person, is_duplicate = self.resolver.resolve_person(
                    phone_e164=clean_phone,
                    email=clean_email,
                    parsed_name_ar=parsed_ar,
                    parsed_name_en=parsed_en,
                    university=clean_uni
                )

                # Fact event linking
                fact_reg = FactRegistration(
                    person_id=person.person_id,
                    sheet_name=sheet_name,
                    dataset_id=engine.dataset_id,
                    attended_flag=bool(attendance) if attendance is not None else False,
                    consent_photo=bool(consent) if consent is not None else False,
                    major=clean_major,
                    university=clean_uni,
                    academic_lvl=clean_academic,
                    registered_at=clean_timestamp or datetime.now(timezone.utc).isoformat(),
                    raw_metadata=extra_meta
                )
                self.resolver.add_registration_event(fact_reg)

                # 7. Construct Clean Natural Row (Updating original raw row with clean values)
                clean_row = dict(raw_row)

                # Replace raw mapped columns with their cleaned versions
                for raw_col, canon_target in resolved_map.items():
                    if canon_target == "full_name_ar" and parsed_ar and parsed_ar.full_clean:
                        clean_row[raw_col] = parsed_ar.full_clean
                    elif canon_target == "full_name_en" and parsed_en and parsed_en.full_clean:
                        clean_row[raw_col] = parsed_en.full_clean
                    elif canon_target == "phone" and clean_phone:
                        clean_row[raw_col] = clean_phone
                    elif canon_target == "email" and clean_email:
                        clean_row[raw_col] = clean_email
                    elif canon_target == "academic_lvl" and clean_academic:
                        clean_row[raw_col] = clean_academic
                    elif canon_target == "university" and clean_uni:
                        clean_row[raw_col] = clean_uni
                    elif canon_target == "college" and clean_college:
                        clean_row[raw_col] = clean_college
                    elif canon_target == "major" and clean_major:
                        clean_row[raw_col] = clean_major
                    elif canon_target == "student_id" and clean_row.get(raw_col) is not None:
                        val_s = str(clean_row[raw_col]).strip()
                        if val_s.endswith(".0"):
                            val_s = val_s[:-2]
                        clean_row[raw_col] = val_s
                    elif canon_target == "registered_at" and clean_timestamp:
                        clean_row[raw_col] = clean_timestamp
                    elif canon_target == "consent_photo" and consent is not None:
                        clean_row[raw_col] = "TRUE" if consent else "FALSE"
                    elif canon_target == "attendance" and attendance is not None:
                        clean_row[raw_col] = "TRUE" if attendance else "FALSE"
                    elif canon_target in ["source_channel", "skills"]:
                        clean_row[raw_col] = CategoricalNormalizer.normalize_multiselect(raw_row[raw_col])

                # Survivorship in cleaned dataset rows: keep most recent submission per person
                p_id = person.person_id
                if p_id in person_latest_clean_row:
                    prev_row = person_latest_clean_row[p_id]
                    # If this submission has positive attendance, keep it
                    if attendance is True:
                        for k, v in clean_row.items():
                            if v is not None:
                                prev_row[k] = v
                    else:
                        prev_row.update({k: v for k, v in clean_row.items() if v is not None})
                else:
                    person_latest_clean_row[p_id] = clean_row

        cleaned_dataset_rows = list(person_latest_clean_row.values())

        # Observability Metrics
        quarantine_rows = len(self.quarantine_manager.records)
        quarantine_rate = self.quarantine_manager.get_quarantine_rate(total_rows_all)
        is_alert = self.quarantine_manager.is_threshold_exceeded(total_rows_all)
        status_str = "ALERT_THRESHOLD_EXCEEDED" if is_alert else "HEALTHY"

        summary = AuditSummary(
            source_file=os.path.basename(input_file_path),
            sheet_name=", ".join(sheet_names_list),
            total_rows=total_rows_all,
            valid_rows=valid_rows_all,
            quarantined_rows=quarantine_rows,
            unique_persons_resolved=len(self.resolver.persons_by_id),
            duplicate_events_merged=self.resolver.merged_duplicate_count,
            quarantine_rate_pct=quarantine_rate,
            status=status_str
        )

        # Persistence
        persons_list = list(self.resolver.persons_by_id.values())
        regs_list = self.resolver.registrations
        quarantine_list = self.quarantine_manager.records

        self.storage.save_to_sqlite(persons_list, regs_list, quarantine_list, summary)

        if not output_excel_path:
            base, _ = os.path.splitext(input_file_path)
            output_excel_path = f"{base}_Cleaned.xlsx"

        self.storage.export_clean_excel(
            output_path=output_excel_path,
            cleaned_dataset_rows=cleaned_dataset_rows,
            headers_order=final_headers_order,
            persons=persons_list,
            quarantine=quarantine_list,
            summary=summary
        )

        return summary

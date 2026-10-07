from typing import Dict, Any, List, Optional
from pipeline.schema import QuarantineRecord

class QuarantineManager:
    """
    Quarantine & Triage Manager.
    Enforces contract assertions and isolates invalid records into a dedicated dead-letter store
    with machine-readable rejection vectors to prevent pipeline corruption.
    """
    def __init__(self, threshold_pct: float = 15.0):
        if not 0 <= threshold_pct <= 100:
            raise ValueError("threshold_pct must be between 0 and 100")
        self.threshold_pct = threshold_pct
        self.records: List[QuarantineRecord] = []

    def evaluate_record(
        self,
        source_file: str,
        sheet_name: str,
        row_index: int,
        raw_payload: Dict[str, Any],
        has_name: bool,
        has_phone: bool,
        has_email: bool,
        is_spam: bool = False
    ) -> Optional[QuarantineRecord]:
        """
        Evaluates record contract assertions. Returns QuarantineRecord if rejected, None if passed.
        """
        rejection_codes = []

        if not has_name:
            rejection_codes.append("MISSING_REQUIRED_NAME")

        if not has_phone and not has_email:
            rejection_codes.append("MISSING_IDENTIFIER_RECORD_CANNOT_BE_LINKED")

        if is_spam:
            rejection_codes.append("SPAM_OR_DUMMY_VALUES_DETECTED")

        if rejection_codes:
            record = QuarantineRecord(
                source_file=source_file,
                sheet_name=sheet_name,
                row_index=row_index,
                raw_payload=raw_payload,
                rejection_codes=rejection_codes
            )
            self.records.append(record)
            return record

        return None

    def get_quarantine_rate(self, total_rows: int) -> float:
        if total_rows < 0:
            raise ValueError("total_rows must be non-negative")
        if total_rows == 0:
            return 0.0
        return round((len(self.records) / total_rows) * 100.0, 2)

    def is_threshold_exceeded(self, total_rows: int) -> bool:
        return self.get_quarantine_rate(total_rows) > self.threshold_pct

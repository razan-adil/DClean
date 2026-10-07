import json
import os
import sqlite3
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from pipeline.schema import CleanPerson, FactRegistration, QuarantineRecord, AuditSummary

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)

class StorageManager:
    """
    Handles dual persistence:
    1. SQLite Database (relational integrity and internal entity resolution).
    2. Formatted multi-sheet Excel Workbook:
       - Sheet 1: Cleaned_Dataset (natural columns cleaned, NO synthetic ID forced onto business users).
       - Sheet 2: quarantine_records (dead-letter store with rejection vectors).
       - Sheet 3: audit_summary (governance and quality metrics).
       - Sheet 4: dim_persons (master entity table for data engineering reference).
    """
    def __init__(self, db_path: str = "cleaned_database.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_sqlite_db()

    def _init_sqlite_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Dimension Table: dim_persons
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_persons (
            person_id TEXT PRIMARY KEY,
            canonical_email TEXT,
            canonical_phone_e164 TEXT,
            full_name_ar TEXT,
            full_name_en TEXT,
            first_name TEXT,
            father_name TEXT,
            family_name TEXT,
            clean_display_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # Fact Table: fact_registrations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_registrations (
            registration_id TEXT PRIMARY KEY,
            person_id TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            attended_flag INTEGER NOT NULL,
            consent_photo INTEGER NOT NULL,
            major TEXT,
            university TEXT,
            academic_lvl TEXT,
            registered_at TEXT NOT NULL,
            raw_metadata TEXT,
            FOREIGN KEY (person_id) REFERENCES dim_persons(person_id)
        );
        """)

        # Quarantine Table: quarantine_records
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarantine_records (
            quarantine_id TEXT PRIMARY KEY,
            source_file TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            raw_payload TEXT NOT NULL,
            rejection_codes TEXT NOT NULL,
            quarantined_at TEXT NOT NULL
        );
        """)

        # Observability Table: audit_runs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            total_rows INTEGER NOT NULL,
            valid_rows INTEGER NOT NULL,
            quarantined_rows INTEGER NOT NULL,
            unique_persons INTEGER NOT NULL,
            merged_duplicates INTEGER NOT NULL,
            quarantine_rate_pct REAL NOT NULL,
            status TEXT NOT NULL,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        conn.close()

    def save_to_sqlite(
        self,
        persons: List[CleanPerson],
        registrations: List[FactRegistration],
        quarantine: List[QuarantineRecord],
        summary: AuditSummary
    ):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        for p in persons:
            cursor.execute("""
            INSERT OR REPLACE INTO dim_persons (
                person_id, canonical_email, canonical_phone_e164, full_name_ar, full_name_en,
                first_name, father_name, family_name, clean_display_name, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                p.person_id, p.canonical_email, p.canonical_phone_e164, p.full_name_ar, p.full_name_en,
                p.first_name, p.father_name, p.family_name, p.clean_display_name, p.created_at, p.updated_at
            ))

        for r in registrations:
            cursor.execute("""
            INSERT OR REPLACE INTO fact_registrations (
                registration_id, person_id, sheet_name, dataset_id, attended_flag, consent_photo,
                major, university, academic_lvl, registered_at, raw_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                r.registration_id, r.person_id, r.sheet_name, r.dataset_id,
                1 if r.attended_flag else 0,
                1 if r.consent_photo else 0,
                r.major, r.university, r.academic_lvl, r.registered_at,
                json.dumps(r.raw_metadata, ensure_ascii=False, default=json_serial)
            ))

        for q in quarantine:
            cursor.execute("""
            INSERT OR REPLACE INTO quarantine_records (
                quarantine_id, source_file, sheet_name, row_index, raw_payload, rejection_codes, quarantined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                q.quarantine_id, q.source_file, q.sheet_name, q.row_index,
                json.dumps(q.raw_payload, ensure_ascii=False, default=json_serial),
                json.dumps(q.rejection_codes, ensure_ascii=False, default=json_serial),
                q.quarantined_at
            ))

        cursor.execute("""
        INSERT INTO audit_runs (
            source_file, sheet_name, total_rows, valid_rows, quarantined_rows,
            unique_persons, merged_duplicates, quarantine_rate_pct, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            summary.source_file, summary.sheet_name, summary.total_rows, summary.valid_rows, summary.quarantined_rows,
            summary.unique_persons_resolved, summary.duplicate_events_merged,
            summary.quarantine_rate_pct, summary.status
        ))

        conn.commit()
        conn.close()

    def export_clean_excel(
        self,
        output_path: str,
        cleaned_dataset_rows: List[Dict[str, Any]],
        headers_order: List[str],
        persons: List[CleanPerson],
        quarantine: List[QuarantineRecord],
        summary: AuditSummary
    ):
        wb = openpyxl.Workbook()
        font_family = "Segoe UI"

        title_font = Font(name=font_family, size=12, bold=True, color="0F172A")
        header_font = Font(name=font_family, size=10, bold=True, color="FFFFFF")
        data_font = Font(name=font_family, size=9, color="1E293B")
        bold_data_font = Font(name=font_family, size=9, bold=True, color="1E293B")
        code_font = Font(name="Consolas", size=9, color="0F172A")

        thin_side = Side(border_style="thin", color="CBD5E1")
        cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        fill_header_clean = PatternFill(start_color="047857", end_color="047857", fill_type="solid") # Emerald
        fill_header_quar = PatternFill(start_color="BE123C", end_color="BE123C", fill_type="solid")  # Rose
        fill_header_audit = PatternFill(start_color="475569", end_color="475569", fill_type="solid") # Slate
        fill_header_dim = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")   # Amber

        fill_even = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        fill_odd = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        fill_quar_row = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

        # -------------------------------------------------------------
        # SHEET 1: Cleaned_Dataset (Natural columns without synthetic IDs)
        # -------------------------------------------------------------
        ws_clean = wb.active
        ws_clean.title = "Cleaned_Data"
        ws_clean.views.sheetView[0].showGridLines = True

        ws_clean["A1"] = f"Cleaned & Deduplicated Data ({summary.source_file})"
        ws_clean["A1"].font = title_font

        # Write clean headers
        for c_idx, h in enumerate(headers_order, 1):
            cell = ws_clean.cell(row=3, column=c_idx, value=h)
            cell.font = header_font
            cell.fill = fill_header_clean
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cell_border
            ws_clean.column_dimensions[get_column_letter(c_idx)].width = max(18, min(len(str(h)) + 4, 40))

        # Write clean data rows
        for r_idx, row_dict in enumerate(cleaned_dataset_rows, start=4):
            ws_clean.row_dimensions[r_idx].height = 20
            row_fill = fill_even if r_idx % 2 == 0 else fill_odd
            for c_idx, h in enumerate(headers_order, 1):
                val = row_dict.get(h, "")
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False, default=json_serial)
                cell = ws_clean.cell(row=r_idx, column=c_idx, value=val)
                cell.font = data_font
                cell.fill = row_fill
                cell.border = cell_border
                cell.alignment = Alignment(horizontal="left", vertical="center")

        ws_clean.freeze_panes = "A4"

        # -------------------------------------------------------------
        # SHEET 2: quarantine_records
        # -------------------------------------------------------------
        ws_quar = wb.create_sheet(title="quarantine_records")
        ws_quar.views.sheetView[0].showGridLines = True

        ws_quar["A1"] = "Quarantine Store (Contract Assertion Violations)"
        ws_quar["A1"].font = title_font

        quar_headers = [("quarantine_id", 32), ("sheet", 16), ("row_index", 12), ("rejection_codes", 36), ("quarantined_at", 20), ("raw_payload", 55)]
        for c_idx, (h_name, width) in enumerate(quar_headers, 1):
            cell = ws_quar.cell(row=3, column=c_idx, value=h_name)
            cell.font = header_font
            cell.fill = fill_header_quar
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = cell_border
            ws_quar.column_dimensions[get_column_letter(c_idx)].width = width

        for r_idx, q in enumerate(quarantine, start=4):
            ws_quar.row_dimensions[r_idx].height = 22
            row_vals = [
                q.quarantine_id, q.sheet_name, q.row_index,
                ", ".join(q.rejection_codes), q.quarantined_at,
                json.dumps(q.raw_payload, ensure_ascii=False, default=json_serial)
            ]
            for c_idx, val in enumerate(row_vals, 1):
                cell = ws_quar.cell(row=r_idx, column=c_idx, value=val)
                cell.font = code_font if c_idx in [1, 6] else data_font
                cell.fill = fill_quar_row
                cell.border = cell_border
                cell.alignment = Alignment(horizontal="center" if c_idx in [1, 2, 3, 5] else "left", vertical="center")

        ws_quar.freeze_panes = "A4"

        # -------------------------------------------------------------
        # SHEET 3: audit_summary
        # -------------------------------------------------------------
        ws_audit = wb.create_sheet(title="audit_summary")
        ws_audit.views.sheetView[0].showGridLines = True

        ws_audit["A1"] = "Pipeline Execution Governance Summary"
        ws_audit["A1"].font = title_font

        metrics = [
            ("Source Dataset File", summary.source_file),
            ("Sheet Name(s)", summary.sheet_name),
            ("Total Rows Ingested", summary.total_rows),
            ("Valid Cleaned Rows", summary.valid_rows),
            ("Quarantined Rows", summary.quarantined_rows),
            ("Quarantine Rate (%)", f"{summary.quarantine_rate_pct}%"),
            ("Unique Entities Resolved", summary.unique_persons_resolved),
            ("Duplicate Submissions Merged", summary.duplicate_events_merged),
            ("Pipeline Health Status", summary.status)
        ]

        for m_idx, (k, v) in enumerate(metrics, start=3):
            ws_audit.row_dimensions[m_idx].height = 22
            c1 = ws_audit.cell(row=m_idx, column=1, value=k)
            c2 = ws_audit.cell(row=m_idx, column=2, value=str(v))
            c1.font = bold_data_font
            c2.font = code_font
            c1.border = cell_border
            c2.border = cell_border
            c1.fill = fill_even
            c2.fill = fill_odd
            c1.alignment = Alignment(horizontal="left", vertical="center")
            c2.alignment = Alignment(horizontal="left", vertical="center")

        ws_audit.column_dimensions["A"].width = 30
        ws_audit.column_dimensions["B"].width = 40

        # -------------------------------------------------------------
        # SHEET 4: dim_persons (Master entity table for engineers / audit)
        # -------------------------------------------------------------
        ws_dim = wb.create_sheet(title="dim_persons")
        ws_dim.views.sheetView[0].showGridLines = True

        ws_dim["A1"] = "Master Person Entity Directory (Internal MDM Layer)"
        ws_dim["A1"].font = title_font

        dim_headers = [("person_id (UUIDv5)", 34), ("display_name", 24), ("phone_e164", 20), ("email", 28), ("name_ar", 24), ("name_en", 24)]
        for c_idx, (h_name, width) in enumerate(dim_headers, 1):
            cell = ws_dim.cell(row=3, column=c_idx, value=h_name)
            cell.font = header_font
            cell.fill = fill_header_dim
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = cell_border
            ws_dim.column_dimensions[get_column_letter(c_idx)].width = width

        for r_idx, p in enumerate(persons, start=4):
            ws_dim.row_dimensions[r_idx].height = 20
            row_fill = fill_even if r_idx % 2 == 0 else fill_odd
            row_vals = [p.person_id, p.clean_display_name, p.canonical_phone_e164 or "", p.canonical_email or "", p.full_name_ar or "", p.full_name_en or ""]
            for c_idx, val in enumerate(row_vals, 1):
                cell = ws_dim.cell(row=r_idx, column=c_idx, value=val)
                cell.font = code_font if c_idx == 1 else data_font
                cell.fill = row_fill
                cell.border = cell_border
                cell.alignment = Alignment(horizontal="center" if c_idx in [1, 3] else "left", vertical="center")

        ws_dim.freeze_panes = "A4"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        try:
            wb.save(output_path)
        except PermissionError:
            base, ext = os.path.splitext(output_path)
            alt_path = f"{base}_new{ext}"
            wb.save(alt_path)
            print(f"[Warning] '{output_path}' was locked; saved clean output to '{alt_path}' instead.")

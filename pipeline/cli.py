import argparse
import os
import sys

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pipeline.runner import PipelineRunner

def main():
    parser = argparse.ArgumentParser(description="Generalized Multi-Sheet Data Cleaning & Entity Resolution Pipeline")
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to raw tabular input file (.xlsx or .csv)"
    )
    parser.add_argument(
        "--contract", "-c",
        default=None,
        help="Optional path to YAML contract schema (auto-generated if omitted)"
    )
    parser.add_argument(
        "--db", "-d",
        default="CleanData/cleaned_database.db",
        help="Path to output SQLite database"
    )
    parser.add_argument(
        "--output-excel", "-o",
        default=None,
        help="Path to output cleaned Excel workbook"
    )

    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    db_path = os.path.abspath(args.db)
    contract_path = os.path.abspath(args.contract) if args.contract else None

    if not os.path.exists(input_path):
        print(f"[Error] Input file '{input_path}' does not exist.")
        sys.exit(1)

    print("=" * 75)
    print("   GENERALIZED DATA CLEANING & ENTITY RESOLUTION PIPELINE")
    print("=" * 75)
    print(f"Input File:        {input_path}")
    print(f"Contract Schema:   {contract_path or '[Auto-Generated via Schema Classifier]'}")
    print(f"SQLite Target:     {db_path}")
    print("-" * 75)

    runner = PipelineRunner(contract_path=contract_path, db_path=db_path)
    summary = runner.run(input_file_path=input_path, output_excel_path=args.output_excel)

    out_excel = args.output_excel or f"{os.path.splitext(input_path)[0]}_Cleaned.xlsx"

    print("\n" + "=" * 75)
    print("   EXECUTION & GOVERNANCE AUDIT SUMMARY")
    print("=" * 75)
    print(f"  Source File:                {summary.source_file}")
    print(f"  Processed Sheet(s):         {summary.sheet_name}")
    print(f"  Total Ingested Rows:        {summary.total_rows}")
    print(f"  Valid Processed Rows:       {summary.valid_rows}")
    print(f"  Quarantined Rows:           {summary.quarantined_rows} ({summary.quarantine_rate_pct}%)")
    print(f"  Unique Entities Resolved:   {summary.unique_persons_resolved}")
    print(f"  Duplicate Submissions Merged:{summary.duplicate_events_merged}")
    print(f"  Pipeline Health Status:     [{summary.status}]")
    print("-" * 75)
    print(f"  Clean Database:             file:///{db_path.replace(os.sep, '/')}")
    print(f"  Clean Excel Output:         file:///{os.path.abspath(out_excel).replace(os.sep, '/')}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    main()

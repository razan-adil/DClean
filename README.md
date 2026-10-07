# DClean — Data Cleaning & Quality System

A team project for cleaning, standardizing, validating, and deduplicating Arabic and English spreadsheet data.

## My Contribution — Razan Adil

My work focused on **Validation & Error Handling**:
- Defining data structures and schemas.
- Validating records and handling invalid data.
- Quarantining records that cannot safely continue through the pipeline.
- Providing clear rejection reasons for review.

## Features
- Arabic and English data normalization
- Schema detection and YAML contracts
- Record validation and quarantine
- Entity resolution and duplicate handling
- Excel output, SQLite storage, and audit summaries
- Streamlit dashboard

## Run locally

Use Python 3.11 or newer. From the project folder:

```bash
python -m pip install -r requirements.txt
python tools/generate_datasets.py
python -m streamlit run dashboard.py
```

Upload `RawData/demo_workshop.csv` to try the application. The demo deliberately leaves phone numbers blank and uses reserved example.com email addresses.

For a CLI demo:

```bash
python -m pipeline.cli -i RawData/demo_workshop.csv -c config/workshop_contract.yaml -o CleanData/demo_cleaned.xlsx
```

## Public demo data and model

This package does not include the original input spreadsheets, processed workbooks, databases, or original trained model. The included classifier was retrained using synthetic templates only. Its accuracy and behavior may differ from the original model; it is a demonstration artifact.

To retrain the demo classifier:

```bash
python tools/train_column_classifier.py --fast-only
```

Do not commit real input files, generated outputs, or screenshots containing personal information.

## Team attribution

DClean was developed collaboratively. This repository documents Razan's contribution and includes the team's source code with public-demo data changes. Other project components were implemented by fellow team members.

Original project: https://github.com/M2sk2/DClean

[LinkedIn](https://www.linkedin.com/in/razan-adil-79639b298)

# DClean — Data Cleaning & Quality System

DClean is a team-built application for cleaning, standardizing, validating, and deduplicating Arabic and English registration data.

Spreadsheet records often contain inconsistent names, missing identifiers, different formatting, and duplicate entries. DClean processes these records through a structured workflow: it detects the data schema, standardizes values, validates records, and resolves duplicates.

Records that fail validation are stored separately with clear rejection reasons. The application exports cleaned data to Excel and stores records and audit information in SQLite.

## My Contribution — Razan Adil

I contributed to the **Validation & Error Handling** layer of the project:

- Defined record structures and validation schemas.
- Implemented checks to identify missing or invalid data.
- Routed rejected records to a quarantine store for review.
- Added rejection codes to explain why each record failed validation.

This layer helps prevent invalid records from continuing through the pipeline and makes data quality issues easier to trace.

## Features

- Arabic and English data normalization.
- Schema detection and YAML-based data contracts.
- Record validation and error handling.
- Quarantine storage with rejection reasons.
- Entity resolution and duplicate handling.
- Excel exports, SQLite storage, and audit summaries.
- Streamlit dashboard for uploading data and reviewing results.

## Application Preview

### Dashboard

The Streamlit dashboard provides an interface for uploading datasets, running the cleaning workflow, and reviewing the output.

<img width="1600" height="725" alt="WhatsApp Image 2026-10-08 at 12 00 33 AM" src="https://github.com/user-attachments/assets/b520182b-5324-43e1-b7d7-023ad5841f1d" />


### Before Cleaning

The input dataset contains registration records before processing, including a deliberately incomplete record used to demonstrate validation.

<img width="1600" height="842" alt="WhatsApp Image 2026-10-08 at 12 02 17 AM" src="https://github.com/user-attachments/assets/fe8fa48f-9f57-48ba-85b8-2bd496212065" />


### After Cleaning

The cleaned output contains the accepted records in a standardized Excel worksheet. In this demo, 12 records passed validation.

<img width="1600" height="832" alt="WhatsApp Image 2026-10-08 at 12 03 03 AM" src="https://github.com/user-attachments/assets/32ca08da-9507-407b-b910-1e43a7046296" />


### Rejected Records and Validation Reasons

Records that fail validation are saved in a separate quarantine worksheet with their source row and rejection codes.

In this demo, record 13 was quarantined because it was missing a required name and an identifier needed for record linkage.

<img width="1599" height="849" alt="WhatsApp Image 2026-10-08 at 12 03 54 AM" src="https://github.com/user-attachments/assets/6b60b131-d7e1-4aad-bfe6-3ca238a99e95" />



### Audit Summary

The audit worksheet summarizes the results of the cleaning run.

| Metric | Demo Result |
| --- | --- |
| Input records | 13 |
| Valid cleaned records | 12 |
| Quarantined records | 1 |
| Quarantine rate | 7.69% |
| Unique entities resolved | 12 |
| Duplicate submissions merged | 0 |

These results describe this demo dataset only.

<img width="1600" height="842" alt="WhatsApp Image 2026-10-08 at 12 04 31 AM" src="https://github.com/user-attachments/assets/2a74eede-a2dc-4c47-aec9-b4e1c386d46f" />


## Technologies

- **Language:** Python
- **Interface:** Streamlit
- **Data processing:** pandas
- **Machine learning:** scikit-learn
- **Data contracts:** YAML
- **Storage:** SQLite
- **Outputs:** Excel workbooks

## Run Locally

Use Python 3.11 or newer. From the project folder, install the dependencies and start the dashboard:

```bash
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

Upload `RawData/demo_workshop.csv` to try the application.

The demo uses fictional records, reserved `example.com` email addresses, and blank phone numbers. One record deliberately has no name or identifier to demonstrate quarantine handling.

To regenerate the demo datasets:

```bash
python tools/generate_datasets.py
```

### Command-Line Demo

```bash
python -m pipeline.cli -i RawData/demo_workshop.csv -c config/workshop_contract.yaml -o CleanData/demo_cleaned.xlsx
```

## Public Demo Data and Model

This public version does not include the original input spreadsheets, processed workbooks, databases, or original trained model.

The included column classifier was retrained using synthetic templates only. Its accuracy and behavior may differ from the original model; it is included for demonstration purposes.

To retrain the demo classifier:

```bash
python tools/train_column_classifier.py --fast-only
```

Do not commit real input files, generated outputs containing personal information, or screenshots showing personal data.

## Team Attribution

DClean was developed collaboratively. This repository presents my contribution to **Validation & Error Handling** and includes the team's source code with changes made for a public demonstration.

Other project components were implemented by fellow team members.

[Original Team Repository](https://github.com/M2sk2/DClean)

## Contact

[Razan Adil — LinkedIn](https://www.linkedin.com/in/razan-adil-79639b298)

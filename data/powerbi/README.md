# Power BI Data

This directory contains the prepared CSV datasets for the Power BI report.

The CSVs are already aggregated and do not require Python, DuckDB, Parquet,
or access to the raw FHIR JSON data.

## Import into Power BI

1. Open Power BI Desktop.
2. Select **Get Data**.
3. Select **Text/CSV**.
4. Open the required CSV files from this directory.
5. Load the data.
6. Build the report using the prepared fields.

## Available datasets

| File | Purpose |
|---|---|
| `patient_summary.csv` | Patient demographics and age |
| `condition_summary.csv` | Condition frequency and patient counts |
| `condition_encounter_summary.csv` | Conditions linked to encounters |
| `encounter_summary.csv` | Encounter types, classes and statuses |
| `medication_summary.csv` | Medication frequency and patient counts |
| `procedure_summary.csv` | Procedure frequency and patient counts |
| `utilisation_by_gender.csv` | Encounter utilisation by gender |
| `utilisation_by_age_group.csv` | Encounter utilisation by age group |
| `encounters_over_time.csv` | Encounter activity by year |
| `resource_summary.csv` | Overall FHIR resource volumes |

## Suggested report pages

### 1. Overview

Use:

- `resource_summary.csv`
- `encounters_over_time.csv`

Suggested visuals:

- Total records KPI
- Total patients KPI
- Total encounters KPI
- Resource volume bar chart
- Encounters over time line chart

### 2. Patient Demographics

Use:

- `patient_summary.csv`
- `utilisation_by_gender.csv`
- `utilisation_by_age_group.csv`

Suggested visuals:

- Patients by gender
- Patients by age
- Encounters by gender
- Encounters by age group

### 3. Conditions

Use:

- `condition_summary.csv`
- `condition_encounter_summary.csv`

Suggested visuals:

- Top conditions
- Patients affected by condition
- Encounters associated with condition

### 4. Healthcare Utilisation

Use:

- `encounter_summary.csv`
- `utilisation_by_gender.csv`
- `utilisation_by_age_group.csv`
- `encounters_over_time.csv`

Suggested visuals:

- Encounter type
- Encounter class
- Encounters by demographic group
- Encounters over time

### 5. Medications & Procedures

Use:

- `medication_summary.csv`
- `procedure_summary.csv`

Suggested visuals:

- Top medications
- Top procedures
- Unique patients associated with each

## Important

These files are analytical summaries rather than the complete clinical
record-level dataset. They are intended to make the Power BI report easy
to build while keeping the underlying Parquet/FHIR processing separate.

The source analytical Parquet data and generated charts are available under
`data/processed/` and `data/analytics/` respectively.

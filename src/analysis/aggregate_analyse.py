from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd


PROC_ROOT = Path("data/processed")
OUTPUT_ROOT = Path("data/analytics")

TABLE_DIR = OUTPUT_ROOT / "tables"
SUMMARY_DIR = OUTPUT_ROOT / "summaries"
CHART_DIR = OUTPUT_ROOT / "charts"

POWERBI_DIR = Path("data/powerbi")


def ensure_directories() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)


def parquet_path(resource_type: str) -> str:
    return str(PROC_ROOT / resource_type / "*.parquet")


def query_to_csv(
    con: duckdb.DuckDBPyConnection,
    query: str,
    output_name: str,
) -> pd.DataFrame:

    df = con.execute(query).fetchdf()

    output_path = TABLE_DIR / output_name

    df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Wrote {len(df):,} rows → {output_path}"
    )

    return df


# ---------------------------------------------------------------------------
# Analytical tables
# ---------------------------------------------------------------------------

def create_patient_summary(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        patient_id,
        gender,
        birth_date,
        family_name,
        given_name,
        marital_status,
        race,
        ethnicity,
        birth_city,
        birth_state,
        deceased_date,

        CASE
            WHEN birth_date IS NULL THEN NULL
            ELSE
                DATE_DIFF(
                    'year',
                    CAST(birth_date AS DATE),
                    CURRENT_DATE
                )
        END AS age

    FROM read_parquet('{parquet_path("patient")}')
    """

    return query_to_csv(
        con,
        query,
        "patient_summary.csv",
    )


def create_condition_summary(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        condition_code,
        condition_display,
        COUNT(*) AS condition_count,
        COUNT(DISTINCT patient_id) AS unique_patients

    FROM read_parquet('{parquet_path("condition")}')
    WHERE condition_code IS NOT NULL
       OR condition_display IS NOT NULL

    GROUP BY
        condition_code,
        condition_display

    ORDER BY condition_count DESC
    """

    return query_to_csv(
        con,
        query,
        "condition_summary.csv",
    )


def create_encounter_summary(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        encounter_type,
        class,
        status,
        COUNT(*) AS encounter_count,
        COUNT(DISTINCT patient_id) AS unique_patients

    FROM read_parquet('{parquet_path("encounter")}')

    GROUP BY
        encounter_type,
        class,
        status

    ORDER BY encounter_count DESC
    """

    return query_to_csv(
        con,
        query,
        "encounter_summary.csv",
    )


def create_condition_encounter_summary(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        c.condition_code,
        c.condition_display,
        COUNT(DISTINCT c.condition_id) AS condition_count,
        COUNT(DISTINCT c.patient_id) AS patients,
        COUNT(DISTINCT c.encounter_id) AS encounters

    FROM read_parquet('{parquet_path("condition")}') c

    GROUP BY
        c.condition_code,
        c.condition_display

    ORDER BY encounters DESC
    """

    return query_to_csv(
        con,
        query,
        "condition_encounter_summary.csv",
    )


def create_medication_summary(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        medication_code,
        medication_display,
        COUNT(*) AS medication_count,
        COUNT(DISTINCT patient_id) AS unique_patients

    FROM read_parquet('{parquet_path("medicationrequest")}')
    WHERE medication_code IS NOT NULL
       OR medication_display IS NOT NULL

    GROUP BY
        medication_code,
        medication_display

    ORDER BY medication_count DESC
    """

    return query_to_csv(
        con,
        query,
        "medication_summary.csv",
    )


def create_procedure_summary(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        procedure_code,
        procedure_display,
        COUNT(*) AS procedure_count,
        COUNT(DISTINCT patient_id) AS unique_patients

    FROM read_parquet('{parquet_path("procedure")}')
    WHERE procedure_code IS NOT NULL
       OR procedure_display IS NOT NULL

    GROUP BY
        procedure_code,
        procedure_display

    ORDER BY procedure_count DESC
    """

    return query_to_csv(
        con,
        query,
        "procedure_summary.csv",
    )


def create_utilisation_by_gender(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        COALESCE(p.gender, 'Unknown') AS gender,
        COUNT(e.encounter_id) AS encounter_count,
        COUNT(DISTINCT e.patient_id) AS unique_patients

    FROM read_parquet('{parquet_path("encounter")}') e

    LEFT JOIN read_parquet('{parquet_path("patient")}') p
        ON e.patient_id = p.patient_id

    GROUP BY
        COALESCE(p.gender, 'Unknown')

    ORDER BY encounter_count DESC
    """

    return query_to_csv(
        con,
        query,
        "utilisation_by_gender.csv",
    )


def create_utilisation_by_age_group(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    WITH patients AS (
        SELECT
            patient_id,

            CASE
                WHEN birth_date IS NULL THEN 'Unknown'

                WHEN DATE_DIFF(
                    'year',
                    CAST(birth_date AS DATE),
                    CURRENT_DATE
                ) < 18 THEN '0-17'

                WHEN DATE_DIFF(
                    'year',
                    CAST(birth_date AS DATE),
                    CURRENT_DATE
                ) < 30 THEN '18-29'

                WHEN DATE_DIFF(
                    'year',
                    CAST(birth_date AS DATE),
                    CURRENT_DATE
                ) < 45 THEN '30-44'

                WHEN DATE_DIFF(
                    'year',
                    CAST(birth_date AS DATE),
                    CURRENT_DATE
                ) < 65 THEN '45-64'

                ELSE '65+'
            END AS age_group

        FROM read_parquet('{parquet_path("patient")}')
    )

    SELECT
        p.age_group,
        COUNT(e.encounter_id) AS encounter_count,
        COUNT(DISTINCT e.patient_id) AS unique_patients

    FROM read_parquet('{parquet_path("encounter")}') e

    LEFT JOIN patients p
        ON e.patient_id = p.patient_id

    GROUP BY
        p.age_group

    ORDER BY
        CASE p.age_group
            WHEN '0-17' THEN 1
            WHEN '18-29' THEN 2
            WHEN '30-44' THEN 3
            WHEN '45-64' THEN 4
            WHEN '65+' THEN 5
            ELSE 6
        END
    """

    return query_to_csv(
        con,
        query,
        "utilisation_by_age_group.csv",
    )


def create_events_over_time(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    query = f"""
    SELECT
        DATE_TRUNC(
            'year',
            TRY_CAST(start_datetime AS TIMESTAMP)
        ) AS year,

        COUNT(*) AS encounter_count,
        COUNT(DISTINCT patient_id) AS unique_patients

    FROM read_parquet('{parquet_path("encounter")}')

    WHERE start_datetime IS NOT NULL

    GROUP BY
        year

    ORDER BY
        year
    """

    return query_to_csv(
        con,
        query,
        "encounters_over_time.csv",
    )


def create_resource_summary(
    con: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:

    resource_paths = {
        "Patient": "patient",
        "Encounter": "encounter",
        "Condition": "condition",
        "Observation": "observation",
        "Immunization": "immunization",
        "Procedure": "procedure",
        "MedicationRequest": "medicationrequest",
        "CarePlan": "careplan",
        "DiagnosticReport": "diagnosticreport",
        "AllergyIntolerance": "allergyintolerance",
    }

    rows = []

    for resource_name, directory in resource_paths.items():

        query = f"""
        SELECT COUNT(*) AS row_count
        FROM read_parquet('{parquet_path(directory)}')
        """

        count = con.execute(query).fetchone()[0]

        rows.append(
            {
                "resource_type": resource_name,
                "row_count": count,
            }
        )

    df = pd.DataFrame(rows)

    df = df.sort_values(
        "row_count",
        ascending=False,
    )

    output_path = SUMMARY_DIR / "resource_summary.csv"

    df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Wrote resource summary → {output_path}"
    )

    return df


# ---------------------------------------------------------------------------
# Visualisations
# ---------------------------------------------------------------------------

def save_bar_chart(
    df: pd.DataFrame,
    category: str,
    value: str,
    title: str,
    filename: str,
    top_n: int = 10,
) -> None:

    plot_df = (
        df.sort_values(
            value,
            ascending=False,
        )
        .head(top_n)
        .copy()
    )

    plot_df = plot_df.sort_values(
        value,
        ascending=True,
    )

    labels = (
        plot_df[category]
        .fillna("Unknown")
        .astype(str)
    )

    plt.figure(
        figsize=(10, 6)
    )

    plt.barh(
        labels,
        plot_df[value],
    )

    plt.title(title)
    plt.xlabel(
        value.replace(
            "_",
            " ",
        ).title()
    )
    plt.ylabel(
        category.replace(
            "_",
            " ",
        ).title()
    )

    plt.tight_layout()

    output_path = CHART_DIR / filename

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    print(
        f"Wrote chart → {output_path}"
    )


def save_age_group_chart(
    df: pd.DataFrame,
) -> None:

    order = [
        "0-17",
        "18-29",
        "30-44",
        "45-64",
        "65+",
        "Unknown",
    ]

    plot_df = (
        df.set_index("age_group")
        .reindex(order)
        .fillna(0)
    )

    plt.figure(
        figsize=(9, 6)
    )

    plt.bar(
        plot_df.index,
        plot_df["encounter_count"],
    )

    plt.title(
        "Healthcare Encounters by Age Group"
    )

    plt.xlabel(
        "Age Group"
    )

    plt.ylabel(
        "Number of Encounters"
    )

    plt.tight_layout()

    output_path = (
        CHART_DIR /
        "encounters_by_age_group.png"
    )

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    print(
        f"Wrote chart → {output_path}"
    )


def save_gender_chart(
    df: pd.DataFrame,
) -> None:

    plt.figure(
        figsize=(8, 5)
    )

    plt.bar(
        df["gender"].astype(str),
        df["encounter_count"],
    )

    plt.title(
        "Healthcare Encounters by Gender"
    )

    plt.xlabel(
        "Gender"
    )

    plt.ylabel(
        "Number of Encounters"
    )

    plt.xticks(
        rotation=30
    )

    plt.tight_layout()

    output_path = (
        CHART_DIR /
        "encounters_by_gender.png"
    )

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    print(
        f"Wrote chart → {output_path}"
    )


def save_time_chart(
    df: pd.DataFrame,
) -> None:

    plot_df = (
        df.dropna(
            subset=["year"]
        )
        .copy()
    )

    plot_df["year"] = pd.to_datetime(
        plot_df["year"]
    )

    plt.figure(
        figsize=(11, 6)
    )

    plt.plot(
        plot_df["year"],
        plot_df["encounter_count"],
        marker="o",
    )

    plt.title(
        "Healthcare Encounters Over Time"
    )

    plt.xlabel(
        "Year"
    )

    plt.ylabel(
        "Number of Encounters"
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.tight_layout()

    output_path = (
        CHART_DIR /
        "encounters_over_time.png"
    )

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    print(
        f"Wrote chart → {output_path}"
    )


# ---------------------------------------------------------------------------
# Written analysis summary
# ---------------------------------------------------------------------------

def write_analysis_summary(
    resource_summary: pd.DataFrame,
    condition_summary: pd.DataFrame,
    encounter_summary: pd.DataFrame,
    medication_summary: pd.DataFrame,
    procedure_summary: pd.DataFrame,
) -> None:

    lines = [
        "# Aggregation and Analysis Outputs",
        "",
        "Generated from the analytical Parquet layer.",
        "",
        "## Dataset summary",
        "",
        f"- Resource types analysed: "
        f"{len(resource_summary)}",

        f"- Total records represented: "
        f"{resource_summary['row_count'].sum():,}",

        "",
    ]

    if not condition_summary.empty:

        condition = condition_summary.iloc[0]

        lines += [
            "## Most frequently recorded condition",
            "",
            f"- Condition: "
            f"{condition['condition_display']}",

            f"- Code: "
            f"{condition['condition_code']}",

            f"- Records: "
            f"{condition['condition_count']:,}",

            f"- Unique patients: "
            f"{condition['unique_patients']:,}",

            "",
        ]

    if not medication_summary.empty:

        medication = medication_summary.iloc[0]

        lines += [
            "## Most frequently recorded medication",
            "",
            f"- Medication: "
            f"{medication['medication_display']}",

            f"- Code: "
            f"{medication['medication_code']}",

            f"- Records: "
            f"{medication['medication_count']:,}",

            f"- Unique patients: "
            f"{medication['unique_patients']:,}",

            "",
        ]

    if not procedure_summary.empty:

        procedure = procedure_summary.iloc[0]

        lines += [
            "## Most frequently recorded procedure",
            "",
            f"- Procedure: "
            f"{procedure['procedure_display']}",

            f"- Code: "
            f"{procedure['procedure_code']}",

            f"- Records: "
            f"{procedure['procedure_count']:,}",

            f"- Unique patients: "
            f"{procedure['unique_patients']:,}",

            "",
        ]

    if not encounter_summary.empty:

        encounter = encounter_summary.iloc[0]

        lines += [
            "## Most common encounter grouping",
            "",
            f"- Encounter type: "
            f"{encounter['encounter_type']}",

            f"- Class: "
            f"{encounter['class']}",

            f"- Status: "
            f"{encounter['status']}",

            f"- Encounters: "
            f"{encounter['encounter_count']:,}",

            f"- Unique patients: "
            f"{encounter['unique_patients']:,}",

            "",
        ]

    output_path = (
        SUMMARY_DIR /
        "analysis_summary.md"
    )

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(
        f"Wrote analysis summary → {output_path}"
    )


# ---------------------------------------------------------------------------
# Power BI export
# ---------------------------------------------------------------------------

def export_powerbi_files() -> None:
    """
    Copy the prepared analytical CSV outputs into a flat directory
    intended for direct import into Power BI.

    The Power BI folder deliberately contains CSVs only, so the next
    student does not need Python, DuckDB, Parquet, or the raw FHIR data
    to build the report.
    """

    files = [
        "patient_summary.csv",
        "condition_summary.csv",
        "condition_encounter_summary.csv",
        "encounter_summary.csv",
        "medication_summary.csv",
        "procedure_summary.csv",
        "utilisation_by_gender.csv",
        "utilisation_by_age_group.csv",
        "encounters_over_time.csv",
        "resource_summary.csv",
    ]

    print()
    print("=" * 60)
    print("POWER BI EXPORT")
    print("=" * 60)

    exported = 0

    for filename in files:

        if filename == "resource_summary.csv":
            source = SUMMARY_DIR / filename
        else:
            source = TABLE_DIR / filename

        destination = POWERBI_DIR / filename

        if not source.exists():
            print(
                f"WARNING: missing source → {source}"
            )
            continue

        destination.write_bytes(
            source.read_bytes()
        )

        print(
            f"Exported {filename}"
        )

        exported += 1

    print()
    print(
        f"Power BI files exported : {exported}/{len(files)}"
    )
    print(
        f"Power BI directory       : {POWERBI_DIR}"
    )


def write_powerbi_readme() -> None:
    """
    Create a short handoff document explaining how to use the Power BI
    datasets.
    """

    readme = """# Power BI Data

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
"""

    output_path = POWERBI_DIR / "README.md"

    output_path.write_text(
        readme,
        encoding="utf-8",
    )

    print(
        f"Wrote Power BI README → {output_path}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:

    print("=" * 60)
    print("FHIR ANALYTICAL AGGREGATION")
    print("=" * 60)

    ensure_directories()

    con = duckdb.connect()

    try:

        patient_summary = create_patient_summary(
            con
        )

        condition_summary = create_condition_summary(
            con
        )

        encounter_summary = create_encounter_summary(
            con
        )

        condition_encounter_summary = (
            create_condition_encounter_summary(
                con
            )
        )

        medication_summary = create_medication_summary(
            con
        )

        procedure_summary = create_procedure_summary(
            con
        )

        utilisation_gender = (
            create_utilisation_by_gender(
                con
            )
        )

        utilisation_age = (
            create_utilisation_by_age_group(
                con
            )
        )

        encounters_over_time = (
            create_events_over_time(
                con
            )
        )

        resource_summary = (
            create_resource_summary(
                con
            )
        )

        # ---------------------------------------------------------------
        # Charts
        # ---------------------------------------------------------------

        save_bar_chart(
            condition_summary,
            "condition_display",
            "condition_count",
            "Top Recorded Conditions",
            "top_conditions.png",
        )

        save_bar_chart(
            medication_summary,
            "medication_display",
            "medication_count",
            "Top Recorded Medications",
            "top_medications.png",
        )

        save_bar_chart(
            procedure_summary,
            "procedure_display",
            "procedure_count",
            "Top Recorded Procedures",
            "top_procedures.png",
        )

        save_bar_chart(
            resource_summary,
            "resource_type",
            "row_count",
            "FHIR Resource Volumes",
            "resource_volumes.png",
            top_n=len(resource_summary),
        )

        save_age_group_chart(
            utilisation_age
        )

        save_gender_chart(
            utilisation_gender
        )

        save_time_chart(
            encounters_over_time
        )

        # ---------------------------------------------------------------
        # Written summary
        # ---------------------------------------------------------------

        write_analysis_summary(
            resource_summary,
            condition_summary,
            encounter_summary,
            medication_summary,
            procedure_summary,
        )

        # ---------------------------------------------------------------
        # Power BI handoff
        # ---------------------------------------------------------------

        export_powerbi_files()

        write_powerbi_readme()

    finally:

        con.close()

    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)

    print(
        f"Analytics output : {OUTPUT_ROOT}"
    )

    print(
        f"Power BI output  : {POWERBI_DIR}"
    )


if __name__ == "__main__":
    main()


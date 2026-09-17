"""
Phase 3 - Analytical Parquet layer validation.

Validates the output of src/extraction/write_parquet.py against the
Phase 1 reconnaissance manifest:

  1. Row counts per table
  2. Schema consistency across Parquet part files
  3. Primary key uniqueness
  4. Column null rates
  5. Referential integrity (patient / encounter foreign keys)
  6. Temporal range sanity

Writes:
    docs/data_quality_report.md

Usage:
    python -m src.validation.validate_parquet
"""

from __future__ import annotations

import time
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROC_ROOT = Path("data/processed")
REPORT_PATH = Path("docs/data_quality_report.md")


# Row counts measured during Phase 1 reconnaissance.
EXPECTED_COUNTS = {
    "patient": 129_218,
    "encounter": 1_201_625,
    "condition": 469_866,
    "observation": 4_756_568,
    "immunization": 862_744,
    "procedure": 563_951,
    "medicationrequest": 334_869,
    "careplan": 238_667,
    "diagnosticreport": 304_845,
    "allergyintolerance": 51_107,
}


# Preferred primary-key columns.
PK_CANDIDATES = {
    "patient": ["patient_id"],
    "encounter": ["encounter_id"],
    "condition": ["condition_id"],
    "observation": ["observation_id"],
    "immunization": ["immunization_id"],
    "procedure": ["procedure_id"],
    "medicationrequest": ["medication_request_id"],
    "careplan": ["careplan_id", "care_plan_id"],
    "diagnosticreport": [
        "diagnostic_report_id",
        "report_id",
    ],
    "allergyintolerance": ["allergy_id"],
}


TEMPORAL_HINTS = (
    "date",
    "datetime",
    "period_start",
    "period_end",
    "_start",
    "_end",
    "issued",
)


FOREIGN_KEYS = (
    "patient_id",
    "encounter_id",
)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def discover_tables(
    root: Path,
) -> dict[str, list[Path]]:
    """
    Map table name -> sorted list of Parquet part files.
    """

    tables: dict[str, list[Path]] = {}

    if not root.exists():
        raise FileNotFoundError(
            f"Parquet root not found: {root}"
        )

    for directory in sorted(
        p for p in root.iterdir()
        if p.is_dir()
    ):
        files = sorted(
            directory.glob("*.parquet")
        )

        if files:
            name = (
                directory.name
                .lower()
                .replace("_", "")
            )

            tables[name] = files

    return tables


def resolve_column(
    schema: pa.Schema,
    candidates: list[str],
) -> str | None:
    """
    Return the first candidate column found in the schema.
    """

    for candidate in candidates:
        if candidate in schema.names:
            return candidate

    return None


# ---------------------------------------------------------------------------
# Arrow helpers
# ---------------------------------------------------------------------------

def safe_null_count(
    column: pa.ChunkedArray | pa.Array,
) -> int:
    """
    Safely count null values.

    Works for ordinary Arrow types as well as Arrow's `null` type.
    """

    if len(column) == 0:
        return 0

    result = pc.sum(
        pc.is_null(column)
    )

    if result is None:
        return 0

    value = result.as_py()

    return int(value or 0)


def safe_distinct_count(
    column: pa.Array,
) -> int:
    """
    Count distinct non-null values.

    Arrow does not provide a count_distinct kernel for the
    `null` data type, so that case is handled explicitly.
    """

    if len(column) == 0:
        return 0

    if pa.types.is_null(column.type):
        return 0

    non_null = pc.drop_null(column)

    if len(non_null) == 0:
        return 0

    return int(
        pc.count_distinct(
            non_null
        ).as_py()
    )


# ---------------------------------------------------------------------------
# Schema comparison helpers
# ---------------------------------------------------------------------------

def schema_signature(
    data_type: pa.DataType,
):
    """
    Return a logical schema representation.

    Struct field order is ignored intentionally.

    This is important for nested structures such as:

        dosage_instruction

    where different Parquet part files may contain the same logical
    fields in different physical orders.

    Field names and field types must still match.
    """

    if pa.types.is_struct(data_type):

        fields = []

        for field in data_type:

            fields.append(
                (
                    field.name,
                    schema_signature(
                        field.type
                    ),
                    field.nullable,
                )
            )

        return (
            "struct",
            tuple(
                sorted(
                    fields,
                    key=lambda x: x[0],
                )
            ),
        )

    if pa.types.is_list(data_type):

        return (
            "list",
            schema_signature(
                data_type.value_type
            ),
        )

    if pa.types.is_large_list(data_type):

        return (
            "large_list",
            schema_signature(
                data_type.value_type
            ),
        )

    if pa.types.is_fixed_size_list(
        data_type
    ):

        return (
            "fixed_size_list",
            data_type.list_size,
            schema_signature(
                data_type.value_type
            ),
        )

    if pa.types.is_map(data_type):

        return (
            "map",
            schema_signature(
                data_type.key_type
            ),
            schema_signature(
                data_type.item_type
            ),
        )

    return (
        "primitive",
        str(data_type),
    )


def logical_schema_signature(
    schema: pa.Schema,
):
    """
    Return a logical signature for an entire Arrow schema.

    Top-level column order is preserved because column ordering is
    useful information for the analytical layer.

    Nested struct field ordering is ignored.
    """

    return tuple(
        (
            field.name,
            schema_signature(
                field.type
            ),
            field.nullable,
        )
        for field in schema
    )


def format_type(
    data_type: pa.DataType,
) -> str:
    """
    Return a readable Arrow type.
    """

    return str(data_type)


def compare_nested_types(
    expected: pa.DataType,
    actual: pa.DataType,
    path: str,
) -> list[str]:
    """
    Recursively compare nested Arrow types.

    Struct field order is ignored.

    Returns human-readable differences.
    """

    differences: list[str] = []

    if (
        pa.types.is_struct(expected)
        and pa.types.is_struct(actual)
    ):

        expected_fields = {
            field.name: field
            for field in expected
        }

        actual_fields = {
            field.name: field
            for field in actual
        }

        expected_names = set(
            expected_fields
        )

        actual_names = set(
            actual_fields
        )

        for name in sorted(
            expected_names - actual_names
        ):
            differences.append(
                f"{path}.{name}: "
                f"missing from actual schema"
            )

        for name in sorted(
            actual_names - expected_names
        ):
            differences.append(
                f"{path}.{name}: "
                f"unexpected field in actual schema"
            )

        for name in sorted(
            expected_names & actual_names
        ):

            expected_field = (
                expected_fields[name]
            )

            actual_field = (
                actual_fields[name]
            )

            child_path = (
                f"{path}.{name}"
            )

            differences.extend(
                compare_nested_types(
                    expected_field.type,
                    actual_field.type,
                    child_path,
                )
            )

            if (
                expected_field.nullable
                != actual_field.nullable
            ):
                differences.append(
                    f"{child_path}: "
                    f"nullability differs "
                    f"(expected "
                    f"{expected_field.nullable}, "
                    f"actual "
                    f"{actual_field.nullable})"
                )

        return differences

    if (
        pa.types.is_list(expected)
        and pa.types.is_list(actual)
    ):

        return compare_nested_types(
            expected.value_type,
            actual.value_type,
            f"{path}[]",
        )

    if (
        pa.types.is_large_list(expected)
        and pa.types.is_large_list(actual)
    ):

        return compare_nested_types(
            expected.value_type,
            actual.value_type,
            f"{path}[]",
        )

    if (
        pa.types.is_fixed_size_list(expected)
        and pa.types.is_fixed_size_list(actual)
    ):

        if (
            expected.list_size
            != actual.list_size
        ):
            differences.append(
                f"{path}: fixed list size "
                f"differs "
                f"(expected "
                f"{expected.list_size}, "
                f"actual "
                f"{actual.list_size})"
            )

        differences.extend(
            compare_nested_types(
                expected.value_type,
                actual.value_type,
                f"{path}[]",
            )
        )

        return differences

    if (
        pa.types.is_map(expected)
        and pa.types.is_map(actual)
    ):

        differences.extend(
            compare_nested_types(
                expected.key_type,
                actual.key_type,
                f"{path}.<key>",
            )
        )

        differences.extend(
            compare_nested_types(
                expected.item_type,
                actual.item_type,
                f"{path}.<value>",
            )
        )

        return differences

    if not expected.equals(actual):

        differences.append(
            f"{path}: type differs "
            f"(expected "
            f"{format_type(expected)}, "
            f"actual "
            f"{format_type(actual)})"
        )

    return differences


def compare_schemas(
    expected: pa.Schema,
    actual: pa.Schema,
) -> list[str]:
    """
    Compare two Arrow schemas.

    Top-level column order is significant.

    Nested struct field order is NOT significant.
    """

    differences: list[str] = []

    expected_names = expected.names
    actual_names = actual.names

    if expected_names != actual_names:

        expected_set = set(
            expected_names
        )

        actual_set = set(
            actual_names
        )

        missing = sorted(
            expected_set - actual_set
        )

        unexpected = sorted(
            actual_set - expected_set
        )

        if missing:
            differences.append(
                "Missing columns: "
                + ", ".join(missing)
            )

        if unexpected:
            differences.append(
                "Unexpected columns: "
                + ", ".join(unexpected)
            )

        if (
            not missing
            and not unexpected
        ):
            differences.append(
                "Top-level column order differs"
            )

    expected_fields = {
        field.name: field
        for field in expected
    }

    actual_fields = {
        field.name: field
        for field in actual
    }

    for name in sorted(
        set(expected_fields)
        & set(actual_fields)
    ):

        differences.extend(
            compare_nested_types(
                expected_fields[name].type,
                actual_fields[name].type,
                name,
            )
        )

        if (
            expected_fields[name].nullable
            != actual_fields[name].nullable
        ):
            differences.append(
                f"{name}: nullability differs "
                f"(expected "
                f"{expected_fields[name].nullable}, "
                f"actual "
                f"{actual_fields[name].nullable})"
            )

    return differences


# ---------------------------------------------------------------------------
# Primary-key helpers
# ---------------------------------------------------------------------------

def calculate_primary_key_stats(
    pk_chunks: list[pa.Array],
) -> dict:
    """
    Calculate primary-key row, null and distinct counts.

    Handles Arrow's `null` data type safely.

    Null primary keys are not included in the distinct-count calculation.
    They are reported separately as missing/null primary keys.
    """

    if not pk_chunks:

        return {
            "pk_total": 0,
            "pk_non_null": 0,
            "pk_null": 0,
            "pk_distinct": 0,
            "pk_null_only": False,
        }

    combined = pa.concat_arrays(
        pk_chunks
    )

    total = len(combined)

    null_count = safe_null_count(
        combined
    )

    non_null_count = (
        total - null_count
    )

    distinct = safe_distinct_count(
        combined
    )

    return {
        "pk_total": total,
        "pk_non_null": non_null_count,
        "pk_null": null_count,
        "pk_distinct": distinct,
        "pk_null_only": pa.types.is_null(
            combined.type
        ),
    }


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def main() -> None:
    start = time.perf_counter()

    print("=" * 60)
    print("PARQUET ANALYTICAL LAYER - VALIDATION")
    print("=" * 60)

    tables = discover_tables(
        PROC_ROOT
    )

    print(
        f"Tables discovered : "
        f"{len(tables)}"
    )

    print(
        f"Files discovered  : "
        f"{sum(len(files) for files in tables.values()):,}"
    )

    print()

    results: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Checks:
    #
    # 1. Row counts
    # 2. Schema consistency
    # 3. Null rates
    # 4. Primary-key uniqueness
    # 5. Temporal ranges
    # ------------------------------------------------------------------

    for table_name, files in tables.items():

        print(
            f"Scanning {table_name:<24} "
            f"({len(files)} files)"
        )

        stats = {
            "rows": 0,
            "nulls": {},
            "totals": {},
            "date_min": {},
            "date_max": {},
            "schema_variants": [],
            "schema_differences": {},
            "pk_column": None,
            "schema_columns": [],
        }

        # First file establishes the reference schema.
        reference_schema = pq.read_schema(
            files[0]
        )

        pk_column = resolve_column(
            reference_schema,
            PK_CANDIDATES.get(
                table_name,
                [],
            ),
        )

        stats["pk_column"] = pk_column
        stats["schema_columns"] = (
            reference_schema.names
        )

        pk_chunks: list[pa.Array] = []

        for path in files:

            # Read schema separately so we can validate it before
            # reading the full data file.
            file_schema = pq.read_schema(
                path
            )

            # ----------------------------------------------------------
            # Schema consistency
            # ----------------------------------------------------------

            schema_differences = (
                compare_schemas(
                    reference_schema,
                    file_schema,
                )
            )

            if schema_differences:

                stats[
                    "schema_variants"
                ].append(
                    path.name
                )

                stats[
                    "schema_differences"
                ][path.name] = (
                    schema_differences
                )

            # ----------------------------------------------------------
            # Read table
            # ----------------------------------------------------------

            table = pq.read_table(
                path
            )

            # ----------------------------------------------------------
            # Row count
            # ----------------------------------------------------------

            stats["rows"] += (
                table.num_rows
            )

            # ----------------------------------------------------------
            # Null rates and temporal ranges
            # ----------------------------------------------------------

            for name in table.column_names:

                column = table.column(
                    name
                )

                null_count = (
                    safe_null_count(
                        column
                    )
                )

                stats["nulls"][name] = (
                    stats["nulls"].get(
                        name,
                        0,
                    )
                    + null_count
                )

                stats["totals"][name] = (
                    stats["totals"].get(
                        name,
                        0,
                    )
                    + len(column)
                )

                # ------------------------------------------------------
                # Temporal range detection
                # ------------------------------------------------------

                is_temporal = any(
                    hint in name.lower()
                    for hint in TEMPORAL_HINTS
                )

                if (
                    is_temporal
                    and (
                        pa.types.is_string(
                            column.type
                        )
                        or pa.types.is_large_string(
                            column.type
                        )
                    )
                ):

                    valid = pc.drop_null(
                        column
                    )

                    if len(valid):

                        try:

                            bounds = pc.min_max(
                                valid
                            )

                            lo = bounds[
                                "min"
                            ].as_py()

                            hi = bounds[
                                "max"
                            ].as_py()

                            current_lo = (
                                stats[
                                    "date_min"
                                ].get(name)
                            )

                            current_hi = (
                                stats[
                                    "date_max"
                                ].get(name)
                            )

                            if (
                                current_lo is None
                                or lo < current_lo
                            ):

                                stats[
                                    "date_min"
                                ][name] = lo

                            if (
                                current_hi is None
                                or hi > current_hi
                            ):

                                stats[
                                    "date_max"
                                ][name] = hi

                        except (
                            TypeError,
                            pa.ArrowException,
                        ):
                            # Ignore columns whose contents cannot
                            # safely be compared as temporal strings.
                            pass

            # ----------------------------------------------------------
            # Collect primary-key values
            # ----------------------------------------------------------

            if pk_column:

                if pk_column in table.column_names:

                    pk_column_data = table.column(
                        pk_column
                    )

                    pk_chunks.extend(
                        pk_column_data.chunks
                    )

        # --------------------------------------------------------------
        # Primary-key uniqueness
        # --------------------------------------------------------------

        if pk_column and pk_chunks:

            pk_stats = (
                calculate_primary_key_stats(
                    pk_chunks
                )
            )

            stats.update(
                pk_stats
            )

        results[
            table_name
        ] = stats

    # ------------------------------------------------------------------
    # Referential integrity
    # ------------------------------------------------------------------

    print()
    print("Building parent ID sets...")

    parent_sets: dict[str, set] = {}

    for table_name, parent_key in (
        ("patient", "patient_id"),
        ("encounter", "encounter_id"),
    ):

        if table_name not in tables:
            continue

        ids: set = set()

        for path in tables[
            table_name
        ]:

            schema = pq.read_schema(
                path
            )

            if parent_key not in schema.names:
                continue

            column = pq.read_table(
                path,
                columns=[parent_key],
            ).column(
                parent_key
            )

            ids.update(
                value
                for value in column.to_pylist()
                if value is not None
            )

        parent_sets[
            parent_key
        ] = ids

        print(
            f"  {parent_key:<15} "
            f"{len(ids):>12,} unique"
        )

    # ------------------------------------------------------------------
    # Foreign-key validation
    # ------------------------------------------------------------------

    print()
    print("Validating foreign keys...")

    fk_results = {}

    for table_name, files in tables.items():

        schema = pq.read_schema(
            files[0]
        )

        fk_columns = [
            column
            for column in FOREIGN_KEYS
            if column in schema.names
        ]

        # Patient and Encounter are parent tables.
        if (
            table_name in (
                "patient",
                "encounter",
            )
            or not fk_columns
        ):
            continue

        for fk_column in fk_columns:

            total = 0
            null_fk = 0
            orphan = 0

            parent = parent_sets.get(
                fk_column,
                set(),
            )

            for path in files:

                file_schema = pq.read_schema(
                    path
                )

                if (
                    fk_column
                    not in file_schema.names
                ):
                    continue

                column = pq.read_table(
                    path,
                    columns=[fk_column],
                ).column(
                    fk_column
                )

                values = (
                    column.to_pylist()
                )

                total += len(values)

                null_fk += sum(
                    value is None
                    for value in values
                )

                orphan += sum(
                    value is not None
                    and value not in parent
                    for value in values
                )

            fk_results[
                (
                    table_name,
                    fk_column,
                )
            ] = {
                "total": total,
                "null": null_fk,
                "orphan": orphan,
            }

    elapsed = (
        time.perf_counter()
        - start
    )

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------

    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    issues = []

    # ------------------------------------------------------------------
    # Table-level checks
    # ------------------------------------------------------------------

    for table_name, stats in results.items():

        expected = EXPECTED_COUNTS.get(
            table_name
        )

        actual = stats["rows"]

        if expected is None:

            match = "?"

        else:

            match = (
                "OK"
                if expected == actual
                else "FAIL"
            )

        print(
            f"{table_name:<24} "
            f"rows={actual:>12,}  "
            f"expected={match}"
        )

        # Row count
        if (
            expected is not None
            and expected != actual
        ):

            issues.append(
                f"Row count mismatch for "
                f"'{table_name}': "
                f"expected {expected:,}, "
                f"found {actual:,}"
            )

        # Schema drift
        if stats[
            "schema_variants"
        ]:

            issues.append(
                f"Schema drift in "
                f"'{table_name}' across "
                f"{len(stats['schema_variants'])} "
                f"part files"
            )

        # Primary key
        pk_total = stats.get(
            "pk_total"
        )

        pk_distinct = stats.get(
            "pk_distinct"
        )

        if (
            pk_total is not None
            and pk_distinct is not None
        ):

            duplicate_count = (
                stats["pk_non_null"]
                - pk_distinct
            )

            if duplicate_count > 0:

                issues.append(
                    f"Duplicate primary keys "
                    f"in '{table_name}' "
                    f"({pk_distinct:,} distinct "
                    f"of {stats['pk_non_null']:,} "
                    f"non-null keys)"
                )

    # ------------------------------------------------------------------
    # Foreign-key results
    # ------------------------------------------------------------------

    for (
        table_name,
        fk_column,
    ), result in sorted(
        fk_results.items()
    ):

        ok = (
            "OK"
            if result["orphan"] == 0
            else "FAIL"
        )

        print(
            f"{table_name}.{fk_column:<12} "
            f"orphans="
            f"{result['orphan']:>10,}  "
            f"nulls="
            f"{result['null']:>10,}  "
            f"{ok}"
        )

        if result["orphan"]:

            issues.append(
                f"{result['orphan']:,} "
                f"orphaned {fk_column} "
                f"in '{table_name}'"
            )

    # ------------------------------------------------------------------
    # Final console output
    # ------------------------------------------------------------------

    print()
    print(
        f"Issues found     : "
        f"{len(issues)}"
    )

    print(
        f"Processing time  : "
        f"{elapsed:.2f} seconds"
    )

    # ------------------------------------------------------------------
    # Write Markdown report
    # ------------------------------------------------------------------

    write_report(
        results,
        fk_results,
        issues,
        elapsed,
    )

    print()
    print(
        f"Report written to: "
        f"{REPORT_PATH}"
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def write_report(
    results: dict[str, dict],
    fk_results: dict,
    issues: list[str],
    elapsed: float,
) -> None:

    lines = [
        "# Data Quality Report",
        "",
        "Automated validation of the analytical "
        "Parquet layer (`data/processed/`) "
        "produced by the Phase 2 extraction pipeline.",
        "",
        f"- Validation runtime: {elapsed:.2f} seconds",
        f"- Issues found: {len(issues)}",
        "",
        "## 1. Row Counts vs Phase 1 Reconnaissance",
        "",
        "| Table | Rows | Expected | Status |",
        "|---|---:|---:|:-:|",
    ]

    # ------------------------------------------------------------------
    # Row counts
    # ------------------------------------------------------------------

    for name, stats in results.items():

        expected = EXPECTED_COUNTS.get(
            name
        )

        if expected is None:

            status = "UNKNOWN"
            expected_text = "-"

        elif expected == stats["rows"]:

            status = "MATCH"
            expected_text = f"{expected:,}"

        else:

            status = "MISMATCH"
            expected_text = f"{expected:,}"

        lines.append(
            f"| {name} | "
            f"{stats['rows']:,} | "
            f"{expected_text} | "
            f"{status} |"
        )

    # ------------------------------------------------------------------
    # Primary-key uniqueness
    # ------------------------------------------------------------------

    lines += [
        "",
        "## 2. Primary Key Uniqueness",
        "",
        "| Table | Key Column | Rows | "
        "Non-null | Nulls | Distinct | Status |",
        "|---|---|---:|---:|---:|---:|:-:|",
    ]

    for name, stats in results.items():

        pk_column = stats.get(
            "pk_column"
        )

        if pk_column is None:

            lines.append(
                f"| {name} | (none) | "
                f"- | - | - | - | N/A |"
            )

            continue

        pk_total = stats.get(
            "pk_total",
            0,
        )

        pk_non_null = stats.get(
            "pk_non_null",
            0,
        )

        pk_null = stats.get(
            "pk_null",
            0,
        )

        pk_distinct = stats.get(
            "pk_distinct",
            0,
        )

        duplicate_count = (
            pk_non_null
            - pk_distinct
        )

        if duplicate_count > 0:

            status = "DUPLICATES"

        elif pk_null > 0:

            status = "UNIQUE*"

        else:

            status = "UNIQUE"

        lines.append(
            f"| {name} | "
            f"{pk_column} | "
            f"{pk_total:,} | "
            f"{pk_non_null:,} | "
            f"{pk_null:,} | "
            f"{pk_distinct:,} | "
            f"{status} |"
        )

    lines += [
        "",
        "*`UNIQUE*` means the non-null primary-key "
        "values are unique, but one or more rows "
        "have a missing primary-key value.*",
        "",
        "## 3. Null Rates",
        "",
    ]

    # ------------------------------------------------------------------
    # Null rates
    # ------------------------------------------------------------------

    for name, stats in results.items():

        lines.append(
            f"### {name}"
        )

        lines += [
            "",
            "| Column | Nulls | Rows | Null % |",
            "|---|---:|---:|---:|",
        ]

        for col, nulls in stats[
            "nulls"
        ].items():

            total = stats[
                "totals"
            ][col]

            pct = (
                nulls / total * 100
                if total
                else 0.0
            )

            lines.append(
                f"| {col} | "
                f"{nulls:,} | "
                f"{total:,} | "
                f"{pct:.2f}% |"
            )

        lines.append("")

    # ------------------------------------------------------------------
    # Referential integrity
    # ------------------------------------------------------------------

    lines += [
        "## 4. Referential Integrity",
        "",
        "| Table.Column | References | "
        "Orphans | Nulls | Status |",
        "|---|---:|---:|---:|:-:|",
    ]

    for (
        table,
        fk,
    ), result in sorted(
        fk_results.items()
    ):

        status = (
            "OK"
            if result["orphan"] == 0
            else "BROKEN"
        )

        lines.append(
            f"| {table}.{fk} | "
            f"{result['total']:,} | "
            f"{result['orphan']:,} | "
            f"{result['null']:,} | "
            f"{status} |"
        )

    # ------------------------------------------------------------------
    # Temporal ranges
    # ------------------------------------------------------------------

    lines += [
        "",
        "## 5. Temporal Ranges",
        "",
    ]

    for name, stats in results.items():

        if not stats["date_min"]:
            continue

        lines.append(
            f"### {name}"
        )

        lines += [
            "",
            "| Column | Earliest | Latest |",
            "|---|---|---|",
        ]

        for col in stats[
            "date_min"
        ]:

            lines.append(
                f"| {col} | "
                f"{stats['date_min'][col]} | "
                f"{stats['date_max'][col]} |"
            )

        lines.append("")

    # ------------------------------------------------------------------
    # Schema consistency
    # ------------------------------------------------------------------

    lines += [
        "## 6. Schema Consistency",
        "",
    ]

    for name, stats in results.items():

        variants = stats[
            "schema_variants"
        ]

        if not variants:

            lines.append(
                f"- **{name}**: consistent"
            )

        else:

            lines.append(
                f"- **{name}**: "
                f"{len(variants)} part files "
                f"differ from the reference schema"
            )

            for variant in variants:

                lines.append(
                    f"  - `{variant}`"
                )

                differences = (
                    stats[
                        "schema_differences"
                    ].get(
                        variant,
                        [],
                    )
                )

                for difference in differences:

                    lines.append(
                        f"    - {difference}"
                    )

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    if issues:

        lines += [
            "",
            "## 7. Issues",
            "",
        ]

        lines.extend(
            f"- {issue}"
            for issue in issues
        )

    else:

        lines += [
            "",
            "## 7. Issues",
            "",
            "None. All checks passed.",
        ]

    # ------------------------------------------------------------------
    # Write report
    # ------------------------------------------------------------------

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()


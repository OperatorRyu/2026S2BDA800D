from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .extract_fhir import find_json_files, iter_resources
from .normalize import normalize_resource


DEFAULT_INPUT_DIR = Path("data/raw/fhir")
DEFAULT_OUTPUT_DIR = Path("data/processed")
DEFAULT_BATCH_SIZE = 10_000


def write_batch(
    records: list[dict],
    resource_type: str,
    output_dir: Path,
    batch_number: int,
) -> Path:
    """
    Write one batch of normalized records to a Parquet file.

    Files are partitioned by FHIR resource type so downstream analysis
    can load only the resource tables it needs.
    """

    if not records:
        raise ValueError("Cannot write an empty batch.")

    partition_dir = output_dir / resource_type.lower()
    partition_dir.mkdir(parents=True, exist_ok=True)

    output_path = (
        partition_dir
        / f"part-{batch_number:05d}.parquet"
    )

    table = pa.Table.from_pylist(records)

    pq.write_table(
        table,
        output_path,
        compression="snappy",
    )

    return output_path


def main() -> None:
    input_dir = DEFAULT_INPUT_DIR
    output_dir = DEFAULT_OUTPUT_DIR
    batch_size = DEFAULT_BATCH_SIZE

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FHIR → PARQUET EXTRACTION")
    print("=" * 60)
    print(f"Input directory  : {input_dir}")
    print(f"Output directory : {output_dir}")
    print(f"Batch size       : {batch_size}")
    print()

    start_time = time.perf_counter()

    file_count = 0
    resource_count = 0
    normalized_count = 0
    skipped_count = 0

    resource_counts: dict[str, int] = defaultdict(int)
    normalized_counts: dict[str, int] = defaultdict(int)
    skipped_counts: dict[str, int] = defaultdict(int)

    batches: dict[str, list[dict]] = defaultdict(list)
    batch_numbers: dict[str, int] = defaultdict(int)

    # Count input files first.
    for _ in find_json_files(input_dir):
        file_count += 1

    print(f"JSON files found : {file_count:,}")
    print()

    for item in iter_resources(input_dir):
        resource = item["resource"]

        resource_type = resource.get("resourceType")

        if not resource_type:
            skipped_count += 1
            skipped_counts["<missing resourceType>"] += 1
            continue

        resource_count += 1
        resource_counts[resource_type] += 1

        try:
            normalized = normalize_resource(resource)

        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            skipped_count += 1
            skipped_counts[resource_type] += 1

            print(
                f"WARNING: failed to normalize "
                f"{resource_type} "
                f"{resource.get('id', '<no id>')}: "
                f"{exc}"
            )

            continue

        if normalized is None:
            skipped_count += 1
            skipped_counts[resource_type] += 1
            continue

        normalized_count += 1
        normalized_counts[resource_type] += 1

        batches[resource_type].append(normalized)

        if len(batches[resource_type]) >= batch_size:
            batch_numbers[resource_type] += 1

            output_path = write_batch(
                batches[resource_type],
                resource_type,
                output_dir,
                batch_numbers[resource_type],
            )

            print(
                f"Wrote {resource_type:<22} "
                f"batch {batch_numbers[resource_type]:>4} "
                f"({batch_size:,} records) "
                f"→ {output_path}"
            )

            batches[resource_type].clear()

        if resource_count % 100_000 == 0:
            print(
                f"Processed {resource_count:,} resources..."
            )

    # Write remaining records for every resource type.
    for resource_type, records in batches.items():

        if not records:
            continue

        batch_numbers[resource_type] += 1

        output_path = write_batch(
            records,
            resource_type,
            output_dir,
            batch_numbers[resource_type],
        )

        print(
            f"Wrote {resource_type:<22} "
            f"batch {batch_numbers[resource_type]:>4} "
            f"({len(records):,} records) "
            f"→ {output_path}"
        )

    elapsed = time.perf_counter() - start_time

    print()
    print("=" * 60)
    print("EXTRACTION RESULTS")
    print("=" * 60)

    print(f"JSON files processed : {file_count:,}")
    print(f"Resources processed  : {resource_count:,}")
    print(f"Resources normalized : {normalized_count:,}")
    print(f"Resources skipped    : {skipped_count:,}")
    print(f"Processing time      : {elapsed:.2f} seconds")

    print()
    print("RESOURCE COUNTS")
    print("-" * 60)

    for resource_type, count in sorted(
        resource_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        normalized = normalized_counts[resource_type]
        skipped = skipped_counts[resource_type]

        print(
            f"{resource_type:<24} "
            f"{count:>10,} "
            f"normalized={normalized:>10,} "
            f"skipped={skipped:>8,}"
        )

    print()
    print("PARQUET OUTPUT")
    print("-" * 60)

    parquet_files = list(
        output_dir.rglob("*.parquet")
    )

    total_bytes = sum(
        path.stat().st_size
        for path in parquet_files
    )

    print(f"Parquet files : {len(parquet_files):,}")
    print(
        f"Parquet size  : "
        f"{total_bytes / (1024 ** 3):.2f} GiB"
    )

    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

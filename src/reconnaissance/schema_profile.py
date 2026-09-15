from collections import Counter, defaultdict
from pathlib import Path
import json
import time


DATA_DIR = Path("data/raw/fhir")


def profile_schemas(data_dir: Path) -> None:
    field_counts = defaultdict(Counter)
    resource_counts = Counter()
    malformed_files = 0
    total_resources = 0

    start = time.perf_counter()

    print("=" * 60)
    print("FHIR SCHEMA RECONNAISSANCE")
    print("=" * 60)

    for index, file_path in enumerate(
        data_dir.rglob("*.json"),
        start=1
    ):
        try:
            with file_path.open("r", encoding="utf-8") as file:
                bundle = json.load(file)

            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})

                resource_type = resource.get(
                    "resourceType",
                    "UNKNOWN"
                )

                resource_counts[resource_type] += 1
                total_resources += 1

                for field in resource:
                    field_counts[resource_type][field] += 1

        except (json.JSONDecodeError, OSError):
            malformed_files += 1

        if index % 10000 == 0:
            print(f"Processed {index:,} files...")

    elapsed = time.perf_counter() - start

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"Resources processed : {total_resources:,}")
    print(f"Malformed files     : {malformed_files:,}")
    print(f"Processing time     : {elapsed:.2f} seconds")

    print("\n" + "=" * 60)
    print("RESOURCE SCHEMAS")
    print("=" * 60)

    for resource_type, count in resource_counts.most_common():

        print(f"\n{resource_type}")
        print("-" * 60)
        print(f"Records: {count:,}")

        for field, field_count in field_counts[
            resource_type
        ].most_common():

            percentage = (field_count / count) * 100

            print(
                f"  {field:<30}"
                f"{field_count:>10,} "
                f"({percentage:6.2f}%)"
            )


if __name__ == "__main__":
    profile_schemas(DATA_DIR)


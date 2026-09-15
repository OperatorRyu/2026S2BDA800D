from collections import Counter
from pathlib import Path
import json


DATA_DIR = Path("data/raw/fhir")


def inspect_dataset(data_dir: Path) -> None:
    json_files = list(data_dir.rglob("*.json"))

    print("=" * 60)
    print("SYNTHETIC HEALTHCARE DATASET — RECONNAISSANCE")
    print("=" * 60)

    print(f"Data directory : {data_dir}")
    print(f"JSON files     : {len(json_files):,}")

    resource_counts = Counter()
    bundle_types = Counter()
    total_resources = 0

    print("\nScanning FHIR bundles...")

    for index, file_path in enumerate(json_files, start=1):

        try:
            with file_path.open("r", encoding="utf-8") as file:
                bundle = json.load(file)

            bundle_type = bundle.get("type", "UNKNOWN")
            bundle_types[bundle_type] += 1

            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})

                resource_type = resource.get(
                    "resourceType",
                    "UNKNOWN"
                )

                resource_counts[resource_type] += 1
                total_resources += 1

        except (json.JSONDecodeError, OSError) as exc:
            print(f"\nERROR: {file_path}")
            print(f"       {exc}")

        if index % 10000 == 0:
            print(f"  Processed {index:,} files...")

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"FHIR bundles    : {len(json_files):,}")
    print(f"FHIR resources  : {total_resources:,}")

    print("\nBundle types:")
    for bundle_type, count in bundle_types.most_common():
        print(f"  {bundle_type:<25} {count:>10,}")

    print("\nResource types:")
    for resource_type, count in resource_counts.most_common():
        print(f"  {resource_type:<25} {count:>10,}")


if __name__ == "__main__":
    inspect_dataset(DATA_DIR)


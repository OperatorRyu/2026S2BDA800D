import json
from collections import Counter
from pathlib import Path
from time import perf_counter


DATA_DIR = Path("data/raw/fhir")
PROGRESS_INTERVAL = 10_000


def main() -> None:
    print("=" * 60)
    print("FHIR RESOURCE COUNT RECONNAISSANCE")
    print("=" * 60)

    files = list(DATA_DIR.rglob("*.json"))

    if not files:
        raise FileNotFoundError(
            f"No JSON files found under {DATA_DIR}"
        )

    counts: Counter[str] = Counter()
    malformed = 0
    files_processed = 0
    resources_processed = 0

    start = perf_counter()

    for path in files:
        files_processed += 1

        try:
            with path.open("r", encoding="utf-8") as f:
                bundle = json.load(f)
        except (json.JSONDecodeError, OSError):
            malformed += 1
            continue

        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")

            if resource_type:
                counts[resource_type] += 1
                resources_processed += 1

        if files_processed % PROGRESS_INTERVAL == 0:
            print(f"Processed {files_processed:,} files...")

    elapsed = perf_counter() - start

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"JSON files processed : {files_processed:,}")
    print(f"Resources processed  : {resources_processed:,}")
    print(f"Malformed files      : {malformed:,}")
    print(f"Processing time      : {elapsed:.2f} seconds")

    print()
    print("RESOURCE TYPE COUNTS")
    print("-" * 60)

    for resource_type, count in counts.most_common():
        percentage = count / resources_processed * 100
        print(
            f"{resource_type:<25}"
            f"{count:>12,}"
            f" ({percentage:>6.2f}%)"
        )

    print("-" * 60)
    print(f"{'TOTAL':<25}{sum(counts.values()):>12,}")

    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

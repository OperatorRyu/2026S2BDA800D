from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


DEFAULT_INPUT_DIR = Path("data/raw/fhir")


def find_json_files(input_dir: Path) -> Iterator[Path]:
    """Yield all JSON files beneath the FHIR input directory."""
    yield from input_dir.rglob("*.json")


def load_bundle(path: Path) -> dict:
    """Load a single FHIR bundle from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_resources(input_dir: Path = DEFAULT_INPUT_DIR) -> Iterator[dict]:
    """
    Stream individual FHIR resources from all bundles.

    Each yielded dictionary contains:
        source_file
        resource
    """
    for path in find_json_files(input_dir):
        bundle = load_bundle(path)

        for entry in bundle.get("entry", []):
            resource = entry.get("resource")

            if resource is None:
                continue

            yield {
                "source_file": str(path),
                "resource": resource,
            }


def main() -> None:
    resource_count = 0
    file_count = 0

    for path in find_json_files(DEFAULT_INPUT_DIR):
        file_count += 1

    for item in iter_resources(DEFAULT_INPUT_DIR):
        resource_count += 1

        if resource_count <= 5:
            resource = item["resource"]
            print(
                f"{resource.get('resourceType'):20s} "
                f"{resource.get('id', '<no id>')}"
            )

    print()
    print("=" * 60)
    print("FHIR EXTRACTION TEST")
    print("=" * 60)
    print(f"JSON files : {file_count:,}")
    print(f"Resources  : {resource_count:,}")


if __name__ == "__main__":
    main()


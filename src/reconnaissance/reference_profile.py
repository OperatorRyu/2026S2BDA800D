from collections import Counter, defaultdict
from pathlib import Path
import json
import time


DATA_DIR = Path("data/raw/fhir")

RESOURCE_TYPES = {
    "Patient",
    "Encounter",
    "Observation",
    "Condition",
    "MedicationRequest",
    "Procedure",
    "DiagnosticReport",
    "CarePlan",
    "Immunization",
    "AllergyIntolerance",
}

REFERENCE_FIELDS = {
    "Encounter": ["patient"],
    "Observation": ["subject", "encounter"],
    "Condition": ["subject", "context"],
    "MedicationRequest": ["patient", "context", "reasonReference"],
    "Procedure": ["subject", "encounter", "reasonReference"],
    "DiagnosticReport": ["subject", "encounter", "performer", "result"],
    "CarePlan": ["subject", "context", "addresses"],
    "Immunization": ["patient", "encounter"],
    "AllergyIntolerance": ["patient"],
}


def extract_reference(value):
    """Extract FHIR reference strings from common reference structures."""

    references = []

    if isinstance(value, dict):
        if "reference" in value:
            references.append(value["reference"])

        for nested_value in value.values():
            if isinstance(nested_value, (dict, list)):
                references.extend(extract_reference(nested_value))

    elif isinstance(value, list):
        for item in value:
            references.extend(extract_reference(item))

    return references


def profile_references(data_dir: Path) -> None:
    reference_counts = defaultdict(Counter)
    resource_counts = Counter()
    examples = defaultdict(list)

    malformed_files = 0
    total_resources = 0

    start = time.perf_counter()

    print("=" * 60)
    print("FHIR REFERENCE RECONNAISSANCE")
    print("=" * 60)

    for index, file_path in enumerate(
        data_dir.rglob("*.json"),
        start=1,
    ):
        try:
            with file_path.open("r", encoding="utf-8") as file:
                bundle = json.load(file)

            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})

                resource_type = resource.get(
                    "resourceType",
                    "UNKNOWN",
                )

                if resource_type not in RESOURCE_TYPES:
                    continue

                resource_counts[resource_type] += 1
                total_resources += 1

                fields = REFERENCE_FIELDS.get(resource_type, [])

                for field in fields:
                    if field not in resource:
                        continue

                    references = extract_reference(resource[field])

                    for reference in references:
                        reference_counts[resource_type][field] += 1

                        if (
                            len(examples[(resource_type, field)])
                            < 3
                        ):
                            examples[
                                (resource_type, field)
                            ].append(reference)

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
    print("REFERENCE FIELDS")
    print("=" * 60)

    for resource_type in resource_counts:

        print(f"\n{resource_type}")
        print("-" * 60)

        for field in REFERENCE_FIELDS.get(resource_type, []):

            count = reference_counts[resource_type][field]

            print(f"  {field:<25} {count:>10,}")

            for example in examples[(resource_type, field)]:
                print(f"      example: {example}")


if __name__ == "__main__":
    profile_references(DATA_DIR)


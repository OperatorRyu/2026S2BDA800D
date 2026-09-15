from collections import Counter, defaultdict
from pathlib import Path
import json
import time


DATA_DIR = Path("data/raw/fhir")


# Fields whose values may contain references to other FHIR resources.
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


def extract_references(value):
    """
    Recursively extract FHIR reference strings.

    Handles:
      {"reference": "urn:uuid:..."}
      lists of reference objects
      nested dictionaries/lists
    """

    references = []

    if isinstance(value, dict):

        if "reference" in value:
            reference = value["reference"]

            if isinstance(reference, str):
                references.append(reference)

        for nested_value in value.values():

            if isinstance(nested_value, (dict, list)):
                references.extend(
                    extract_references(nested_value)
                )

    elif isinstance(value, list):

        for item in value:
            references.extend(
                extract_references(item)
            )

    return references


def scan_resource_ids(data_dir):
    """
    First pass:
    Build an index of every resource ID in the dataset.
    """

    resource_ids = defaultdict(set)

    malformed_files = 0
    total_resources = 0

    print("=" * 60)
    print("PASS 1 — BUILDING RESOURCE ID INDEX")
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

                resource_type = resource.get("resourceType")
                resource_id = resource.get("id")

                if resource_type and resource_id:

                    resource_ids[resource_type].add(
                        resource_id
                    )

                    total_resources += 1

        except (json.JSONDecodeError, OSError):
            malformed_files += 1

        if index % 10000 == 0:
            print(f"Processed {index:,} files...")

    print("\nID INDEX")
    print("-" * 60)

    for resource_type in sorted(resource_ids):

        print(
            f"{resource_type:<25}"
            f"{len(resource_ids[resource_type]):>12,}"
        )

    print(f"\nResources indexed : {total_resources:,}")
    print(f"Malformed files   : {malformed_files:,}")

    return resource_ids


def resolve_reference(reference, resource_ids):
    """
    Determine whether a FHIR reference points to a known resource.

    Expected local references look like:

        urn:uuid:<resource-id>
    """

    if not isinstance(reference, str):
        return None, None

    if reference.startswith("urn:uuid:"):

        resource_id = reference.removeprefix("urn:uuid:")

        # Search all resource types because a UUID alone
        # does not tell us which FHIR resource type it targets.
        matching_types = [
            resource_type
            for resource_type, ids
            in resource_ids.items()
            if resource_id in ids
        ]

        if matching_types:
            return resource_id, matching_types

        return resource_id, []

    return None, None


def scan_references(data_dir, resource_ids):
    """
    Second pass:
    Validate references against the resource ID index.
    """

    statistics = defaultdict(
        lambda: {
            "total": 0,
            "valid": 0,
            "broken": 0,
            "external": 0,
        }
    )

    broken_examples = defaultdict(list)
    target_types = defaultdict(Counter)

    malformed_files = 0

    print("\n" + "=" * 60)
    print("PASS 2 — VALIDATING REFERENCES")
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

                resource_type = resource.get("resourceType")

                if resource_type not in REFERENCE_FIELDS:
                    continue

                for field in REFERENCE_FIELDS[resource_type]:

                    if field not in resource:
                        continue

                    references = extract_references(
                        resource[field]
                    )

                    for reference in references:

                        key = (
                            resource_type,
                            field,
                        )

                        statistics[key]["total"] += 1

                        resource_id, matches = resolve_reference(
                            reference,
                            resource_ids,
                        )

                        if resource_id is None:

                            statistics[key]["external"] += 1

                            continue

                        if matches:

                            statistics[key]["valid"] += 1

                            for target_type in matches:
                                target_types[key][
                                    target_type
                                ] += 1

                        else:

                            statistics[key]["broken"] += 1

                            if len(
                                broken_examples[key]
                            ) < 5:

                                broken_examples[key].append(
                                    reference
                                )

        except (json.JSONDecodeError, OSError):
            malformed_files += 1

        if index % 10000 == 0:
            print(f"Processed {index:,} files...")

    return (
        statistics,
        target_types,
        broken_examples,
        malformed_files,
    )


def print_results(
    statistics,
    target_types,
    broken_examples,
):
    print("\n" + "=" * 60)
    print("REFERENCE INTEGRITY RESULTS")
    print("=" * 60)

    for resource_type, field in sorted(statistics):

        stats = statistics[
            (resource_type, field)
        ]

        total = stats["total"]
        valid = stats["valid"]
        broken = stats["broken"]
        external = stats["external"]

        if total:
            valid_pct = valid / total * 100
            broken_pct = broken / total * 100
        else:
            valid_pct = 0
            broken_pct = 0

        print(
            f"\n{resource_type}.{field}"
        )
        print("-" * 60)

        print(f"References : {total:,}")
        print(
            f"Valid      : {valid:,}"
            f" ({valid_pct:6.2f}%)"
        )
        print(
            f"Broken     : {broken:,}"
            f" ({broken_pct:6.2f}%)"
        )
        print(f"External   : {external:,}")

        if target_types[
            (resource_type, field)
        ]:

            print("Target resource types:")

            for target_type, count in (
                target_types[
                    (resource_type, field)
                ].most_common()
            ):

                print(
                    f"  {target_type:<25}"
                    f"{count:>12,}"
                )

        if broken_examples[
            (resource_type, field)
        ]:

            print("Broken reference examples:")

            for reference in broken_examples[
                (resource_type, field)
            ]:

                print(f"  {reference}")


def main():

    start = time.perf_counter()

    print("=" * 60)
    print("FHIR REFERENCE INTEGRITY ANALYSIS")
    print("=" * 60)

    resource_ids = scan_resource_ids(
        DATA_DIR
    )

    (
        statistics,
        target_types,
        broken_examples,
        malformed_files,
    ) = scan_references(
        DATA_DIR,
        resource_ids,
    )

    print_results(
        statistics,
        target_types,
        broken_examples,
    )

    elapsed = time.perf_counter() - start

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)

    print(
        f"Total processing time : "
        f"{elapsed:.2f} seconds"
    )

    print(
        f"Malformed files       : "
        f"{malformed_files:,}"
    )


if __name__ == "__main__":
    main()


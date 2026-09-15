from __future__ import annotations

from datetime import datetime
from typing import Any


def reference_id(value: Any) -> str | None:
    """Extract the UUID/resource ID from a FHIR reference."""
    if not isinstance(value, dict):
        return None

    reference = value.get("reference")

    if not reference:
        return None

    # Handles references such as:
    # urn:uuid:6bb7cb36-...
    # Patient/6bb7cb36-...
    return reference.split("/")[-1].removeprefix("urn:uuid:")


def coding_value(value: Any) -> tuple[str | None, str | None]:
    """
    Extract code and display text from a FHIR CodeableConcept.
    """
    if not isinstance(value, dict):
        return None, None

    coding = value.get("coding", [])

    if not coding:
        return None, value.get("text")

    first = coding[0]

    return (
        first.get("code"),
        first.get("display") or value.get("text"),
    )


def parse_datetime(value: Any) -> str | None:
    """Return a normalized ISO datetime/date string."""
    if not value:
        return None

    return str(value)


def normalize_patient(resource: dict) -> dict:
    race = None
    ethnicity = None
    birth_city = None
    birth_state = None

    for extension in resource.get("extension", []):
        url = extension.get("url", "")

        if url.endswith("us-core-race"):
            concept = extension.get("valueCodeableConcept", {})
            _, race = coding_value(concept)

        elif url.endswith("us-core-ethnicity"):
            concept = extension.get("valueCodeableConcept", {})
            _, ethnicity = coding_value(concept)

        elif url.endswith("placeOfBirth"):
            address = extension.get("valueAddress", {})
            birth_city = address.get("city")
            birth_state = address.get("state")

    marital_code, marital_display = coding_value(
        resource.get("maritalStatus")
    )

    return {
        "patient_id": resource.get("id"),
        "gender": resource.get("gender"),
        "birth_date": resource.get("birthDate"),
        "marital_status": marital_display or marital_code,
        "race": race,
        "ethnicity": ethnicity,
        "birth_city": birth_city,
        "birth_state": birth_state,
        "deceased_date": resource.get("deceasedDateTime"),
    }


def normalize_encounter(resource: dict) -> dict:
    encounter_code, encounter_display = coding_value(
        resource.get("type")
    )

    encounter_class = resource.get("class", {})

    return {
        "encounter_id": resource.get("id"),
        "patient_id": reference_id(resource.get("patient")),
        "status": resource.get("status"),
        "encounter_type": encounter_display or encounter_code,
        "class": encounter_class.get("code"),
        "start_datetime": (
            resource.get("period", {}).get("start")
        ),
        "end_datetime": (
            resource.get("period", {}).get("end")
        ),
        "reason_code": (
            coding_value(resource.get("reason", [{}])[0].get("valueCodeableConcept"))
            if resource.get("reason")
            else (None, None)
        )[0],
    }


def normalize_condition(resource: dict) -> dict:
    code, display = coding_value(resource.get("code"))

    return {
        "condition_id": resource.get("id"),
        "patient_id": reference_id(resource.get("subject")),
        "encounter_id": reference_id(resource.get("context")),
        "condition_code": code,
        "condition_display": display,
        "clinical_status": (
            coding_value(resource.get("clinicalStatus"))[1]
            or coding_value(resource.get("clinicalStatus"))[0]
        ),
        "verification_status": (
            coding_value(resource.get("verificationStatus"))[1]
            or coding_value(resource.get("verificationStatus"))[0]
        ),
        "onset_datetime": resource.get("onsetDateTime"),
        "abatement_datetime": resource.get("abatementDateTime"),
    }


def normalize_observation(resource: dict) -> dict:
    code, display = coding_value(resource.get("code"))

    value_numeric = None
    value_unit = None
    value_code = None
    value_text = None

    quantity = resource.get("valueQuantity")

    if quantity:
        value_numeric = quantity.get("value")
        value_unit = quantity.get("unit")

    concept = resource.get("valueCodeableConcept")

    if concept:
        value_code, value_text = coding_value(concept)

    return {
        "observation_id": resource.get("id"),
        "patient_id": reference_id(resource.get("subject")),
        "encounter_id": reference_id(resource.get("encounter")),
        "status": resource.get("status"),
        "code": code,
        "display": display,
        "effective_datetime": resource.get("effectiveDateTime"),
        "value_numeric": value_numeric,
        "value_unit": value_unit,
        "value_code": value_code,
        "value_text": value_text,
        "has_components": bool(resource.get("component")),
    }


def normalize_immunization(resource: dict) -> dict:
    code, display = coding_value(resource.get("vaccineCode"))

    return {
        "immunization_id": resource.get("id"),
        "patient_id": reference_id(resource.get("patient")),
        "encounter_id": reference_id(resource.get("encounter")),
        "vaccine_code": code,
        "vaccine_display": display,
        "date": resource.get("date"),
        "status": resource.get("status"),
        "primary_source": resource.get("primarySource"),
    }


def normalize_procedure(resource: dict) -> dict:
    code, display = coding_value(resource.get("code"))

    performed_start = None
    performed_end = None

    if resource.get("performedDateTime"):
        performed_start = resource["performedDateTime"]

    elif resource.get("performedPeriod"):
        period = resource["performedPeriod"]
        performed_start = period.get("start")
        performed_end = period.get("end")

    reason_condition_id = None

    reasons = resource.get("reasonReference", [])

    if reasons:
        reason_condition_id = reference_id(reasons[0])

    return {
        "procedure_id": resource.get("id"),
        "patient_id": reference_id(resource.get("subject")),
        "encounter_id": reference_id(resource.get("encounter")),
        "procedure_code": code,
        "procedure_display": display,
        "status": resource.get("status"),
        "performed_start": performed_start,
        "performed_end": performed_end,
        "reason_condition_id": reason_condition_id,
    }


def normalize_medication_request(resource: dict) -> dict:
    code, display = coding_value(
        resource.get("medicationCodeableConcept")
    )

    reason_condition_id = None

    reasons = resource.get("reasonReference", [])

    if reasons:
        reason_condition_id = reference_id(reasons[0])

    return {
        "medication_request_id": resource.get("id"),
        "patient_id": reference_id(resource.get("patient")),
        "encounter_id": reference_id(resource.get("context")),
        "medication_code": code,
        "medication_display": display,
        "status": resource.get("status"),
        "stage": resource.get("stage"),
        "date_written": resource.get("dateWritten"),
        "reason_condition_id": reason_condition_id,
        "dosage_instruction": resource.get("dosageInstruction"),
    }


def normalize_careplan(resource: dict) -> dict:
    category_code, category_display = coding_value(
        resource.get("category")
    )

    condition_id = None

    addresses = resource.get("addresses", [])

    if addresses:
        condition_id = reference_id(addresses[0])

    period = resource.get("period", {})

    return {
        "careplan_id": resource.get("id"),
        "patient_id": reference_id(resource.get("subject")),
        "encounter_id": reference_id(resource.get("context")),
        "status": resource.get("status"),
        "category": category_display or category_code,
        "period_start": period.get("start"),
        "period_end": period.get("end"),
        "condition_id": condition_id,
    }


def normalize_allergy(resource: dict) -> dict:
    code, display = coding_value(resource.get("code"))

    return {
        "allergy_id": resource.get("id"),
        "patient_id": reference_id(resource.get("patient")),
        "clinical_status": (
            coding_value(resource.get("clinicalStatus"))[1]
            or coding_value(resource.get("clinicalStatus"))[0]
        ),
        "allergy_type": resource.get("type"),
        "category": resource.get("category", [None])[0],
        "criticality": resource.get("criticality"),
        "code": code,
        "display": display,
        "asserted_date": resource.get("assertedDate"),
    }


def normalize_resource(resource: dict) -> dict | None:
    """Dispatch a FHIR resource to its resource-specific normalizer."""

    resource_type = resource.get("resourceType")

    normalizers = {
        "Patient": normalize_patient,
        "Encounter": normalize_encounter,
        "Condition": normalize_condition,
        "Observation": normalize_observation,
        "Immunization": normalize_immunization,
        "Procedure": normalize_procedure,
        "MedicationRequest": normalize_medication_request,
        "CarePlan": normalize_careplan,
        "AllergyIntolerance": normalize_allergy,
    }

    normalizer = normalizers.get(resource_type)

    if normalizer is None:
        return None

    return normalizer(resource)


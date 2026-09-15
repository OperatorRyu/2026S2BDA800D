from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def reference_id(value: Any) -> str | None:
    """Extract the resource ID from a FHIR Reference."""
    if not isinstance(value, dict):
        return None

    reference = value.get("reference")

    if not isinstance(reference, str) or not reference:
        return None

    if reference.startswith("urn:uuid:"):
        return reference.removeprefix("urn:uuid:")

    return reference.split("/")[-1]


def coding_value(value: Any) -> tuple[str | None, str | None]:
    """
    Extract code and display/text from a FHIR CodeableConcept.

    Supports:
        {"coding": [{"code": "...", "display": "..."}]}

    and:
        {"text": "..."}
    """
    if not isinstance(value, dict):
        return None, None

    coding = value.get("coding")

    if isinstance(coding, list) and coding:
        first = coding[0]

        if isinstance(first, dict):
            return (
                first.get("code"),
                first.get("display") or value.get("text"),
            )

    return None, value.get("text")


def first_reference(value: Any) -> str | None:
    """Extract the first reference from either a reference or list."""
    if isinstance(value, dict):
        return reference_id(value)

    if isinstance(value, list) and value:
        return reference_id(value[0])

    return None


def first_codeable_concept(value: Any) -> Any:
    """
    Return the first CodeableConcept from either a single object or list.
    """
    if isinstance(value, dict):
        return value

    if isinstance(value, list) and value:
        return value[0]

    return None


def period_value(resource: dict, field: str) -> str | None:
    """Safely extract a value from a FHIR Period."""
    period = resource.get(field)

    if not isinstance(period, dict):
        return None

    value = period.get("start")

    if value is None and field == "period":
        value = period.get("end")

    return value


# ---------------------------------------------------------------------------
# Patient
# ---------------------------------------------------------------------------

def normalize_patient(resource: dict) -> dict:
    race = None
    ethnicity = None
    birth_city = None
    birth_state = None

    extensions = resource.get("extension", [])

    if isinstance(extensions, list):
        for extension in extensions:
            if not isinstance(extension, dict):
                continue

            url = extension.get("url", "")

            if url.endswith("us-core-race"):
                concept = extension.get(
                    "valueCodeableConcept",
                    {},
                )

                _, race = coding_value(concept)

            elif url.endswith("us-core-ethnicity"):
                concept = extension.get(
                    "valueCodeableConcept",
                    {},
                )

                _, ethnicity = coding_value(concept)

            elif url.endswith("placeOfBirth"):
                address = extension.get(
                    "valueAddress",
                    {},
                )

                if isinstance(address, dict):
                    birth_city = address.get("city")
                    birth_state = address.get("state")

    family_name = None
    given_name = None

    names = resource.get("name")

    if isinstance(names, list) and names:
        name = names[0]

        if isinstance(name, dict):
            family_name = name.get("family")

            given = name.get("given")

            if isinstance(given, list) and given:
                given_name = given[0]

    marital_code, marital_display = coding_value(
        resource.get("maritalStatus")
    )

    return {
        "patient_id": resource.get("id"),
        "gender": resource.get("gender"),
        "birth_date": resource.get("birthDate"),
        "family_name": family_name,
        "given_name": given_name,
        "marital_status": marital_display or marital_code,
        "race": race,
        "ethnicity": ethnicity,
        "birth_city": birth_city,
        "birth_state": birth_state,
        "deceased_date": resource.get("deceasedDateTime"),
    }


# ---------------------------------------------------------------------------
# Encounter
# ---------------------------------------------------------------------------

def normalize_encounter(resource: dict) -> dict:
    encounter_code, encounter_display = coding_value(
        resource.get("type")
    )

    encounter_class = resource.get("class")

    class_code = None

    if isinstance(encounter_class, dict):
        class_code = encounter_class.get("code")

    elif isinstance(encounter_class, list) and encounter_class:
        first_class = encounter_class[0]

        if isinstance(first_class, dict):
            class_code = first_class.get("code")

    reason = resource.get("reason")

    reason_code = None

    if isinstance(reason, dict):
        concept = reason.get("valueCodeableConcept")

        if concept is None:
            concept = reason.get("code")

        reason_code, _ = coding_value(concept)

    elif isinstance(reason, list) and reason:
        first_reason = reason[0]

        if isinstance(first_reason, dict):
            concept = first_reason.get(
                "valueCodeableConcept"
            )

            if concept is None:
                concept = first_reason.get("code")

            reason_code, _ = coding_value(concept)

    period = resource.get("period")

    start_datetime = None
    end_datetime = None

    if isinstance(period, dict):
        start_datetime = period.get("start")
        end_datetime = period.get("end")

    return {
        "encounter_id": resource.get("id"),
        "patient_id": reference_id(
            resource.get("patient")
        ),
        "status": resource.get("status"),
        "encounter_type": (
            encounter_display or encounter_code
        ),
        "class": class_code,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "reason_code": reason_code,
    }


# ---------------------------------------------------------------------------
# Condition
# ---------------------------------------------------------------------------

def normalize_condition(resource: dict) -> dict:
    code, display = coding_value(
        resource.get("code")
    )

    clinical_code, clinical_display = coding_value(
        resource.get("clinicalStatus")
    )

    verification_code, verification_display = coding_value(
        resource.get("verificationStatus")
    )

    return {
        "condition_id": resource.get("id"),
        "patient_id": reference_id(
            resource.get("subject")
        ),
        "encounter_id": reference_id(
            resource.get("context")
        ),
        "condition_code": code,
        "condition_display": display,
        "clinical_status": (
            clinical_display or clinical_code
        ),
        "verification_status": (
            verification_display or verification_code
        ),
        "onset_datetime": resource.get(
            "onsetDateTime"
        ),
        "abatement_datetime": resource.get(
            "abatementDateTime"
        ),
    }


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

def normalize_observation(resource: dict) -> dict:
    code, display = coding_value(
        resource.get("code")
    )

    value_numeric = None
    value_unit = None
    value_code = None
    value_text = None

    quantity = resource.get("valueQuantity")

    if isinstance(quantity, dict):
        value_numeric = quantity.get("value")
        value_unit = quantity.get("unit")

    concept = resource.get(
        "valueCodeableConcept"
    )

    if isinstance(concept, dict):
        value_code, value_text = coding_value(
            concept
        )

    effective_datetime = resource.get(
        "effectiveDateTime"
    )

    if effective_datetime is None:
        effective_period = resource.get(
            "effectivePeriod"
        )

        if isinstance(effective_period, dict):
            effective_datetime = effective_period.get(
                "start"
            )

    return {
        "observation_id": resource.get("id"),
        "patient_id": reference_id(
            resource.get("subject")
        ),
        "encounter_id": reference_id(
            resource.get("encounter")
        ),
        "status": resource.get("status"),
        "code": code,
        "display": display,
        "effective_datetime": effective_datetime,
        "value_numeric": value_numeric,
        "value_unit": value_unit,
        "value_code": value_code,
        "value_text": value_text,
        "has_components": bool(
            resource.get("component")
        ),
    }


# ---------------------------------------------------------------------------
# Immunization
# ---------------------------------------------------------------------------

def normalize_immunization(resource: dict) -> dict:
    code, display = coding_value(
        resource.get("vaccineCode")
    )

    return {
        "immunization_id": resource.get("id"),
        "patient_id": reference_id(
            resource.get("patient")
        ),
        "encounter_id": reference_id(
            resource.get("encounter")
        ),
        "vaccine_code": code,
        "vaccine_display": display,
        "date": resource.get("date"),
        "status": resource.get("status"),
        "primary_source": resource.get(
            "primarySource"
        ),
    }


# ---------------------------------------------------------------------------
# Procedure
# ---------------------------------------------------------------------------

def normalize_procedure(resource: dict) -> dict:
    code, display = coding_value(
        resource.get("code")
    )

    performed_start = None
    performed_end = None

    performed_datetime = resource.get(
        "performedDateTime"
    )

    if performed_datetime:
        performed_start = performed_datetime

    else:
        performed_period = resource.get(
            "performedPeriod"
        )

        if isinstance(performed_period, dict):
            performed_start = performed_period.get(
                "start"
            )

            performed_end = performed_period.get(
                "end"
            )

    reason_condition_id = first_reference(
        resource.get("reasonReference")
    )

    return {
        "procedure_id": resource.get("id"),
        "patient_id": reference_id(
            resource.get("subject")
        ),
        "encounter_id": reference_id(
            resource.get("encounter")
        ),
        "procedure_code": code,
        "procedure_display": display,
        "status": resource.get("status"),
        "performed_start": performed_start,
        "performed_end": performed_end,
        "reason_condition_id": reason_condition_id,
    }


# ---------------------------------------------------------------------------
# MedicationRequest
# ---------------------------------------------------------------------------

def normalize_medication_request(
    resource: dict,
) -> dict:
    medication = resource.get(
        "medicationCodeableConcept"
    )

    code, display = coding_value(
        medication
    )

    reason_condition_id = first_reference(
        resource.get("reasonReference")
    )

    return {
        "medication_request_id": resource.get(
            "id"
        ),
        "patient_id": reference_id(
            resource.get("patient")
        ),
        "encounter_id": reference_id(
            resource.get("context")
        ),
        "medication_code": code,
        "medication_display": display,
        "status": resource.get("status"),
        "stage": resource.get("stage"),
        "date_written": resource.get(
            "dateWritten"
        ),
        "reason_condition_id": reason_condition_id,
        "dosage_instruction": resource.get(
            "dosageInstruction"
        ),
    }


# ---------------------------------------------------------------------------
# CarePlan
# ---------------------------------------------------------------------------

def normalize_careplan(resource: dict) -> dict:
    category_code, category_display = coding_value(
        resource.get("category")
    )

    condition_id = first_reference(
        resource.get("addresses")
    )

    period = resource.get("period")

    period_start = None
    period_end = None

    if isinstance(period, dict):
        period_start = period.get("start")
        period_end = period.get("end")

    return {
        "careplan_id": resource.get("id"),
        "patient_id": reference_id(
            resource.get("subject")
        ),
        "encounter_id": reference_id(
            resource.get("context")
        ),
        "status": resource.get("status"),
        "category": (
            category_display or category_code
        ),
        "period_start": period_start,
        "period_end": period_end,
        "condition_id": condition_id,
    }


# ---------------------------------------------------------------------------
# AllergyIntolerance
# ---------------------------------------------------------------------------

def normalize_allergy(
    resource: dict,
) -> dict:
    code, display = coding_value(
        resource.get("code")
    )

    clinical_code, clinical_display = coding_value(
        resource.get("clinicalStatus")
    )

    category = resource.get("category")

    category_value = None

    if isinstance(category, list) and category:
        category_value = category[0]

    elif isinstance(category, str):
        category_value = category

    return {
        "allergy_id": resource.get("id"),
        "patient_id": reference_id(
            resource.get("patient")
        ),
        "clinical_status": (
            clinical_display or clinical_code
        ),
        "allergy_type": resource.get("type"),
        "category": category_value,
        "criticality": resource.get(
            "criticality"
        ),
        "code": code,
        "display": display,
        "asserted_date": resource.get(
            "assertedDate"
        ),
    }


# ---------------------------------------------------------------------------
# DiagnosticReport
# ---------------------------------------------------------------------------

def normalize_diagnostic_report(
    resource: dict,
) -> dict:
    code, display = coding_value(
        resource.get("code")
    )

    result_references = resource.get(
        "result",
        [],
    )

    result_observation_ids = []

    if isinstance(result_references, list):
        for reference in result_references:
            observation_id = reference_id(
                reference
            )

            if observation_id:
                result_observation_ids.append(
                    observation_id
                )

    elif isinstance(result_references, dict):
        observation_id = reference_id(
            result_references
        )

        if observation_id:
            result_observation_ids.append(
                observation_id
            )

    return {
        "diagnostic_report_id": resource.get(
            "id"
        ),
        "patient_id": reference_id(
            resource.get("subject")
        ),
        "encounter_id": reference_id(
            resource.get("encounter")
        ),
        "status": resource.get("status"),
        "code": code,
        "display": display,
        "effective_datetime": resource.get(
            "effectiveDateTime"
        ),
        "issued_datetime": resource.get(
            "issued"
        ),
        "result_observation_ids": (
            result_observation_ids
        ),
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def normalize_resource(
    resource: dict,
) -> dict | None:
    """
    Dispatch a FHIR resource to its resource-specific
    normalizer.

    Returns None for unsupported resource types.
    """

    if not isinstance(resource, dict):
        return None

    resource_type = resource.get(
        "resourceType"
    )

    normalizers = {
        "Patient": normalize_patient,
        "Encounter": normalize_encounter,
        "Condition": normalize_condition,
        "Observation": normalize_observation,
        "Immunization": normalize_immunization,
        "Procedure": normalize_procedure,
        "MedicationRequest": (
            normalize_medication_request
        ),
        "CarePlan": normalize_careplan,
        "AllergyIntolerance": normalize_allergy,
        "DiagnosticReport": (
            normalize_diagnostic_report
        ),
    }

    normalizer = normalizers.get(
        resource_type
    )

    if normalizer is None:
        return None

    return normalizer(resource)


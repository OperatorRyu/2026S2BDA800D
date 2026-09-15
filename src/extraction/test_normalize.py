from src.extraction.normalize import normalize_resource


def main():
    patient = {
        "resourceType": "Patient",
        "id": "patient-123",
        "gender": "female",
        "birthDate": "1980-01-01",
    }

    result = normalize_resource(patient)

    assert result["patient_id"] == "patient-123"
    assert result["gender"] == "female"
    assert result["birth_date"] == "1980-01-01"

    encounter = {
        "resourceType": "Encounter",
        "id": "encounter-123",
        "status": "finished",
        "patient": {
            "reference": "urn:uuid:patient-123"
        },
    }

    result = normalize_resource(encounter)

    assert result["encounter_id"] == "encounter-123"
    assert result["patient_id"] == "patient-123"

    print("Normalization tests passed.")


if __name__ == "__main__":
    main()


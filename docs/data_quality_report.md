# Data Quality Report

Automated validation of the analytical Parquet layer (`data/processed/`) produced by the Phase 2 extraction pipeline.

- Validation runtime: 10.31 seconds
- Issues found: 0

## 1. Row Counts vs Phase 1 Reconnaissance

| Table | Rows | Expected | Status |
|---|---:|---:|:-:|
| allergyintolerance | 51,107 | 51,107 | MATCH |
| careplan | 238,667 | 238,667 | MATCH |
| condition | 469,866 | 469,866 | MATCH |
| diagnosticreport | 304,845 | 304,845 | MATCH |
| encounter | 1,201,625 | 1,201,625 | MATCH |
| immunization | 862,744 | 862,744 | MATCH |
| medicationrequest | 334,869 | 334,869 | MATCH |
| observation | 4,756,568 | 4,756,568 | MATCH |
| patient | 129,218 | 129,218 | MATCH |
| procedure | 563,951 | 563,951 | MATCH |

## 2. Primary Key Uniqueness

| Table | Key Column | Rows | Non-null | Nulls | Distinct | Status |
|---|---|---:|---:|---:|---:|:-:|
| allergyintolerance | allergy_id | 51,107 | 0 | 51,107 | 0 | UNIQUE* |
| careplan | careplan_id | 238,667 | 0 | 238,667 | 0 | UNIQUE* |
| condition | condition_id | 469,866 | 469,866 | 0 | 469,866 | UNIQUE |
| diagnosticreport | diagnostic_report_id | 304,845 | 304,845 | 0 | 304,845 | UNIQUE |
| encounter | encounter_id | 1,201,625 | 1,201,625 | 0 | 1,201,625 | UNIQUE |
| immunization | immunization_id | 862,744 | 0 | 862,744 | 0 | UNIQUE* |
| medicationrequest | medication_request_id | 334,869 | 0 | 334,869 | 0 | UNIQUE* |
| observation | observation_id | 4,756,568 | 4,756,568 | 0 | 4,756,568 | UNIQUE |
| patient | patient_id | 129,218 | 129,218 | 0 | 129,218 | UNIQUE |
| procedure | procedure_id | 563,951 | 0 | 563,951 | 0 | UNIQUE* |

*`UNIQUE*` means the non-null primary-key values are unique, but one or more rows have a missing primary-key value.*

## 3. Null Rates

### allergyintolerance

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| allergy_id | 51,107 | 51,107 | 100.00% |
| patient_id | 0 | 51,107 | 0.00% |
| clinical_status | 51,107 | 51,107 | 100.00% |
| allergy_type | 0 | 51,107 | 0.00% |
| category | 0 | 51,107 | 0.00% |
| criticality | 0 | 51,107 | 0.00% |
| code | 0 | 51,107 | 0.00% |
| display | 0 | 51,107 | 0.00% |
| asserted_date | 0 | 51,107 | 0.00% |

### careplan

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| careplan_id | 238,667 | 238,667 | 100.00% |
| patient_id | 0 | 238,667 | 0.00% |
| encounter_id | 0 | 238,667 | 0.00% |
| status | 0 | 238,667 | 0.00% |
| category | 238,667 | 238,667 | 100.00% |
| period_start | 0 | 238,667 | 0.00% |
| period_end | 119,613 | 238,667 | 50.12% |
| condition_id | 60,942 | 238,667 | 25.53% |

### condition

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| condition_id | 0 | 469,866 | 0.00% |
| patient_id | 0 | 469,866 | 0.00% |
| encounter_id | 0 | 469,866 | 0.00% |
| condition_code | 0 | 469,866 | 0.00% |
| condition_display | 0 | 469,866 | 0.00% |
| clinical_status | 469,866 | 469,866 | 100.00% |
| verification_status | 469,866 | 469,866 | 100.00% |
| onset_datetime | 0 | 469,866 | 0.00% |
| abatement_datetime | 197,876 | 469,866 | 42.11% |

### diagnosticreport

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| diagnostic_report_id | 0 | 304,845 | 0.00% |
| patient_id | 0 | 304,845 | 0.00% |
| encounter_id | 0 | 304,845 | 0.00% |
| status | 0 | 304,845 | 0.00% |
| code | 0 | 304,845 | 0.00% |
| display | 0 | 304,845 | 0.00% |
| effective_datetime | 0 | 304,845 | 0.00% |
| issued_datetime | 0 | 304,845 | 0.00% |
| result_observation_ids | 0 | 304,845 | 0.00% |

### encounter

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| encounter_id | 0 | 1,201,625 | 0.00% |
| patient_id | 0 | 1,201,625 | 0.00% |
| status | 0 | 1,201,625 | 0.00% |
| encounter_type | 1,201,625 | 1,201,625 | 100.00% |
| class | 4 | 1,201,625 | 0.00% |
| start_datetime | 0 | 1,201,625 | 0.00% |
| end_datetime | 0 | 1,201,625 | 0.00% |
| reason_code | 1,201,625 | 1,201,625 | 100.00% |

### immunization

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| immunization_id | 862,744 | 862,744 | 100.00% |
| patient_id | 0 | 862,744 | 0.00% |
| encounter_id | 0 | 862,744 | 0.00% |
| vaccine_code | 0 | 862,744 | 0.00% |
| vaccine_display | 0 | 862,744 | 0.00% |
| date | 0 | 862,744 | 0.00% |
| status | 0 | 862,744 | 0.00% |
| primary_source | 0 | 862,744 | 0.00% |

### medicationrequest

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| medication_request_id | 334,869 | 334,869 | 100.00% |
| patient_id | 0 | 334,869 | 0.00% |
| encounter_id | 0 | 334,869 | 0.00% |
| medication_code | 0 | 334,869 | 0.00% |
| medication_display | 0 | 334,869 | 0.00% |
| status | 0 | 334,869 | 0.00% |
| stage | 0 | 334,869 | 0.00% |
| date_written | 0 | 334,869 | 0.00% |
| reason_condition_id | 188,834 | 334,869 | 56.39% |
| dosage_instruction | 0 | 334,869 | 0.00% |

### observation

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| observation_id | 0 | 4,756,568 | 0.00% |
| patient_id | 0 | 4,756,568 | 0.00% |
| encounter_id | 0 | 4,756,568 | 0.00% |
| status | 0 | 4,756,568 | 0.00% |
| code | 0 | 4,756,568 | 0.00% |
| display | 0 | 4,756,568 | 0.00% |
| effective_datetime | 0 | 4,756,568 | 0.00% |
| value_numeric | 589,490 | 4,756,568 | 12.39% |
| value_unit | 589,490 | 4,756,568 | 12.39% |
| value_code | 4,746,020 | 4,756,568 | 99.78% |
| value_text | 4,746,020 | 4,756,568 | 99.78% |
| has_components | 0 | 4,756,568 | 0.00% |

### patient

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| patient_id | 0 | 129,218 | 0.00% |
| gender | 0 | 129,218 | 0.00% |
| birth_date | 0 | 129,218 | 0.00% |
| family_name | 0 | 129,218 | 0.00% |
| given_name | 0 | 129,218 | 0.00% |
| marital_status | 36,178 | 129,218 | 28.00% |
| race | 0 | 129,218 | 0.00% |
| ethnicity | 0 | 129,218 | 0.00% |
| birth_city | 0 | 129,218 | 0.00% |
| birth_state | 0 | 129,218 | 0.00% |
| deceased_date | 99,489 | 129,218 | 76.99% |

### procedure

| Column | Nulls | Rows | Null % |
|---|---:|---:|---:|
| procedure_id | 563,951 | 563,951 | 100.00% |
| patient_id | 0 | 563,951 | 0.00% |
| encounter_id | 0 | 563,951 | 0.00% |
| procedure_code | 0 | 563,951 | 0.00% |
| procedure_display | 0 | 563,951 | 0.00% |
| status | 0 | 563,951 | 0.00% |
| performed_start | 0 | 563,951 | 0.00% |
| performed_end | 354,906 | 563,951 | 62.93% |
| reason_condition_id | 404,756 | 563,951 | 71.77% |

## 4. Referential Integrity

| Table.Column | References | Orphans | Nulls | Status |
|---|---:|---:|---:|:-:|
| allergyintolerance.patient_id | 51,107 | 0 | 0 | OK |
| careplan.encounter_id | 238,667 | 0 | 0 | OK |
| careplan.patient_id | 238,667 | 0 | 0 | OK |
| condition.encounter_id | 469,866 | 0 | 0 | OK |
| condition.patient_id | 469,866 | 0 | 0 | OK |
| diagnosticreport.encounter_id | 304,845 | 0 | 0 | OK |
| diagnosticreport.patient_id | 304,845 | 0 | 0 | OK |
| immunization.encounter_id | 862,744 | 0 | 0 | OK |
| immunization.patient_id | 862,744 | 0 | 0 | OK |
| medicationrequest.encounter_id | 334,869 | 0 | 0 | OK |
| medicationrequest.patient_id | 334,869 | 0 | 0 | OK |
| observation.encounter_id | 4,756,568 | 0 | 0 | OK |
| observation.patient_id | 4,756,568 | 0 | 0 | OK |
| procedure.encounter_id | 563,951 | 0 | 0 | OK |
| procedure.patient_id | 563,951 | 0 | 0 | OK |

## 5. Temporal Ranges

### allergyintolerance

| Column | Earliest | Latest |
|---|---|---|
| asserted_date | 1907-03-18T14:12:19-05:00 | 2017-02-20T14:21:56-05:00 |

### careplan

| Column | Earliest | Latest |
|---|---|---|
| period_start | 1907-03-01 | 2017-02-24 |
| period_end | 1911-06-24 | 2017-02-24 |

### condition

| Column | Earliest | Latest |
|---|---|---|
| onset_datetime | 1907-01-19T15:48:42-05:00 | 2017-02-24T10:42:55-05:00 |
| abatement_datetime | 1908-09-07T09:48:43-05:00 | 2017-02-24T12:09:34-05:00 |

### diagnosticreport

| Column | Earliest | Latest |
|---|---|---|
| effective_datetime | 1926-11-13T10:15:21-05:00 | 2017-02-24T11:20:36-05:00 |
| issued_datetime | 1926-11-13T10:15:21-05:00 | 2017-02-24T11:20:36-05:00 |

### encounter

| Column | Earliest | Latest |
|---|---|---|
| start_datetime | 1926-11-13T10:15:21-05:00 | 2017-02-24T11:30:58-05:00 |
| end_datetime | 1926-11-13T10:30:21-05:00 | 2017-02-24T11:49:13-05:00 |

### immunization

| Column | Earliest | Latest |
|---|---|---|
| date | 2010-02-24T07:18:59-05:00 | 2017-02-24T11:20:36-05:00 |

### medicationrequest

| Column | Earliest | Latest |
|---|---|---|
| date_written | 1906-11-12 | 2017-02-24 |

### observation

| Column | Earliest | Latest |
|---|---|---|
| effective_datetime | 1926-11-13T10:15:21-05:00 | 2017-02-24T11:20:36-05:00 |

### patient

| Column | Earliest | Latest |
|---|---|---|
| birth_date | 1906-03-04 | 2017-03-01 |
| deceased_date | 1907-05-03T10:11:45-05:00 | 2020-12-06T08:23:47-05:00 |

### procedure

| Column | Earliest | Latest |
|---|---|---|
| performed_start | 2010-02-24T07:18:59-05:00 | 2017-02-24T11:30:58-05:00 |
| performed_end | 2010-02-24T09:50:40-05:00 | 2017-03-08T16:38:55-05:00 |

## 6. Schema Consistency

- **allergyintolerance**: consistent
- **careplan**: consistent
- **condition**: consistent
- **diagnosticreport**: consistent
- **encounter**: consistent
- **immunization**: consistent
- **medicationrequest**: consistent
- **observation**: consistent
- **patient**: consistent
- **procedure**: consistent

## 7. Issues

None. All checks passed.
Analytical Data Model

---------------------
Purpose
---------------------
This document defines the analytical data model for the Synthea FHIR healthcare dataset used in the Big Data Analytics 800 group project.

The source dataset consists of FHIR JSON bundles containing multiple healthcare resource types. The raw data is retained unchanged as the source layer. The analytical model transforms these heterogeneous FHIR resources into structured, queryable datasets suitable for data validation, statistical analysis, machine learning, and visualisation.

The model is designed to:

    Preserve the original FHIR data as an immutable raw source.

    Extract individual FHIR resource types into structured analytical tables.

    Maintain relationships between patients, encounters, clinical events, and healthcare activities.

    Store processed analytical data in columnar Parquet format.

    Support scalable processing using Apache Spark.

    Provide a foundation for patient-level feature engineering and machine learning.

-----------------------
Source Data
-----------------------
The source dataset is a collection of Synthea-generated FHIR JSON bundles.

Current reconnaissance identified:
Metric	Value
JSON bundles	129,218
FHIR resources	8,913,460
Resource types	10
Malformed JSON files	0
Raw storage	Approximately 13 GB

The ten identified resource types are:

    Patient

    Encounter

    Observation

    Immunization

    Procedure

    Condition

    MedicationRequest

    DiagnosticReport

    CarePlan

    AllergyIntolerance

The resource distribution is highly heterogeneous. Observations account for approximately 53.36% of all resources, while Patient resources account for approximately 1.45%.

This distribution demonstrates why the source data should not be treated as a single flat table.

-----------------------
Data Layer Architecture
-----------------------

The pipeline will use three conceptual data layers.

                         RAW DATA
                            │
                            │ FHIR JSON
                            ▼
                  ┌─────────────────────┐
                  │   Raw / Source      │
                  │                     │
                  │ 129,218 JSON files  │
                  │ ~13 GB              │
                  └──────────┬──────────┘
                             │
                             │ Spark extraction
                             ▼
                  ┌─────────────────────┐
                  │   Staging Layer     │
                  │                     │
                  │ Resource extraction │
                  │ Schema normalization│
                  │ Basic validation    │
                  └──────────┬──────────┘
                             │
                             │ Transformation
                             ▼
                  ┌─────────────────────┐
                  │ Analytical Layer    │
                  │                     │
                  │ Parquet datasets    │
                  │ Patient features    │
                  └──────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          Statistics      Machine        Visualisation
                          Learning
---------------
Raw Layer
---------------
The raw layer contains the original Kaggle FHIR JSON files.

data/raw/fhir/

These files should not be modified by the processing pipeline.

The raw layer provides reproducibility and allows the analytical pipeline to be rerun from the original source data.

----------------
Staging Layer
----------------
The staging layer contains extracted and normalized FHIR resources.

At this stage:

    FHIR bundles are decomposed into individual resources.

    Resource types are identified.

    Relevant fields are extracted.

    Nested FHIR structures are normalized.

    References between resources are retained.

    Dates and numeric values are converted into appropriate data types.

    Invalid records can be flagged for later validation.

-----------------
Analytical Layer
-----------------

The analytical layer contains structured Parquet datasets.

data/processed/
├── patients/
├── encounters/
├── conditions/
├── observations/
├── medications/
├── procedures/
├── immunizations/
├── diagnostic_reports/
├── care_plans/
├── allergies/
└── patient_features/

Parquet is selected because its columnar storage format is appropriate for analytical workloads and supports efficient column selection and compression.

------------------
Core Analytical Tables
------------------

Each analytical table has a defined grain. The grain describes what one row represents.

-------------------
Patients
-------------------
Grain: One row per patient.

The patients dataset represents the demographic and identifying information associated with each synthetic patient.

Potential fields include:

Field	Description
patient_id	Unique patient identifier
gender	Patient gender
birth_date	Date of birth
marital_status	Marital status where available
deceased_date	Date of death where applicable
race	Race information from FHIR extension
ethnicity	Ethnicity information from FHIR extension
city	Patient location
state	Patient state

---------------
Encounters
---------------
Grain: One row per healthcare encounter.

The encounters dataset represents interactions between patients and the healthcare system.

Potential fields include:
Field	Description
encounter_id	Unique encounter identifier
patient_id	Associated patient
status	Encounter status
encounter_type	Type of encounter
class	FHIR encounter class
start_datetime	Encounter start
end_datetime	Encounter end
reason	Reason for encounter

This table provides the foundation for healthcare-utilisation analysis.

------------
Conditions
------------
Grain: One row per recorded clinical condition.

The conditions dataset represents diagnoses and other clinical conditions associated with patients.

Potential fields include:
Field	Description
condition_id	Unique condition identifier
patient_id	Associated patient
encounter_id	Related encounter
code	Condition code
clinical_status	Current clinical status
verification_status	Verification status
onset_datetime	Condition onset
abatement_datetime	Condition resolution where available

Conditions can be connected to medication, procedures, and care plans through FHIR references.
---------------
Observations
---------------
Grain: One row per clinical observation.

Observations represent measurements, laboratory results, vital signs, and other recorded clinical values.

Potential fields include:
Field	Description
observation_id	Unique observation identifier
patient_id	Associated patient
encounter_id	Related encounter
status	Observation status
code	Observation/measurement code
effective_datetime	Time of observation
value_numeric	Numeric measurement where applicable
value_unit	Measurement unit
value_code	Coded result where applicable

The observation dataset is the largest resource category in the source data and therefore represents a significant component of the analytical workload.

--------------
Medications
--------------
Grain: One row per medication request.

The medications dataset represents medication prescriptions or requests.

Potential fields include:
Field	Description
medication_request_id	Unique medication request
patient_id	Associated patient
encounter_id	Related encounter
medication_code	Medication code
status	Medication request status
date_written	Date prescribed
reason_condition_id	Associated condition where available
dosage_instruction	Dosage information

Medication requests can be connected to conditions through reasonReference.
-------------------
Procedures
-------------------
Grain: One row per recorded procedure.

Potential fields include:
Field	Description
procedure_id	Unique procedure identifier
patient_id	Associated patient
encounter_id	Related encounter
code	Procedure code
status	Procedure status
performed_datetime	Procedure timestamp where available
reason_condition_id	Associated condition where available

-----------------
Immunizations
-----------------
Grain: One row per immunization record.

Potential fields include:
Field	Description
immunization_id	Unique immunization identifier
patient_id	Associated patient
encounter_id	Related encounter
vaccine_code	Vaccine identifier
date	Immunization date
status	Immunization status
primary_source	Whether record is from primary source
was_not_given	Indicates whether immunization was not administered

-------------------
Diagnostic Reports
-------------------
Grain: One row per diagnostic report.

Potential fields include:
Field	Description
diagnostic_report_id	Unique report identifier
patient_id	Associated patient
encounter_id	Related encounter
code	Diagnostic report code
status	Report status
effective_datetime	Date of diagnostic activity
issued_datetime	Report issue timestamp
result_observation_ids	Associated observations

Diagnostic reports provide a higher-level relationship to the individual observations that form their results.

---------------------
Care Plans
--------------------
Grain: One row per care plan.

Potential fields include:
Field	Description
care_plan_id	Unique care plan identifier
patient_id	Associated patient
encounter_id	Related encounter
status	Care plan status
category	Care plan category
start_date	Care plan start
end_date	Care plan end
condition_ids	Conditions addressed by the plan
4.10 Allergies

Grain: One row per allergy/intolerance record.

Potential fields include:
Field	Description
allergy_id	Unique allergy identifier
patient_id	Associated patient
clinical_status	Clinical status
type	Allergy/intolerance type
category	Allergy category
criticality	Clinical criticality
code	Allergy code
asserted_date	Date recorded

--------------------
Entity Relationships
--------------------
The analytical model is centered around the patient.

The principal relationships identified during reconnaissance are:

                              ┌──────────────┐
                              │   Patient    │
                              │              │
                              │ patient_id   │
                              └──────┬───────┘
                                     │
             ┌───────────────────────┼────────────────────────┐
             │                       │                        │
             ▼                       ▼                        ▼
       ┌────────────┐         ┌────────────┐           ┌────────────┐
       │ Encounter  │         │ Condition  │           │  Allergy   │
       └─────┬──────┘         └─────┬──────┘           └────────────┘
             │                      │
       ┌─────┼──────────────┐       │
       │     │              │       │
       ▼     ▼              ▼       ▼
 Observation Procedure  Medication  CarePlan
       │
       │
       ▼
DiagnosticReport

The relationships identified during reference-integrity analysis were successfully resolved with no broken internal references in the examined relationships.

Important relationships include:

    Encounter.patient → Patient

    Condition.subject → Patient

    Condition.context → Encounter

    Observation.subject → Patient

    Observation.encounter → Encounter

    Immunization.patient → Patient

    Immunization.encounter → Encounter

    Procedure.subject → Patient

    Procedure.encounter → Encounter

    Procedure.reasonReference → Condition

    MedicationRequest.patient → Patient

    MedicationRequest.context → Encounter

    MedicationRequest.reasonReference → Condition

    DiagnosticReport.subject → Patient

    DiagnosticReport.encounter → Encounter

    DiagnosticReport.result → Observation

    CarePlan.subject → Patient

    CarePlan.context → Encounter

    CarePlan.addresses → Condition

    AllergyIntolerance.patient → Patient

This structure allows clinical events to be analyzed in both patient-level and encounter-level contexts.
-------------------------
Patient Feature Dataset
-------------------------
In addition to the resource-level analytical tables, a derived patient_features dataset will be created.

Grain: One row per patient.

The purpose of this dataset is to transform the longitudinal clinical records into features suitable for statistical analysis and machine learning.

An initial feature set may include:
Feature	Description
patient_id	Unique patient identifier
age	Derived patient age
gender	Patient gender
number_of_encounters	Total recorded encounters
number_of_conditions	Number of recorded conditions
number_of_observations	Number of observations
number_of_medications	Number of medication requests
number_of_procedures	Number of procedures
number_of_diagnostic_reports	Number of diagnostic reports
number_of_immunizations	Number of immunizations
number_of_allergies	Number of allergy records

Additional features may be introduced after exploratory analysis.

For example:

    Encounters per year

    Number of active conditions

    Medication count per encounter

    Procedure frequency

    Observation frequency

    Diagnostic report frequency

    Age at first encounter

    Time between encounters

    Chronic-condition indicators

The final feature set will depend on the business question and the results of exploratory analysis.

---------------------------------------
Analytical Model and Business Questions
---------------------------------------
The analytical model is intended to support investigation of healthcare utilisation and patient characteristics.

Potential analytical questions include:
Descriptive Analytics

    What are the demographic characteristics of the synthetic patient population?

    What types of encounters occur most frequently?

    Which conditions are most commonly recorded?

    What medications and procedures are most frequently associated with encounters?

    How does healthcare utilisation vary across age groups?

Diagnostic Analytics

    Which patient characteristics are associated with higher healthcare utilisation?

    Are particular conditions associated with increased encounter frequency?

    How are medications, procedures, observations, and diagnoses related?

Predictive Analytics

The patient_features dataset can be used to investigate predictive tasks such as:

    Predicting whether a patient belongs to a high-utilisation group.

    Predicting encounter frequency.

    Identifying patient characteristics associated with increased healthcare utilisation.

The exact predictive target will be selected after exploratory analysis and validation of the available data.
Prescriptive Analytics

If supported by the analysis, findings may be translated into potential recommendations for:

    Healthcare resource planning

    Patient monitoring

    Identification of high-utilisation populations

    Prioritisation of further investigation

Recommendations will be based on analytical findings rather than assumptions about individual patients.

--------------------------
Big Data Characteristics
--------------------------

The analytical model supports examination of the five commonly discussed Big Data characteristics.
Volume

The dataset contains approximately 13 GB of raw data, consisting of 129,218 JSON bundles and 8.9 million FHIR resources.

This volume provides an opportunity to demonstrate scalable processing using Apache Spark.
Variety

The source data contains ten different FHIR resource types with different schemas and nested structures.

The data includes:

    Demographic information

    Clinical conditions

    Measurements

    Diagnoses

    Medications

    Procedures

    Immunizations

    Diagnostic reports

    Care plans

    Allergy information

This heterogeneous structure demonstrates the variety characteristic of Big Data.
Velocity

The dataset is synthetic and static rather than a live healthcare feed. Therefore, velocity is not directly represented as a streaming characteristic.

However, the timestamped longitudinal records allow temporal healthcare activity to be analyzed, while the Spark-based pipeline provides an architecture that could be extended to continuously arriving data.
Veracity

Data veracity will be assessed through:

    JSON validity checks

    Schema validation

    Missing-value analysis

    Data-type validation

    Range checks

    Duplicate detection

    Referential-integrity checks

    Temporal consistency checks

Initial reconnaissance found zero malformed JSON files and no broken internal references in the relationships examined.
Value

The analytical layer is designed to transform the raw clinical records into information that can support healthcare-utilisation analysis, statistical investigation, predictive modelling, and visualisation.

--------------------------------
Storage and Processing Strategy
--------------------------------

The raw FHIR JSON files will remain unchanged.

Apache Spark will be used to process the raw data and produce structured analytical datasets.

The planned pipeline is:

Kaggle Dataset
      │
      ▼
Raw FHIR JSON
      │
      │ Spark
      ▼
Resource Extraction
      │
      ▼
Schema Normalisation
      │
      ▼
Data Validation
      │
      ▼
Parquet Analytical Tables
      │
      ├──────────────┐
      ▼              ▼
Patient Features   Resource Analysis
      │              │
      └───────┬──────┘
              ▼
       Statistical / ML
              │
              ▼
        Visualisation

Parquet datasets will be partitioned where appropriate to improve analytical performance. Partitioning decisions will be based on observed query patterns and dataset characteristics rather than applied indiscriminately.

--------------
Data Lineage
--------------

The project will maintain a clear lineage between source data and analytical outputs.

Kaggle
  │
  ▼
data/raw/fhir/
  │
  ▼
Spark ingestion
  │
  ├── Patient ───────────────► patients/
  ├── Encounter ─────────────► encounters/
  ├── Condition ─────────────► conditions/
  ├── Observation ───────────► observations/
  ├── MedicationRequest ─────► medications/
  ├── Procedure ─────────────► procedures/
  ├── Immunization ──────────► immunizations/
  ├── DiagnosticReport ──────► diagnostic_reports/
  ├── CarePlan ──────────────► care_plans/
  └── AllergyIntolerance ────► allergies/
                                      │
                                      ▼
                              patient_features/

Scripts used to generate each transformation will be stored in the project repository.

The raw dataset itself will not be committed to Git because of its size. Instead, acquisition instructions and dataset metadata will be documented so that another group member can reproduce the environment.
-------------------
Design Principles
-------------------
The analytical model follows these principles:

    Preserve the source data. Raw FHIR JSON is treated as immutable input.

    Separate extraction from analysis. Data engineering produces reusable analytical datasets before statistical or machine-learning analysis begins.

    Maintain referential relationships. FHIR identifiers are retained so that resources can be joined without losing clinical context.

    Define table grain explicitly. Each analytical dataset has a clear meaning for one row.

    Use scalable processing. Apache Spark will process the large raw dataset rather than relying exclusively on single-record Python processing.

    Use columnar storage. Parquet will be used for processed analytical data.

    Validate before analysis. Data-quality checks will be performed before analytical conclusions are drawn.

    Maintain reproducibility. Processing scripts, configuration, documentation, and environment definitions will be version-controlled.

------------------
Planned Extensions
------------------
The initial model will be expanded after exploratory analysis.

Potential extensions include:

    Time-based aggregation tables

    Annual healthcare-utilisation summaries

    Condition prevalence datasets

    Medication-condition association datasets

    Encounter-level feature datasets

    High-utilisation patient classifications

    Machine-learning feature matrices

    Aggregated datasets for visualisation tools

These extensions will be introduced only when they support a defined analytical question.

----------------
Summary
----------------
The proposed analytical model converts the heterogeneous Synthea FHIR dataset into a structured collection of related analytical datasets while preserving the original healthcare records.

The model uses Patient as the central entity and connects encounters, conditions, observations, medications, procedures, immunizations, diagnostic reports, care plans, and allergies through their FHIR identifiers.

This approach provides a clear separation between raw data, data engineering, analytical storage, and downstream analysis. It also provides the foundation for demonstrating Big Data concepts including volume, variety, veracity, scalable processing, columnar storage, statistical analysis, machine learning, and visualisation.

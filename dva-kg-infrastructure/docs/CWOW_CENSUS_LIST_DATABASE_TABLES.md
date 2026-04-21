# CWOW Census List - Database Tables and Schema

*Generated from DVA Knowledge Graph on 2025-11-23*

## Overview

The CWOW Census List feature is built using multiple database tables that store patient demographics, clinical information, treatment details, and facility data. This document outlines the key tables and their schemas used to construct the census list functionality.

---

## Core Tables

### 1. **PATIENT** (Primary Table)

The main patient demographics and identification table.

**Columns:**
- `PATIENT_ID` - Primary key, unique patient identifier
- `PATIENT_EUID` - External unique identifier
- `MASTER_PATIENT_IDENTIFIER` - MPI number displayed in UI
- `FIRST_NAME` - Patient's first name
- `MIDDLE_NAME` - Patient's middle name
- `LAST_NAME` - Patient's last name
- `DATE_OF_BIRTH` - Patient's date of birth
- `GENDER` - Patient's gender (Male/Female)
- `IKC_FLAG` - Integrated Kidney Care program flag
- `CREATE_DATE_TIME_GMT` - Record creation timestamp
- `UPDATE_DATE_TIME_GMT` - Record update timestamp
- `DELETE_DATE_TIME_GMT` - Soft delete timestamp

**Purpose:** Core patient demographic information displayed in census list and patient banner.

---

### 2. **PATIENT_STATUS**

Tracks patient status information and flags for filtering.

**Key Columns:**
- `PATIENT_ID` - Foreign key to PATIENT table
- `FACILITY_NUMBER` - Associated facility
- `VISITING_FLAG` - Indicates visiting patient status
- Additional status flags and codes

**Purpose:** Determines patient status categories (Active, Pending, Ready to Treat, Visiting) used in census list filters.

---

### 3. **PATIENT_RENAL_FUNCTION_STATUS**

Stores renal function and dialysis-related dates.

**Columns:**
- `PATIENT_ID` - Foreign key to PATIENT table
- `REGULAR_CHRONIC_DIALYSIS_BEGIN_DATE` - Date dialysis began (key for "New" patient determination)
- `RENAL_FUNCTION_EFFECTIVE_END_DATE` - End date of renal function status
- `INACTIVE_DATE_TIME_GMT` - Inactivation timestamp
- `DELETE_DATE_TIME_GMT` - Soft delete timestamp
- `ENTERED_IN_ERROR_FLAG` - Error flag
- `UPDATE_DATE_TIME_GMT` - Last update timestamp

**Purpose:** 
- Determines "New" patient status (< 91 days from REGULAR_CHRONIC_DIALYSIS_BEGIN_DATE)
- Tracks dialysis history and renal function changes

---

### 4. **PATIENT_MODALITY**

Tracks patient treatment modality (PD, HHD, In-Center HD, etc.).

**Columns:**
- `PATIENT_ID` - Foreign key to PATIENT table
- `MODALITY_CODE_ID` - Code identifying modality type
- `CREATE_DATE_TIME_GMT` - Record creation timestamp
- `END_DATE_TIME_GMT` - Modality end date
- `DELETE_DATE_TIME_GMT` - Soft delete timestamp
- `ENTERED_IN_ERROR_FLAG` - Error flag

**Modality Types:**
- PD (Peritoneal Dialysis)
- HHD (Home Hemodialysis)
- In-Center Hemodialysis
- Others

**Purpose:** Used in "Home Early Referral" filter (PD or HHD modalities) and general patient categorization.

---

### 5. **PATIENT_TREATMENT_LOCATION**

Links patients to treatment facilities.

**Columns:**
- `PATIENT_ID` - Foreign key to PATIENT table
- `FACILITY_ID` / `FACILITY_NUMBER` - Treatment facility identifier
- `PATIENT_DISCHARGE_DATE` - Discharge date from facility
- `INACTIVE_DATE_TIME_GMT` - Inactivation timestamp
- `DELETE_DATE_TIME_GMT` - Soft delete timestamp
- `REGGIE_PATIENT_LOCATION_ID` - Legacy system location ID
- `CREATE_SESSION_TOKEN_ID` - Creation session identifier
- `UPDATE_SESSION_TOKEN_ID` - Update session identifier

**Purpose:** Determines which facility's census list displays the patient; filters patients by facility.

---

### 6. **PATIENT_SCHEDULES**

Stores patient treatment schedules and shift assignments.

**Columns:**
- `PATIENT_ID` - Foreign key to PATIENT table
- `PATIENT_SCHEDULE_ID` - Primary key for schedule record
- `FACILITY_NUMBER` - Facility where treatment occurs
- `FACILITY_NUMBER_DOCUMENTED_AT` - Documentation facility
- `SHIFT_NAME` - Treatment shift name (Morning, Afternoon, Evening, etc.)
- `FACILITY_SCHEDULE_SHIFT_IDENTIFIER` - Shift identifier
- `DAY_OF_WEEK_DISPLAY_NAME` - Treatment day (Monday, Tuesday, etc.)
- `DAY_OF_WEEK_RECORD_NO` - Numeric day representation
- `FREQUENCY_CODE_ID` - Treatment frequency code
- `FREQUENCY_DISPLAY_NAME` - Frequency description
- `CREATE_DATE_TIME_GMT` - Record creation timestamp
- `CREATE_SESSION_TOKEN_ID` - Creation session identifier
- `DELETE_DATE_TIME_GMT` - Soft delete timestamp
- `ENTERED_IN_ERROR_FLAG` - Error flag

**Purpose:** Powers the Treatment Shift Filter on census list; displays patient treatment days and times.

---

### 7. **PATIENT_PROVIDER**

Links patients to healthcare providers (nephrologists, etc.).

**Columns:**
- `PATIENT_ID` - Foreign key to PATIENT table
- `PROVIDER_IDENTIFIER` - Provider's unique identifier
- `PROVIDER_TYPE_DISPLAY` - Provider type description
- `PROVIDER_TYPE_CODE_ID` - Provider type code
- `PRIMARY_NEPHROLOGIST_FLAG` - Indicates primary nephrologist
- `FACILITY_NUMBER_DOCUMENTED_AT` - Documentation facility
- `END_DATE_TIME` - Provider relationship end date
- `ENTERED_IN_ERROR_FLAG` - Error flag
- `DELETE_DATE_TIME_GMT` - Soft delete timestamp
- `CREATE_DATE_TIME_GMT` - Record creation timestamp

**Purpose:** Displays primary nephrologist information in patient banner; used for provider-based filtering.

---

### 8. **PILLAR_FACILITY**

Master facility information table.

**Columns:**
- `FACILITY_NUMBER` - Primary key, unique facility identifier
- `FACILITY_NAME` - Facility name
- `DELETE_DATE_TIME_GMT` - Soft delete timestamp

**Purpose:** Provides facility names and identifiers for census list filtering and display.

---

## Supporting Tables

### Additional Tables Referenced in Queries:

- **PATIENT_ALLERGIES** - Patient allergy information
- **PATIENT_MEDICATION_REFUSALS** - Medication refusal records
- **PATIENT_PHONE** - Patient contact phone numbers
- **PATIENT_ORDERS** (DNR) - Do Not Resuscitate orders
- **PATIENT_CLINICAL_DETAILS** - Various clinical attributes
- **PATIENT_FALL_RISK** - Fall risk assessments
- **PATIENT_HEPATITIS_STATUS** - Hepatitis B status
- **PATIENT_MDRO** - Multi-Drug Resistant Organism flags
- **PATIENT_STUDY_ENROLLMENT** - Clinical study participation
- **CODE_TABLES** - Various lookup/reference code tables

---

## Key Relationships and Joins

### Census List Query Pattern:

```sql
SELECT 
    P.PATIENT_ID,
    P.FIRST_NAME,
    P.LAST_NAME,
    P.MASTER_PATIENT_IDENTIFIER,
    P.DATE_OF_BIRTH,
    P.GENDER,
    PS.VISITING_FLAG,
    PS.IKC_FLAG,
    PM.MODALITY_CODE_ID,
    PRFS.REGULAR_CHRONIC_DIALYSIS_BEGIN_DATE,
    PSC.SHIFT_NAME,
    PSC.DAY_OF_WEEK_DISPLAY_NAME,
    PP.PROVIDER_IDENTIFIER,
    PF.FACILITY_NAME
FROM PATIENT P
LEFT JOIN PATIENT_STATUS PS 
    ON P.PATIENT_ID = PS.PATIENT_ID
LEFT JOIN PATIENT_RENAL_FUNCTION_STATUS PRFS 
    ON P.PATIENT_ID = PRFS.PATIENT_ID
LEFT JOIN PATIENT_MODALITY PM 
    ON P.PATIENT_ID = PM.PATIENT_ID
LEFT JOIN PATIENT_TREATMENT_LOCATION PTL 
    ON P.PATIENT_ID = PTL.PATIENT_ID
LEFT JOIN PATIENT_SCHEDULES PSC 
    ON P.PATIENT_ID = PSC.PATIENT_ID
LEFT JOIN PATIENT_PROVIDER PP 
    ON P.PATIENT_ID = PP.PATIENT_ID 
    AND PP.PRIMARY_NEPHROLOGIST_FLAG = 'Y'
LEFT JOIN PILLAR_FACILITY PF 
    ON PTL.FACILITY_NUMBER = PF.FACILITY_NUMBER
WHERE PTL.FACILITY_NUMBER = :facilityNumber
    AND PTL.DELETE_DATE_TIME_GMT IS NULL
    AND PS.DELETE_DATE_TIME_GMT IS NULL
```

---

## Filter Implementation

### Patient Type Filter Logic:

```sql
CASE
    WHEN PS.VISITING_FLAG = 'Y' THEN 'Visiting'
    WHEN P.IKC_FLAG = 'Y' THEN 'IKC'
    WHEN DATEDIFF(day, PRFS.REGULAR_CHRONIC_DIALYSIS_BEGIN_DATE, GETDATE()) < 91 
        THEN 'New'
    WHEN DATEDIFF(day, PRFS.REGULAR_CHRONIC_DIALYSIS_BEGIN_DATE, GETDATE()) >= 91 
        THEN 'Regular Chronic Dialysis > 90 Days'
    WHEN PS.TRANSITIONAL_CARE_PROGRAM_FLAG = 'Y' 
        THEN 'Transitional Care Program'
    WHEN P.PEDIATRIC_FLAG = 'Y' THEN 'Pediatric'
    WHEN PS.AKI_FLAG = 'Y' THEN 'AKI'
    ELSE 'Other'
END AS PATIENT_TYPE
```

### Home Early Referral Filter:

```sql
WHERE PM.MODALITY_CODE_ID IN ('PD', 'HHD')
    AND PS.STATUS_CODE IN ('PENDING', 'READY_TO_TREAT')
    AND PS.ANTICIPATED_example_START_DATE > DATEADD(day, 30, GETDATE())
```

### Treatment Shift Filter:

```sql
WHERE PSC.SHIFT_NAME IN (:selectedShifts)
    AND PSC.DELETE_DATE_TIME_GMT IS NULL
    AND PSC.ENTERED_IN_ERROR_FLAG = 'N'
```

---

## Data Flow

### Census List Construction Flow:

1. **Base Query**: Start with PATIENT table filtered by facility
2. **Join Status**: Add PATIENT_STATUS for status flags and filters
3. **Join Clinical**: Add PATIENT_RENAL_FUNCTION_STATUS for dialysis dates
4. **Join Modality**: Add PATIENT_MODALITY for treatment type
5. **Join Location**: Add PATIENT_TREATMENT_LOCATION for facility association
6. **Join Schedule**: Add PATIENT_SCHEDULES for shift information
7. **Join Provider**: Add PATIENT_PROVIDER for nephrologist info
8. **Join Facility**: Add PILLAR_FACILITY for facility details
9. **Apply Filters**: Apply user-selected filters (patient type, shift, etc.)
10. **Calculate Fields**: Compute derived fields (patient type, new status, etc.)
11. **Sort & Display**: Order results and display in census list UI

---

## Performance Considerations

### Indexes Required:

- `PATIENT.PATIENT_ID` (Primary Key)
- `PATIENT_STATUS.PATIENT_ID` (Foreign Key)
- `PATIENT_STATUS.FACILITY_NUMBER` (Filter Index)
- `PATIENT_TREATMENT_LOCATION.PATIENT_ID` (Foreign Key)
- `PATIENT_TREATMENT_LOCATION.FACILITY_NUMBER` (Filter Index)
- `PATIENT_SCHEDULES.PATIENT_ID` (Foreign Key)
- `PATIENT_SCHEDULES.SHIFT_NAME` (Filter Index)
- `PATIENT_RENAL_FUNCTION_STATUS.PATIENT_ID` (Foreign Key)
- `PATIENT_MODALITY.PATIENT_ID` (Foreign Key)
- `PATIENT_PROVIDER.PATIENT_ID` (Foreign Key)

### Query Optimization:

- Use `DELETE_DATE_TIME_GMT IS NULL` for soft delete filtering
- Use `ENTERED_IN_ERROR_FLAG = 'N'` to exclude erroneous records
- Filter by facility early in query execution
- Consider materialized views for complex patient type calculations
- Cache frequently accessed facility and code table data

---

## SQL Query References

Based on the knowledge graph, the following SQL query files are used:

- `FIND_PATIENT_DETAILS_WITH_FACILITY_NUMBER.sql`
- `find_patients_by_facility_and_statuscode_and_date_range.sql`
- `find_active_patients_by_facility_and_patient_id.sql`
- `find_patientdetails_by_trtmtlocation_byfacilityid.sql`
- `find_patient_treatment_location_by_patientId_list.sql`
- `find_patient_eligible_for_displaying_new_icon.sql`
- `find_clinical_detail_dto_data_w_facility.sql`
- `find_patient_nephrologist_detail.sql`
- `get_patient_calendars.sql`

---

## Summary

The CWOW Census List is built on a **normalized relational database schema** with the following characteristics:

- **8 Core Tables**: PATIENT, PATIENT_STATUS, PATIENT_RENAL_FUNCTION_STATUS, PATIENT_MODALITY, PATIENT_TREATMENT_LOCATION, PATIENT_SCHEDULES, PATIENT_PROVIDER, PILLAR_FACILITY
- **Multiple Supporting Tables**: For allergies, medications, clinical details, etc.
- **Soft Delete Pattern**: Uses `DELETE_DATE_TIME_GMT` for logical deletes
- **Audit Trail**: Includes `CREATE_DATE_TIME_GMT` and `UPDATE_DATE_TIME_GMT`
- **Error Handling**: `ENTERED_IN_ERROR_FLAG` for data quality
- **Complex Joins**: Multi-table joins with careful NULL handling
- **Calculated Fields**: Patient type derived from multiple flags and date calculations
- **Filter Optimization**: Indexed columns for common filter operations

This schema supports the full range of census list functionality including patient type filtering, shift-based views, status tracking, and comprehensive patient information display.

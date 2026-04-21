# Complete Patient Modality Behavior Analysis for SNF Clinics
## Analysis Using Glean MCP Data + Patient Domain Repository

---

## Executive Summary

This comprehensive analysis combines data from the CWOW patient domain documentation and example's internal knowledge base (via Glean) to identify patient modality behaviors specific to SNF (Skilled Nursing Facility) clinics. The analysis reveals critical insights about how SNF patients are managed differently from standard ICHD patients, including system integration challenges and operational workflows.

---

## 1. SNF Modality Architecture

### 1.1 Modality Classification

**SNF operates as ICHD modality with special designation:**

| Aspect | SNF Dialysis | Regular ICHD |
|--------|--------------|--------------|
| **Modality Type** | ICHD (In-Center Hemodialysis) | ICHD |
| **Reggie Modality Value** | "SNF Dialysis" | "In Center Hemo-Staff" or "In Center Hemo-Self" |
| **CWOW Display** | SNF Dialysis | ICHD |
| **Schedule Hub Treatment** | ICHD modality operations | ICHD modality operations |
| **Facility Flag** | SNF flag at location level | Standard facility flag |

**Key Finding:** SNF facilities operate functionally as ICHD modalities but maintain a distinct "SNF Dialysis" designation in Reggie for tracking and reporting purposes.

### 1.2 Modality Mappings

**Reggie Modality Dropdown Mappings:**

```
DropDownBox ID | Name                    | Modality | Modality Group
31             | In Center Hemo-Staff    | ICHD     | ICHD
271            | In Center Hemo-Self     | ICHD     | ICHD
[SNF]          | SNF Dialysis            | ICHD     | SNF
32             | CAPD                    | PD       | PD
33             | CCPD                    | PD       | PD
110            | Home Hemo-Staff         | HHD      | HHD
272            | Home Hemo-Self          | HHD      | HHD
```

**Source:** Global Requirements for Metrics (Confluence)

---

## 2. Critical SNF-Specific Behaviors

### 2.1 Modality Mismatch Issue (Real-World Case)

**Problem Identified:**
When example SNF Dialysis (DSD) facilities were initially brought onto CWOW, a modality mismatch issue was discovered:

**Scenario:**
- **Patient Location:** SNF Clinic
- **CWOW Modality:** HHD (Home Hemodialysis)
- **Reggie Modality:** HHD
- **Issue:** SNF facilities cannot support home modalities

**Resolution:**
- Change patient modality in CWOW from HHD to ICHD
- CWOW publishes modality change event to Reggie
- Reggie updates to "SNF Dialysis" modality
- Systems synchronize on ICHD-based treatment

**Root Cause:**
CWOW maintains the SNF flag at the **location level**, not the patient level. If a patient is active at multiple locations (e.g., regular ICHD facility + SNF facility), the system must correctly identify which modality applies to which location.

**Source:** Email thread "FW: Modality Mismatch between Reggie and CWOW" (November 2025)

### 2.2 SNF Flag Management

**Location-Level Flag:**
```
CWOW maintains SNF flag at location level
├── Patient can have multiple active locations
├── Each location has its own modality designation
└── SNF location requires ICHD modality
```

**Implications:**
1. Patient modality must match facility capabilities
2. Home modalities (PD, HHD) are incompatible with SNF locations
3. System validations needed to prevent modality mismatches
4. Patient transitions between facilities require modality verification

---

## 3. Schedule Hub Integration for SNF

### 3.1 R18 Enhancement: Enable Schedule Hub for DSD Facilities

**Project Scope:** LS-21606, LS-20248

**Key Requirements:**
1. Allow SNF (Skilled Nurse Facility) in Schedule Hub (SH)
2. Create Queue/PGs/Roles for SNF clinics
3. Enable patient list display for SNF facilities
4. Support treatment plan management without PPS integration

### 3.2 Facility Modality Configuration

**Schedule Hub Label Update:**
- **Label:** DKC ICHD Facility Modalities (DKC_ICHD_Facility_Modalities)
- **Action:** Add "SNF Dialysis" to picklist
- **Purpose:** Enable Queue/PG/Role creation for SNF clinics

**Sample SNF Facilities:**
```
09291 - SNF DIALYSIS AT KIMBERLY HALL SOUTH-BLOOMFIELD
09301 - SNF DIALYSIS AT DIAMONDBACK-TEMPE
09226 - SNF DIALYSIS AT HIGHLAND-KANSAS CITY RENAL
```

### 3.3 Patient List Query Logic

**Current Query (Pre-SNF):**
```sql
SELECT DKC_Patient__r.DKC_Full_Name__c, 
       DKC_Patient__r.DKC_MPI__c,
       DKC_Patient__r.DKC_Mobile__c,
       DKC_Patient__r.DKC_HomePhone__c,
       DKC_Patient__r.DKC_AmbulatoryStatus__c,
       DKC_Patient__r.DKC_HoyerLift__c,
       DKC_Patient__r.DKC_PatientScheduleFlexible__c,
       DKC_ClinicType__c
FROM DKC_PLI__c
WHERE (DKC_Facility__c = $recordId AND
       (DKC_EndDate__c >= TODAY OR DKC_EndDate__c = null))
  AND DKC_PatientModalityContainInCenterHemo__c = True
  AND DKC_Patient__r.DKC_Status__c != 'Inactive'
```

**Updated Formula (SNF Support):**
- **Object:** Patient Location (DKC_PLI__c)
- **Formula:** DKC_PatientModalityContainInCenterHemo
- **Update:** Check for "SNF Dialysis" modality in addition to ICHD

**Effect:** SNF patients now appear in Schedule Hub patient lists

### 3.4 Treatment Plan Management

**Key Differences from Regular ICHD:**

| Feature | Regular ICHD | SNF Dialysis |
|---------|--------------|--------------|
| **PPS Integration** | Yes | No |
| **Treatment Plan Source** | PPS creates TPs | Manual/Block Slot |
| **Enrollment Workflow** | PPS-driven | Reggie PLI → Reserve Slot |
| **Order Type** | ICHD Tx Order | ICHD Tx Order |
| **DNR Orders** | Yes | Yes (same process) |

**SNF Treatment Plan Workflow:**
1. Patient enrolled in SNF facility (Reggie)
2. Reggie sends Patient Location Information (PLI)
3. Schedule Hub uses Block/Reserve Slot feature
4. Treatment appointments created manually
5. No PPS automation

### 3.5 SNF Operational Characteristics

**Confirmed Behaviors (Same as Regular ICHD):**
- ✅ Float Pool: Not applicable (business decision)
- ✅ Nocturnal Shifts: Supported
- ✅ Station/POD Management: Same as regular clinics
- ✅ Buffer Station Concept: Applies
- ✅ Skill Sets: Same as regular teammates
- ✅ Opener/Closure Shifts: Yes
- ✅ Patient Events (Hospitalization/Treating Elsewhere): Same handling
- ✅ ISO Patients: Treated same day, different times
- ✅ Patient Access: No change
- ✅ Auto Assign/Publish: Enabled
- ✅ SH Mobile: Eligible
- ✅ Manage My Day: Supported

**SNF-Specific Constraints:**
- ❌ Float Pool: Not enabled for SNF facilities
- ❌ PPS Integration: Not applicable
- ❌ Community Schedule: Under review (should work, no restrictions)
- ❌ Construction Zone: Under review with business
- ❌ DPC Targets: Discussion in progress

---

## 4. Metrics and Performance Tracking

### 4.1 SNF Modality in Metrics

**Modalities Tracked:**
- ICHD (In-Center Hemodialysis)
- PD (Peritoneal Dialysis)
- HHD (Home Hemodialysis)
- **SNF (Skilled Nursing Facility - Post-Acute)**
- Peds-ICHD (Pediatric ICHD)
- Peds-PD (Pediatric PD)

**Source:** Global Requirements for Metrics

### 4.2 SNF Top/Bottom Percentile Calculations

**Calculation Methodology:**

SNF facilities are tracked separately from regular ICHD for performance metrics:

**Example Data:**
```
Facility | SNF Measure Value | SNF Flag | Display Location
---------|-------------------|----------|------------------
A        | 98                | Y        | Under SNF in FHR NG
B        | 97                | Y        | Under SNF in FHR NG
C        | 95                | Y        | Under SNF in FHR NG
D        | 94                | Y        | Under SNF in FHR NG
E        | 88                | N        | Not under SNF
F        | 79                | N        | Not under SNF
```

**Percentile Calculation (Favorable Direction: UP):**
- **Top 20%:** Score >= 97 (facilities A, B)
- **Bottom 20%:** Score <= 88 (facility D)

**Key Points:**
1. Only facilities offering SNF services included in SNF percentile calculations
2. SNF metrics tracked separately from regular ICHD metrics
3. Post-Acute metrics only apply to Post-Acute facilities
4. Uses PERCENTILE_CONT function for calculations

### 4.3 Performance Census for SNF

**Patient Inclusion Criteria:**
- Flagged as "Performance" patient
- Assigned to facility with SNF flag
- Modality_Group determines patient's modality
- Source: `VIEW_DB.VIEW_DB_USR.CLINICAL_INSIGHTS_DQI_MON_DATA_VW`

**Example:**
```
Patient 1234 is a SNF Performance Patient in Facility 11394
Modality: SNF Dialysis
Performance Flag: Y
```

---

## 5. System Integration Architecture

### 5.1 Integration Points

**Systems Involved:**
1. **CWOW** - Clinical workflow, modality management
2. **Reggie** - Patient demographics, modality source
3. **Schedule Hub (SH)** - Scheduling and appointments
4. **Kronos** - Teammate scheduling
5. **OIM** - Teammate provisioning
6. **Ellie** - (Integration details TBD)
7. **Sedgwick** - PTO/LOA management
8. **SH Mobile** - Mobile scheduling
9. **BART** - Machine type data

**Not Integrated:**
- ❌ **PPS** - Not applicable for SNF clinics
- ❌ **DPP** - Future consideration

### 5.2 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Patient Enrollment                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Reggie: Create Patient Location (PLI)                      │
│  - Modality: "SNF Dialysis"                                 │
│  - Location: SNF Facility                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  AI Filter (LS-20299): Send SNF data to Schedule Hub        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Schedule Hub: Patient appears in facility patient list     │
│  - Query checks DKC_PatientModalityContainInCenterHemo      │
│  - Includes "SNF Dialysis" modality                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  CWOW: Modality Management                                  │
│  - Display: SNF Dialysis                                    │
│  - SNF flag at location level                               │
│  - Validation: No home modalities for SNF locations         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Treatment Scheduling                                        │
│  - Manual Block/Reserve Slot (no PPS)                       │
│  - ICHD treatment orders                                    │
│  - Standard ICHD workflow                                   │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Modality Change Event Flow

**When Patient Modality Changes in CWOW:**

```
1. User updates modality in CWOW Clinical Details
   ↓
2. CWOW displays confirmation: "Changing the modality will impact other areas of CWOW"
   ↓
3. User saves change
   ↓
4. CWOW publishes modality change event
   ↓
5. Reggie consumes event and updates patient modality
   ↓
6. If location is SNF: Reggie sets modality to "SNF Dialysis"
   ↓
7. Schedule Hub receives updated PLI data
   ↓
8. Patient list refreshes with correct modality
```

---

## 6. Clinical Workflow Implications

### 6.1 Patient Admission to SNF

**Workflow Steps:**
1. **Patient Referral:** Patient referred to SNF facility
2. **Modality Verification:** Ensure patient modality is ICHD-compatible
3. **Location Setup:** Create Patient Location (PLI) in Reggie
4. **Modality Assignment:** Reggie assigns "SNF Dialysis" modality
5. **CWOW Sync:** CWOW receives PLI update
6. **Schedule Hub Enrollment:** Patient appears in SH patient list
7. **Treatment Scheduling:** Use Block/Reserve Slot for appointments
8. **Treatment Delivery:** Standard ICHD treatment protocol

### 6.2 Modality Validation Rules

**System Validations:**

| Scenario | Validation | Action |
|----------|------------|--------|
| Patient with HHD at SNF location | ❌ Invalid | Change to ICHD |
| Patient with PD at SNF location | ❌ Invalid | Change to ICHD |
| Patient with ICHD at SNF location | ✅ Valid | Allow |
| Patient with SNF Dialysis at SNF location | ✅ Valid | Allow |
| Patient with SNF Dialysis at regular ICHD location | ⚠️ Review | May need change |

### 6.3 Patient Transitions

**SNF → Regular ICHD Facility:**
1. Patient discharged from SNF
2. New PLI created for regular ICHD facility
3. Modality may remain "SNF Dialysis" or change to "In Center Hemo-Staff"
4. CWOW updates patient location
5. Schedule Hub reflects new facility assignment

**Regular ICHD → SNF Facility:**
1. Patient needs SNF-level care
2. New PLI created for SNF facility
3. Modality changed to "SNF Dialysis"
4. CWOW validates modality compatibility
5. Treatment plan transitioned to manual scheduling

---

## 7. Technical Implementation Details

### 7.1 Patient Location Information (PLI) Object

**Key Fields:**
- `DKC_Facility__c` - Facility ID
- `DKC_Patient__r` - Patient reference
- `DKC_EndDate__c` - Location end date
- `DKC_PatientModalityContainInCenterHemo__c` - ICHD/SNF modality flag
- `DKC_Status__c` - Patient status
- `DKC_ClinicType__c` - Clinic type designation

**SNF-Specific Logic:**
```javascript
// Formula update for SNF support
DKC_PatientModalityContainInCenterHemo__c = 
    (Modality == "In Center Hemo-Staff" || 
     Modality == "In Center Hemo-Self" ||
     Modality == "SNF Dialysis")
```

### 7.2 Facility Configuration

**Facility Modality Picklist:**
- Label: `DKC_ICHD_Facility_Modalities`
- Values: ICHD, SNF Dialysis, HDF (Hemodiafiltration)

**Queue/Permission Group/Role Creation:**
- Automatically created when facility modality includes "SNF Dialysis"
- Naming convention: `[Facility_Name]_SNF_[Queue/PG/Role]`

### 7.3 Data Cleanup Requirements

**Issues Identified (R18 Implementation):**

| Object | Issue | Count | Status |
|--------|-------|-------|--------|
| Facility | Name contains "Placeholder" | 216 | Needs correction |
| Permission Group | Name/Dev Name = "Placeholder" | 343 | Needs correction |
| Queue | Name/Dev Name = "Placeholder" | 137 | Needs correction |
| Role | Dev Name = "Placeholder" | 138 | Corrected |
| Role | Name/Dev Name = "Placeholder" | 7 | Needs correction |

**Recommendation:** Full data load for SNF/PD facilities to correct placeholder values

---

## 8. Operational Protocols

### 8.1 SNF-Specific Protocols

**Protocol Examples:**
- **CWAP-14823:** Skilled Nursing Facilities (SNF) CE request 3 ICHD ONS rev 2.0 NAPs
- **Approval Date:** 2022-12-28
- **Modality:** ICHD
- **Source:** All Protocols - Publish Protocol and Formulary Comprehensive List

### 8.2 Treatment Scheduling Constraints

**Scheduling Rules:**
1. **No PPS Integration:** Manual scheduling required
2. **Block Slot Usage:** Reserve slots for SNF patients
3. **Treatment Days:** Typically M/W/F or T/Th/Sat (same as ICHD)
4. **Shift Assignment:** 1, 2, or 3 (same as ICHD)
5. **Nocturnal Option:** Available if facility supports

### 8.3 Teammate Assignment

**Staffing Considerations:**
- SNF teammates can work at regular ICHD facilities (if neighboring assignment in OIM)
- Regular ICHD teammates can help SNF clinics
- Same skill sets required
- Kronos integration for shift scheduling

---

## 9. Reporting and Analytics

### 9.1 Metric Categories

**SNF-Specific Metrics:**
- Operational Census (SNF)
- Treatment Volume (SNF)
- Hospitalization Rate (SNF)
- Missed Treatment Rate (SNF)
- Patient Satisfaction (SNF)

**Calculation Level:**
- Facility/Modality level (SNF separate from ICHD)
- CCN rollup includes SNF facilities
- Village percentiles calculated separately for SNF

### 9.2 Patient Lists for Metrics

**Standard Fields:**
- Patient Name
- MPI (Master Patient Index)
- Schedule (e.g., M/W/F)
- Shift (1, 2, or 3)
- IKC Flag
- Missed Treatment Secondary Reason
- Hospitalization Admit Date
- Mortality Reason

**SNF Flag:** Included in reporting to distinguish SNF patients

### 9.3 FHR NextGen Integration

**Data Load Requirements:**
- Two-year backload of SNF data
- Monthly data accumulation
- Combination of CWOW and Snappy data (if applicable)
- Patient lists not backloaded
- Pathway metrics include available CWOW data

---

## 10. Key Findings and Recommendations

### 10.1 Critical Insights

1. **SNF operates as ICHD functionally** but maintains distinct "SNF Dialysis" designation
2. **Location-level SNF flag** prevents modality mismatches
3. **No PPS integration** requires manual treatment scheduling
4. **Separate performance tracking** for SNF vs. regular ICHD
5. **System validations needed** to prevent home modalities at SNF locations

### 10.2 Modality Mismatch Prevention

**Recommended Validations:**

```sql
-- Validation Rule: Prevent home modalities at SNF locations
IF (Location.SNF_Flag = TRUE) THEN
    ASSERT (Patient.Modality IN ('ICHD', 'SNF Dialysis'))
    ERROR: "SNF locations only support ICHD modalities"
END IF

-- Validation Rule: Auto-correct modality on SNF admission
IF (Patient.New_Location.SNF_Flag = TRUE AND 
    Patient.Modality IN ('HHD', 'PD')) THEN
    Patient.Modality = 'SNF Dialysis'
    TRIGGER: Modality_Change_Event
    NOTIFY: User with confirmation message
END IF
```

### 10.3 Implementation Checklist

**For New SNF Facility Setup:**
- [ ] Create facility with SNF flag
- [ ] Add "SNF Dialysis" to facility modality picklist
- [ ] Create Queue/PG/Role for SNF clinic
- [ ] Configure AI filter to send SNF data to Schedule Hub
- [ ] Update PLI formula to include SNF modality
- [ ] Test patient list display in Schedule Hub
- [ ] Verify modality validation rules
- [ ] Configure metrics tracking for SNF
- [ ] Set up teammate assignments in OIM
- [ ] Enable BART integration for machine types

**For Patient Admission to SNF:**
- [ ] Verify patient current modality
- [ ] Create PLI record with SNF location
- [ ] Assign "SNF Dialysis" modality in Reggie
- [ ] Confirm CWOW sync and SNF flag
- [ ] Verify patient appears in Schedule Hub
- [ ] Create treatment schedule using Block Slot
- [ ] Assign teammates to patient
- [ ] Configure treatment orders (ICHD Tx Order)

### 10.4 Operational Best Practices

1. **Modality Management:**
   - Always verify modality compatibility before SNF admission
   - Use automated validation rules to prevent mismatches
   - Monitor modality change events for SNF patients

2. **Scheduling:**
   - Leverage Block/Reserve Slot feature for SNF patients
   - Maintain consistent treatment schedules (M/W/F or T/Th/Sat)
   - Coordinate with teammate availability

3. **Performance Tracking:**
   - Track SNF metrics separately from regular ICHD
   - Use SNF flag for accurate reporting
   - Monitor top/bottom percentiles specific to SNF

4. **System Integration:**
   - Ensure AI filter includes SNF facilities
   - Verify PLI data flow from Reggie to Schedule Hub
   - Test CWOW-Reggie modality synchronization

5. **Data Quality:**
   - Clean up placeholder facility/queue/role names
   - Validate SNF flag accuracy
   - Audit patient modality assignments regularly

---

## 11. Future Enhancements

### 11.1 Under Review

- **Community Schedule:** Should work for SNF (no restrictions planned)
- **Construction Zone:** Business needs assessment
- **DPC Targets:** Discussion in progress
- **DPP Integration:** Future consideration

### 11.2 Potential Improvements

1. **Automated Modality Correction:**
   - Auto-detect home modality at SNF location
   - Prompt user to change to ICHD
   - Log modality change events

2. **Enhanced Reporting:**
   - SNF-specific dashboards
   - Modality transition tracking
   - Patient flow analytics (SNF ↔ Regular ICHD)

3. **PPS Integration (Future):**
   - Evaluate feasibility of PPS for SNF
   - Automated treatment plan creation
   - Reduce manual scheduling burden

4. **Float Pool Support:**
   - Assess business need for SNF float pool
   - Design teammate assignment logic
   - Implement if demand exists

---

## 12. Conclusion

SNF patient modality behavior is characterized by:

1. **Functional ICHD Operations:** SNF facilities operate as ICHD modalities with all standard ICHD workflows
2. **Distinct Designation:** "SNF Dialysis" modality in Reggie for tracking and reporting
3. **Location-Level Management:** SNF flag maintained at location level to prevent modality mismatches
4. **Manual Scheduling:** No PPS integration; uses Block/Reserve Slot approach
5. **Separate Performance Tracking:** SNF metrics calculated independently from regular ICHD
6. **System Integration Complexity:** Requires coordination across CWOW, Reggie, Schedule Hub, and other systems

**Key Operational Principle:**
> SNF patients must have ICHD-compatible modalities. Home modalities (PD, HHD) are incompatible with SNF locations and must be corrected to "SNF Dialysis" or ICHD upon admission.

---

## 13. Sources and References

### Primary Sources

1. **Confluence Documentation:**
   - R18 | Enable Schedule Hub for example SNF Dialysis (DSD) facilities
   - 0. Global Requirements for Metrics
   - All Protocols - Publish Protocol and Formulary Comprehensive List
   - ScheduleHub Integration Requirements Documents

2. **Email Communications:**
   - FW: Modality Mismatch between Reggie and CWOW (November 2025)

3. **Patient Domain Repository:**
   - CWOW-235996 View and Update Clinical Details 17_Baseline 4.0.pdf
   - CWOW-244309 View Patient List 06_Baseline 4.0.pdf
   - CWOW-226167 Display Patient Banner 10_Baseline 4.0.pdf

4. **Code Repositories (via Glean):**
   - Tableau Medcost Extract.SQL
   - GMN_T2_CHE_SCHEDULING_VHES.sql
   - Various performance management and analytics scripts

### Tickets Referenced

- **LS-21606:** Enable Schedule Hub for SNF facilities
- **LS-20248:** SNF Schedule Hub integration
- **LS-20681:** Patient list display for SNF
- **LS-20718:** Treatment plan visibility for SNF
- **LS-20299:** AI filter update for SNF data flow
- **LS-21605:** Kronos integration for SNF
- **LS-16853:** Open shifts feature for SNF
- **CWAP-14823:** SNF protocol approval

### Subject Matter Experts

- **Rahul Kumar:** Technical design lead (Schedule Hub)
- **Rahul Yadav:** Business requirements
- **Renuka Thakur:** Product management
- **Tami Peters:** Operational requirements
- **Mary Gillis:** Metrics documentation owner

---

## Analysis Metadata

**Analysis Date:** December 2, 2025  
**Analysis Method:** Glean MCP Data Search + Patient Domain Repository Review  
**Repository:** cwow-patient-model-spanner.git (develop branch)  
**Analyst:** DVA Agentic CLI  
**Version:** 2.0 (Complete Analysis with Glean Integration)

---

## Appendix A: Glossary

- **SNF:** Skilled Nursing Facility (Post-Acute care setting)
- **DSD:** example SNF Dialysis
- **ICHD:** In-Center Hemodialysis
- **PD:** Peritoneal Dialysis
- **HHD:** Home Hemodialysis
- **PLI:** Patient Location Information
- **CWOW:** Clinical Workflow on the Web
- **SH:** Schedule Hub
- **PPS:** Patient Planning System
- **OIM:** Organizational Identity Management
- **CCN:** CMS Certification Number
- **MPI:** Master Patient Index
- **FHR:** Facility Health Report
- **DPC:** Dialysis Patient Care
- **IKC:** Integrated Kidney Care

---

## Appendix B: System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        example SNF Ecosystem                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Reggie     │────────▶│    CWOW      │────────▶│ Schedule Hub │
│              │         │              │         │              │
│ - Patient    │         │ - Clinical   │         │ - Scheduling │
│   Demographics│        │   Workflow   │         │ - Appointments│
│ - Modality   │         │ - Modality   │         │ - Patient    │
│   Assignment │         │   Management │         │   Lists      │
│ - PLI Data   │         │ - SNF Flag   │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
       │                        │                        │
       │                        │                        │
       ▼                        ▼                        ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Kronos     │         │     OIM      │         │    BART      │
│              │         │              │         │              │
│ - Teammate   │         │ - Teammate   │         │ - Machine    │
│   Scheduling │         │   Provisioning│        │   Types      │
└──────────────┘         └──────────────┘         └──────────────┘

                         ┌──────────────┐
                         │  FHR NextGen │
                         │              │
                         │ - Metrics    │
                         │ - Reporting  │
                         │ - Analytics  │
                         └──────────────┘
```

---

**End of Analysis**

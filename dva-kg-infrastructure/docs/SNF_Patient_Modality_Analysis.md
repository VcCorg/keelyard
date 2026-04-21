# Patient Modality Behavior Analysis for SNF Clinics

## Executive Summary

Based on analysis of the CWOW (Clinical Workflow on the Web) patient domain documentation, this report identifies patient modality behaviors relevant to Skilled Nursing Facility (SNF) clinics within the example dialysis care system.

## Patient Modality Types

The CWOW system tracks three major dialysis modalities:

### 1. **ICHD (In-Center Hemodialysis)**
- **Description**: Patients come to a dialysis center typically 3 times per week
- **Session Duration**: 3-4 hours per visit
- **Process**: Patient connected to dialyzer machine that pumps blood through a dialyzer with semipermeable membrane
- **Relevance to SNF**: Most common modality for SNF patients who cannot perform home dialysis

### 2. **PD (Peritoneal Dialysis)**
- **Description**: Home-based dialysis using peritoneal cavity
- **Process**: Fluid placed into peritoneum via catheter, exchanged 4-6 times per day
- **Requirements**: Patient or care partner must manage devices and supplies
- **Relevance to SNF**: Less common for SNF patients due to self-management requirements

### 3. **HHD (Home Hemodialysis)**
- **Description**: Home-based hemodialysis
- **Requirements**: Patient or care partner must be able and willing to manage equipment
- **Relevance to SNF**: Rare for SNF patients due to complexity and training requirements

## SNF-Specific Modality Behavior Patterns

### Primary Modality for SNF Clinics
**ICHD (In-Center Hemodialysis)** is the predominant modality for SNF patients because:

1. **Limited Self-Management Capability**: SNF patients typically cannot manage home dialysis equipment
2. **Medical Supervision Required**: In-center treatment provides necessary medical oversight
3. **Facility-Based Care**: Aligns with SNF care model where patients receive supervised treatment

### Modality Filtering and Patient Management

The CWOW system provides filtering capabilities for patient lists by modality:

**Filter Options:**
- ICHD (In-Center Hemodialysis)
- PD (Peritoneal Dialysis)
- HHD (Home Hemodialysis)

**Filter Behavior:**
- Modalities available for selection depend on modalities assigned to patients in current patient list
- Allows care teams to segment patient populations by treatment type

## Modality Update Workflow

### Key Behaviors When Modality Changes:

1. **Confirmation Message Display**
   - System displays: "Changing the modality will impact other areas of CWOW"
   - Message appears under modality status field

2. **Update Flag for Downstream Systems**
   - System flags modality changes for other functional areas within CWOW
   - Ensures data consistency across integrated systems

3. **Immediate Data Availability**
   - Modality updates are immediately available throughout CWOW
   - Data fed to downstream systems (e.g., Reggie)

4. **Special Handling for PD Transitions**
   - When modality changes FROM Peritoneal Dialysis to another modality:
     - System displays "Modality Change Successful" modal
     - Triggers PD Loss Assessment requirement
     - Assessment added to Patient Care Activity List

### Modality History Tracking

The system maintains comprehensive modality history:

**History Records Include:**
- **Entered Date and Time**: When modality was documented
- **Entered By**: User who made the change
- **Change Details**:
  - New modality: "Added Modality Status - [MODALITY]"
  - Modified modality: "Changed Modality Status - [OLD] to [NEW]"
  - Example: "Changed Modality Status - ICHD to HHD"

**Display Format:**
- Reverse chronological order based on entered date/time
- Sourced from CWOW or Reggie systems
- View-only (no editing of historical records)

## Patient Type Filtering Related to Modality

### Home Early Referral Patient Type
The system includes a special patient type filter with modality-based criteria:

**Selection Criteria (ALL must be true):**
1. Patient Modality must be **PD or HHD**
2. Patient Status must be **Pending or Ready to Treat**
3. Anticipated example Start Date must be **>30 days from current date**

**Implication for SNF Clinics:**
- SNF patients typically do NOT qualify for Home Early Referral
- This filter effectively excludes most SNF patients (who are primarily ICHD)

## Modality-Dependent Clinical Requirements

### Home Early Referral Consent
**Conditional Requirement:**
- **When Required**: Patient has PD/HHD modality AND Anticipated example Start Date > 30 days
- **Behavior**: "Home Early Referral Consent Obtained" question becomes mandatory
- **User Options**: Document response or defer to later
- **Modal Display**: If user clicks Save without answering, system displays "Missing Home Early Referral Consent" modal

**SNF Impact:**
- Not applicable to most SNF patients (ICHD modality)
- SNF patients bypass this requirement

### Kt/V Recalculation
**Modality-Specific Rules:**
- **ICHD Patients**: Optional
- **PD/HHD Patients**: Conditionally required

**SNF Impact:**
- SNF patients (primarily ICHD) have optional Kt/V recalculation

## Data Integration and Downstream Impact

### Systems Integration
Patient modality data integrates with:
1. **Reggie**: Primary data source and consumer
2. **CWOW Clinical Details**: Editable modality management
3. **Downstream Billing Systems**: Modality affects billing codes
4. **Patient Care Activity Lists**: Modality changes trigger assessments

### Data Flow Characteristics
- **Immediate Availability**: Changes available instantly across CWOW
- **Bidirectional Sync**: Data sourced from and fed to Reggie
- **Audit Trail**: Complete history maintained with timestamps and user attribution

## SNF Clinic Operational Implications

### 1. Patient List Management
- **Filter by ICHD**: Primary method to identify SNF-appropriate patients
- **Exclude Home Modalities**: PD/HHD filters identify patients requiring home capability

### 2. Clinical Workflow
- **Simplified Requirements**: ICHD patients have fewer conditional requirements
- **No Home Training**: SNF patients don't require home dialysis education
- **Facility-Based Scheduling**: ICHD modality aligns with SNF operational model

### 3. Care Coordination
- **IDT Assignment**: Can be filtered by modality for team assignments
- **Treatment Day/Shift**: ICHD patients require scheduling coordination
- **Provider Assignment**: Modality-specific provider expertise may be needed

### 4. Quality Metrics
- **Modality-Specific Measures**: Different quality indicators for ICHD vs. home modalities
- **SNF Performance**: Primarily measured against ICHD benchmarks

## Recommendations for SNF Clinic Operations

### Patient Identification
1. **Primary Filter**: Use ICHD modality filter to identify SNF-appropriate patients
2. **Status Monitoring**: Track modality changes that might affect SNF placement
3. **History Review**: Check modality history for patients transitioning to/from SNF

### Workflow Optimization
1. **Simplified Protocols**: Leverage reduced requirements for ICHD patients
2. **Scheduling Integration**: Align ICHD treatment schedules with SNF care plans
3. **Data Validation**: Ensure modality accurately reflects SNF care delivery model

### System Configuration
1. **Default Views**: Configure patient lists with ICHD filter for SNF clinics
2. **Alert Configuration**: Set up alerts for modality changes affecting SNF patients
3. **Reporting**: Create SNF-specific reports filtered by ICHD modality

## Technical Specifications

### Data Fields
- **Field Name**: Patient Modality
- **Field Type**: Text (Radio Buttons in edit mode)
- **Source Systems**: CWOW (editable), Reggie (source/consumer)
- **Valid Values**: ICHD, PD, HHD
- **Required**: Yes (conditionally based on patient status)

### API/Integration Points
- **Update Endpoint**: Modality changes trigger updates to downstream systems
- **History Endpoint**: Modality history accessible for reporting
- **Filter Endpoint**: Patient list filtering by modality

## Conclusion

For SNF clinics within the example system:

1. **ICHD is the predominant modality** - SNF patients primarily receive in-center hemodialysis
2. **Simplified workflows** - ICHD patients have fewer conditional requirements than home modality patients
3. **Effective filtering** - Modality-based filtering enables SNF-specific patient list management
4. **Comprehensive tracking** - System maintains complete modality history for care continuity
5. **Integrated data flow** - Modality changes immediately propagate to all relevant systems

The CWOW system's modality management capabilities support SNF clinic operations by providing clear patient segmentation, streamlined workflows for ICHD patients, and robust data integration for care coordination.

---

## Source Documents
- CWOW-235996 View and Update Clinical Details 17_Baseline 4.0.pdf
- CWOW-244309 View Patient List 06_Baseline 4.0.pdf
- CWOW-226167 Display Patient Banner 10_Baseline 4.0.pdf

## Analysis Date
December 2, 2025

## Repository
cwow-patient-model-spanner.git (develop branch)

# CWOW Census List Use Cases

*Generated from DVA Knowledge Graph on 2025-11-23*

## Overview

The Census List in CWOW is a display list that allows healthcare providers to view and filter patients based on various criteria. It serves as a central tool for managing patient populations across different treatment contexts.

---

## Primary Use Cases

### 1. **Patient Filtering by Type**
The Census List provides filtering capabilities through the "Patient Type" dropdown, enabling users to narrow down patient populations based on specific categories.

#### Available Patient Type Filters:

- **New**
  - Patients new to the facility or starting treatment with example
  - Indicated by "New" icon
  - Typically patients with Regular Chronic Dialysis Begin Date < 91 days from current date

- **AKI (Acute Kidney Injury)**
  - Patients experiencing sudden kidney failure or damage
  - Occurs within hours or days
  - Requires immediate clinical attention

- **IKC (Integrated Kidney Care)**
  - Patients in example's Integrated Kidney Care program
  - Renal population health management division
  - Manages late-stage CKD and ESRD patients requiring dialysis

- **Visiting**
  - Transient patients receiving treatment at the facility
  - Not regular patients at this location
  - Indicated by specific icon

- **Pediatric**
  - Patients ≤ 17 years and 364 days old
  - Pediatric Clinical Standards applied
  - Special care protocols

- **Transitional Care Program**
  - Patients enrolled in transitional care services
  - Bridge between care settings

- **Regular Chronic Dialysis > 90 Days**
  - Established dialysis patients
  - Regular treatment schedule
  - > 90 days since dialysis began

- **Home Early Referral** *(New Feature)*
  - **Criteria:**
    - Patient Modality: PD (Peritoneal Dialysis) OR HHD (Home Hemodialysis)
    - Patient Status: Pending OR Ready to Treat
    - Anticipated example Start Date: > 30 days from current date
  - **Purpose:** Identify patients suitable for early home dialysis planning

---

### 2. **Treatment Shift Filtering**

**Feature:** Treatment Shift Filter (FREQ-343204)

**Functionality:**
- Filter patients by specific treatment shifts/time slots
- Multi-select capability
- Available shifts determined by facility's patient schedules
- Helps staff organize daily treatment schedules

**Use Case:**
- View patients scheduled for morning shift
- Plan staffing based on shift census
- Coordinate treatment resources by time slot

---

### 3. **Patient Status Monitoring**

The Census List integrates with patient status tracking to display:

#### Active CWOW Status Categories:
- **Active - Currently Treating/Training**
  - Patient is Active
  - Criteria to Treat met
  - Documented dialysis treatment or training at facility

- **Active - Pending**
  - Patient is Active at facility
  - Criteria to Treat NOT yet met

- **Active - Ready to Treat/Train**
  - Patient is Active at facility
  - Criteria to Treat met
  - Ready for treatment initiation

---

## Patient Information Display

### Census List Columns
The Census List displays key patient identifiers and status information for quick reference and decision-making.

### Patient Banner Integration
When a patient is selected from the Census List, the Patient Banner displays:

#### Core Demographics:
- Patient Name
- MPI (Master Patient Index) number
- Age
- Date of Birth
- Gender (Male/Female)

#### Contact Information:
- Primary Phone Number with type (Home, Work, Mobile)
- "No Phone" if not documented
- "No Primary Number Selected" if exists but not marked primary

#### Clinical Information:
- Primary Nephrologist (abbreviated name, hover for full name + NPI)
- Allergies
- Medication Refusals

#### Visual Indicators (Icons):
- **New Icon**: New patient or RCD Begin Date < 90 days
- **Birthday Cake**: Birthday today or yesterday
- **DNR Icon**: Active Do Not Resuscitate order
- **Hepatitis B Icon**: Positive Hepatitis B status
- **Fall Risk Icon**: Patient has fall risk score
- **MDRO Icons**: 
  - C. auris problems
  - CRE (Carbapenem-Resistant Enterobacteriaceae) problems
- **Diabetic Icon**: Diabetic patient
- **Clinical Study Icon**: Enrolled in clinical study
- **AKI Icon**: Acute Kidney Injury
- **IKC Icon**: Integrated Kidney Care patient
- **In-Treatment Icon**: Currently receiving treatment

---

## Workflow Integration

### Typical Census List Workflows:

1. **Daily Census Review**
   - Filter by shift to view scheduled patients
   - Review patient status changes
   - Identify new admissions or discharges

2. **Home Dialysis Planning**
   - Use "Home Early Referral" filter
   - Identify candidates for PD/HHD
   - Plan early intervention and training

3. **Special Population Management**
   - Filter by Pediatric to apply age-specific protocols
   - Filter by Visiting to manage transient patients
   - Filter by AKI for urgent care coordination

4. **Program-Specific Views**
   - IKC patients for integrated care management
   - Transitional Care Program for care transitions
   - Clinical Study participants for research coordination

---

## Technical Implementation

### Patient Status Determination Logic:
Uses SQL CASE statements with flags:
- `VISITING_FLAG` → "Visiting" status
- `IKC_FLAG` → "IKC" status
- `REGULAR_CHRONIC_DIALYSIS_BEGIN_DATE` duration → "New" vs "Regular Chronic Dialysis > 90 Days"
- `TRANSITIONAL_CARE_PROGRAM_FLAG` → "Transitional Care Program"
- `PEDIATRIC_FLAG` → "Pediatric"

### Filter Behavior:
- Multi-select capability for most filters
- Real-time filtering of patient list
- Persists user preferences across sessions
- Integrates with facility-specific configurations

---

## References

- **CWOW-244309**: View Patient List 06 (Census List functionality)
- **CWOW-226167**: Display Patient Banner 10 (Patient information display)
- **CWOW-235996**: View and Update Clinical Details 17 (Clinical data integration)
- **FREQ-882358**: Patient Type Filter - Home Early Referral
- **FREQ-343204**: Display Patient List: Shift (Treatment Shift Filter)

---

## Summary

The CWOW Census List serves as a comprehensive patient management tool that enables:
- **Efficient patient filtering** by type, status, and shift
- **Quick access** to critical patient information
- **Workflow optimization** for different care scenarios
- **Population health management** across diverse patient categories
- **Visual indicators** for rapid clinical decision-making

The integration with the Patient Banner provides seamless access to detailed patient information, making the Census List a central hub for daily clinical operations in dialysis facilities.

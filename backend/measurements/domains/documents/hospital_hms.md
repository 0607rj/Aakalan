# Hospital Management System — Requirement Document

Version 1.0 · Synthetic measurement document for Aakalan (not a real tender)

## 1. About the hospital

1.1 Sanjeevani Hospital is a 180-bed multi-speciality hospital in Nagpur with an outpatient department (OPD), wards, a pharmacy and a pathology lab.
1.2 Today registrations, bills and stock are kept in paper registers and Excel sheets. The management wants one web system used by all departments.
1.3 Insurance (TPA) claim processing is handled by an outside agency and is out of scope.

## 2. Users

2.1 The system will be used by patients, front-desk staff, doctors, nurses, pharmacists, lab technicians, billing staff and the hospital administrator.
2.2 Doctors and staff shall sign in with their existing hospital Microsoft accounts (single sign-on through the hospital's Active Directory).

<!-- page -->

## 3. Functional requirements

3.1 Patients shall book OPD appointments online with a chosen doctor and time slot, and front-desk staff shall book walk-in visits.
3.2 The system shall send an SMS reminder to the patient a day before the appointment.
3.3 Patients shall be able to pay the consultation fee online when booking.
3.4 Doctors shall record each visit's diagnosis, notes and prescriptions in the patient's electronic medical record, and see the patient's past visits.
3.5 Nurses shall see which beds are free in each ward, admit patients to a bed, transfer them and discharge them.
3.6 Doctors shall order lab tests; lab technicians shall enter results, which appear in the patient's record.
3.7 The pharmacy shall keep stock of medicines with batch numbers and expiry dates, and get an alert when stock is low.
3.8 Billing staff shall create patient bills with GST for consultations, bed charges, lab tests and medicines, and print receipts.
3.9 Patients shall upload old reports (PDF or photos) to their record.
3.10 The administrator shall see dashboards of daily OPD visits, bed occupancy, collections and pharmacy stock value.
3.11 Patient records of the last five years shall be moved from the existing Excel sheets into the new system.
3.12 Screens shall be available in English and Hindi.

<!-- page -->

## 4. Later phases and exclusions

4.1 Video consultation (telemedicine) is planned for phase 2 and is not part of this work.
4.2 A separate mobile app is not required; the web system shall work on phones and tablets.
4.3 Connecting the lab analyser machines directly to the system is not required in this phase.

## 5. Support and hosting

5.1 The vendor shall host the system on an Indian cloud and provide support for two years after go-live during hospital office hours.
5.2 Patient data shall be kept confidential and access shall be logged.

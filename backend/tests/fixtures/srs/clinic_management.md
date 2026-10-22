# Clinic Management System — Software Requirements Specification

Version 1.0 · Synthetic test document for Aakalan (not a real tender)

## 1. Overview and objectives

1.1 CareFirst runs three small clinics and wants one web system for its patients and staff.
1.2 The objective of the first release is that patients book and pay for a visit without calling the front desk, and that the owner sees each day's visits and collections.
1.3 The hospital group currently uses an ERP for accounting and pharmacy purchases.
1.4 Integration with that ERP is out of scope for this release.

## 2. User roles and permissions

2.1 There are four roles: patient, doctor, receptionist and clinic administrator.
2.2 Each role shall see only its own screens; this is the standard account behaviour of the system.

<!-- page -->

## 3. Functional requirements

3.1 Patients shall create an account with their name, phone number and email address.
3.2 Each doctor profile shall show qualifications, consultation timings and fees.
3.3 Patients shall book appointments with a chosen doctor and time slot.
3.4 The system shall send email reminders to the patient one day before each appointment.
3.5 Patients shall pay online through a payment gateway when they book.
3.6 The clinic administrator shall see a dashboard of the day's appointments and collections.

## 4. Non-functional requirements

4.1 The system shall be available 99.5% of the time during clinic hours.
4.2 Pages shall open within three seconds for up to 200 people using it at the same time.

## 5. Security and data

5.1 Staff and patients sign in with an email address and a password.
5.2 Multi-factor authentication is not required for the first release.
5.3 Patient records shall be protected as the DPDP Act requires.

<!-- page -->

## 6. Integrations and dependencies

6.1 The payment gateway account is opened and paid for by CareFirst.
6.2 Emails are sent through CareFirst's existing email provider.

## 7. Future phase

7.1 Phase 2 may add WhatsApp messages for appointment reminders.

## 8. Acceptance criteria

8.1 A patient can book a slot, pay and receive a reminder email the day before.
8.2 The administrator's dashboard totals match the day's paid bookings.

## 9. Included and not included in this release

9.1 Included: accounts, doctor profiles, appointment booking, online payment, email reminders and the administrator's dashboard.
9.2 Not included in this release: ERP integration, multi-factor authentication and WhatsApp messages.

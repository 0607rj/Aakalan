# Digital Lending Platform — Requirement Document

Version 1.0 · Synthetic measurement document for Aakalan (not a real tender)

## 1. Background

1.1 Sahyog Finance is an RBI-registered NBFC giving small business loans of ₹50,000 to ₹10 lakh.
1.2 Loan applications are today collected on paper by field officers. Sahyog wants customers to apply online and the credit team to decide faster.
1.3 The core loan accounting system (an existing product) stays as it is; this project is the front end for applications and approvals.

## 2. Users

2.1 Applicants, field officers, credit analysts, credit managers, the operations team and the administrator will use the platform.
2.2 Employees shall sign in with their company Microsoft Azure AD accounts.

<!-- page -->

## 3. Functional requirements

3.1 Applicants shall apply for a loan online through a web form and an Android and iOS app, and save a draft to finish later.
3.2 Applicants shall verify their identity with Aadhaar e-KYC and fetch their PAN from DigiLocker.
3.3 Applicants shall upload documents: bank statements, GST returns and shop photos.
3.4 The system shall read the uploaded bank statements automatically and pull out monthly credits, debits and balances.
3.5 The system shall fetch the applicant's credit score from a credit bureau (CIBIL) through its API.
3.6 A rules engine shall score each application from the bureau score, bank statement figures and business age, with rules the credit manager can change without a developer.
3.7 Each application shall go through credit analyst review and credit manager approval; loans above ₹5 lakh also need a second manager.
3.8 Approved applicants shall sign the loan agreement online with Aadhaar e-Sign.
3.9 Applicants shall set up an e-NACH mandate so that EMIs are collected from their bank account every month.
3.10 Borrowers shall be able to pay an overdue EMI online through a payment gateway.
3.11 Applicants shall get SMS and email updates at each step of their application.
3.12 Sign-in for applicants shall use a one-time password sent to their mobile number.
3.13 Every change to an application shall be recorded in an audit trail.
3.14 Management shall see dashboards of applications, approval rates, disbursed amounts and turnaround times.

<!-- page -->

## 4. Compliance and exclusions

4.1 The platform shall follow the RBI digital lending guidelines and pass a security audit before go-live.
4.2 A wallet or UPI payments app is out of scope.
4.3 Field officer tools will be built in a later phase.

## 5. Support

5.1 The vendor shall provide support and maintenance for three years after go-live.

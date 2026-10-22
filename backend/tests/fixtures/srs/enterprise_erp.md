# Enterprise ERP — Software Requirements Specification

Version 1.0 · Synthetic test document for Aakalan (not a real tender)

## 1. Overview and objectives

1.1 Northwind Group wants one ERP for purchasing, stores, finance and HR across its companies.
1.2 Group companies shall share one installation as a multi-tenant system with separate books.

## 2. User roles and permissions

2.1 Access shall be role based: requester, approver, storekeeper, accountant, HR officer and administrator.

## 3. Functional requirements

3.1 Purchase requests and purchase orders shall follow a multi-level approval workflow.
3.2 The stores module shall manage inventory with stock in and stock out entries for each warehouse.
3.3 The finance module shall raise invoices and record receipts.
3.4 Supporting documents shall be kept in a document repository with version history.
3.5 Purchase orders above the approval limit shall carry a digital signature.
3.6 The system shall keep an audit trail of every approval and every change to master data.
3.7 Management shall see MIS reports and pendency reports for each department.
3.8 Vendors shall receive approved purchase orders through webhooks.
3.9 Bank statements shall be loaded every night through a scheduled import.
3.10 The legacy payroll system shall be connected so that HR records stay in step.

<!-- page -->

## 4. Identity

4.1 Employees shall sign in through single sign-on with the group's Active Directory.

## 5. Non-functional requirements

5.1 The system shall be available 99.95% of the time with a disaster recovery site.
5.2 Support shall be provided 24x7.
5.3 The system shall be hosted in a MeitY empanelled cloud.

## 6. Items that need clarification

6.1 The number of legal entities to be configured is to be decided.
6.2 Statutory payroll rules for each state shall be configured as per requirement.

## 7. Not priced by a standard catalog

7.1 The source code and intellectual property shall be handed over to Northwind at the end of the contract.

## 8. Acceptance criteria

8.1 A purchase order passes every approval level, is signed and reaches the vendor by webhook.
8.2 Every approval appears in the audit trail with the user and time.

## 9. Included and not included in this release

9.1 Included: purchasing with approvals, stores, finance, documents, digital signatures, audit trail, reports, vendor webhooks, the nightly bank import, payroll connection and single sign-on.

# AI Document Processing SaaS — Software Requirements Specification

Version 1.0 · Synthetic test document for Aakalan (not a real tender)

## 1. Overview and objectives

1.1 DocuSense lets businesses upload invoices and contracts and get the key fields back as data.
1.2 Each customer organisation shall have its own isolated workspace in a multi-tenant system.

## 2. User roles and permissions

2.1 Roles: workspace owner, member and DocuSense administrator.

## 3. Functional requirements (current release)

3.1 Users shall upload documents in PDF or image format.
3.2 The system shall extract fields from each uploaded document using an external AI provider's language model.
3.3 Each plan shall have a monthly limit on pages processed; uploads beyond the limit are blocked until the next month.
3.4 Customers shall pay a monthly subscription through a payment gateway with recurring billing.
3.5 The system shall email invoices for every payment.
3.6 Customers shall receive extraction results through webhooks.
3.7 Two-factor authentication shall be available for workspace owners.

<!-- page -->

## 4. External AI provider dependency

4.1 The AI provider's account and API key are supplied and paid for by DocuSense.
4.2 When the API key is missing or the provider cannot be reached, documents shall wait in a queue and the user shall see that processing is delayed. The system must never report a result it did not receive.

## 5. Non-functional requirements

5.1 The platform shall be available 99.9% of the time.
5.2 Uploaded documents shall be deleted 30 days after processing.

## 6. Security and data

6.1 Documents shall be encrypted at rest; data protection follows the DPDP Act.

## 7. Planned enhancements

7.1 A public API for bulk uploads may be added in a later phase.
7.2 A chatbot that answers questions about a customer's documents is a future enhancement.

## 8. Acceptance criteria

8.1 A paying customer uploads an invoice and receives its fields by webhook within five minutes.
8.2 With no AI provider key configured, an upload stays queued and is shown as delayed.

## 9. Included and not included in this release

9.1 Included: accounts, document upload, AI extraction, usage limits, subscriptions, invoices, webhooks and two-factor authentication for owners.
9.2 Not included: the bulk-upload public API and the document chatbot.

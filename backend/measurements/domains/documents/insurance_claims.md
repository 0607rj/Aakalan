# Motor Claims Platform — Requirement Document

Version 1.0 · Synthetic measurement document for Aakalan (not a real tender)

## 1. Background

1.1 Suraksha General Insurance sells motor insurance through agents and online, and settles about 4,000 motor claims a month.
1.2 Claims are reported on calls and email today; surveyors send photos on WhatsApp. The company wants one platform for claim intake, survey and settlement.
1.3 Policies are kept in the company's existing policy administration system, which stays as it is.

## 2. Users

2.1 Policyholders, garages, surveyors, claim handlers, claim managers and the fraud team will use the platform.
2.2 Employees shall sign in with the company's Azure Active Directory accounts.

<!-- page -->

## 3. Functional requirements

3.1 Policyholders shall report a claim online with the policy number, accident details and place, and upload photos of the damage, the driving licence and the FIR where needed.
3.2 The platform shall check the policy number and cover against the policy administration system through its API.
3.3 The system shall read the uploaded driving licence and garage estimate automatically and fill in the fields.
3.4 The system shall look at the damage photos and suggest which parts of the vehicle are damaged.
3.5 Claim handlers shall assign a surveyor by location; surveyors shall see their assigned claims on a map.
3.6 Surveyors shall submit their survey report with photos and the assessed amount.
3.7 Each claim shall be approved by the claim handler; claims above ₹2 lakh also need the claim manager's approval.
3.8 Fraud rules shall flag claims for the fraud team, for example a claim within 30 days of the policy start or several claims on the same vehicle.
3.9 Settlement amounts shall be sent to the payments team's existing bank file system; no payment gateway is needed.
3.10 Policyholders shall get SMS and email updates at each stage and can see their claim status online.
3.11 Policyholders shall be able to raise a complaint about a claim and track it.
3.12 Every action on a claim shall be kept in an audit trail.
3.13 Managers shall see dashboards of claims reported, settled, pending, average settlement time and fraud flags.

<!-- page -->

## 4. Exclusions and compliance

4.1 A chatbot for policyholders is planned for a later phase.
4.2 The platform shall meet IRDAI cyber security guidelines and pass a VAPT audit by a CERT-In empanelled auditor before launch.

## 5. Support

5.1 The vendor shall support the platform for three years, during business hours.

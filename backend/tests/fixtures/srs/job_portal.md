# Job Portal — Software Requirements Specification

Version 1.0 · Synthetic test document for Aakalan (not a real tender)

## 1. Overview and objectives

1.1 HireRight wants a job portal where companies post jobs and candidates apply.
1.2 Recruiters currently receive resumes by email and track them in spreadsheets.

## 2. User roles and permissions

2.1 Every user has one role: candidate, recruiter or administrator. This is standard account functionality.
2.2 Advanced permissions, such as recruiter teams with custom permission sets, are not required in this release.

## 3. Functional requirements

3.1 Recruiters shall post jobs with title, location, salary range and closing date.
3.2 Candidates shall submit an online application for each job they choose.
3.3 Candidates shall upload documents such as their resume and certificates.
3.4 Candidates shall find jobs through advanced search with filters for location and salary.
3.5 Recruiters shall move each application through a workflow: applied, shortlisted, interviewed, offered.
3.6 The system shall send email alerts to candidates when their application status changes.
3.7 Recruiters shall see MIS reports of applications per job and per stage.
3.8 Candidates shall verify their phone number with an OTP when they register.
3.9 Candidates shall be able to sign in with Google.

<!-- page -->

## 4. Non-functional requirements

4.1 The portal shall be available 99.5% of the time.
4.2 The portal shall be hosted on Amazon Web Services.

## 5. Security and data

5.1 Resumes shall be visible only to the recruiters of the jobs a candidate applied for.

## 6. Integrations

6.1 Sign in with Google is the only external sign-in method.
6.2 Integration with LinkedIn is planned for a later phase.

## 7. Acceptance criteria

7.1 A candidate can register with an OTP, apply with a resume and receive an email alert on each status change.

## 8. Included and not included in this release

8.1 Included: job posting, applications, resume upload, search, the recruiter workflow, email alerts, OTP check, Google sign-in and reports.
8.2 Not included: advanced recruiter permissions and LinkedIn integration.

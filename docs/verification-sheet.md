# Verification sheet: six judgement calls (for your decision)

Date: 2026-10-24. No code change. No AI call: the quotes come from the tender files read with
the app's own parser, and the prices from the local engine.

**How to read this sheet**

- **Quotes** are copied exactly from the tender text, including its typing errors. Line breaks
  are joined.
- **Page** is the page as the app counts it: the physical PDF page. For the IOB tenders the
  printed page number is one lower. Canara's `att08` is a Word file, so its pages are the app's
  approximate 3,000-character pages.
- **Engine** is the saved reading in `backend/tests/fixtures/readings/`, made by a stand-in
  model, not the production call. **Hand** is the hand reading in
  [`answer-accuracy-8.md`](answer-accuracy-8.md).
- **Prices** are the production path (B+doc). Each one is the likely (P50) price without AI tools
  in ₹ Cr, with only that answer changed. The ratio is that price ÷ the published price in
  today's money. The range is P10-P90 as a ratio.
- **Staff answers on the form are people for every support year.** The form can't say "for 2
  years" or "per shift".
- No verdicts are given. The line under each call is for yours.

---

## 1. iob-chatbot (IOB Chatbot and WhatsApp Banking, `att01.pdf`)

### 1a. Onsite staff

| | Answer | Source |
|---|---|---|
| Engine | **1** | clause 29, p.57 (the onsite developer) |
| Hand | **5** | onsite developer (p.57) + onsite L2 (p.103) + L1, L2, L3 one per shift (p.115), all counted as onsite heads for 5 years |

**The clauses**

> **Annexure I, item 29, p.57:** "The bidder has to provide costing for one onsite developer who
> will be responsible for customization, parameterization and designing workflows. Any
> replacement of developer should have concurrence of bank."

> **Service levels, p.103:** "Onsite support engineer (L2 level) for initial 1 year for smooth
> rollout, issue redressal, handholding, training, etc. Thereafter rate contract for L2 level
> engineer."

> **Service levels, p.103:** "Time bound problem addressing team (onsite/ offsite) for the
> complete contract period."

> **Commercial bid, Table VI "Managed Services Resource Cost", p.115:** rows "1.a … L1 1",
> "1.b L2 1", "1.c … L3 1", product "CHATBOT AND WHATSAPP BANKING SOLUTION – FOR REQUIRED
> RESOURCE PER SHIFT COST"; columns "PER YEAR COST (PRICE VALID FOR 5 YEARS CONTRACT TERM)",
> "QTY". Note under it: "* Bank at its own discretion may ask any number of resources to
> deployed based on business requirements and the resources shall be required to work on 24*7
> basis."

**Other clauses that add context or conflict**

> **VII. Help Desk Requirements, p.60:** "Bank reserves the rights to decide on Resource headcount
> as per business requirements. Backup arrangement for personnel must be fully taken care by the
> SB. Managed services shall be billed based on actual headcount required in each role as sought
> by the bank from time to time irrespective of the number of distinct resources deployed to
> achieve the headcount for a role."

> **Managed Service - Resource Experience and Skill, p.61:** L1 1 year's experience, L2 3 years,
> trained and certified.

> **C3.1, p.84:** "Service provider shall provide requisite production support including L1, L2,
> L3 support"

> **Item 10, p.54:** "Bidder has to provide on-Site maintenance of Chatbot, API management and
> related products with customization, change management, addition of new reports as required and
> desired by the Bank."

> **Item 6, p.54:** "Bidder should ensure availability of technical expertise and SMEs to extend
> continuous support to the on-site team."

- **Not stated anywhere:** where the L1, L2 and L3 sit, or how many shifts there are.
- **The engine noticed** the gap and drafted a pre-bid query (p.60, VII): "Please state the
  number of L1, L2 and L3 resources per shift, the number of shifts, and which resources must sit
  onsite and for how long."

**About the "2.42 people per seat" figure.** No 2.42 figure appears in our work or in the tender.
The number used is **4.2 people per round-the-clock seat**:
- It comes from our parameters (`helpdesk_coverage_fte` 24x7 = 4.2, parameters v23, a
  placeholder, OPEN_QUESTIONS 26), not from a tender clause.
- It is 168 hours a week ÷ 40 hours a person.
- The tender clause it would apply to is Table VI on p.115 (quoted above): one L1, one L2 and one
  L3 "per shift", "on 24*7 basis".
- The hand call of 5 counted each per-shift seat as **1** person, not 4.2.

**Price of each choice** (published ₹6.12 Cr)

| Choice | P50 ₹ Cr | Ratio | Range |
|---|---:|---:|---|
| Engine: onsite 1 | 4.00 | 0.65 | 0.34-1.06 |
| Onsite 2 (developer + L2) | 4.87 | 0.80 | 0.41-1.27 |
| Hand: onsite 5 (each per-shift seat = 1 person) | 7.51 | 1.23 | 0.63-1.90 |
| Onsite 2 + 3 seats × 4.2 = 14.6 people onsite | 15.72 | 2.57 | 1.31-3.93 |
| Onsite 2 + the 3 seats × 4.2 as offsite support staff | 14.64 | 2.39 | 1.22-3.67 |

The onsite L2 is "for initial 1 year". Every row above prices it for all 5 years, because the
form can't say otherwise.

**Your verdict, onsite staff:** ______________________ (right / wrong / tender doesn't say)

### 1b. Support hours

| | Answer | Source |
|---|---|---|
| Engine | **always** (round the clock, staffed in shifts) | Table VI note, p.115 |
| Hand | **always** | p.103, p.115 |

**The clauses**

> **Table VI note, p.115:** "the resources shall be required to work on 24*7 basis."

> **Service levels, p.103:** "The Vendor should have 24X7X365 monitoring, escalation and
> resolution infrastructure."

> **Service levels, p.103:** "Application availability will be 99.5% on 24x7x365."

> **Annexure I, p.49:** "24x7 monitoring to log and capture customer conversation data." (a
> system feature, not staffing)

**Price of each choice** (onsite 1 as the engine read; published ₹6.12 Cr)

| Choice | P50 ₹ Cr | Ratio | Range |
|---|---:|---:|---|
| Engine and hand: always | 4.00 | 0.65 | 0.34-1.06 |
| On call | 2.71 | 0.44 | 0.23-0.68 |
| Office hours | 2.55 | 0.42 | 0.22-0.64 |

**Your verdict, support hours:** ______________________ (right / wrong / tender doesn't say)

---

## 2. iob-website: 5 offsite support staff (IOB corporate website, `att01.pdf`)

| | Answer | Source |
|---|---|---|
| Engine | **none** (the reading didn't find it) | – |
| Hand | **5**, for all support years | 6.1 F (b), p.71 |

**The clause**

> **6.1 F "RESOURCE/s DURING WARRANTY AND AMC PERIOD", p.71:** "Extensive support team is required
> after "Go-Live". The resources required are as under: a. On-Site support team - 1 resource must
> be available at the Bank premises at all times to provide (onsite resources work timing will be
> as per the Bank timings normally from 9 AM to 7 PM) support and to coordinate with off-site team
> when required. b. Off-Site team - Team of not less than 5 people consisting of developer,
> designer, hosting / server admin, tester and quality assurer."

**Other clauses that add context or conflict**

> **Same page, just above F (the ATS support list), p.71:** "24*7 support for website related
> malfunctions as defined in the RFP, SLAs and ability to log requests online." and "One onsite
> resource must be available from 8:00 AM to 10:00 PM on all days."

> **6.1 F, p.71:** "The Facility Management Services i.e Onsite Technical Support is required for
> the entire duration of the project."

> **Commercial bid, Format 8.13 Table I, p.115:** one line per year, "Cost of ATS (Annual Technical
> Support) / AMC (Annual Maintenance Contract) –Maintenance of Website – 2nd year" (to 5th year).
> There is **no separate line for the offsite team**; it sits inside the ATS/AMC price.

- **Not stated:** whether the 5 offsite people are full time on this bank, or a shared team that
  is available when needed.
- **The onsite hours conflict** (8 AM-10 PM vs 9 AM-7 PM, both on p.71). The engine raised a
  pre-bid query on it.

**Price of each choice** (published ₹4.54 Cr; the engine's support hours "on call")

| Choice | P50 ₹ Cr | Ratio | Range |
|---|---:|---:|---|
| Engine: no support staff | 2.94 | 0.65 | 0.36-0.96 |
| Hand: support staff 5, full time, every support year | 6.06 | 1.34 | 0.74-1.99 |
| Support staff 5 and hours "always" | 7.41 | 1.63 | 0.89-2.45 |
| No support staff, hours "always" | 4.24 | 0.93 | 0.52-1.44 |

**Your verdict, 5 offsite support staff:** ______________________ (right / wrong / tender doesn't say)

---

## 3. ewaste: the two BoQ staff lines added together (CPCB EPR E-Waste portal, `att01.pdf`)

| | Answer | Source |
|---|---|---|
| Engine | support staff **1**, onsite **1** | 5.9 (iii) p.26 for support; 5.8 (i) p.26 for onsite |
| Hand | support staff **4** (= 2 + 2), onsite 2 | BoQ items 8 and 10(b), p.55; onsite from 10(a) |

**The two BoQ lines** (Annexure-II, Financial Bid Form, BoQ with Price Schedule, p.55)

> **Item 8:** "Helpdesk support comprising of 2 professionals for resolving user level queries with
> the applicant for 2 years" (quantity "As per requirement")

> **Item 10(b):** "Annual cost of technical support center with 2 nos of developers till atleast 2
> years after go live" (quantity column: "02")

The quantity "02" in 10(b) could be the number of years or the number of developers. The text
doesn't say which.

**Other clauses that add context or conflict**

> **BoQ item 10(a), same page:** "1st year AMC cum development support along with cost of cloud
> environment for UAT and development, along with 2 developers at CPCB Head Office and remote
> support from vendor", then years 2 to 5: "along with 1 developer at CPCB head office and remote
> support from vendor"

> **1.0 Project Duration (h), p.51:** "Service desk operation for two years from the date of Go
> Live! Go Live! (Twodevelopers during warranty and 1st year AMC and One developer during rest of
> 4 years AMC)"

> **5.4 Hand holding support, p.23:** "Provide 24x7 support through a helpdesk to stakeholders to
> manage its connectivity."

> **5.4, p.24:** "The services require posting a senior IT Expert with technical, managerial and
> business analyst experience and two IT Developers with programming experience working remotely."

> **5.8 (i), p.26:** "One programmer has to be deployed at CPCB on five days a week in office hours
> at CPCB for the entire project duration."

> **5.9 (iii), p.26** (the engine's support-staff source): "To maintain the system for five years
> (01yr warranty+ 05yr Maintenance including development) by assistance and deploying at least one
> programmer / IT Engineer at CPCB."

> **5.6 Maintenance, Training & Security, p.25:** "The full stack developer placed in the CPCB HO will continue to work for the
> project during AMC period also."

- **Both BoQ lines are for 2 years**, not the full support period.
- **The two lines may be the same people.** "Helpdesk support … 2 professionals" (item 8) and
  "technical support center with 2 nos of developers" (item 10(b)) could overlap with each other.
  Both could also overlap with the "two IT Developers … working remotely" (5.4).
- **The engine raised a pre-bid query** on the number and place of staff (5.4, 5.8, 1.0(h)).

**Price of each choice** (published ₹8.10 Cr; onsite 1 as the engine read)

| Choice | P50 ₹ Cr | Ratio | Range |
|---|---:|---:|---|
| Engine: support staff 1 | 5.60 | 0.69 | 0.40-1.06 |
| Support staff 2 (one line, all support years) | 5.74 | 0.71 | 0.41-1.08 |
| Hand: support staff 4 (both lines, all support years) | 7.52 | 0.93 | 0.52-1.39 |
| Both lines, for their stated 2 years only (96 person-months ≈ 1.6 people on average) | 5.60 | 0.69 | 0.40-1.06 |

The last row doesn't move the price: the support work the engine already prices covers 1.6
people (stated staff are the least support labour, OPEN_QUESTIONS 157).

**Your verdict, adding items 8 and 10(b) together:** ______________________ (right / wrong / tender doesn't say)

---

## 4. tyre: 24x7 support (CPCB EPR Waste Tyre portal, `att01.pdf`)

| | Answer | Source |
|---|---|---|
| Engine | **not set** (the form's usual answer, office hours); a pre-bid query raised on the conflict | – |
| Hand | **always** (round the clock, staffed) | 7.0, p.17 |

**The clause**

> **7.0 REQUEST FOR PROPOSAL (RFP), p.17:** "The selected organization shall also be responsible for
> the complete turnkey operation of the IT systems to ensure 24 x 7 operations."

**Other clauses that add context or conflict**

> **6.8 Manpower Deliverables (i), p.17:** "Three persons (programmer cum coordinator) has to be
> deployed at CPCB on five days a week in office hours at CPCB for the entire project duration."

> **6.4 Hand holding support for portal functionality, p.15:** "Provide support through a help desk
> to stakeholders to manage its connectivity." (no hours stated; the e-waste tender's same line
> says "24x7")

> **6.4, p.15:** "The services are required to be provided from the office of Central Pollution
> Control Board (CPCB) in Delhi."

> **16.0 Project Duration (h), p.35:** "Service desk operation for six years from the date of Go
> Live! (Two developers during warranty and 1st year AMC and One developer during rest of 4 years
> AMC)"

> **Annexure-II Financial Bid Form, item 12(b), p.37:** "Annual cost of technical support center
> with 3 nos of developers for 5 years after go live" (quantity "03")

- **The tender never says** "24x7 support", "24x7 helpdesk" or shifts. "24 x 7 operations" is
  the only round-the-clock wording.
- **The engine's pre-bid query** (7.0, p.17): "Clause 7.0 asks for 24 x 7 operations while
  clause 6.8 asks for staff five days a week in office hours. Please state the required support
  hours and who must be available outside office hours."

**Price of each choice** (published ₹2.39 Cr; the 3-month deadline is dropped, as it can't be met)

| Choice | P50 ₹ Cr | Ratio | Range |
|---|---:|---:|---|
| Engine: not set (office hours) | 6.73 | 2.82 | 1.57-4.15 |
| On call | 6.95 | 2.91 | 1.62-4.29 |
| Hand: always (staffed round the clock) | 8.63 | 3.61 | 2.02-5.42 |

**Your verdict, 24x7 support:** ______________________ (right / wrong / tender doesn't say)

---

## 5. canara: 24x7 support and helpdesk (Canara Bank chatbot, `att08.docx` + `att01.pdf`)

| | Support hours | Helpdesk | Source |
|---|---|---|---|
| Engine | **on call** | **no** | `att08` p.57: support office in Bengaluru and Mumbai "for 24x7 supports" |
| Hand | **always** | **yes** | `att08` p.4 onsite resources 365x24x7; p.11 complaints 24x7x365 |

**The clauses** (`att08.docx`, the GeM bid terms)

> **"Onsite Resources", p.4:** "The selected bidder has to provide onsite resources on 365x24x7 and
> should have OEM Certification for the proposed solution with minimum 5 years of Implementation,
> Operations & Hands-on experience."

> **p.11 (support terms):** "The bidder shall provide centralized complaint booking/lodging facility
> to the bank and the dash board, if available, shall be provided to the Bank. The method of
> booking complaints shall be E-mail, Toll-free no, on line portal, web, etc."

> **"Local support", p.11:** "The bidder will be responsible for attending complaints during all
> hours 24x7x365 basis of contract period."

> **"Local support", p.11:** "The support should be provided over phone, E mail web based, in
> person, if required. All escalations will be attended / responded-promptly not later than 30
> minutes of reporting."

> **Eligibility criteria, p.57** (the engine's source): "The applicant shall have support office in
> Bengaluru and Mumbai for 24x7 supports."

**Other clauses that add context or conflict**

> **"Uptime", p.4:** "The selected bidder shall guarantee a 24x7x365 availability with monthly
> uptime of 98.00 % for the solution"

> **p.5:** "Response Time shall be 2 hours and MTTR shall be 4 hours."

> **Commercial bid, Table D "Charges for Offsite Resources"** (heading and note on p.33; the row
> on p.58): "Dedicated Offsite Support charges*", No. of Months **60**, No. of Resources **1**.
> Note: "The quantity mentioned in Table-D is indicative only. *Bank at its discretion can avail
> onsite / offsite resources based on the requirement. Bank can at its discretion decide the
> number of resources in case of Onsite/Offsite support."

> **Payment terms, p.46:** "Dedicated Onsite/Offsite Support charges | 100% | Monthly in arrears
> after calculating the number of day's resources work"

> **Penalties 1.3.1 (`att03.pdf` p.2, also `att08` p.9):** "Penalties/liquidated damages for
> Onsite resources: In case the resources goes on leave/absent, replacements having equivalent or
> more experience and qualification has to be arranged…"

**What doesn't line up:**
- The only priced staff table names **1 offsite** resource for 60 months.
- The terms ask for **onsite** resources "on 365x24x7".
- One person can't staff round the clock.
- The engine raised pre-bid queries on the number of onsite resources (1.3.1) and on Table D.

**Price of each choice** (published ₹5.77 Cr)

| Choice | P50 ₹ Cr | Ratio | Range |
|---|---:|---:|---|
| Engine: on call, helpdesk no | 2.71 | 0.47 | 0.24-0.69 |
| Always, helpdesk no | 2.71 | 0.47 | 0.24-0.69 |
| On call, helpdesk yes | 3.26 | 0.57 | 0.30-0.87 |
| Hand: always, helpdesk yes | 4.56 | 0.79 | 0.42-1.26 |
| Office hours, helpdesk no | 2.69 | 0.47 | 0.24-0.69 |

**Support hours only change the price when the helpdesk is "yes"**, because the hours set how
many people the helpdesk needs. None of these rows add the Table D resource; that is the
separate onsite or support staff answer (hand: onsite 1).

**Your verdict, support hours:** ______________________ (right / wrong / tender doesn't say)

**Your verdict, helpdesk:** ______________________ (right / wrong / tender doesn't say)

---

## 6. meghalaya: build type "ready product" (ONE Meghalaya citizen services, `att05.pdf`, `att09.pdf`, `att13.pdf`)

| | Answer | Source |
|---|---|---|
| Engine | **framework** ("on a framework with ready admin screens") | `att13` 5.7.2, p.54 |
| Hand | **ready_product** (set up and configured, not built) | low-code OEM platform with a 3-year licence |

**What each answer does:**
- **ready_product** prices the build at 0.2 of a custom build's effort (parameters v23,
  `answer_effort_multiplier`).
- **framework** cuts the screens and data-entry share (`reuse`).
- **custom** builds everything.

**The clauses**

> **Terms of Reference 5.1 Scope of Work, `att05` p.1:** "Component 2: Develop workflow based
> back-end systems on No Code Low Code platform to enable department officers resolve service
> requests"

> **2.7.2 Key Technical Features, `att05` p.12 (same text in `att13` 5.7.2, p.54):** "1. The platfor
> must be built in low-code/no-code principle and following micro service architecture
> framework. 2. All types of data fields must be available to be added in a form. Form creation,
> edit and submission for production must be through configuration changes only, no coding
> should be involved. 3. Conditional data fields, client-side validation and server-side
> validation must be available as much as possible through configurations. No coding should be
> involved."

> **2.6 Annual Maintenance & Post Implementation Support, `att05` p.7-8:** "The SI should ensure
> upgrades, updates & patches of the Solution and tools to Client (Department) as and when released
> by Low Code/No Code OEM." and "The SI shall provide services for LCNC license management and
> control."

> **Form FIN-3 (Component #1), `att09` p.3, item 5:** "Required Platforms License Cost for 3 years
> from date of implementation"

> **Form FIN-4 (Component #2), `att09` p.4:** "1. Low-code/No-code based workflow System" (No of
> Units **200**); "2. Cost of Service form" (**200**)

**Other clauses that add context or conflict**

> **5.1, `att05` p.1:** "Component 1: Develop and implement best in-class UI/UX for ONE Meghalaya
> platform: The platform includes access channels such as mobile app, web portal, WhatsApp chatbot
> and Mobile App (Occasionally online mode) for VCFs" and "Component 3: Develop Beneficiary
> Management System to provide state specific beneficiary ID and family ID for all citizens to
> apply to services" and "Component 4: Develop analytics-based dashboard for review and monitoring
> above components"

> **Form FIN-3, `att09` p.3:** separate price lines "1. Mobile App – citizen facing", "2. Web
> Portal", "3. Chatbots", "4. Mobile App (Occasionally online mode) for VCFs"

> **`att05` p.3:** "In case of any COTS products, the SI should follow disciplined approach (as per
> the best practice defined by the OEM) for configuration and customization which should not
> restrict department for any future upgrades to its solution."

- **The form takes one build type for the whole project.** The tender asks for a licensed
  low-code platform for the back-end workflows (Component 2), and separately priced apps, a
  portal, chatbots, a beneficiary system and dashboards (Components 1, 3, 4). It doesn't say
  whether these are built on the same low-code platform.
- **The platform licence** ("Required Platforms License Cost for 3 years") has no input on the
  form under any of the three answers (answer-accuracy-8 §7).
- **One file wasn't read:** the Excel annexure (`att01.xlsx`), because the app refuses `.xlsx`
  uploads.

**Price of each choice** (published ₹14.12 Cr)

| Choice | P50 ₹ Cr | Ratio | Range |
|---|---:|---:|---|
| Engine: framework | 3.96 | 0.28 | 0.15-0.43 |
| Hand: ready_product | 2.45 | 0.17 | 0.09-0.26 |
| Custom | 4.41 | 0.31 | 0.16-0.47 |

**Your verdict, build type:** ______________________ (right / wrong / tender doesn't say)

---

## How these were made (to check or repeat)

- **Tender text:** `services/documents/parsing.py` `parse_document` on each attachment, the
  same parser an upload uses. No AI was used.
- **Prices:** `reading_request` (the review form's pre-fill) on the saved reading, then one
  answer changed, then `plan_quick`, then `priced_range`. Same seed (7), runs (200), parameters
  (v23), rate card (v9) and today-money conversion as `docs/backtest-production-path.md`.
- **The person-month rows** (iob-chatbot 4.2 per seat, ewaste 2 years only) set the staff
  directly, as average people over the support years. The form can't enter them.
- **The scripts are not committed:** `verify/dump.py` and `verify/choices.py` in the session
  scratchpad.

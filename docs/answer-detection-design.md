# Reading staff, support hours and chatbot level from the tender (design only)

Date: 2026-10-24. **Design only: no code, parameter, rate card or golden change.** Measured on
the production-path back-test ([`backtest-production-path.md`](backtest-production-path.md)):
8 tenders, readings from a stand-in model (not the production `claude-sonnet-5-5` call).

Four answers move our price most on these tenders ([`answer-accuracy-8.md`](answer-accuracy-8.md)):
onsite staff, support staff, support hours, and the chatbot level. This proposes how to read each
one in the style of the RailTel hosting and helpdesk fix (`client_provided.py`,
`support_terms.py`, OPEN_QUESTIONS 157): **the code decides from cited clauses; the AI only
finds and quotes them.**

## 1. Why today's reading misses

The reading keeps **one number or one sentence per answer**. A tender states staff as several
lines, each with a role, a count, a place, a period, and sometimes "per shift". Today all of
that collapses into one head count for every support year. The reader often notices the
problem and lists it as an unclear point, but nothing prices it. Seen in the 8 readings:

| Tender | What the tender says | What the reading kept |
|---|---|---|
| iob-chatbot | onsite developer (p.57) + onsite L2, year one (p.103) + L1/L2/L3 "one per shift", 24x7 (p.61, p.115), place not stated | onsite 1; the rest only as an unclear point |
| ewaste | BoQ 10(a): 2 developers at HO in year 1, then 1; BoQ 8: helpdesk 2 for 2 years; BoQ 10(b): support centre 2 for 2 years (p.55) | onsite 1, support 1 |
| iob-website | offsite team "not less than 5" (p.71) | nothing ("not less than" is not a support-staff phrase) |
| tyre | 24x7 turnkey operation (p.17) and office-hours programmers (p.17) | support hours unset (office by default); the conflict only as an unclear point |
| canara | "onsite resources 365x24x7" (att08 p.4); Table D 60 resource-months (p.58); "Bank decides number" | support hours on call; helpdesk no; onsite none |
| canara | transactions, document processing (att01 p.11) and "basic level queries" (att06 p.1) | chatbot simple |
| iob-trade | priced table: L1, L2, developer × 365 days (p.117-119); scope text: at least 4 L1 in 2 shifts (p.87) | onsite 4 (neither) |

## 2. Rules every answer follows

1. **Read from the clause, cite clause and page.** Every staff line, hours statement and
   chatbot capability keeps its quote, clause number, page and file. A quote not found on its
   page is dropped, as today (`verify_findings`).
2. **Where the AI and the code split the work:**
   - The AI reading gets one new list, `staff_lines`, in the prompt and schema (next version).
     Each line has: role, count, `count_basis` (people / per shift / resource-months),
     `location` (client site / vendor site / not stated), `phase` (build / warranty / AMC /
     whole contract), months, hours stated, `priced_in` (BoQ or commercial format / scope text),
     and evidence.
   - Code then decides the four answers from those lines, never the AI. It works in
     `services/extraction/staffing.py`, called from the merge like `_support_terms`. Phrase lists
     and thresholds go in `quick_estimate.yaml` `staffing:`, each with a `source`.
3. **Clauses that conflict → pre-bid query, priced by a fixed priority.** Two clauses state
   different values for the same thing. The priced table wins, because it is what the
   financial bid prices: BoQ or commercial format, then the SLA, then the scope of work. The
   other clause becomes an `UnclearPoint` with a drafted `prebid_query` that quotes both. The
   price uses one reading and says which.
4. **A clause that leaves a gap → price both readings, widen the range, pre-bid query.** For
   example, the place isn't stated, a duration isn't stated, or a count can't cover the hours
   asked. Here no clause wins. The extraction carries an `alternative` (the other reading,
   with the same citation) and an unclear point with its query. The price covers both
   readings (section 7).
5. **Nothing is guessed.** An answer the tender doesn't state stays at the form's usual
   answer and gets the existing "not stated" pre-bid query. People per 24x7 seat come from
   the parameter set (`helpdesk_coverage_fte`), not from the AI.

## 3. Onsite staff

**Reads:** staff lines whose location is the client's site ("at CPCB", "at the Bank
premises", "onsite", "resident").

- **Count person-months, not heads.** Sum count × months for each line in the support phase
  (warranty + AMC). A line for the whole contract counts its support months only. A per-shift
  line becomes people as seats × shifts cover: the 24x7 seat factor, or 1 per seat in office
  hours.
- **Engine change:** the planner passes role lines with months. The engine prices
  `count × months` at the onsite role's rate, spread over the support years
  (`maintenance.onsite_months.v1`). Today's `maintenance.onsite.v1` assumes every head stays
  every year.
- **Conflict → query, priced table wins:**
  - iob-trade: cost tables (3) vs scope text (6).
  - ewaste: BoQ developers (2 then 1) vs scope text adding a TL/PM and a 5-day programmer.
  - meghalaya: DBA for the whole project (att11) vs 6 months (att13).
- **Gap → both readings:**
  - Place not stated, as with iob-chatbot's L1/L2/L3 (A453 "onsite/offsite"): price as onsite
    and as support staff.
  - Resource-months that mix onsite and offsite, as with canara Table D: price both.
  - Roles with no duration, as with battery's senior expert and 2 remote developers: price
    without them and with them for the support period.

## 4. Support staff

**Reads:** staff lines at the vendor's site or "support centre", "offsite", "remote team".

- **Phrase gaps to close** in `support_terms`: "not less than", "team of", "support centre",
  "service desk".
- **BoQ table rows**, where the number sits in a cell, not a sentence. The reading's
  `priced_in: boq` line covers them.
- **Separate lines add up:** ewaste items 8 and 10(b) are 2 + 2 for 2 years each, 96
  person-months.
- **Never the same person twice:** a role that is also an onsite line counts once, and the
  stated place wins.
- **Engine:** the same months-based line, kept as "the least support labour"
  (`maintenance.support_staff.v1`'s shortfall rule, OPEN_QUESTIONS 157).
- **Gap → both readings:**
  - tyre: does the service desk (2, then 1) overlap the support centre (3)? Price the support
    centre alone and both together.

## 5. Support hours (office / on call / always)

- **always** needs a round-the-clock clause **and** a staffed sign in the same clause or the
  same staff line:
  - a staffed desk word ("helpdesk", "call centre", "manned");
  - "shift" or "per shift";
  - "onsite resources" with 24x7 (canara);
  - an L1 count per shift.
- **on_call:** round the clock with no staffed sign. Examples: "24x7 support for
  malfunctions", "24x7 incident response", "24x7 turnkey operation".
- **office:** business or office hours only.
- **What changes from today:** the staffed list gains onsite resources, per shift and L1-L3
  roles. A round-the-clock *operation* (tyre) no longer falls to the default.
- **helpdesk_scope = yes** when a staffed desk, complaint booking or service desk is asked
  for (canara: centralised complaint booking, 24x7x365).
- **Conflict → query:** round the clock and office hours both stated (the existing rule).
  New: named onsite hours that are shorter than 24x7 (iob-trade L1 8am-8pm, iob-website
  8am-10pm vs 9am-7pm).
- **Gap → both readings:** a staffed 24x7 clause where the stated headcount can't fill one
  seat's shift cover (`count < seats × helpdesk_coverage_fte[24x7]`). Price as staffed
  (always) and as on call.
  - ewaste: 2 helpdesk people, 24x7.
  - canara: 1 resource-month a month, "onsite resources 365x24x7".

## 6. Chatbot level (simple / advanced)

- **advanced** when the tender asks the chatbot to do any of these (phrase list in
  `staffing:` or its own `chatbot_terms:`):
  - transactions or account-specific answers through bank or core systems (balance,
    statements, payments, CBS or API integration);
  - multi-step journeys;
  - document processing;
  - reasoning over many documents.
- **simple** for FAQs, information from documents, "basic queries".
- **Conflict → query, capability wins:** a clause requiring a capability outweighs a general
  description of it, because the capability is what has to be built. Canara: transactions
  (att01 p.11) over "basic level queries" (att06 p.1).
- **Gap:** a chatbot named in one line with nothing about what it handles (iob-trade p.87)
  stays simple. It gets the existing "Not sure" treatment (`not_sure`, wider range) and a
  pre-bid query.

## 7. Pricing both readings

- The extraction carries `alternatives: [{answer, value, evidence, query}]`.
- The planner builds the two plans: the base reading (the one a priority or a stated place
  supports) and the other.
- The engine runs the same seed on both plans, half the runs each, and reads P10 / P50 / P90
  from the pooled draws. P50 then lies between the two readings, and the range covers both.
- The cost lines shown are the base reading's. The other appears as a priced option
  ("If the L1-L3 team sits at the bank: +₹x"), like `PricedOption` today.
- **Gate:** this widens the range, so it ships **off** (new parameter set, `source:
  placeholder`). It is switched on only after the production-path back-test shows P10-P90
  coverage by size improves without inflating width elsewhere. That follows the rule that
  range width needs coverage evidence.

## 8. Test cases (using the 8 tenders)

Each test feeds the code rule the quoted clauses as page text: a few sentences per page, taken
from the readings and the hand evidence, not whole documents. Each one checks the answer, the
citation (file, page, clause), any pre-bid query, and any alternative.

| # | Answer | Tender and clauses | Expected |
|---|---|---|---|
| O1 | onsite | iob-trade: tables IV-VI 1 L1, 1 L2, 1 developer × 365 days (p.117-119); p.87 "minimum 4 persons in all on a 2-shift basis" | 3 people, 5 years, cited p.119; query quoting p.87 and p.119; no alternative |
| O2 | onsite | ewaste BoQ 10(a): 2 developers year 1, 1 developer years 2-5 (p.55) | 72 person-months; scope TL/PM (p.23) gives a query |
| O3 | onsite | iob-chatbot: developer (p.57), onsite L2 year one (p.103), L1/L2/L3 per shift 24x7 (p.61, p.115), "onsite/offsite" (p.103) | onsite 72 person-months + 3 seats × 24x7 cover; alternative: the 3 seats as support staff; query on place |
| O4 | onsite | canara Table D 60 resource-months (att08 p.58), "Bank decides number" (p.4) | 60 person-months; alternative offsite; query |
| O5 | onsite | meghalaya PM 1, SA 2, DBA 1, UI/UX 1 onsite (att11 p.1); DBA first 6 months (att13 p.66) | 5 people for the support period; query on the DBA |
| O6 | onsite | tyre 3 programmers (6.8 p.17) + TL/PM (6.4 p.15); "at least one programmer" (6.9 iii) | 4 people; 6.9 iii not added (same role, same place) |
| O7 | onsite | iob-website "1 resource must be available at the Bank premises at all times" (6.1 F p.71) | 1 person, whole support period |
| S1 | support | ewaste BoQ 8 helpdesk 2 × 2 years + BoQ 10(b) support centre 2 × 2 years (p.55) | 96 person-months, two lines added |
| S2 | support | iob-website "off-site team of not less than 5" (p.71) | 5 people, whole support period |
| S3 | support | tyre BoQ 12(b) support centre 3 × 5 years (p.37); service desk 2 then 1 (p.35) | 180 person-months; alternative adds the service desk; query |
| S4 | support | battery BoQ 12(b) 2 developers ≥ 2 years (att03 p.3); senior expert + 2 remote, no duration (att02 p.14) | 48 person-months; alternative adds 3 for the support period; query |
| S5 | support | a role stated onsite and in a support line (battery full-stack developer, att02 p.15) | counted once, as onsite |
| H1 | hours | canara "onsite resources … 365x24x7" (att08 p.4) | always; helpdesk yes |
| H2 | hours | tyre "24x7 turnkey operation" (7.0 p.17) + programmers 5 days a week (p.17) | on_call; query quoting both |
| H3 | hours | iob-website "24*7 support for website related malfunctions" (p.71) | on_call (no staffed sign) |
| H4 | hours | iob-trade help desk 24x7x365 (p.87) + L1 8am-8pm (p.87) | always; query on the L1 hours |
| H5 | hours | ewaste "24x7 support through a helpdesk" (p.23) + helpdesk of 2 (BoQ 8 p.55) | always; alternative on_call (2 people can't fill one 24x7 seat); query |
| H6 | hours | iob-chatbot "work on 24*7 basis", one per role per shift (p.115) | always |
| H7 | hours | meghalaya: no hours stated | office (usual answer); existing "not stated" query |
| C1 | chatbot | canara transactions, document processing (att01 p.11) + "basic level queries" (att06 p.1) | advanced; query quoting both |
| C2 | chatbot | iob-chatbot "handling all the queries related to every product and service" (p.69) + integrations | advanced |
| C3 | chatbot | ewaste "well-trained with FAQs, multilingual" (p.9) | simple |
| C4 | chatbot | iob-trade "online help or chat bot" only (p.87) | not sure (simple, wider range); query |
| P1 | pricing | any alternative above | P50 between the two readings; P10 ≤ the lower reading's P10; P90 ≥ the higher reading's P90; same seed → same result |
| P2 | pricing | `maintenance.onsite_months.v1` | 72 person-months over 5 support years = 1.2 heads a year at the onsite rate; formula registered and traced |

Plus the production-path back-test (`backtest_production`) run before and after, reported by
size, with P10-P90 coverage.

## 9. Predicted B+doc ratio per tender after the fix

These are computed, not guessed:
- each tender is priced on the production path with the answers the rules above would give;
- staff go in as person-months, as average heads over the support years;
- per-shift seats become people at the engine's 24x7 cover (4.2 a seat, parameters v23).

Today's engine, parameters, rate card and catalog are used throughout. The predictions assume
the reader finds the clauses the hand reading found.

| Tender | Size | B+doc now | After: base reading | After: other reading | P10-P90 covering both | Published inside? |
|---|---|---:|---:|---:|---|---|
| battery | medium | 2.59 | **2.93** | 3.97 (+ 3 remote staff) | 1.62-5.95 | no |
| ewaste | medium | 0.69 | **0.71** | 0.55 (on call) | 0.32-1.09 | yes |
| tyre † | medium | 2.82 | **3.74** | 4.34 (+ service desk) | 2.06-6.38 | no |
| iob-trade | medium | 1.49 | **1.63** | — | 0.84-2.58 | yes |
| iob-website | medium | 0.65 | **1.34** | — | 0.74-1.99 | yes |
| canara | large | 0.47 | **1.02** | 0.66 (offsite, on call) | 0.35-1.62 | yes |
| iob-chatbot | large | 0.65 | **2.46** | 2.28 (team offsite) | 1.16-3.76 | no |
| meghalaya | large | 0.28 | **0.28** | — | 0.15-0.43 | no |
| **Median, medium** | | 1.49 | **1.63** | | | 3 of 5 |
| **Median, large** | | 0.47 | **1.02** | | | 1 of 3 |
| **Inside P10-P90, all** | | 3 of 8 | | | | **4 of 8** |

† deadline not feasible, priced without it.

**Reading these predictions:**
- **Large tenders move toward 1.0x.** The median goes 0.47x → 1.02x. Canara lands on 1.02x.
- **iob-chatbot overshoots to 2.46x.** "One per role per shift, 24x7" read as staffed seats
  means 3 × 4.2 = 12.6 people for 5 years. The published price is about ₹80k per
  person-month on that staffing, below our all-in ₹1.2 L (answer-accuracy-8 §6). Either the
  4.2 people per seat factor (a v22 placeholder) is too high for bank managed services, or
  the bank's L1-L3 seats are shared with other clients. **This must be checked before
  shipping H6/O3.** The hand reading (3 people) gives 1.19x.
- **CPCB tenders go further over** (battery 2.93x, tyre 3.74x). Reading their staff right
  adds cost. Their published prices are below our cost per staff-month
  (answer-accuracy-8 §6), so the gap is the market rate, not the reading. This design doesn't
  fix that, and should not try to.
- **iob-website doubles** (0.65x → 1.34x) from its 5 offsite support staff. That is the
  answer the tender states.
- **Meghalaya doesn't move.** Its gap is the platform licence and infrastructure billed at
  actuals (answer-accuracy-8 §7), not these four answers.

## 10. What this doesn't cover

- Support years (om_years) conflicts. Battery is 6 vs 5, ewaste 5 vs 6; they are separate
  answers with their own queries today.
- Build type (ready product / framework / CMS).
- The 24x7 people-per-seat factor (see iob-chatbot above).
- The market rate behind the CPCB gap.
- The predictions use a stand-in model's readings. Readings from the production model call
  can differ; the back-test should be run again once real readings are saved.

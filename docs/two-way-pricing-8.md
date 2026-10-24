# Two-way pricing: 8 tenders priced from the manual reading and from the engine's reading

Measurement only (2026-10-24). No code, parameters, rate card, goldens or benchmark file were
changed. The main back-test set was not touched, and nothing outside these 8 was priced. No AI
call was made: pricing is the local deterministic engine with `ANTHROPIC_API_KEY` blanked, and the
mapping work was done by Claude Code subagents. Nothing here is a proposed fix.

> **Back-test paths (added 2026-10-24):** "back-test" in this report means the **legacy back-test, not the production path** (the benchmark file's hand-mapped scope; the app never prices this way). The headline back-test is now the production path: see [`backtest-production-path.md`](backtest-production-path.md).

## Set-up

- **Engine and reference data:** today's engine with the newest active India reference data, as
  the back-test uses it: parameters v23, rate card v9, catalog v7. Seed 7, 200 Monte Carlo runs,
  dated 2026-10-24.
- **Pricing path:** every run goes through the app's own `plan_quick` → `plan_to_input` →
  `calculate`.
- **Basis:** every price is **without AI tools** and matched to the published value's tax
  treatment. That is the back-test's round-3 column (target 1.0x), the same basis as the "large
  0.27x" figure.
- **Published today:** the award value escalated to 2026, as in the back-test.
- **Check:** the "as the legacy back-test stands" column reproduces the back-test's own number for all 8
  tenders exactly.

| Run | Scope | Answers to the form's questions |
|---|---|---|
| As the legacy back-test stands (not the production path) | the benchmark's keyword-reader feature list | the back-test's fixed mapping |
| **A** | the manual reading in round-3 format (`gemdocs/<tender>.reading.json`: modules, story counts → levels and units, by the round-3 conversion rule), plus scope items its requirements map to | what the manual reading records (`two/<tender>.answers.json`, each cited to an A id and page) |
| **B** | the engine's reading (`cov/out/<tender>/merged.json`), untouched, as the review form pre-fills it (a port of `review.tsx`: suggested features, story levels and units, extra features, explicit scope items, payment terms) | what the engine's reading found; the form's defaults for the rest |
| **C** | B's scope | A's answers. The questions that add features (platforms, integrations, old data) stay B's, because they are scope. |

A and C differ only in scope. B and C differ only in answers.

**Stop condition:** no tender came out identical to the rupee between A and B. The hand readings
reach the pricer.

## Results per tender

₹ crore, P50. "✓" means the published price falls inside that run's P10–P90. "†" means the
stated deadline cannot be met at that scope, so the run is priced without the deadline (see
method notes).

| Tender | Size | Award (year) | Published today | As the legacy back-test stands (not the production path) | Run A | Run B | Run C | **A ÷ published** | B ÷ published | C ÷ published |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cpcb-battery | medium | 1.58 (2023) | 1.99 | 0.88 (0.44x) | 7.97 | 5.01 | 7.76 | **4.00x** | 2.51x | 3.89x |
| cpcb-ewaste | medium | 6.43 (2023) | 8.10 | 1.53 (0.19x) | 8.46 ✓† | 5.46 ✓ | 7.90 ✓ | **1.04x** | 0.68x | 0.98x |
| cpcb-tyre | medium | 1.90 (2023) | 2.39 | 1.83 ✓ (0.77x) | 11.12 † | 6.49 † | 10.33 † | **4.66x** | 2.72x | 4.32x |
| iob-trade | medium | 2.94 (2025) | 3.17 | 1.22 (0.39x) | 5.26 ✓ | 4.65 ✓ | 5.04 ✓ | **1.66x** | 1.47x | 1.59x |
| iob-website | medium | 4.20 (2025) | 4.54 | 1.42 (0.31x) | 7.07 ✓ | 2.87 | 6.93 ✓ | **1.56x** | 0.63x | 1.53x |
| canara-chatbot | large | 4.58 (2023) | 5.77 | 2.82 (0.49x) | 5.45 ✓ | 2.68 | 5.79 ✓ | **0.94x** | 0.47x | 1.00x |
| iob-chatbot | large | 5.24 (2024) | 6.12 | 4.30 ✓ (0.70x) | 7.46 ✓ | 3.94 ✓ | 7.27 ✓ | **1.22x** | 0.64x | 1.19x |
| meghalaya | large | 11.21 (2023) | 14.12 | 1.99 (0.14x) | 2.34 | 3.85 | 2.40 | **0.17x** | 0.27x | 0.17x |

P10–P90 ranges for run A (₹ Cr):

| Tender | P10–P90 |
|---|---|
| cpcb-battery | 4.43–11.89 |
| cpcb-ewaste | 4.40–13.09 |
| cpcb-tyre | 5.83–17.28 |
| iob-trade | 2.74–8.19 |
| iob-website | 3.70–11.07 |
| canara-chatbot | 2.88–8.43 |
| iob-chatbot | 3.87–11.56 |
| meghalaya | 1.20–3.55 |

Passing the engine's reading into the plan, as the app does, moves B by 1–4% through the clarity
score: 2.59, 0.69, 2.82, 1.49, 0.65, 0.47, 0.65 and 0.28x, in table order.

## By size band (run A is the headline)

None of the 8 is small. With 2–3 tenders per band one outlier moves the median, so the
per-tender ratios are shown in each cell.

| Band | Run A | Run B | Run C | As the legacy back-test stands (not the production path) |
|---|---|---|---|---|
| **Medium (5)**, median | **1.66x** (4.00, 1.04, 4.66, 1.66, 1.56) | 1.47x (2.51, 0.68, 2.72, 1.47, 0.63) | 1.59x | 0.39x |
| **Large (3)**, median | **0.94x** (0.94, 1.22, 0.17) | 0.47x (0.47, 0.64, 0.27) | 1.00x | 0.49x |
| All 8, median | 1.39x | 0.66x | 1.36x | 0.41x |

**Published price inside our P10–P90:**

| Run | Medium | Large | All 8 |
|---|---:|---:|---:|
| As the legacy back-test stands (not the production path) | 1 of 5 | 1 of 3 | **2 of 8** |
| Run A | 3 of 5 | 2 of 3 | **5 of 8** |
| Run B | 2 of 5 | 1 of 3 | **3 of 8** |
| Run C | 3 of 5 | 2 of 3 | **5 of 8** |

On these 8 the legacy back-test's large median is 0.49x, not the 0.27x seen over all 9
large back-test projects.

## What separates A from B: scope or answers

**Scope (A vs C, same answers):** within −6% to +8% on every tender. The A/C pairs are:

| Tender | A | C |
|---|---:|---:|
| cpcb-battery | 4.00 | 3.89 |
| cpcb-ewaste | 1.04 | 0.98 |
| cpcb-tyre | 4.66 | 4.32 |
| iob-trade | 1.66 | 1.59 |
| iob-website | 1.56 | 1.53 |
| canara-chatbot | 0.94 | 1.00 |
| iob-chatbot | 1.22 | 1.19 |
| meghalaya | 0.17 | 0.17 |

The hand scope has 33–79 feature points against B's 28–55, yet the price barely moves.

**Answers (B vs C, same scope):** up to 2.4x. These answers differ:

| Tender | B → C | Answers that differ (B → C) |
|---|---|---|
| canara-chatbot | 0.47 → 1.00 | helpdesk no → yes; support hours on call → always; onsite staff none → 1; chatbot task simple → advanced; languages 10 → 11 |
| iob-chatbot | 0.64 → 1.19 | onsite staff 1 → 5; peak concurrent users none → 1000 |
| iob-website | 0.63 → 1.53 | support staff none → 5; support hours on call → always; build type cms → ready product; design custom → some; domain commercial → client's |
| cpcb-ewaste | 0.68 → 0.98 | onsite staff 1 → 2; support staff 1 → 4; build type custom → framework; launch help usual → extra; deadline none → 4 months |
| cpcb-battery | 2.51 → 3.89 | onsite staff 2 → 3; support staff none → 2; O&M years 5 → 6 |
| cpcb-tyre | 2.72 → 4.32 | support hours office → always; onsite staff 3 → 4; support staff none → 3; users none → 2,000 total, 5,000 concurrent; build type custom → framework; launch help usual → extra |
| iob-trade | 1.47 → 1.59 | support hours on call → always; onsite staff 4 → 3; launch help usual → extra; deadline none → 6 months |
| meghalaya | 0.27 → 0.17 | build type framework → ready product (the manual reading marks a low-code platform); deadline none → 12 months |

**Where the money sits in our price.** Shares of our likely sum, run A then run B:

| Part of our price | Share |
|---|---|
| Build plus management | 5–16% in A; 5–28% in B |
| Run stage | 54–67% in A, of which onsite staff and helpdesk are 35–59% |
| Commercial: GST, margin, working capital, guarantees | about 29% |

So the scope a reader extracts can only move the build share, which is small for these tenders
(and smaller still for a ready product, priced at 0.2x build effort). The staffing and support
answers move the rest.

**Against the expectation in the request:**
- **"Run A close to Run B": not the case.** The median is 1.39x against 0.66x. But the gap is not
  scope: A and C, which share answers, agree. Scope extraction is exonerated as predicted. The
  difference is a handful of answers: staff counts, support hours and helpdesk, support years and
  build type.
- **"A near 1.0x while B stays near 0.3x means one measurement is wrong": both stand.** Large A is
  0.94x and large B is 0.47x. The recall measurement weights every requirement equally, and an
  onsite headcount or "24x7" is one requirement among hundreds. The price, though, lives mostly in
  those few answers. Recall of 85% and a 2x price gap are consistent.

## Raw vs comparable price

Every A requirement that is cost-relevant and has no input in the app was checked for things the
published price contains that we never price. For every licence and service fee among them, the
amount is **not published**: GeM shows only the contract total, and the tenders' price schedules
list the lines with amounts blank. So a comparable ratio can be computed only where the amount is
known. Otherwise the table gives the share of the published price the exclusions would have to be
for our price to reach 1.0x (break-even = 1 − raw ratio).

| Tender | In the published price, not priced by us (A id) | Amount removed | Raw A | Comparable A | Break-even share, A | Raw B | Break-even share, B |
|---|---|---|---:|---|---:|---:|---:|
| canara-chatbot | enterprise licence, unlimited use, renewals for 5 years (A159, A160) | not published | 0.94x | above 0.94x | 6% | 0.47x | 53% |
| iob-chatbot | perpetual enterprise licence and ATS fees (unlimited users); WhatsApp conversation charges (volumes stated, the column is garbled in the text) | not published | 1.22x | above 1.22x | none (already ≥ 1) | 0.64x | 36% |
| iob-trade | perpetual unlimited-user enterprise licence (A295); source-code escrow 5 years (A253) | not published | 1.66x | above 1.66x | none | 1.47x | none |
| meghalaya | platform licence for 3 years (A173); DLP, WAF and DDoS tools (A140) | not published | 0.17x | see below | 84% | 0.27x | 73% |
| meghalaya, other direction | infrastructure charged on actuals, the bid quotes an agency fee only (A167). The published price excludes it, but our runs price hosting, DR, backups and environments. | about ₹0.13 Cr incl. GST, removed from **our** price | 0.17x | **about 0.16x** | | | |
| iob-website | software, database and CMS licences (A46, A65); third-party map licence (A102); security services: DDoS/WAF, firewall/IPS, SOC, PAM, anti-APT (A152–A157); STQC and other certificates (A27, A202); ongoing SEO service | not published | 1.56x | above 1.56x | none | 0.63x | 37% |
| cpcb-battery, -ewaste, -tyre | no product licence or pass-through fee. "Perpetual licence" here is the client's right to its own custom code (ewaste A94, tyre A146). There is open-ended development inside the AMC at no extra charge (battery A86, ewaste A116, tyre A114) and video production (ewaste A68). | not published | 4.00x, 1.04x, 4.66x | above raw | none | 2.51x, 0.68x, 2.72x | none, 32%, none |

The four tenders named in the request (canara-chatbot, iob-chatbot, meghalaya, iob-trade):

- **Run A:** none of the exclusions can absorb any gap, because three of the four are already at
  or above 1.0x raw. Removing a licence only raises the ratio. Meghalaya would need its platform
  licence to be 84% of the contract.
- **Run B:** the gaps on canara-chatbot and iob-chatbot would close only if their licences were
  36–53% of the contract. iob-trade is already above 1.0x.
- **Undetermined:** whether those shares are real can't be settled from these documents.

Under the benchmark file's written rules, the licence-based tenders raise the `subscription` rule
question that round 3 set aside to check on reading (OPEN_QUESTIONS 155). This is recorded here
only; the back-test was not changed.

**Published prices of near-identical scopes.** The three CPCB EPR portals have the same buyer, the
same year and nearly the same scope. They were awarded at ₹1.58 Cr (battery), ₹1.90 Cr (tyre) and
₹6.43 Cr (e-waste); battery and tyre went to the same vendor. Our run A prices them at ₹7.97 Cr,
₹11.12 Cr and ₹8.46 Cr. No single model of this scope can be near 1.0x on all three.

## How much the round-3 format can hold

Each of the 1835 A requirements was sorted by where it can go: a reading module (user stories), a
form input (question, number or scope item), nothing but priced by default (standard blocks and
run costs), only partly (a home exists but a cost-relevant part is lost), or nowhere.

| Tender | A reqs | Reading | Form | Default | Partial | Nowhere | Nowhere, cost-relevant | Partial, cost-relevant |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cpcb-battery | 114 | 51 | 28 | 16 | 8 | 11 | 4 | 8 |
| cpcb-ewaste | 148 | 78 | 23 | 14 | 16 | 17 | 8 | 16 |
| cpcb-tyre | 153 | 78 | 32 | 13 | 9 | 21 | 10 | 9 |
| iob-trade | 305 | 204 | 31 | 19 | 24 | 27 | 8 | 24 |
| iob-website | 213 | 93 | 29 | 29 | 14 | 48 | 26 | 12 |
| canara-chatbot | 201 | 116 | 26 | 16 | 9 | 34 | 9 | 9 |
| iob-chatbot | 474 | 250 | 52 | 65 | 41 | 66 | 25 | 40 |
| meghalaya | 227 | 117 | 28 | 34 | 20 | 28 | 8 | 17 |
| **All 8** | **1835** | **987 (54%)** | **249 (14%)** | **206 (11%)** | **141 (8%)** | **252 (14%)** | **98 (5%)** | **135 (7%)** |

**458 of 1835 (25%) have no input of their own.** Of those, 206 are priced by default and 252 go
nowhere. 233 (13%) are cost-relevant and are lost in whole or in part:

- **Nowhere (98):** licences and pass-through fees, open-ended development inside the AMC,
  security services, escrow, exit support and certificates.
- **Partial (135):** several staff roles collapsed into one count, staff by year, response,
  restore and resolution times beyond the uptime answer, and environments beyond the default.

**What this means for the test:**
- Run A inherits the cap. Every cost-relevant item it cannot hold is work or a fee the vendor
  carries, so it would raise our price, except licences, which sit on the published side.
- Run A is already at or above 1.0x on 6 of 8, so the cap cannot be hiding an under-price there.
- The two below 1.0x are canara-chatbot (0.94x, inside its range) and meghalaya (0.17x).
- For meghalaya, the format holds 117 of its 227 requirements as module stories. Its run A is set
  mostly by the ready-product answer (build at 0.2x) and 5 onsite staff for 2 years.

## Method notes

- **A's answers:** Sonnet subagents mapped them from the manual reading under a fixed rulebook
  (`two/MAP_BRIEF.md`). Each answer cites the A id and page. Where the reading records two values,
  the one the price schedule prices was used; the other is listed under `conflicts`. These are
  judgment calls:
  - **Staff counts:** roles stated at the client's office are added up (cpcb-battery: 2 team
    leads plus 1 developer = 3). Where the price schedule's counts differ from the scope text, the
    schedule's were used (iob-trade 3, against 4+ L1 in the scope text).
  - **Support hours:** "24x7" is read as round the clock.
  - **Build type:** iob-website is a ready product, because the reading marks its licensed CMS
    as a ready product (B said cms).
  - **Hosting:** canara-chatbot is "public cloud" in both A and B.
- **EMD and performance-guarantee percent** come from the document's figures in every run. A was
  blind to the EMD.
- **Extra features** are priced by their generic block in every run, as the back-test does. The
  app may match a catalog or research block, which was not done here.
- **Deadlines that cannot be met (†):**
  - cpcb-ewaste run A: 4 months.
  - cpcb-tyre runs A, B and C: 3 months.

  The engine returns "not feasible" for that scope, so these runs are priced with the engine's
  own duration.
- **Pricing basis:** prices are without AI tools (round-3 target 1.0x). iob-trade and iob-website
  were awarded in 2025, and the back-test's judged column scores them with AI tools.
- **Sample:** 8 tenders, 5 medium and 3 large. Treat medians as hints.

**Files** (session scratchpad, not the repo):
- `two_price/two_way.py` (script) and `two_price/results.json` (every run's request, P10/P50/P90
  and line totals by bucket).
- `two/<tender>.answers.json`, `two/<tender>.cap.jsonl` and `two/<tender>.cap_summary.json`.

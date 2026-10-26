# Task 2: staff and support rules (OPEN_QUESTIONS 162)

Date: 2026-10-24. No AI call was made. No tender was re-read.

## What was changed in the readings

The 8 saved readings were **not** read again by an AI. Each one was copied to
`backend/tests/fixtures/readings_v9/` with two additions:

- **Staff lines**, entered by hand from the clauses in `docs/verification-sheet.md` and the page
  text.
- **The chatbot's systems**, where the chatbot must connect to the buyer's own systems.

Every quote was checked by the app's own quote check (`verify_findings`) against the page text
from the app's parser. Then the code checks (support terms and the new staff rules) were run again
on the page text. Nothing else in the readings was changed.

Since there was no re-read, "new reading + old rules" is the same as "before". So the report has
two columns, not three.

## Predictions (written before the back-test was run)

Ratio = our P50 without AI tools ÷ published price in today's money. "Inside" means 1.0 falls
inside our P10-P90 range.

| Tender | Before | Predicted | Inside (predicted) | Why |
|---|---:|---:|---|---|
| battery | 2.59 | 2.4 | no | 24x7 helpdesk with no shifts is on call (was staffed); one more onsite developer for the AMC (quantity unclear) |
| ewaste | 0.69 | 0.57 | no | 24x7 helpdesk with no shifts is on call (was staffed); the 2-year staff lines add little over the support work already priced |
| tyre | 2.82 | 2.6 | no | 3 staff for 60 months (the BoQ line), not all 6 support years |
| iob-trade | 1.49 | 1.21 | yes | the cost tables' 1 L1 + 1 L2 + 1 developer (3 people), not the narrative's 4 L1 |
| iob-website | 0.65 | 1.34 | yes | the 5-person offsite team is now priced |
| canara | 0.47 | 0.61 | no | complaint desk = helpdesk yes; chatbot connects to the bank's systems = complex questions |
| iob-chatbot | 0.65 | 0.75 | yes | call-off L1/L2/L3 priced as 3 people, on call (was staffed shifts); onsite L2 for 12 months |
| meghalaya | 0.28 | 0.28 | no | same 5 onsite staff |
| **Medium median** | 1.49 | 1.34 | | |
| **Large median** | 0.47 | 0.61 | | |
| **Inside the range** | 3 of 8 | 3 of 8 | | |

## Results (production-path back-test, run after the predictions)

Both runs: rate card v9, catalog v7, seed 7, 200 runs, without AI tools. **Before** = the old
readings with the old rules and parameters v23. **After** = the readings with staff lines, the
new rules and parameters v24. v24 (4.0 people per round-the-clock seat) changes none of the
"after" prices: no tender ends up with a committed round-the-clock team.

| Tender | Size | Before | After | Predicted | After range (P10-P90) | Inside before | Inside after |
|---|---|---:|---:|---:|---|---|---|
| battery | medium | 2.59 | **2.44** | 2.4 | 1.35-3.62 | no | no |
| ewaste | medium | 0.69 | **0.63** | 0.57 | 0.36-0.92 | yes | **no** |
| tyre † | medium | 2.82 | **2.52** | 2.6 | 1.43-3.73 | no | no |
| iob-trade | medium | 1.49 | **1.22** | 1.21 | 0.61-1.81 | yes | yes |
| iob-website | medium | 0.65 | **1.34** | 1.34 | 0.72-1.93 | no | **yes** |
| canara | large | 0.47 | **0.66** | 0.61 | 0.35-1.01 | no | **yes** |
| iob-chatbot | large | 0.65 | **0.72** | 0.75 | 0.37-1.10 | yes | yes |
| meghalaya | large | 0.28 | **0.28** | 0.28 | 0.15-0.43 | no | no |

† tyre's 3-month deadline can't be met, so it is priced without it.

| Summary | Before | After |
|---|---:|---:|
| Medium median | 1.49 | **1.34** |
| Large median | 0.47 | **0.66** |
| Typical miss (median of \|1 − ratio\|) | 51% | **36%** |
| Inside the range | 3 of 8 | **4 of 8** |

**Predictions vs results:** 6 of 8 within 0.05 of the prediction. Ewaste came out higher than
predicted (0.63 vs 0.57) and canara higher (0.66 vs 0.61, so it moved inside the range, which I
had not predicted). Ewaste moved outside the range.

**Not done as asked:**
- **Tyre support hours** stay office hours, not on call. The "24 x 7 operations" sentence is
  joined to the heading before it by the sentence splitter (486 characters, over the 400 limit),
  so the support-terms check skips it. The on-call price would be about 0.1 higher.
- **Three columns** became two, because there was no re-read (see the top).

## Pre-bid queries the new rules raised

| Tender | Answer | Page | Query (short) |
|---|---|---|---|
| canara | support hours | att08 p.4 | Onsite resources round the clock, number set by the Bank: staffed team from the start? Priced on call. |
| canara | staff | att08 p.58 | Table D's offsite resource is at the Bank's discretion: confirm the number; priced 1. |
| canara | staff | att08 p.4 | Table D: 1 offsite; terms: an unstated number onsite 365x24x7. Priced the table. |
| battery | staff | att02 p.14 | BoQ 12(b): 2 developers; terms: senior IT Expert + 2 IT Developers. Priced the table. |
| battery | staff | att02 p.15 | Full stack developer at CPCB HO: may be one of the 2 BoQ developers. Priced 1 as read. |
| ewaste | staff | att01 p.55 | Helpdesk's 2 professionals: where they sit not stated. Priced offsite. |
| ewaste | staff | att01 p.55 | BoQ 10(b) "02": years or developers? Priced 2 as read. |
| ewaste | staff | att01 p.24 | BoQ 10(b): 2 developers; terms: senior IT Expert + 2 IT Developers. Priced the table. |
| tyre | staff | att01 p.35 | BoQ 12(b): 3 developers; service desk clause: 2 developers. Priced the table. |
| iob-chatbot | support hours | att01 p.115 | L1/L2/L3 round the clock, number set by the Bank: staffed team from the start? Priced on call. |
| iob-chatbot | staff | att01 p.115 | L1/L2/L3: where they sit not stated. Priced offsite. |
| iob-chatbot | staff | att01 p.115 | L1/L2/L3 at the Bank's discretion: confirm the number; priced 3. |
| iob-trade | support hours | att01 p.117 | Onsite L1 round the clock, number set by the Bank: staffed team from the start? Priced on call. |
| iob-trade | staff | att01 p.117 | Onsite L1 at the Bank's discretion; priced 1. |
| iob-trade | staff | att01 p.117 | Onsite L2 at the Bank's discretion; priced 1. |
| iob-trade | staff | att01 p.117 | Onsite developer at the Bank's discretion; priced 1. |
| iob-trade | staff | att01 p.87 | Cost tables: 1 L1; help desk terms: 4 L1 on 2 shifts. Priced the tables. |
| meghalaya | staff | att11 p.1 | UI/UX Designer: no deployment period stated. Priced 1 as read. |

iob-website raised no new query (its onsite-hours conflict was already raised by the reading).
The full texts are in the readings (`unclear_points` with an `answer`).

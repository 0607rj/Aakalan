# Back-test on the production path

Date: 2026-10-24. Branch `phase2/accuracy`, uncommitted. Parameters v23, rate card v9, catalog
v7, seed 7, 200 runs, as of 2026-10-24. No price, parameter, rate card or golden file changed.
No AI API call was made.

**Read this first:** this headline covers **8 tenders** only. Their readings came from a
**stand-in model**: a Claude Code Sonnet subagent answering the app's own prompts. That is
**not the production `claude-sonnet-5-5` API call**, so a production reading could differ.

## What changed

- **One pre-fill, in the backend.** `services/quick/prefill.py` (`review_prefill`) does what the
  review form did in `review.tsx`. It works out the form's starting state from a reading, and
  the request the form sends when everything is accepted. The form now loads it from
  `GET /documents/{id}/form?country=` and starts from it. Edits still work in the form as
  before.
- **The 8 readings are committed fixtures:** `backend/tests/fixtures/readings/<benchmark id>.json`.
  Each one names its reader (`reader_model`), the date read (`read_on`), the code path and the
  files read.
- **Production-path back-test:** `calibration/backtest.py` `backtest_production`. For every
  benchmark with a saved reading, it builds the review form's request with `reading_request`,
  using the same pre-fill function with no copy of its logic. It then plans with the reading
  passed in, as `POST /quick-estimates` does, and prices.
- **The `backtest` command** prints the production path first, as the headline. The old
  back-test follows under "LEGACY, NOT THE PRODUCTION PATH". `--calibrate` and `--layers` run
  on the legacy path and say so.

## Checks

| Check | Result |
|---|---|
| Lint and tests at the start | passed (391 tests) |
| Pre-fill vs the real `review.tsx`, before the switch: the real form was rendered on each reading and the request it sends was captured, all fields including `answered` | **same on all 8** (byte for byte; saved as `tests/fixtures/review_form/requests.json`, checked by `tests/core/test_prefill.py`) |
| Form after the switch (rendered the same way, with the pre-fill) | **sends the same on all 8**, on the first screen and on a question screen |
| Production path vs B+doc in `answer-accuracy-8.md` | **same to the paisa on all 8** (P10, P50 and P90 without AI tools) |

**Bug found and fixed during the switch:** a number the document doesn't state came in as
`null` and showed as "0" on the facts screen (JavaScript's `Number(null)` is 0). It now shows
blank, as before. The after-switch check caught it before anything was reported.

## Both back-tests, side by side

Ratio = our P50 without AI tools ÷ published price in today's money (target 1.0x).

| Tender | Size | Published today (₹ Cr) | **Production path** | Legacy (not the production path) |
|---|---|---:|---:|---:|
| battery | medium | 1.99 | **2.59** | 0.44 |
| ewaste | medium | 8.10 | **0.69** | 0.19 |
| tyre | medium | 2.39 | **2.82** † | 0.77 |
| iob-trade | medium | 3.17 | **1.49** | 0.39 |
| iob-website | medium | 4.54 | **0.65** | 0.31 |
| canara | large | 5.77 | **0.47** | 0.49 |
| iob-chatbot | large | 6.12 | **0.65** | 0.70 |
| meghalaya | large | 14.12 | **0.28** | 0.14 |
| **Median, medium (5)** | | | **1.49** | 0.39 |
| **Median, large (3)** | | | **0.47** | 0.49 |
| **Median, all 8** | | | **0.67** | 0.41 |
| Inside our P10-P90 (without AI tools) | | | **3 of 8** (medium 2, large 1) | 2 of 8 |

† tyre's 3-month deadline cannot be met, so it is priced without it. The app would show the
plan as not feasible, with no price.

The legacy back-test over all its 55 projects is unchanged (medium bias 0.36x, large 0.27x
without AI tools). It stays available for the projects that have no saved reading.

## What the production path still does not cover

- **Custom features** are priced by their generic block. The app may match a catalog or
  researched block, which needs the company's database.
- **No independent check:** the readings have no inventory, and the check explains the price
  but doesn't change it.
- **Must-choose answers** (AI passthrough) are left at the request default. They don't change
  the price without AI tools.
- **The stand-in model** read the tenders, not the production API call (see the top).
- **One file not read:** meghalaya's Excel annexure. The app refuses `.xlsx` uploads.

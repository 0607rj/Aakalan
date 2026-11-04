# Five-domain reading measurement (OPEN_QUESTIONS 205)

Not part of the test suite. Five synthetic requirement documents from industries the catalog was
not built around, each with an answer file. Each document was read twice (run A, run B) by
stand-in readers (Sonnet on the Claude plan, no API key) that answered the app's exact prompts
(reading prompt `extract_tender_v10` + `gap_check_v4`) and never saw the answer files. Their
replies (`readings/`) go through the app's own code: citation check, merge, keyword net, coverage
list, the review form's pre-fill and pricing.

| Folder / file | What |
|---|---|
| `documents/` | hospital_hms, logistics_fleet, fintech_lending, video_meet, beekeeping_coop |
| `answers/` | expected industry, features, add-ons, custom items, optional items, warnings |
| `readings/runA`, `readings/runB` | the stand-in replies (first pass + second pass) |
| `harness.py` | `prep`, `gap-user`, `evaluate` (see its docstring) |
| `results.json` | the last `evaluate` output |

Re-score the saved readings (from `backend/`):

```
mkdir work && cp -r measurements/domains/readings/runA measurements/domains/readings/runB work/
ANTHROPIC_API_KEY= PYTHONPATH=. uv run python measurements/domains/harness.py evaluate work
```

## Result, 2026-11-02 (10 readings)

| | Run A | Run B |
|---|---|---|
| Listed features found (recall) | 43 / 44 | 43 / 44 |
| Ticked features that are right (precision) | 43 / 44 | 43 / 44 |
| Ruled-out items priced (later phase / excluded) | 0 | 0 |
| Custom items found | 17 / 17 | 16 / 17 |
| Add-ons offered | 9 / 13 | 9 / 13 |
| Industry right | 5 / 5 | 5 / 5 |
| Prerequisite warnings as expected | 5 / 5 | 5 / 5 |

Same ticked features on both reads: 5 of 5 documents. Same add-ons: 4 of 5. Pre-filled P50 gap
between the reads: hospital 4.5%, logistics 8.5%, lending 0%, video 31.2%, beekeeping 0%.

The miss is lending's credit bureau API, read both times as a custom integration rather than
"connect to existing systems" (priced either way). The wrong tick is logistics' inventory, added
by the keyword net from "scan the barcode on every parcel". The add-ons missed are hospital
"pay when booking" (the payment feature is ticked), lending e-KYC / DigiLocker (the Aadhaar
feature is ticked) and lending's security audit (both reads).

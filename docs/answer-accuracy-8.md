# Answer accuracy on 8 GeM tenders (measurement only)

Date: 2026-10-24. Branch `phase2/accuracy`, uncommitted working tree. Parameters v23, rate card v9,
catalog v7, seed 7, 200 runs, priced without AI tools, prices brought to today's money (the same
basis as [`two-way-pricing-8.md`](two-way-pricing-8.md)). No code, seed, parameter, rate card or
golden file was changed. No fix is proposed here. All pricing ran locally with
`ANTHROPIC_API_KEY` blank; no AI API call was made.

> **Back-test paths (added 2026-10-24):** "back-test" in this report means the **legacy back-test, not the production path** (the benchmark file's hand-mapped scope; the app never prices this way). The headline back-test is now the production path: see [`backtest-production-path.md`](backtest-production-path.md).

Runs, as in the two-way report: **A** = hand reading + hand answers; **B** = engine reading +
answers the review form fills in; **B+doc** = B with the reading passed to the planner, as the app
does; **C** = B's scope + A's answers. Ratios are our P50 ÷ published price (today's money).
† = the tender's deadline is not feasible, priced again without it (ewaste A; tyre A, B, C).

## 0. Lint and tests (run first)

Both passed (`python scripts/tasks.py lint`, then `python scripts/tasks.py test`):

```
ruff check: All checks passed!   ruff format --check: 167 files already formatted
mypy app tests: Success: no issues found in 145 source files
eslint: clean   prettier --check: All matched files use Prettier code style!
pytest: 391 passed in 49.83s     frontend typecheck (next typegen && tsc --noEmit): clean
```

## 1. First: the all-swaps row against run C

Swapping **every** answer from B to the hand answer gives run C to the paisa on all 8 tenders.
Swapping only the **six** price-driving answers (section 3) does **not** match C on 7 of 8. The
difference comes from the other answers the hand changed:

| Tender | B | Six swaps | C | Six − C | Other answers that differ (B → hand) |
|---|---:|---:|---:|---:|---|
| battery | 5.01 | 7.76 | 7.76 | 0.00 | none |
| canara | 2.68 | 5.27 | 5.79 | −0.52 | chatbot_task simple → advanced, languages 10 → 11 |
| iob-chatbot | 3.94 | 7.26 | 7.27 | −0.01 | peak_concurrent_users – → 1000 |
| meghalaya | 3.85 | 2.38 | 2.40 | −0.03 | deadline_months – → 12 |
| ewaste | 5.46 | 7.68 | 7.90 | −0.22 | deadline_months – → 4, launch_help usual → extra |
| tyre | 6.49 | 10.24 | 10.33 | −0.09 | launch_help usual → extra, peak 5000, users_total 2000 |
| iob-trade | 4.65 | 5.02 | 5.04 | −0.02 | deadline_months – → 6, launch_help usual → extra |
| iob-website | 2.87 | 6.931 | 6.930 | +0.001 | design custom → some, web_domain commercial → client |

(₹ Cr, P50.) Only canara has a material gap: the chatbot task level is the seventh price-driving
answer there (−0.52 Cr).

Single swaps also do not add up to the six-swap total, because commercial costs (margin,
contingency, GST, guarantees) sit on top of every line and the support lines multiply staff by
hours by years. The six together move the price by more than the sum of the singles:

| Tender | Sum of single swaps | Six together |
|---|---:|---:|
| battery | +2.39 | +2.75 |
| canara | +2.56 | +2.59 |
| iob-chatbot | +3.31 | +3.31 |
| meghalaya | −1.47 | −1.47 |
| ewaste | +2.18 | +2.22 |
| tyre | +3.60 | +3.75 |
| iob-trade | +0.35 | +0.37 |
| iob-website | +4.00 | +4.06 |

## 2. Legacy back-test (not the production path) vs run B: two different paths

**The back-test is not expected to reproduce run B.** It runs on a path the app does not use. Only
the `backtest` command calls `benchmark_request()`; an upload in the app never does. That function
hard-codes:

- features: the hand list in `seeds/benchmarks/india.yaml` (`model.features`). The scope was read
  by the keyword reader (each value_note says "scope read from the full document by the keyword
  reader");
- feature levels by size class (`LEVEL_BY_SIZE`: standard for medium, advanced for large);
- `scale` from the size class (`SCALE_BY_CLASS`; up_to_1l for these 8);
- `ai_use` (scored without AI tools);
- hosting `aws` if `hosting_included`, else `existing`;
- helpdesk_scope yes/no from a flag (no for all 8);
- security_audit and reporting set to yes for government above small;
- support_years from om_years (only if 0, 1, 2, 3 or 5);
- overrides only om_years, deadline_months and onsite_staff, each only if set in the file.

It never sets support_hours, support_staff, availability, disaster_site, penalties, build_type,
extra features, scope items or a payment schedule. It passes no reading to the planner. Seed 7,
200 runs, `today_value` escalation, `pin_size=False`.

**Input difference per tender** (back-test → B):

| Tender | Features (levels) | Extra features | Scope items | Answers B sets that the back-test leaves at the default | Answers that differ |
|---|---|---:|---:|---|---|
| battery | 6 (standard) → 8 (story levels) | 0 → 14 | 0 → 3 | build framework, support_hours always, onsite 2, disaster_site, penalties, deadline 6, users 3500, payment schedule | helpdesk no → yes, scale up_to_1l → up_to_10k |
| canara | 9 (advanced) → 16 | 0 → 19 | 0 → 6 | build ready_product, support_hours on_call, languages 10, peak 1000, deadline 2 | hosting existing → aws, scale up_to_1l → up_to_10k |
| iob-chatbot | 12 (advanced) → 13 | 0 → 19 | 0 → 13 | build ready_product, support_hours always, onsite 1, chatbot advanced, languages 11, deadline 3 | helpdesk no → yes, reporting yes → no |
| meghalaya | 10 (advanced) → 13 | 0 → 14 | 0 → 9 | build framework, support_hours office, onsite 5, design custom, old data, languages 4, payment schedule | helpdesk no → yes, hosting existing → indian_cloud, reporting yes → no, scale up_to_1l → up_to_10k |
| ewaste | 6 (standard) → 8 | 0 → 8 | 0 → 0 | build custom, support_hours always, onsite 1, support_staff 1, old data | helpdesk no → yes, om_years 6 → 5 |
| tyre | 7 (standard) → 8 | 0 → 12 | 0 → 3 | build custom, support_hours office, onsite 3, payment schedule | helpdesk no → yes, scale up_to_1l → up_to_10k |
| iob-trade | 8 (standard) → 7 | 0 → 29 | 0 → 9 | build ready_product, availability high, support_hours on_call, onsite 4 | helpdesk no → yes, reporting yes → no |
| iob-website | 8 (standard) → 10 | 0 → 22 | 0 → 11 | build cms, availability critical, support_hours on_call, onsite 1, design custom, languages 2, deadline 4, payment schedule | helpdesk no → yes, hosting existing → aws, reporting yes → no |

The back-test also sets no guarantee amounts (EMD, performance guarantee); B takes them from the
document.

- **Timeline:** the same function prices both. The back-test sets no deadline for these 8, so none
  is infeasible there. In B only tyre's deadline is infeasible (priced again without it).
- **Blank key:** it changes nothing in either path here. The back-test makes no AI call. Run B's
  reading came through a relay that called `ai_read` directly, so the blank key never triggered the
  app's fallback. In the app, an upload with no key falls back to `basic_read` (the keyword reader,
  `basic_reader_v1`; `services/documents/service.py`, `LLMNotConfiguredError`). That is the same
  reader the back-test's scope came from.
- **Model:** run B's reading was made by a stand-in, a Sonnet subagent in Claude Code, **not the
  production model call**. The app calls `llm_model = "claude-sonnet-5-5"`
  (`app/core/config.py:56`) through `AnthropicClient` with its own prompt and caching. The two
  readings can differ.

**Which path reflects production:** B+doc (upload → AI reading → review form filled in → planner
with the reading). With no key set, production reads with the keyword reader instead, as the
back-test's scope did, but it still uses the review form and planner, not `benchmark_request()`.

| Ratio | legacy back-test (not the production path) | B | B+doc |
|---|---:|---:|---:|
| battery | 0.44 | 2.51 | 2.59 |
| canara | 0.49 | 0.47 | 0.47 |
| iob-chatbot | 0.70 | 0.64 | 0.65 |
| meghalaya | 0.14 | 0.27 | 0.28 |
| ewaste | 0.19 | 0.67 | 0.69 |
| tyre | 0.77 | 2.72† | 2.82† |
| iob-trade | 0.38 | 1.47 | 1.49 |
| iob-website | 0.31 | 0.63 | 0.65 |

## 3. Answer accuracy: engine answer vs hand answer

Single swap = B with only that answer changed to the hand answer (P50, ₹ Cr). Hand sources are the
hand mapper's citations into the tender (A-numbers are its requirement ids). Engine answers come
from the engine reading through the review-form prefill. Rows where the two agree are left out
(listed after the table).

| Tender | Answer | Engine (B) | Hand | Hand source | Single swap |
|---|---|---|---|---|---:|
| iob-chatbot | onsite staff | 1 | 5 | onsite developer A281 p.57 + onsite L2 A452 p.103 + L1/L2/L3 one per shift A298 p.61, A467 p.115 | +3.31 |
| iob-website | support staff | – | 5 | offsite team "not less than 5" A183, att01 p.71 | +3.10 |
| tyre | support hours | office | always | 24x7 turnkey operation A129, att01 p.17 (7.0) | +1.87 |
| ewaste | support staff | 1 | 4 | helpdesk 2 (BoQ item 8) + support centre 2 (BoQ item 10b), att01 p.55 | +1.85 |
| canara | support hours / helpdesk | on_call / no | always / yes | onsite 365x24x7 A164 att08 p.4; 24x7x365 A186 p.11 | +1.74 |
| meghalaya | build type | framework | ready_product | low-code OEM platform, 3-yr licence A49, A173, att05 p.1, 7-8 | −1.47 |
| tyre | support staff | – | 3 | support centre 3 developers, BoQ 12b, att01 p.37 | +1.37 |
| iob-website | support hours | on_call | always | 24x7 support A180 p.71; 24x7 incident response A167 p.68 | +1.29 |
| iob-trade | support hours | on_call | always | 24x7x365 A221 p.87, A237 p.79; onsite 24x7 p.119 | +1.21 |
| battery | support years (om_years) | 5 | 6 | 1-yr warranty A83 + "05 Years AMC" A84, att02 p.15 | +1.12 |
| tyre | onsite staff | 3 | 4 | 3 programmers A122 p.17 (6.8) + TL/PM A103 p.15 (6.4) | +1.06 |
| ewaste | onsite staff | 1 | 2 | BoQ 10(a): 2 developers at HO year 1, att01 p.55 | +0.87 |
| iob-trade | onsite staff | 4 | 3 | cost tables IV-VI, 1 L1 + 1 L2 + 1 developer, att01 p.117-119 | −0.86 |
| canara | onsite staff | – | 1 | Table D, 60 resource-months over 60 months, att08 p.58 | +0.82 |
| battery | onsite staff | 2 | 3 | 2 TL/PM A75 att02 p.14 + 1 full-stack A87 p.15 | +0.82 |
| tyre | build type | custom | framework | extends CPCB's own portal A21/A22 att01 p.7 | −0.70 |
| ewaste | build type | custom | framework | "maintain/upgrade/integrate existing" A82 att01 p.4 | −0.54 |
| battery | support staff | – | 2 | support centre 2 developers, BoQ 12(b), att03 p.3 | +0.46 |
| iob-website | build type | cms | ready_product | licensed CMS required A65, att01 p.56, 63, 70 | −0.40 |

Agreeing rows (swap = 0): hosting on all 8; build type on battery, canara, iob-chatbot, iob-trade;
support hours on battery, iob-chatbot, ewaste, meghalaya; onsite staff on meghalaya, iob-website;
support staff (none) on canara, iob-chatbot, iob-trade, meghalaya. Support years differs only as
`per_year` vs a number on the form; om_years drives the price and differs only on battery.

**Ranked by total impact** (sum of |single swap|):

| Rank | Answer | Total | Net | Tenders that differ |
|---:|---|---:|---:|---:|
| 1 | onsite staff | 7.74 | +6.03 | 6 |
| 2 | support staff | 6.78 | +6.78 | 4 |
| 3 | support hours / helpdesk | 6.11 | +6.11 | 4 |
| 4 | build type | 3.12 | −3.12 | 4 |
| 5 | support years | 1.12 | +1.12 | 1 (battery) |
| 6 | hosting | 0 | 0 | 0 |

## 4. Hand-answer audit: every judgement call

Each line is a call the hand mapper made where the tender allows another reading. **Bold** = one of
the six largest single-swap impacts.

**iob-chatbot**
- **Onsite staff 5 (+3.31).** Adds 1 onsite developer (A281 p.57), 1 onsite L2 for year one (A452
  p.103) and the managed-service L1, L2, L3 at one per shift (A298 p.61, A467 p.115). The reading
  lists them as onsite, but the text does not say where they sit (A453 says "onsite/offsite"). If
  offsite, onsite would be 2 with 3 support staff. The onsite L2 is year one only, but is priced for
  the full support period. The per-shift count is used as a head count; 24x7 at 4.2 people per seat
  would be far more (section 6).
- Build type ready_product: COTS chatbot, perpetual licence plus ATS (A2 p.9, A32, A33).
- Hosting existing, not on_prem: the bank supplies all hardware (A3, A288, A423).

**iob-website**
- **Support staff 5 (+3.10).** Offsite team "not less than 5" (developer, designer, server admin,
  tester, QA; A183 p.71) collapsed into one count, for all support years.
- Support hours always (+1.29): 24x7 malfunction support and incident response (A180, A167) used.
  The onsite person's hours conflict on the same page (9-7 vs 8-10, A181). on_call would also fit
  "malfunction support with online logging".
- Build type ready_product (−0.40): licensed CMS (Adobe, Liferay, Sitecore) required (A65). "cms"
  would also fit a licensed CMS with custom modules.
- om_years 5: warranty 1 + maintenance 4 (A190 p.73); the contract runs 5 years from the purchase
  order (about 4.7 years after go-live); a 2-year extension is not used.
- Hosting aws: closest option to "dedicated servers in two seismic zones, deployable on public or
  private cloud" (A29, A69, A175).

**tyre**
- **Support hours always (+1.87).** The 24x7 is the "turnkey operation" (A129 p.17); the onsite
  programmers work 5 days a week in office hours (A122). No shift staffing is stated.
- Support staff 3 (+1.37): BoQ 12(b), 3 support-centre developers for 5 years. The service desk text
  says 2 then 1 (A148 p.35); 2 remote developers (A104) are not added.
- Onsite staff 4 (+1.06): 3 programmers + 1 TL/PM. "At least one programmer" for maintenance (6.9
  iii) is taken as one of the 3; adding it gives 5. The senior IT expert (place not stated) is left
  out.
- Build type framework (−0.70): extends CPCB's in-house portal (A21, A22); custom fits if the portal
  is seen as replaced.
- om_years 6 (1 + 5 AMC); the AMC can run until CPCB replaces the system (p.16).

**ewaste**
- **Support staff 4 (+1.85).** Two BoQ lines added together: helpdesk 2 (item 8) + support centre 2
  (item 10b), both for 2 years only. The senior IT expert + 2 remote developers (A121) are left out.
- Onsite staff 2 (+0.87): BoQ 10(a), 2 developers in year 1, then 1 in years 2-5; the year-1 count is
  priced for all years. The TL/PM (A122) and the 5-day programmer (A123) are left out (would make 4).
- Support hours always: 24x7 stated (A110, A118), but 2 helpdesk people cannot cover shifts.
- om_years 5 from the BoQ and project duration (p.51, p.55); the scope of work says 1 + 5 = 6 (A113).
- Build type framework (−0.54): "maintain/upgrade/integrate existing" EPR modules (A82).

**canara**
- **Support hours always + helpdesk yes (+1.74).** Onsite resources 365x24x7 (A164), support
  24x7x365 (A186), complaint booking (A183).
- Onsite staff 1 (+0.82): derived from Table D, 60 resource-months over 60 months (A199 p.58). No head
  count is stated ("Bank decides number", A164), and the 60 resource-months mix onsite and offsite.
  24x7 onsite cover would need several people. The project manager is not counted.
- om_years 5: 3 warranty + 2 ATS (another passage says 1 + 4; same total).
- Hosting aws: SaaS from a dedicated cloud in India (A68, A197); on-premises is possible at the
  bank's choice (A155).
- Chatbot task advanced (−0.52 when left out of the six swaps; section 1).

**meghalaya**
- **Build type ready_product (−1.47).** Back-end on a low-code OEM platform with a 3-year licence
  line (A49, A173); the rest is bespoke. framework (engine) fits the bespoke part.
- Onsite staff 5: PM 1 + SA 2 + DBA 1 + UI/UX 1 (att11 p.1). These are project key personnel, not
  stated as support staff; the DBA is 6 months in att13 p.66.
- Hosting indian_cloud: the SI hosts per p.3 and p.23, but the department procures per p.2, and
  infrastructure is billed at actuals with the bidder quoting an agency fee only (A167).
- om_years 2: ATS after acceptance; the 3-month adoption gap is not modelled.

**iob-trade**
- Onsite staff 3 (−0.86): the priced cost tables (1 L1, 1 L2, 1 developer × 365 days, p.117-119) are
  used. The scope text needs at least 4 L1 in two shifts + 1 L2 + 1 developer = 6 (A222 p.87).
- Support hours always (+1.21): 24x7x365 helpdesk and SLA (A221, A237); onsite L1 is 8 am-8 pm.
- om_years 5 (1 + 4 ATS); the optional 3-year extension is not used.

**battery**
- om_years 6 (+1.12): scope of work, 1 warranty + 5 AMC (A83, A84). att04 p.2 says 5 in total (A96).
- Onsite staff 3 (+0.82): 2 TL/PM + 1 full-stack at CPCB. The support centre (A93) could sit at the
  client but is counted as support staff.
- Support staff 2 (+0.46): support centre, BoQ 12(b). The senior expert + 2 remote developers (A77)
  are left out (would make 5).
- Support hours always: 24x7 helpdesk (A73), no shift staffing stated.

## 5. Run A: build vs operations

Likely values (₹ Cr, incl. GST). Build = pre-build, build, go-live and programme lines. Operations =
the `run.*` lines (support, onsite staff, AMC, AI runtime) except hosting. Hosting = hosting, DR,
backups, SSL and domain. Other = commercial (margin, contingency, guarantees, GST).

| Tender | Build | Operations | Hosting | Other | Likely sum | P50 |
|---|---:|---:|---:|---:|---:|---:|
| battery | 0.67 (10%) | 4.23 (61%) | 0.00 | 2.01 (29%) | 6.91 | 7.97 |
| canara | 0.48 (10%) | 2.02 (43%) | 0.92 (19%) | 1.34 (28%) | 4.76 | 5.45 |
| iob-chatbot | 0.47 (7%) | 4.17 (64%) | 0.00 | 1.83 (28%) | 6.47 | 7.46 |
| meghalaya | 0.25 (12%) | 1.11 (54%) | 0.11 (5%) | 0.58 (28%) | 2.05 | 2.34 |
| ewaste | 1.20 (16%) | 4.02 (54%) | 0.00 | 2.18 (29%) | 7.40 | 8.46 |
| tyre | 1.22 (13%) | 5.66 (58%) | 0.00 | 2.85 (29%) | 9.74 | 11.12 |
| iob-trade | 0.31 (7%) | 2.97 (65%) | 0.00 | 1.32 (29%) | 4.59 | 5.26 |
| iob-website | 0.31 (5%) | 3.86 (62%) | 0.25 (4%) | 1.76 (28%) | 6.19 | 7.07 |

Hosting is near zero where the client hosts (battery, iob-chatbot, ewaste, tyre, iob-trade).

## 6. Staff check: person-months the tender asks for

Person-months (pm) = roles × months stated in the tender, from the hand reading. Published ÷ pm =
the whole contract price (build, licence, hosting, GST) divided by those months. It is an upper
bound on what the staff could cost, not a staff rate.

| Tender | Roles × months (source) | pm | Published today ÷ pm | Award ÷ pm |
|---|---|---:|---:|---:|
| battery | TL/PM 2 × 66 (att02 p.14) + full-stack 1 × 48 (att02 p.15; AMC 4 yrs att04 p.2) + support centre 2 × 24 (att03 p.3, BoQ 12b). Senior expert and 2 remote developers left out (no duration) | 228 | ₹87k | ₹69k |
| ewaste | developers at HO 2 × 12 + 1 × 48 (BoQ 10a, p.51/55) + helpdesk 2 × 24 (BoQ 8) + support centre 2 × 24 (BoQ 10b) | 168 | ₹4.82 L | ₹3.83 L |
| tyre | programmers 3 × 75 (p.17, 6.8) + TL/PM 1 × 75 (p.15) + service desk 2 × 24 + 1 × 48 (p.35, 16.0h) + support centre 3 × 60 (p.37, BoQ 12b). The 6.9(iii) programmer not added (overlap) | 576 | ₹41k | ₹33k |
| iob-trade | cost tables: 3 × 60 (pp.117-118) | 180 | ₹1.76 L | ₹1.63 L |
| iob-trade | scope text: 4 L1 + 1 L2 + 1 developer = 6 × 60 (p.87) | 360 | ₹88k | ₹82k |
| iob-website | onsite 1 × 60 (p.71) | 60 | ₹7.56 L | ₹7.00 L |
| iob-website | plus offsite team ≥ 5 × 56 (p.71) | 340 | ₹1.33 L | ₹1.24 L |
| canara | Table D, 60 resource-months (att08 p.58) | 60 | ₹9.61 L | ₹7.63 L |
| iob-chatbot | L1/L2/L3 one per shift × 60 = 180 seat-months + onsite L2 12 (p.61, 115, 103) | 192 | ₹3.19 L | ₹2.73 L |
| iob-chatbot | the same seats at 4.2 people per 24x7 seat = 756 + 12 | 768 | ₹80k | ₹68k |
| meghalaya | PM 1 + SA 2 + DBA 1 × ~36 months (att11 p.1) | 144 | ₹9.80 L | ₹7.78 L |
| meghalaya | DBA 6 months only (att13 p.66) | 114 | ₹12.38 L | ₹9.83 L |

**Our engine's own rate per person-month**, for comparison:

- rate card cost, `role.developer` (onsite and support role): ₹3,121 a day × 22 = **₹68,662**;
- engine onsite line (`run.onsite_resources`) per onsite person-month in run A: **₹87,008** where
  only onsite staff land in that line (canara, iob-chatbot, iob-trade); meghalaya ₹77,121. The
  others share the line with support staff, so per onsite month it reads higher: battery ₹1.05 L,
  tyre ₹1.16 L, ewaste ₹1.75 L, iob-website ₹4.10 L;
- all-in, after commercial (× 1.39 to 1.42 in run A): about **₹1.21 L to ₹1.23 L**.

Read side by side: battery, tyre, iob-trade (scope-text count) and iob-chatbot (4.2 per seat) have
published ÷ pm at or below our all-in ₹1.2 L per staff month, so the published price leaves little
or nothing beyond the staff. Canara, iob-website (onsite only), ewaste and meghalaya are 4 to 10
times our all-in rate per month.

## 7. Exclusion rule and band medians

**Rule (pass-through):** leave a tender out of band medians when part of its scope is billed at
actuals and not quoted by the bidder, so the published value cannot be matched to what we price. It
is a case of the file's `unreliable_price` rule ("the price cannot be matched to a scope").

Applied to all 8 from the hand readings:

| Tender | Caught | Why |
|---|---|---|
| meghalaya | yes | infrastructure on actuals, bidder quotes agency fee only (A167, att05 p.23; A158 marks the cloud bill as on actuals) |
| iob-chatbot | no | managed services billed on actual headcount (A297), but at quoted per-role rates; nothing passed through |
| the other 6 | no | no at-actuals or pass-through line in the hand reading |

It catches **meghalaya only**.

For comparison, the file's written `subscription` rule ("a subscription or licence of an existing
product … not a build"), tested as "the reading's ready_product is true", catches 5: canara,
iob-chatbot, iob-trade, iob-website and meghalaya. iob-website (site built on a licensed CMS) and
meghalaya (back-end on a licensed platform, the rest bespoke) are borderline. With it, no large
tender is left. That rule is shown, not applied.

**Band medians** (ratio our P50 ÷ published, today's money):

| Band | Tenders | A | B | B+doc | C |
|---|---|---:|---:|---:|---:|
| medium | battery, ewaste, tyre, iob-trade, iob-website (none caught) | 1.66 | 1.47 | 1.49 | 1.59 |
| large, meghalaya excluded | canara, iob-chatbot | 1.08 | 0.55 | 0.56 | 1.10 |
| all 7 | | 1.56 | 0.67 | 0.69 | 1.53 |
| *large, all 3 (before the rule)* | | *0.94* | *0.47* | *0.47* | *1.00* |
| *if the subscription rule were applied:* 3 CPCB only | | *4.00* | *2.51* | *2.59* | *3.89* |

**Meghalaya, reported separately:** published ₹14.12 Cr today (award ₹11.21 Cr, 2023). Ratios: A
0.17, B 0.27, B+doc 0.28, C 0.17. Run A prices it at ₹2.34 Cr.

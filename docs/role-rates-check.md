# Role-rate check: each staff line at its own role's rate

Date: 2026-10-25. A check only: no code, seed or rate changed. No AI or API call. No tender was
re-read: the staff lines are the ones in `backend/tests/fixtures/readings_v9/`. Today every
staff line is priced at the developer rate (`onsite_role` / `support_role`).

## The mapping

| Tender | Name in the tender | Clause | Rate-card role |
|---|---|---|---|
| battery | Team Leader or Project Manager | att02 p.14 "two qualified and competent staff (Team Leader or Project Manager) at CPCB" | project_manager |
| battery | technical support center developers | att03 p.3, BoQ 12(b) | developer |
| battery | full stack developer at CPCB HO | att02 p.15 | developer |
| ewaste | helpdesk support professionals | att01 p.55, BoQ item 8 | helpdesk_executive |
| ewaste | developer at CPCB Head Office | att01 p.55, BoQ 10(a) | developer |
| ewaste | second developer at CPCB Head Office (1st year AMC) | att01 p.55, BoQ 10(a) | developer |
| ewaste | technical support center developers | att01 p.55, BoQ 10(b) | developer |
| tyre | technical support center developers | att01 p.37, BoQ 12(b) | developer |
| iob-chatbot | onsite developer | att01 p.57, item 29 | developer |
| iob-trade | onsite developer | att01 p.117, Table VI | developer |
| iob-trade | onsite L1 support | att01 p.117, Table IV | helpdesk_executive (L1 = first-line support) |
| meghalaya | Project Manager | att11 p.1 | project_manager |
| meghalaya | System Analyst | att11 p.1 | business_analyst (closest; no system-analyst role) |
| meghalaya | UI/UX Designer | att11 p.1 | ui_ux_designer |

**Unmapped roles** (priced at the developer rate):

| Tender | Name | Why unmapped |
|---|---|---|
| canara | dedicated offsite support resource | role not named |
| iob-chatbot | L1, L2 and L3 managed-services resources | three levels in one line |
| iob-chatbot | onsite support engineer (L2 level) | no support-engineer role in the rate card |
| iob-website | onsite support resource | role not named |
| iob-website | off-site team (developer, designer, hosting / server admin, tester, quality assurer) | five roles in one line |
| iob-trade | onsite L2 support | no support-engineer role in the rate card |
| meghalaya | Database Administrator | no DBA role in the rate card |

## The rates (rate card v9, unchanged)

All are **employee cost**, not billing rates: PayScale India average CTC × 1.15 (office, HR,
leave, bench) ÷ 264 working days. Profit is added only by the estimate's margin. The 1.15 is a
reasoned figure, not published (rate card v7 note).

| Role | ₹ per day | Source |
|---|---:|---|
| developer | 3,121 | salary data: PayScale IN avg CTC ₹7,16,462 (n=2,101) |
| project_manager | 7,877 | salary data: PayScale IN avg CTC ₹18,08,231 |
| helpdesk_executive | 1,638 | salary data: PayScale IN avg CTC ₹3,76,067 (**n=22, small sample**) |
| business_analyst | 3,235 | salary data: PayScale IN avg CTC ₹7,42,591 (n=970) |
| ui_ux_designer | 2,640 | salary data: PayScale IN avg CTC ₹6,06,130 (n=181) |

- **NICSI rate contract:** not used. The rate card notes that NICSI, GeM and MeitY per-role
  rates are per empanelment and not public.
- **Minimum wage for L1 helpdesk:** not used. The helpdesk rate is PayScale salary data from a
  small sample.
- No rate here is a placeholder. No rate was changed to fit these 8.

## Predictions (written before the run)

Method: one developer onsite for 5 years adds about ₹0.87 Cr at P50 (iob-chatbot, verification
sheet), about ₹557 of P50 per ₹1 of day rate per person-year. Support staff (offsite) only add
their shortfall over the support work already priced, so their role mostly doesn't move the
price.

| Tender | Now | Predicted | Why |
|---|---:|---:|---|
| battery | 2.44 | **2.57** | 2 onsite TL/PM at the PM rate for 5 years: about +₹0.27 Cr |
| ewaste | 0.63 | **0.63** | helpdesk staff are support staff, already covered by the support work |
| tyre | 2.52 | **2.52** | developers only |
| iob-trade | 1.22 | **1.21** | 1 onsite L1 at the helpdesk rate for 5 years: about −₹0.04 Cr |
| iob-website | 1.34 | **1.34** | unmapped |
| canara | 0.66 | **0.66** | unmapped |
| iob-chatbot | 0.72 | **0.72** | developer or unmapped |
| meghalaya | 0.28 | **0.28** | PM up, designer down, 2 years: about +₹0.05 Cr on ₹14 Cr |
| Medium median | 1.34 | **1.34** | |
| Large median | 0.66 | **0.66** | |
| Inside the range | 4 of 8 | **4 of 8** | |

Expected verdict: the rates are sourced, but the effect is small, and it moves battery the wrong
way.

## Results

Same run settings as Task 2 (parameters v24, rate card v9, seed 7, 200 runs, without AI tools).

| Tender | Now | Predicted | After | Range after (P10-P90) | Inside |
|---|---:|---:|---:|---|---|
| battery | 2.44 | 2.57 | **3.75** | 2.07-5.57 | no |
| ewaste | 0.63 | 0.63 | **0.63** | 0.36-0.92 | no |
| tyre | 2.52 | 2.52 | **2.52** | 1.43-3.73 | no |
| iob-trade | 1.22 | 1.21 | **1.09** | 0.54-1.62 | yes |
| iob-website | 1.34 | 1.34 | **1.34** | 0.72-1.93 | yes |
| canara | 0.66 | 0.66 | **0.66** | 0.35-1.01 | yes |
| iob-chatbot | 0.72 | 0.72 | **0.72** | 0.37-1.10 | yes |
| meghalaya | 0.28 | 0.28 | **0.31** | 0.16-0.47 | no |

| | Now | After |
|---|---:|---:|
| Medium median | 1.34 | 1.34 |
| Large median | 0.66 | 0.66 |
| Typical miss | 36% | 36% |
| Inside the range | 4 of 8 | 4 of 8 |

**My predictions were wrong for battery, iob-trade and meghalaya, by a factor of 10.** The method
was right, but I slipped a decimal: ₹4,756 a day more × ₹557 per rupee a day is about ₹26.5 lakh
per person-year, not ₹2.65 lakh. With the right arithmetic, the method gives:
- battery 2.44 + 1.33 = 3.77 (result 3.75);
- iob-trade 1.22 − 0.13 = 1.09 (result 1.09);
- meghalaya 0.28 + 0.035 = 0.31 (result 0.31).

So the moves are what the rates should do. The written predictions were not.

## Verdict

- **Sourced:** yes. Every mapped rate is salary data (PayScale), employee cost, unchanged. None
  is from NICSI or minimum wage. The helpdesk rate rests on a small sample (n=22).
- **Coverage:** 7 of the 18 priced staff lines are unmapped. Most tender lines name a level
  (L1, L2) or a mixed team, not one role.
- **Effect:** none on the medians, the typical miss or the count inside the range. Battery moves
  from 2.44x to 3.75x, much further from the published price.
- **A likely double count:** battery's "Team Leader or Project Manager" at CPCB may be the same
  person as the O&M project manager the engine already prices by project size. At the PM rate,
  any overlap now costs much more.
- **Recommendation:** don't adopt this as it stands. Before any role mapping:
  1. decide whether a tender's onsite PM or team leader replaces the engine's own O&M PM line;
  2. add sourced rates for L1 / L2 support engineers and a DBA.

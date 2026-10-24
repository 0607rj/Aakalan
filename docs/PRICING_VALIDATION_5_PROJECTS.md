# Pricing validation — five representative projects (2026-10-19)

What Aakalan actually prices for the five synthetic requirement documents in
`backend/tests/fixtures/srs/`, why, and what that says about the current pricing. This is a
check of internal consistency and scope coverage, not of real-world accuracy: no completed
project with recorded hours exists yet, and the documents are synthetic.

## How the numbers were produced

- **Flow:** the document flow without an API key, as the app runs it. The keyword (basic) reader
  reads each document; the request sends the ticked features, the answers and numbers it found,
  and **every offered scope item confirmed** (as if the user pressed "Tick the suggested ones").
  Questions the document does not answer keep the app's defaults (see "Defaults" below).
- **Engine:** `plan_quick` → `plan_to_input` → `calculate`, in memory (no database), with the
  reference data the app uses after seeding: catalog **v6**, rate card **v5**, parameters **v16**
  (effort multiplier 1.4, margin 15%, GST 18%). Seed 2026, 10,000 Monte Carlo runs, as of
  2026-10-19.
- **Nothing in the pricing was changed** for this validation.

**Units.**
- Money is in rupees; **1 L = ₹1,00,000**.
- **P10 / P50 / P90** are the simulated total price (GST included).
- **Planned** is the sum of the line items' most likely values; the gap between P50 and planned
  is the risk allowance.
- **Hours** are the engine's year-0 person-days × 8: discovery and design, build, launch and
  management. Support years are excluded.
- The engine gives hours as **one most-likely figure only**. It simulates money, not hours, so
  there is no P10/P90 for effort, and the price range must not be read as an effort range.

## 1. Comparison of the five projects

**Price, hours and duration**

| Project | Size (points) | Hours (year 0) | Build months | Planned | P10 | P50 | P90 |
|---|---|---|---|---|---|---|---|
| Clinic Management | small–medium (6) | 2,186 | 2.6 | 58.66 L | 53.43 L | **69.94 L** | 90.99 L |
| E-commerce | small–medium (10) | 2,961 | 3.3 | 72.36 L | 65.96 L | **86.31 L** | 112.16 L |
| Job Portal | small–medium (12) | 3,394 | 3.6 | 81.47 L | 74.27 L | **97.11 L** | 126.37 L |
| AI SaaS | small–medium (6) | 2,425 | 2.8 | 63.55 L | 58.02 L | **75.84 L** | 98.73 L |
| Enterprise ERP | medium (14) | 6,736 | 5.5 | 152.83 L | 139.82 L | **183.42 L** | 238.37 L |

**Share of the planned cost by layer**

| Project | Requested feature blocks | Standard blocks | Management | Run, 3 years | Commercial | Risk allowance (P50 − planned) |
|---|---|---|---|---|---|---|
| Clinic | 11.1% (821 h) | 13.2% (1,019 h) | 9.6% | 35.4% | 28.4% | 11.27 L (19.2%) |
| E-commerce | 14.8% (1,451 h) | 11.2% (1,061 h) | 10.3% | 32.7% | 28.6% | 13.95 L (19.3%) |
| Job Portal | 18.1% (1,879 h) | 9.5% (1,019 h) | 10.2% | 31.1% | 28.7% | 15.64 L (19.2%) |
| AI SaaS | 12.6% (984 h) | 12.7% (1,061 h) | 9.8% | 34.1% | 28.5% | 12.29 L (19.3%) |
| ERP | 14.5% (2,749 h) | 18.2% (3,235 h) | 9.9% | 25.7% | 29.5% | 30.59 L (20.0%) |

- **Requested feature blocks** are the catalog blocks a feature or confirmed scope item asked
  for. **Standard blocks** are the ones every project of that size gets: discovery, design,
  sign-in, front end, testing, documentation, set-up.
- **Commercial** is margin, GST, working capital and the penalty reserve. Parameters v16 have no
  fixed contingency, so risk is carried only by the simulation (the risk-allowance column).

**AI savings and market comparison**

| Project | P50 without AI tools | P50 if the effort data predates AI tools | Published prices of similar-size projects (P25 / median / P75) |
|---|---|---|---|
| Clinic | 70.30 L | 63.31 L | 12.7 / 26.7 / 114.9 L (19 projects, small–medium) |
| E-commerce | 86.34 L | 76.71 L | same 19 projects |
| Job Portal | 97.08 L | 86.21 L | same 19 projects |
| AI SaaS | 76.16 L | 68.40 L | same 19 projects |
| ERP | 183.57 L | 163.86 L | 297.5 / 484.3 / 645.0 L (8 projects, medium) |

## 2. Requirement coverage and how scope reaches the price

**Kinds of coverage used below:**
- **Feature:** a ticked feature that brings its catalog blocks.
- **Scope item:** an item confirmed in "What else does it need?".
- **Standard:** inside the standard blocks.
- **Already included:** confirmed, but its block was already in the project, so it adds ₹0.
- **Partly priced:** only part of the work has a catalog block.
- **Not priced:** listed for the user, no number.
- **Unpriced:** no feature or item matches. It is only priced if the user adds it as their own
  feature.

**Scope-item columns:**
- "Δ hours / Δ planned" is the change when the item is removed and the project re-priced. It
  includes management, support and commercial effects.
- "Building cost" is what the result's "What else you asked for" list shows: the block's own
  line only.

### 2.1 Clinic Management System

**Requirement coverage**

| Requirement (clause) | Coverage |
|---|---|
| Appointments (3.3) | Feature *bookings* → booking block M (379 h, 2.57 L) |
| Online payment (3.5) | Feature *payments* → payment-gateway block M (151 h, 1.75 L) |
| Dashboard (3.6) | Feature *dashboards* → reports block M (227 h, 1.58 L) |
| Pay when booking (3.5) | Scope *booking_payment*: **already included** (payments brings the gateway) |
| Email reminders (3.4) | Scope *booking_reminders*: **adds** the SMS / email gateway S (Δ 30 h, Δ planned 0.70 L; building cost ≈ 30,000). Notifications is already a standard block at this size |
| Roles, accounts (2.1, 3.1) | Standard (user-accounts block S, 76 h) |
| Doctor profiles (3.2) | **Unpriced**: no feature or item |
| MFA "not required" (5.2) | Set aside as ruled out; not priced ✓ |
| WhatsApp "Phase 2" (7.1) | Set aside as later; not priced ✓ |
| ERP "out of scope" / "currently uses" (1.3–1.4) | Not found as a feature ✓ |
| DPDP Act (5.3) | Not priced, listed ✓ |

**Sensitivity**

| Change | Δ hours | Δ planned | Δ P50 |
|---|---|---|---|
| Add Google sign-in | +45 h | +1.07 L | +1.31 L |
| Add one-time codes (needs the SMS gateway) | 0 | 0 | 0 (correct: reminders already brought the gateway) |

### 2.2 E-commerce Platform

**Requirement coverage**

| Requirement (clause) | Coverage |
|---|---|
| Catalogue, cart, checkout (3.1, 3.3) | Feature *online_store* → store block M (631 h, 4.25 L); its payment gateway is shared with *payments* (one block) |
| Search (3.2) | Feature *search* → search block M (127 h, 1.08 L) |
| GST invoice (3.6) | Feature *billing* → billing block M (315 h, 2.03 L); scope *store_invoices* **already included** |
| Subscriptions with pause / cancel (3.5) | Scope *subscriptions*: **already included** (billing block). See issue 6 |
| Order tracking (3.7), customer accounts | Inside the store block / standard (no separate item) |
| Seller payouts, video calls (6.1–6.2) | Ruled out; not listed ✓ |
| Loyalty and mobile app "phase 2" (7.1) | Not found ✓ |
| PCI DSS (5.1) | Not priced, listed ✓ |

**Sensitivity**

| Change | Δ hours | Δ planned | Δ P50 |
|---|---|---|---|
| Add an API / webhooks for a courier (a separate integration) | +53 h | +1.22 L | +1.51 L |

### 2.3 Job Portal

**Requirement coverage**

| Requirement (clause) | Coverage |
|---|---|
| Applications (3.2) | Feature *online_forms* → application block M (403 h, 2.58 L) + master-data block M (151 h, 1.04 L) |
| Resume upload (3.3) | Feature *documents* → document block M (315 h, 2.28 L) + search block |
| Search (3.4) | Feature *search* (shares the search block) |
| Recruiter workflow (3.5) | Feature *approval_workflow* → workflow block M (504 h, 4.54 L) |
| Email alerts (3.6), OTP (3.8) | Feature *notifications*; scope *workflow_alerts* and *otp_codes* **already included** |
| Reports (3.7) | Feature *dashboards*; scope *workflow_reports* **already included** |
| Google sign-in (3.9) | Scope *social_login*: **adds** the SSO block S (Δ 40 h, Δ planned 0.94 L) |
| Job posting by recruiters (3.1) | **Unpriced** as such (no item) |
| Advanced permissions (2.2) | Ruled out ✓ |
| LinkedIn (6.2) | Later phase; no item ✓ |

**Sensitivity:** Google sign-in is already confirmed in the base scope, so it was measured by
removing it: +40 h, +0.94 L planned.

### 2.4 AI SaaS Platform

**Requirement coverage**

| Requirement (clause) | Coverage |
|---|---|
| Document upload (3.1) | Feature *documents* (315 h, 2.28 L) |
| Payments and invoices (3.4–3.5) | Features *payments*, *billing* |
| Recurring subscription (3.4) | Scope *subscriptions*: **already included** (billing block) |
| Webhooks (3.6) | Scope *public_api*: **adds** a general integration block S; **partly priced** (Δ 59 h, Δ planned 1.35 L; building cost ≈ 56,000) |
| Two-factor for owners (3.7) | Scope *two_step_sign_in*: **adds** the gateway; **partly priced** (Δ 30 h, Δ planned 0.70 L) |
| **AI field extraction — the product's core (3.2)** | **Unpriced** in this flow. The keyword reader cannot size it; only an AI reader or the user adding it as their own feature would |
| Usage limits (3.3) | **Unpriced** |
| Multi-tenant workspaces (1.2) | Not priced, listed ✓ |
| Public bulk API and chatbot "later" (7.1–7.2) | Not priced ✓ (the chatbot feature is correctly not found) |

**Sensitivity**

| Change | Δ hours | Δ planned | Δ P50 |
|---|---|---|---|
| Add the core AI extraction as the user's own AI feature (size M) | **+266 h** | **+5.63 L** | **+7.03 L (+9%)** |
| Webhooks (with vs without, already in the base) | +59 h | +1.35 L | — |

### 2.5 Enterprise ERP (and corrigendum)

**Requirement coverage**

| Requirement (clause) | Coverage |
|---|---|
| Approvals (3.1) | Feature *approval_workflow* (504 h, 4.54 L) |
| Stores / inventory (3.2) | Feature *inventory* (631 h, 4.07 L) |
| Invoices and receipts (3.3) | Feature *billing* |
| Document repository (3.4) | Feature *documents* |
| Reports and pendency (3.7) | Feature *dashboards*; scope *workflow_reports* **already included** |
| Legacy payroll connection (3.10) | Feature *connect_existing* → existing-system block M (252 h, 2.73 L) |
| Single sign-on with Active Directory (4.1) | Feature *staff_login*; scope *enterprise_sso* **already included** |
| Audit trail (3.6) | Scopes *audit_log*, *workflow_audit*, *documents_audit*: **already included** (a standard block at medium size; charged once) |
| Vendor webhooks (3.8), nightly bank import (3.9), digital signature (3.5) | **Three separate** general integration blocks S, each Δ 59 h, Δ planned 1.47 L (two of them partly priced) |
| Multi-tenant group companies (1.2), source-code handover (7.1) | Not priced, listed ✓ |
| HR module and finance beyond invoices (1.1) | **Unpriced** (no feature) |
| Two vague clauses (6.1–6.2) | Pre-bid queries ✓ |
| Availability 99.95% + DR, 24×7, MeitY cloud (5.1–5.3) | Read as answers ✓ |

**Corrigendum scenario** (merged documents: clause 3.5 withdrawn)

| | Value |
|---|---|
| Digital signature | No longer offered; set aside as ruled out |
| Δ hours | −59 h |
| Δ planned | −1.47 L |
| Δ P50 | −1.80 L |
| P50 after the corrigendum | 181.62 L |

### 2.6 Defaults that the documents do not state

None of the five documents gives support years or user numbers, so the app's defaults apply:

| Default | Value |
|---|---|
| Support years | 3 |
| Users | 1,000–10,000 (peak 200) |
| Hosting | AWS, unless the document names one |

The review screen asks these questions before pricing. The tables above use the defaults.

**Effect of support years on the planned cost**

| Support years | Clinic planned / P50 | ERP planned / P50 |
|---|---|---|
| 0 | 27.53 L / 33.26 L | 89.73 L / 108.68 L |
| 1 | 37.09 L / 44.38 L | 109.15 L / 131.13 L |
| 3 (default) | 58.66 L / 69.70 L | 152.83 L / 182.72 L |

The P50 in this table comes from a 3,000-run check, so it differs slightly from section 1.

**Clinic, 3 years of running cost: 20.79 L**

| Item | Cost |
|---|---|
| Hosting | 11.04 L |
| Patching and bug fixes | 6.04 L |
| Change requests | 1.91 L |
| SSL / domain, services, backups | ~1.8 L |

**Clinic hosting, year 1 (≈ 3.4 L)**

| Item | Cost |
|---|---|
| Two small app servers | 84,484 |
| Managed database | 1,58,427 |
| Load balancer | 22,542 |
| Monitoring | 64,590 |

Rates are converted from USD at 96.77 + 3% buffer and escalated 8% a year. The ERP, on an
Indian cloud, gets a lower hosting line (8.86 L for 3 years) plus DR (3.07 L), because the rate
card's Indian cloud prices are lower and it is sized on the same default 200 peak users.

## 3. Plausibility and consistency review

### Is the effort proportionate to the scope?

- **Within each project, yes:**
  - Bigger requested scope → more hours (clinic 2,186 → job portal 3,394 → ERP 6,736).
  - Each priced requirement maps to one block.
  - Scope items add hours only when they add a block.
- **Across the whole price, the requested features are a small part:**
  - Their building work is 11–18% of the planned cost.
  - The rest is standard blocks, management, three default years of running, margin and tax,
    with a ~19% risk allowance on top.
  - On the clinic, functional testing alone (S, 351 h, a standard block) is about as large as
    the bookings feature (379 h).
  - This follows from the catalog's fixed project blocks and the default support years, not
    from an arithmetic error.

### Are large requirements represented by suspiciously small increments?

Yes, in three places. Each is a coverage limit, not a calculation error:
- **AI SaaS:** the core AI extraction is unpriced in the keyword flow. Adding it as the user's
  own AI feature adds +266 h and +7.0 L at P50.
- **ERP:** the HR module and finance beyond invoices are unpriced.
- **Clinic and job portal:** doctor profiles and recruiter job posting are unpriced.
- **Subscriptions (with pause / cancel and repeat charges)** show as "already included" because
  the billing block covers them. Whether the billing block's hours really include
  recurring-billing work is not shown by the catalog's sources.

### Are simple projects dominated by fixed overheads?

- **Yes.** Fixed standard blocks plus management plus running are 50–58% of a small project's
  planned cost. Requested features are 11–15%.
- Without support years the clinic falls from 58.66 L to 27.53 L planned.
- **Whether this is wrong needs completed small projects' hours by activity.** Testing, design,
  set-up and management for real small projects are the missing data.

### Is the enterprise estimate driven by justified scope or by repetition?

- **Justified scope, not repetition.** Three audit items and three reporting / SSO items all
  add 0, and the three integrations are three different systems.
- **But the ERP is sized as a medium project on default users (10,000, peak 200).** A group-wide
  ERP may be larger. The price would follow the users answer once given.

### Are integrations separate only when genuinely distinct?

- **Yes** (`plan_quick`):
  - Shared blocks are one instance (the payment gateway shared by store and payments; the SMS
    gateway shared by reminders and one-time codes).
  - Items on the general integration block get one block each.
  - The legacy payroll connection and the bank import are separate.

### Are AI savings applied by the existing rules?

- **Yes.** In every project only `documentation_manuals` (provisional pre-AI) gets the saving.
  Every other block is unknown-era and gets none (trace: `ai_saving: not applied`).
- So the price with AI tools is about the same as without them (clinic 69.94 L vs 70.30 L).
- The "if the effort data predates AI tools" reading is 9–11% lower and is shown beside the
  price, not in it.

### Are market prices kept apart from the effort estimate?

- **Yes.** The published-price box is computed from the benchmark file, never from the estimate,
  and is labelled as prices, not hours.
- **What it shows:**
  - The four smaller projects sit above the median published price of similar-size projects
    (26.7 L) but inside their wide middle range (12.7–114.9 L).
  - The ERP sits below the medium group's P25 (297.5 L).
  - This is the known pattern from the back-test (the legacy back-test, not the production path). Contract prices cannot say which is right.

## 4. Findings: proven, and what needs data

### Proven by this run (facts about the code and its output)

1. **No arithmetic or double-counting defect was found.** Checked:
   - shared blocks are charged once;
   - already-included items add exactly 0;
   - separate integrations add one block each;
   - removing a confirmed item lowers the estimate by exactly its blocks plus their knock-on
     costs;
   - the corrigendum removes the withdrawn item's cost;
   - an unconfirmed suggestion leaves the price unchanged (by-hand form vs document flow).
2. **The keyword flow leaves some core requirements unpriced** (AI extraction, HR, finance, job
   posting, doctor profiles). The largest measured gap is +7.0 L at P50 on the AI SaaS project.
3. **"What else you asked for" shows only the block's building cost.** For example, webhooks
   show about ₹56,000, while the item raises the planned cost by 1.35 L and P50 by about 1.5 L
   once management, support, margin, tax and risk are added. This is accurate as labelled
   ("building cost"), but a user can easily read it as the price impact.
4. **Defaults the document does not state move the price a lot.** Three support years are 26–35%
   of the planned cost; default users set the hosting and the project size.

### Hypotheses that need real data (not fixed, and not tuned)

5. **Fixed standard blocks are too heavy for small projects** (testing S 351 h, discovery, design,
   set-up). Needs completed small projects' hours by activity.
6. **Recurring billing** priced inside the billing block may under-count subscription logic.
   Needs project hours for billing with and without subscriptions.
7. **Hosting for small apps** (≈ ₹3.4 L a year on AWS at 99.5%: two servers, managed database,
   load balancer, monitoring) may be high for a three-clinic system. Needs provider quotes and
   real bills. The rates are already marked "to verify" in `docs/OPEN_QUESTIONS.md` (102).
8. **Size bias against market prices** (small above, ERP below). Contract prices are not hours;
   needs completed-project costs.

## 5. Ranked issues to investigate next

| # | Issue | Why it matters | Smallest justified next step (not done) |
|---|---|---|---|
| 1 | Unpriced core requirements in the keyword flow | Underestimates the product's main feature (AI SaaS +7.0 L at P50) | Validate the AI reader with a key (it reports unknown capabilities as `other_features`). Until then, say on the review screen that requirements without a match must be added as the user's own features |
| 2 | Silent weight of defaults (support years, users) | 26–35% of small-project price | Show "assumed: 3 years of support, 1,000–10,000 users (not in the document)" next to the price |
| 3 | Scope-item amount shown as building cost only | Users may under-read an item's price impact (₹56,000 vs ≈ 1.5 L) | Show both, e.g. "building ₹56,000; adds about 1.5 L to the price" (display only; the engine already has the numbers) |
| 4 | Fixed-block share on small projects | Possible systematic overestimate of small work | Collect hours by activity from finished small projects; compare per block |
| 5 | Hosting placeholders for small apps | ≈ 11 L over 3 years on the clinic | Replace placeholder rates with quoted ones (new rate-card version) |
| 6 | "Already included" hiding extra work (subscriptions, MFA flow) | Possible under-count | Project hours for these items |

None of these changes pricing formulas without evidence.

## 6. What this shows, and what is still needed

**What the five projects show:**
- **The calculation is internally consistent.** Scope that adds work is priced once, scope that
  is already there adds nothing, ruled-out and later requirements stay out, and a corrigendum
  takes its item back out. Results are reproducible with a fixed seed.
- **The estimate is dominated by project-level and commercial layers, not by the requested
  features:**
  - fixed blocks;
  - three default years of running;
  - margin and tax;
  - a ~19% simulated risk allowance.

  That makes small projects comparatively expensive, and makes the price very sensitive to the
  support-years answer.
- **The largest accuracy risk in the no-key flow is unpriced core scope** rather than
  mis-priced scope.

**What is needed to establish real-world accuracy:**
- hours by activity and role from completed projects (small ones in particular);
- real hosting bills;
- validation of the AI reader on real documents;
- recorded outcomes compared with the estimate's P10–P90.

Synthetic documents and contract prices cannot provide this.

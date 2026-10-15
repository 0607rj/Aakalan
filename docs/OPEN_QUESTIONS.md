# Open questions and chosen defaults

Every item below was unclear or unspecified in `docs/PROJECT_BRIEF.md`. The agent did not stop
to ask; it picked the default shown and moved on. Change any of them by editing the relevant
seed file, config value or code, and update this list.

## Carried over from brief Section 16

| # | Question | Default chosen |
|---|---|---|
| 1 | Final product name | **Aakalan** (working name) |
| 2 | LLM provider / model | Anthropic Claude via API, model name in `LLM_MODEL` config. Bedrock (ap-south-1) is a later `LLMClient` implementation. Not used before M3. |
| 3 | Default O&M years / escalation / GST / contingency | 3 years · 8 %/yr (labour and prices, set separately) · 18 % · 5–15 % interpolated linearly from average clarity (5 → 5 %, 1 → 15 %) |
| 4 | Max team size curve | Simple size-band table in `seeds/parameters/v1.yaml` (`timeline.size_bands`) |
| 5 | Pricing of our own product | Not in v1 |

## Raised while building

| # | Question | Default chosen |
|---|---|---|
| 6 | Repo root vs. `aakalan/` folder in brief Section 5 | The git repo root **is** the `aakalan/` folder. |
| 7 | `make` is not installed on the Windows dev machine | `Makefile` targets are thin wrappers around `python scripts/tasks.py <target>`, a stdlib-only task runner that works without `make`. |
| 8 | Docker is not installed on the dev machine | `docker-compose.yml` and Dockerfiles are written for `python:3.12-slim` / `node` images but could not be verified locally. Local dev uses `uv` + `npm`. |
| 9 | Where engine parameters (multipliers, AI factors, compression curve, hosting sizing rules, spreads…) live | A versioned **ParameterSet** (`seeds/parameters/v1.yaml` → `parameter_sets` table), pinned by each estimate alongside the rate-card version and catalog version. Rate cards hold only prices. |
| 10 | Rate items priced in USD or with sub-paise precision (cloud per-hour, tokens) | `RateItem.amount` is a `Decimal` (stored as a string, never float) in **major units of its `currency`**; USD is converted with the `forex.USD_INR` rate item plus a forex buffer parameter. Cost lines and totals are stored as **integer paise**. |
| 11 | Monte Carlo distribution | Triangular (closed-form inverse CDF), 10,000 runs, `numpy` PCG64. One quantile stream per *uncertainty group* (component instance or run bucket), seeded from `(estimate seed, sha256(group key))`, so adding scope never re-shuffles other groups' draws. PERT can be added as a parameter option later. |
| 12 | How commercial lines (contingency, financing, margin, GST) enter the simulation | Applied to each simulated base total with the same linear factors as the likely case: `total_run = base_run × k + fixed`, where `k` and `fixed` come from the deterministic commercial layer. Documented in the trace. |
| 13 | Brief property "shorter deadline never lowers cost" conflicts with "longer deadline adds programme overhead" | The property is enforced and tested for deadlines **at or below natural duration** (compression region). Above natural duration a longer deadline costs more, as Section 7.3 requires. |
| 14 | Programme costs when the schedule is compressed | Programme (PM, environments, MIS) is costed over `max(deadline, natural duration)`; compressed schedules keep the same management load but raise build labour via the compression multiplier. |
| 15 | Manpower view granularity | Roles × stage with person-days, person-months and average FTE over the build duration, plus FTE per O&M year. No month-by-month loading curve in v1. |
| 16 | O&M year escalation exponent | O&M year *y* is priced at `(1 + escalation)^y` (year 1 assumed to start about a year after the estimate date). |
| 17 | Margin visibility for non-finance roles | Margin line values and `margin_percent` are redacted (null) for `estimator` and `viewer`. Headline totals still include margin, so it can be inferred by subtraction; a separate "cost view" total is a candidate for later. |
| 18 | Requirement source before document ingestion (M1) | Manual requirements carry `source_refs: [{clause_ref, page}]` entered by the user; M3 adds `chunk_id` to the same structure. |
| 19 | Tables from Section 6 not needed until later milestones | M1 creates Organisation, User, Project, Requirement, QuestionnaireAnswer, CatalogComponent, ComponentInstance, RateCard, RateItem, ParameterSet, TaxonomyBucket, Estimate, CostLine, Assumption. Document, Chunk, Flag (M3), Template (M4), Outcome and AuditLog (M5) are added in their milestones. |
| 20 | Template-match strength before templates exist (M1–M3) | Treated as `none`, which adds the `template_match.none` spread and lowers confidence. |
| 21 | Date used for rate-card freshness | An explicit `as_of_date` stored in the estimate snapshot (defaults to the creation date), never "today", so re-runs are reproducible. |
| 22 | Hardware for on-prem scenario | Capex in year 0 (bucket `go_live.infrastructure_procurement`) plus hardware AMC % and colocation per O&M year. |
| 23 | Frontend component library | shadcn/ui-style components are hand-written under `frontend/src/components/ui` (shadcn is copy-in by design); TanStack Table, React Hook Form/Zod and Recharts are added in the milestone that first needs them. |
| 24 | Login identifier | Email + password; JWT (HS256) access token, 8 h expiry, no refresh token in v1. |
| 25 | Dev users | `make seed` creates a demo organisation with `admin@`, `finance@`, `estimator@` and `viewer@aakalan.local`, all with password `SEED_USER_PASSWORD` from `.env` (default `aakalan-dev`). Dev only. |

# Aakalan

Defensible, traceable cost estimates (P10 / P50 / P90) for Government and PSU software tenders.
An LLM reads the requirement document; a deterministic engine computes every number, and every
number traces back to an RFP clause.

- What and why: [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md)
- How to work on it (commands, rules, layout): [`AGENTS.md`](AGENTS.md)
- Design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · Decisions: [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md)

## Quick start

Requires Python 3.12, [uv](https://docs.astral.sh/uv/) and Node 22+.

```sh
cp .env.example .env
make install          # or: python scripts/tasks.py install
make dev              # migrates, seeds demo users, runs API :8000, web :3000 and the worker
```

Sign in at http://localhost:3000 as `admin@gmail.com` with the password from
`SEED_USER_PASSWORD` (default `admin123`; local development only). This single user can do everything; role-based
access (admin / estimator / finance / viewer) exists in the backend but is switched off for now.
API docs: http://localhost:8000/docs.

`make seed` also creates a demo project ("AI chatbot + online empanelment portal (PSU) — demo")
with confirmed requirements, components and answers: open it, go to **Estimate** and click
**Calculate estimate**. Click any cost line to see its trace back to the RFP clause. All seed
rates and parameters are placeholders, so every estimate is labelled *uncalibrated*.

**Reading tender documents.** Upload works without any setup using a basic keyword reader.
For much better reading, create an API key at https://console.anthropic.com, put it in `.env` as
`ANTHROPIC_API_KEY=...` and restart. The AI only reads the document; it never calculates prices.

```sh
make test             # backend pytest + frontend typecheck
make lint             # ruff, mypy, eslint, prettier
```

# Aakalan

**Know what your software will cost before you build it.**

Aakalan ("estimation") prices a software project feature by feature and gives an honest range:
a **low, likely and high** cost for the whole life of the project. That covers the build, going
live, hosting, AI running costs, support and upkeep for the years you choose, and taxes.

It is for anyone who needs a software price they can trust:

- **People and businesses who want software built.** Find out what a website, app or portal
  should cost before you talk to developers, and see what each feature adds.
- **Freelancers, agencies and IT companies quoting a client.** Build an itemised quote in
  minutes instead of a spreadsheet, at your own day rates.
- **Vendors bidding on Indian Government and PSU tenders.** Upload the RFP, SRS or BRD and get
  a price that traces every rupee back to the clause and page it came from.

The price follows what is built, not who orders it: the same features cost the same for a
startup, a shop or a ministry.

## How it works

1. **Tell us what you want to build.** Either type it in your own words ("a clinic booking app
   with payments and SMS reminders") or upload a requirement document (PDF or Word).
2. **Check what we found.** AI reads your words or the document and lists the features it
   finds, each with the sentence or page it came from. You tick, untick and add features, and
   answer a few plain questions: website or app, who builds it, how many users, where it runs.
   Every other answer already has the usual setting, so you change only what is different.
3. **Get your cost.** A fixed calculation engine prices each feature from a dated rate card and
   gives the low / likely / high range. Open any line to see how it was worked out.

**AI reads, it never sets a price.** AI only reads text and suggests features. Every number
comes from the engine, so the same answers always give the same price, and each number can be
traced back to the rate, the hours and the source behind it.

## What you get

- An **itemised price per feature**, with the level of each one (basic, standard, advanced)
  that you can change and see the price move.
- The **whole-life cost**: build, hosting, support, upkeep, AI running costs and GST.
- A **low / likely / high range** from many simulated runs, not one guessed figure.
- **Which answers move the price most**, and what each choice would cost.
- **Checks before you send it**: an independent count of the work, warnings on prices that look
  unusual, and a list of what is not included and what was assumed.
- A **PDF report and an Excel bill of quantities** to share.
- For tenders: each cost line linked to the RFP clause and page, support and staffing terms read
  from the document, and pre-bid queries where the document contradicts itself.
- **Saved estimates and templates**, and bid results that help calibrate future estimates.

Built for India first (prices in rupees, Indian cloud options, GST, Government website rules).
Company data is kept separate per organisation; documents go only to the configured AI provider.

## Run it on your machine

Requires Python 3.12, [uv](https://docs.astral.sh/uv/) and Node 22+.

```sh
cp .env.example .env
make install          # or: python scripts/tasks.py install
make dev              # migrates, seeds, runs the API on :8000, the web app on :3000 and the worker
```

On Windows without `make`, use `python scripts/tasks.py <target>` for every command.

Open http://localhost:3000 and sign up, or sign in as `SEED_USER_EMAIL` (default
`admin@example.com`) with `SEED_USER_PASSWORD` (default `admin123`, local development only).
Without email settings, sign-up codes are printed in the API server log. API docs:
http://localhost:8000/docs.

**AI reading.** Everything works without an AI key: a basic keyword reader finds features in
documents and descriptions. For much better reading, put an Anthropic API key in `.env` as
`ANTHROPIC_API_KEY=...` and restart.

Seed rates and parameters marked `placeholder` are not yet calibrated, and estimates that use
them say so.

```sh
make test             # backend tests + frontend type check
make lint             # ruff, mypy, eslint, prettier
```

## More

- What and why: [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md)
- How to work on it (commands, rules, layout): [`AGENTS.md`](AGENTS.md)
- Design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · Decisions:
  [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md)
- Running it on a server: [`docs/DEPLOY.md`](docs/DEPLOY.md)

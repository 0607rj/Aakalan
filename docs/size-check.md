# Story-size check: a third size for every build (OPEN_QUESTIONS 163)

Date: 2026-10-25. No AI or API call. No tender was re-read: the run used the saved readings in
`backend/tests/fixtures/readings_v9/`, through the app's own path (`create_quick_estimate`, then
the summary). A check only: no price, range or rate changed.

## What it does

For each priced feature, the document's user stories give a size:

```
function points = stories × 4.6  +  stories × 0.3 × 7.0     (6.7 per story)
story hours     = function points × 4.7 / 9.8 / 18.4         (low / likely / high)
our hours       = the feature's share of our building cost × our build hours
                  (without AI tools; planning, build and go-live, so project work is spread in)
```

- **Ours agrees** when it falls between the low and high story hours.
- **Features to check:** those with at least 3 stories that fall outside, furthest first.
- **No verdict on a CMS or ready-product build.** The published rate is for new code, and much of
  such a build is set up, not built, so ours is expected to be lower.
- With the independent check (when the document was counted), the app shows three sizes.
- **On the results page** it is one plain line, e.g. "Our build size matches a standard industry
  method. 2 features may be priced low: A and B. Check them." User stories, function points and
  hours (with and without AI tools) sit behind a closed "How we checked" link.

| Figure | Value | Source |
|---|---|---|
| Points per story (one story = one process) | 4.6 | Simple Function Points (Meli 2010, IFPUG SPM 2021), [Wikipedia](https://en.wikipedia.org/wiki/The_Simple_Function_Point_method). "One story = one process" is our assumption |
| Points per data group | 7.0 | Same source |
| Data groups per story | 0.3 | **Placeholder**, reasoned: data is about a quarter to a third of the points in a business application |
| Hours per point | 4.7 / 9.8 / 18.4 | ISBSG delivery rate, new development, 300-500 FP, n=488 (P25 / median / P75), [van Heeringen](https://www.slideshare.net/slideshow/the-value-of-benchmarking-software-projects/28954202). Pre-AI projects, so compared with our hours without AI tools |

## Results on the 8 readings

| Tender | Built as | Stories | Our hours | Story hours (low-likely-high) | Ours ÷ likely | Verdict |
|---|---|---:|---:|---|---:|---|
| battery | from scratch | 47 | 2,562 | 1,480 - 3,086 - 5,794 | 0.83 | agree |
| ewaste | from scratch | 36 | 2,661 | 1,134 - 2,364 - 4,438 | 1.13 | agree |
| tyre † | from scratch | 51 | 3,351 | 1,606 - 3,349 - 6,287 | 1.00 | agree |
| meghalaya | from scratch | 38 | 3,405 | 1,197 - 2,495 - 4,685 | 1.36 | agree |
| canara | ready product | 57 | 1,840 | 1,795 - 3,743 - 7,027 | 0.49 | no verdict |
| iob-chatbot | ready product | 115 | 1,922 | 3,621 - 7,551 - 14,177 | 0.25 | no verdict |
| iob-trade | ready product | 92 | 1,248 | 2,897 - 6,041 - 11,342 | 0.21 | no verdict |
| iob-website | CMS | 75 | 2,307 | 2,362 - 4,925 - 9,246 | 0.47 | no verdict |

† Tyre's 3-month deadline can't be met without AI tools, so in the app the check says it cannot
compare. For this table it was run without the deadline.

**What this shows:**
- The 4 built from scratch agree with an outside, published method: 0.83 to 1.36.
- The 4 on a ready product or CMS sit at 0.21 to 0.49, below as expected.

**Features flagged most often:** small extras with 3 stories, priced at 12 to 66 hours, where
the story size says about 200. Examples:
- battery: certificate exchange and audit management, 66 hours each;
- iob-trade: 18 modules at about 18 hours each.

Either our small extra block is too small, or a 3-story extra is smaller than 3 full processes.
This check can't tell which. An expert check (option 1) can.

## Limits

- It shows that two methods agree, not that either is right. Both could be wrong the same way.
- Standard blocks (login, roles, set-up) and items with no stories are left out of both sides.
  They are listed as "no user stories".
- The range is **not** narrowed when the methods agree. That needs coverage evidence first.
- The ISBSG rate is for Java new development at 300-500 FP. Smaller or larger builds may differ.

## Projects without a document (OPEN_QUESTIONS 164)

When a project is typed in, the form has an optional step, "What can people do with it?". The AI
can draft the stories from the description, and the user edits or skips them. They feed this
check only. They never change a level, a price or the random seed.

Six private projects were priced locally through the app, with stories written by hand in place
of the AI draft (no API call). Prices are P50 in lakh rupees, including support, tax and margin.

| Project | Size | P50 | Build only | Stories | Ours ÷ story size | Line on the results page |
|---|---|---:|---:|---:|---:|---|
| Company website (5 pages + enquiry form) | small | 10.6 | 2.8 | 9 | 0.47 | lower; website feature may be priced low |
| Clinic booking | small-medium | 18.7 | 6.4 | 17 | 0.70 | matches |
| Online store | small-medium | 37.5 | 9.7 | 25 | 0.93 | matches |
| Job portal | small-medium | 39.5 | 10.6 | 18 | 1.65 | matches; forms and approvals may be high, search low |
| AI document SaaS | small-medium | 21.2 | 7.5 | 15 | 1.06 | matches; AI document reading may be low |
| Company ERP | medium | 69.4 | 19.6 | 27 | 1.46 | matches |

**Problem found: hosting for small projects.**
- The website's first year of hosting is about ₹2.85 lakh: a managed database (₹1.58 lakh), app
  servers, a load balancer and monitoring.
- With availability set to "Not a problem" it is still about ₹1.4 lakh.
- That is more than its whole build (₹2.8 lakh). A small site usually runs on one small server.
- **Fixed in parameters v25 (OPEN_QUESTIONS 165)** for one-server sites: the database runs on the
  server and AWS's free monitoring covers it. At "Not a problem" uptime the website's hosting is
  now about ₹42,000 a year and its P50 ₹7.2 lakh (was ₹8.6 lakh). At the default "Some trouble"
  it is still two servers (open question).

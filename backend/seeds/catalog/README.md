# Component catalogs

**The current catalog is the highest number (now `v9.yaml`).** Every new estimate is priced
from it. To read it, open [`docs/CATALOG.md`](../../docs/CATALOG.md) (one plain table,
regenerated with `uv run python -m app.cli catalog-table`).

The older files are history, not alternatives:

- every saved estimate records the catalog version it was priced with, so it can always be
  re-checked and explained the same way (architecture rule 4: old estimates never change);
- tests pin old versions (the golden estimates use `v1`; others check that each new version
  kept every earlier block and number);
- a version is never edited once published: a change is a new file that copies the last one and
  adds to it (v8 = v7 unchanged + 15 industry blocks).

So do not merge or delete them. To change a block's hours, add `v9.yaml` (copy of v8 plus the
change, with a `source` for every number), run `make seed`, and say why in
`docs/OPEN_QUESTIONS.md`.

| Version | What it added |
|---|---|
| v1 | Government portal + workflow + AI chatbot blocks |
| v2 | Generic blocks for features outside the list (by type and size) |
| v3 | Private-sector modules: inventory, billing, bookings, online store, CRM |
| v4 | Maps and location |
| v5 | Hours from published effort data instead of placeholders |
| v6 | Where each number comes from (`evidence`, `source_era`) |
| v7 | A tech-stack section per block, 27 new blocks (web, e-commerce, mobile, AI), a link per source |
| v8 | 15 industry blocks (school, online learning, healthcare, fitness, delivery, property, finance, hotel) |
| v9 | v8 unchanged, one block renamed: "Online forms and applications" (was a government tender's words) |

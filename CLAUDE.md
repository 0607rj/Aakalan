@AGENTS.md

# Claude-specific notes

- Run `python scripts/tasks.py lint` and `python scripts/tasks.py test` (or the `make` equivalents) before saying a task is done; report failures with their output rather than summarising them away.
- This dev machine is Windows without `make` or Docker: use `python scripts/tasks.py <target>` and `uv run` inside `backend/`.
- Never put a number in engine code or ask an LLM for one; add it to a seed YAML with a `source` instead.
- If golden totals change, say so explicitly and explain why before running `make golden`.
- Record any new ambiguity and the default you chose in `docs/OPEN_QUESTIONS.md` instead of stopping to ask.

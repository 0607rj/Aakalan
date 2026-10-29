"""deploy/update.sh keeps the server's own shared-library entries across a pull."""

from datetime import date
from pathlib import Path

from app.services.research.library import LibraryEntry, _write, merge_library, read_library


def entry(key: str) -> LibraryEntry:
    return LibraryEntry(
        key=key,
        name=key,
        section="core",
        base_type="module",
        method="analysis",
        added=date(2026, 10, 29),
        spec={"key": key},
        sources=[],
    )


def test_merge_adds_only_missing_entries_after_the_repository_ones(tmp_path: Path) -> None:
    repo, saved = tmp_path / "library.yaml", tmp_path / "saved.yaml"
    _write(repo, [entry("a"), entry("b")])
    _write(saved, [entry("a"), entry("c"), entry("d")])
    assert merge_library(repo, saved) == 2
    assert [e.key for e in read_library(repo)] == ["a", "b", "c", "d"]
    assert merge_library(repo, saved) == 0  # nothing new the second time

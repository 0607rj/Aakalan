"""Architecture guard rails (brief Sections 3 and 5)."""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
PURE_PACKAGES = ("services/engine", "services/hosting")
# The engine must never touch an LLM (rule 1) and stays free of DB access so it is pure.
FORBIDDEN_PREFIXES = (
    "app.llm",
    "anthropic",
    "openai",
    "sqlalchemy",
    "app.models",
    "app.core.db",
    "app.api",
)


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, f"{path}: use absolute imports in pure packages"
            names.add(node.module or "")
    return names


def test_engine_and_hosting_have_no_llm_or_db_imports() -> None:
    files = [f for pkg in PURE_PACKAGES for f in (APP_DIR / pkg).rglob("*.py")]
    assert files, "engine package missing"
    for path in files:
        for name in _imports(path):
            assert not name.startswith(FORBIDDEN_PREFIXES), f"{path} imports {name}"

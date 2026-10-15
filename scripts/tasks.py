#!/usr/bin/env python3
"""Cross-platform task runner (stdlib only). Every Makefile target delegates here, so the
same commands work on Windows without `make`:

    python scripts/tasks.py <task> [args]

Run `python scripts/tasks.py --help` for the list of tasks.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def _exe(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        sys.exit(f"error: '{name}' not found on PATH")
    return found


def run(cmd: Sequence[str], cwd: Path) -> None:
    print(f"$ ({cwd.relative_to(ROOT) or '.'}) {' '.join(cmd)}", flush=True)
    result = subprocess.run([_exe(cmd[0]), *cmd[1:]], cwd=cwd, check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)


def uv(*args: str) -> None:
    run(["uv", "run", *args], BACKEND)


def npm(*args: str) -> None:
    run(["npm", *args], FRONTEND)


# --- tasks -----------------------------------------------------------------------------------


def install(_: argparse.Namespace) -> None:
    run(["uv", "sync"], BACKEND)
    npm("ci" if (FRONTEND / "package-lock.json").exists() else "install")


def migrate(_: argparse.Namespace) -> None:
    uv("alembic", "upgrade", "head")


def migration(args: argparse.Namespace) -> None:
    if not args.message:
        sys.exit('usage: tasks.py migration -m "describe change"')
    uv("alembic", "revision", "--autogenerate", "-m", args.message)


def seed(_: argparse.Namespace) -> None:
    uv("python", "-m", "app.cli", "seed")


def test_backend(_: argparse.Namespace) -> None:
    uv("pytest")


def test_frontend(_: argparse.Namespace) -> None:
    npm("run", "typecheck")


def test(args: argparse.Namespace) -> None:
    test_backend(args)
    test_frontend(args)


def lint(_: argparse.Namespace) -> None:
    uv("ruff", "check", ".")
    uv("ruff", "format", "--check", ".")
    uv("mypy", "app", "tests")
    npm("run", "lint")
    npm("run", "format:check")


def fmt(_: argparse.Namespace) -> None:
    uv("ruff", "check", "--fix", ".")
    uv("ruff", "format", ".")
    npm("run", "format")


def openapi(_: argparse.Namespace) -> None:
    uv("python", "-m", "app.cli", "openapi")
    npm("run", "gen:api")


def golden(_: argparse.Namespace) -> None:
    uv("python", "-m", "app.cli", "golden")


def worker(_: argparse.Namespace) -> None:
    uv("huey_consumer", "app.jobs.huey", "-w", "2")


def dev(args: argparse.Namespace) -> None:
    """Migrate, seed demo data (idempotent), then run API, web and worker until Ctrl+C."""
    migrate(args)
    seed(args)
    procs: list[tuple[str, subprocess.Popen[bytes]]] = []
    specs = [
        ("api", [_exe("uv"), "run", "uvicorn", "app.main:app", "--reload", "--port", "8000"], BACKEND),
        ("web", [_exe("npm"), "run", "dev"], FRONTEND),
        ("worker", [_exe("uv"), "run", "huey_consumer", "app.jobs.huey"], BACKEND),
    ]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    for name, cmd, cwd in specs:
        print(f"starting {name}: {' '.join(cmd)}", flush=True)
        procs.append((name, subprocess.Popen(cmd, cwd=cwd, creationflags=flags)))
    print("API http://localhost:8000/docs · Web http://localhost:3000 · Ctrl+C to stop", flush=True)
    try:
        while all(p.poll() is None for _, p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for _, p in procs:
            if p.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.send_signal(signal.SIGINT)
        for _, p in procs:
            p.wait()


TASKS: dict[str, tuple[Callable[[argparse.Namespace], None], str]] = {
    "install": (install, "install backend (uv) and frontend (npm) dependencies"),
    "dev": (dev, "migrate + seed, then run API :8000, web :3000 and Huey worker"),
    "migrate": (migrate, "apply Alembic migrations"),
    "migration": (migration, 'create a migration: migration -m "message"'),
    "seed": (seed, "load seed data and demo users (idempotent)"),
    "test": (test, "backend pytest + frontend typecheck"),
    "test-backend": (test_backend, "backend pytest only"),
    "test-frontend": (test_frontend, "frontend typecheck only"),
    "lint": (lint, "ruff, ruff format --check, mypy, eslint, prettier --check"),
    "format": (fmt, "auto-format backend and frontend"),
    "openapi": (openapi, "export OpenAPI JSON and regenerate frontend API types"),
    "golden": (golden, "regenerate golden estimate expectations (intentional changes only)"),
    "worker": (worker, "run the Huey background worker"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="task", required=True, metavar="task")
    for name, (func, help_text) in TASKS.items():
        p = sub.add_parser(name, help=help_text)
        if name == "migration":
            p.add_argument("-m", "--message", default="")
        p.set_defaults(func=func)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

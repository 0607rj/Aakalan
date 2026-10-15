"""Backend management commands: `uv run python -m app.cli <command>`."""

import argparse
import json
import sys
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings
from app.core.db import get_session_factory


def cmd_seed(args: argparse.Namespace) -> None:
    from app.services.seeding.database import seed_demo_project, seed_reference
    from app.services.seeding.reference import load_reference
    from app.services.seeding.users import seed_demo_users

    settings = get_settings()
    reference = load_reference(settings.seeds_dir)
    with get_session_factory()() as session:
        for warning in seed_reference(session, reference):
            sys.stderr.write(f"warning: {warning}\n")
        sys.stdout.write("Seeded reference data (taxonomy, catalog, rate cards, parameters).\n")
        if not args.no_demo:
            org = seed_demo_users(session, settings.seed_user_password)
            sys.stdout.write("Seeded demo organisation and users.\n")
            if seed_demo_project(session, org, reference):
                sys.stdout.write("Seeded demo project.\n")
        session.commit()


def cmd_openapi(args: argparse.Namespace) -> None:
    from app.main import create_app

    out = Path(args.out)
    out.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"Wrote {out}\n")


def cmd_golden(_args: argparse.Namespace) -> None:
    from app.services.seeding.golden import write_expectations

    for path in write_expectations():
        sys.stdout.write(f"Wrote {path}\n")
    sys.stdout.write("Review the diff (git diff tests/engine/golden) before committing.\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p_seed = sub.add_parser("seed", help="load reference seed data, demo users and project")
    p_seed.add_argument("--no-demo", action="store_true", help="reference data only")
    p_seed.set_defaults(func=cmd_seed)
    p_openapi = sub.add_parser("openapi", help="export the OpenAPI schema")
    p_openapi.add_argument("--out", default=str(BACKEND_DIR / "openapi.json"))
    p_openapi.set_defaults(func=cmd_openapi)
    sub.add_parser("golden", help="regenerate golden expectations").set_defaults(func=cmd_golden)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

"""Backend management commands: `uv run python -m app.cli <command>`."""

import argparse
import json
import sys
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings
from app.core.db import get_session_factory


def cmd_seed(_args: argparse.Namespace) -> None:
    from app.services.seeding.users import seed_demo_users

    settings = get_settings()
    with get_session_factory()() as session:
        seed_demo_users(session, settings.seed_user_password)
        session.commit()
    sys.stdout.write("Seeded demo organisation and users.\n")


def cmd_openapi(args: argparse.Namespace) -> None:
    from app.main import create_app

    out = Path(args.out)
    out.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"Wrote {out}\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="load seed data and demo users").set_defaults(func=cmd_seed)
    p_openapi = sub.add_parser("openapi", help="export the OpenAPI schema")
    p_openapi.add_argument("--out", default=str(BACKEND_DIR / "openapi.json"))
    p_openapi.set_defaults(func=cmd_openapi)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

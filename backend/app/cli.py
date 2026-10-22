"""Backend management commands: `uv run python -m app.cli <command>`."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings
from app.core.db import get_session_factory


def cmd_seed(args: argparse.Namespace) -> None:
    from app.services.quick.config import quick_config
    from app.services.research.library import seed_library, share_existing
    from app.services.seeding.database import seed_demo_project, seed_reference
    from app.services.seeding.reference import load_reference
    from app.services.seeding.users import seed_demo_users

    settings = get_settings()
    reference = load_reference(settings.seeds_dir)
    with get_session_factory()() as session:
        for warning in seed_reference(session, reference):
            sys.stderr.write(f"warning: {warning}\n")
        sys.stdout.write("Seeded reference data (taxonomy, catalog, rate cards, parameters).\n")
        added = seed_library(session, settings.resolved_research_library)
        research = quick_config().research
        shared = share_existing(session) if research and research.share else 0
        sys.stdout.write(
            f"Research library: {added} loaded from the file, {shared} shared from companies.\n"
        )
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


BUYER_TITLES = {
    "government": "GOVERNMENT",
    "private": "PRIVATE COMPANIES",
    "small_business": "STARTUPS / SMALL BUSINESSES",
}


def cmd_backtest(args: argparse.Namespace) -> None:
    from app.services.calibration.backtest import (
        BacktestReport,
        backtest,
        fit_points_curve,
        layer_shares,
        load_benchmarks,
        reference_for,
    )
    from app.services.engine.reference import Calibration
    from app.services.quick.config import quick_config
    from app.services.seeding.reference import load_reference

    settings = get_settings()
    bench = load_benchmarks(settings.seeds_dir / "benchmarks" / f"{args.country}.yaml")
    reference = reference_for(load_reference(settings.seeds_dir), args.country)
    cfg = quick_config()

    def show(title: str, r: BacktestReport) -> None:
        sys.stdout.write(
            f"\n{title}: effort x{r.effort_multiplier} support x{r.run_multiplier} | "
            f"used {r.projects_used} | median ratio {r.median_ratio} | "
            f"median |error| {r.median_abs_error_percent}% | within 25%: {r.within_25_percent}"
            f" | inside our low-high range: {r.inside_range}\n"
        )
        for row in r.rows:
            mark = "*" if row.use else " "
            ours = f"{row.estimate_minor / 100:,.0f}" if row.estimate_minor else "-"
            published = f"{row.published_minor / 100:,.0f}"
            if row.published_high_minor:
                published += f"-{row.published_high_minor / 100:,.0f}"
            sys.stdout.write(
                f" {mark} {row.id[:38]:38} {row.buyer[:5]:5} published {published:>21}"
                f"  ours {ours:>14}  error {row.error_percent}%\n"
            )

    dials = reference["parameters"].calibration or Calibration(source="none")
    effort, run = dials.effort_multiplier, dials.run_multiplier
    if args.calibrate:
        # one smooth size factor by feature points, on all client types (as the app prices)
        fit = fit_points_curve(cfg, bench, reference)
        sys.stdout.write(
            f"\nsize factor = {fit.a} x points^{fit.b} | {fit.projects} projects | "
            f"in-sample median |error| {fit.median_abs_error_percent}% | left out "
            f"{fit.loo_median_abs_error_percent}% (within 25%: {fit.loo_within_25_percent})\n"
            f"curve: {[(n, str(f)) for n, f in fit.curve]}\n"
        )
        for size, st in fit.by_size.items():
            sys.stdout.write(f"{size}: {st.model_dump()}\n")
        for buyer, r in fit.by_buyer.items():
            sys.stdout.write(f"{BUYER_TITLES.get(buyer, buyer)}: actual / ours {r}\n")
    elif args.layers:
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        sys.stdout.write(
            "\nShare of the planned cost by layer (median per hand-set size), priced as the app "
            "prices. A diagnostic of how size changes the mix, not a fit.\n"
        )
        for size, layers in layer_shares(cfg, bench, reference, as_of=as_of).items():
            parts = ", ".join(f"{k} {v:.0%}" for k, v in layers.items())
            sys.stdout.write(f"  {size:14} {parts}\n")
    else:
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        report = backtest(cfg, bench, reference, effort, run, as_of=as_of)
        show("ALL PROJECTS", report)
        params = reference["parameters"]
        sys.stdout.write(
            f"\nparameter set {params.version}, catalog {reference['catalog'].version}. Published "
            "prices are contract values, not effort: these numbers compare prices only. bias = "
            "ours / published (median of logs); band hits count as exact and flatter the result.\n"
        )
        titles = {"all": "All", "size": "By size (set by hand)", "derived_size": "By size (app)"}
        for key, segments in report.segments.items():
            sys.stdout.write(f"\n{titles.get(key, 'By client type')}\n")
            for m in segments:
                sys.stdout.write(
                    f"  {BUYER_TITLES.get(m.segment, m.segment):28} n={m.projects:3}  "
                    f"median |error| {m.median_abs_error_percent:6.1f}%  bias x{m.bias:<6}  "
                    f"within 25%: {m.within_25_percent:3}  in P10-P90: {m.inside_range:3}  "
                    f"band hits: {m.band_hits}\n"
                )


def cmd_test_email(args: argparse.Namespace) -> None:
    """Send one email the way sign-up codes go out, to check the SMTP settings."""
    from app.services.email import EmailNotConfiguredError, LogSender, get_email_sender

    sender = get_email_sender()
    if isinstance(sender, LogSender):
        sys.stderr.write("SMTP is not set up (SMTP_HOST / SMTP_PASSWORD in .env): not sent.\n")
        raise SystemExit(1)
    try:
        sender.send(args.to, "Aakalan test email", "Email from Aakalan works.\n\nAakalan")
    except EmailNotConfiguredError as exc:
        sys.stderr.write(f"Not sent: {exc.__cause__ or exc}\n")
        raise SystemExit(1) from exc
    sys.stdout.write(f"Sent a test email to {args.to}.\n")


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
    p_mail = sub.add_parser("test-email", help="send one email to check the SMTP settings")
    p_mail.add_argument("to")
    p_mail.set_defaults(func=cmd_test_email)
    p_bt = sub.add_parser("backtest", help="compare estimates with real published contracts")
    p_bt.add_argument("--country", default="india", choices=["india", "us"])
    p_bt.add_argument(
        "--calibrate",
        action="store_true",
        help="fit project-size and ready-made-product factors on all projects",
    )
    p_bt.add_argument(
        "--layers", action="store_true", help="show how the cost splits into layers, by size"
    )
    p_bt.add_argument("--as-of", help="price as of this date (YYYY-MM-DD) for a repeatable report")
    p_bt.set_defaults(func=cmd_backtest)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

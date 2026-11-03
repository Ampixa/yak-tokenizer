"""Yak evaluation harness CLI.

    uv run python scripts/eval_panel.py fetch            # build data/eval/ (FLORES+ needs HF access)
    uv run python scripts/eval_panel.py fetch --code-math   # also fetch the optional code and math sets
    uv run python scripts/eval_panel.py run              # measure the panel, then write docs/RESULTS.md
    uv run python scripts/eval_panel.py run --code-math  # include code (HumanEval, MBPP) and math (GSM8K, MATH)
    uv run python scripts/eval_panel.py run --only gpt2,o200k --add mine=path/to/tokenizer.json
    uv run python scripts/eval_panel.py report           # re-render docs/RESULTS.md from artifacts/eval/

``--add`` accepts ``name=path/to/tokenizer.json``, ``name=path/to/dir``, ``name=sp:path.model``,
``name=hf:org/repo`` and ``name=tiktoken:o200k_base``; repeat it for several tokenizers.
``--only`` with no panel names (``--only none``) measures just the ``--add`` tokenizers.
"""

from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from yak_tokenizer.eval import fetch, panel, report
from yak_tokenizer.eval.adapters import parse_extra
from yak_tokenizer.eval.evalsets import load_registry


def cmd_fetch(args: argparse.Namespace) -> int:
    which = args.which.split(",") if args.which else None
    if args.code_math:
        which = (which or [b for b in fetch.BUILDERS if b not in fetch.OPTIONAL]) + list(fetch.OPTIONAL)
    for row in fetch.fetch_all(which):
        print(f"{row['path']}\t{row['segments']} segments\t{row['bytes']} bytes\t{row['license']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    cfg = panel.load_panel(args.config)
    specs = cfg["tokenizers"]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        unknown = wanted - {s["name"] for s in specs} - {"none"}
        if unknown:
            print(f"unknown panel names: {sorted(unknown)}", file=sys.stderr)
            return 2
        specs = [s for s in specs if s["name"] in wanted]
    extras = [parse_extra(a) for a in args.add or []]
    names = [s["name"] for s in specs]
    clash = [e["name"] for e in extras if e["name"] in names]
    if clash:
        print(f"--add names clash with panel names: {clash}", file=sys.stderr)
        return 2
    registry = load_registry()
    set_ids = (
        args.sets.split(",")
        if args.sets
        else [s for s, spec in registry["sets"].items() if spec.get("panel", True)]
    )
    if args.code_math:
        set_ids += [
            s
            for s, spec in registry["sets"].items()
            if spec.get("domain") in ("code", "math") and s not in set_ids
        ]
    records = panel.run_panel(specs + extras, set_ids, force=args.force, timeout=args.timeout)
    failed = [r["name"] for r in records if r.get("status") != "ok"]
    print(f"{len(records) - len(failed)} ok, {len(failed)} failed {failed if failed else ''}")
    if not args.no_report:
        path = report.write_results(cfg)
        print(f"wrote {path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    path = report.write_results(panel.load_panel(args.config))
    print(f"wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="build the eval sets under data/eval/")
    p.add_argument(
        "--which", help=f"comma list of {','.join(fetch.BUILDERS)} (default: all but code,math)"
    )
    p.add_argument("--code-math", action="store_true", help="also fetch the code and math sets")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("run", help="measure tokenizers and write docs/RESULTS.md")
    p.add_argument("--config", default=str(panel.PANEL_CONFIG))
    p.add_argument("--only", help="comma list of panel names to run ('none' = only --add)")
    p.add_argument(
        "--add",
        action="append",
        metavar="NAME=SOURCE",
        help="extra tokenizer, e.g. mine=path/to/tokenizer.json",
    )
    p.add_argument("--sets", help="comma list of eval set ids (default: sets with panel: true)")
    p.add_argument(
        "--code-math", action="store_true", help="also measure code and math (fetch them first)"
    )
    p.add_argument("--force", action="store_true", help="ignore cached results")
    p.add_argument("--timeout", type=int, default=1800, help="seconds per tokenizer")
    p.add_argument("--no-report", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", help="re-render docs/RESULTS.md from artifacts/eval/*.json")
    p.add_argument("--config", default=str(panel.PANEL_CONFIG))
    p.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

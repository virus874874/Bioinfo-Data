from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import ConfigError, load_config
from .core import Scout
from .evaluation import evaluate


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gdc-scout", description="Evidence-first GDC metadata scout")
    p.add_argument("--version", action="version", version=f"gdc_scout {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run"); run.add_argument("--config", required=True); run.add_argument("--output", required=True); run.add_argument("--verbose", action="store_true"); run.add_argument("--dry-run", action="store_true")
    ev = sub.add_parser("eval"); ev.add_argument("--output", required=True); ev.add_argument("--threshold", type=float, default=0.8); ev.add_argument("--use-cache", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "run":
            config = load_config(args.config)
            if args.dry_run:
                print(f"OK: Configuration valid ({len(config['projects'])} projects)")
                return 0
            cards = Scout(config, args.output, args.config).run()
            print("OK: Run completed successfully")
            print("OK: Generated 8 artifacts")
            print(f"OK: Assessed {len(cards)} projects with evidence audit trail")
        else:
            if not 0 <= args.threshold <= 1:
                raise ValueError("threshold must be between 0 and 1")
            report = evaluate(args.output, args.threshold)
            print(json.dumps({"overall_confidence": report["overall_confidence"], "passes_threshold": report["passes_threshold"]}, indent=2))
        return 0
    except (ConfigError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from keeplint.report import format_json, format_text
from keeplint.rules import RULES, lint


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="keeplint", description="Lint CHANGELOG.md files in the Keep a Changelog layout."
    )
    parser.add_argument("files", nargs="+", metavar="FILE")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--disable", action="append", default=[], metavar="RULE")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2

    for rule in args.disable:
        if rule not in RULES:
            print(f'keeplint: unknown rule "{rule}"', file=sys.stderr)
            return 2

    texts: list[tuple[str, str]] = []
    for path in args.files:
        try:
            texts.append((path, Path(path).read_bytes().decode("utf-8")))
        except OSError as exc:
            print(f"keeplint: {path}: {exc.strerror or exc}", file=sys.stderr)
            return 2
        except UnicodeDecodeError as exc:
            print(f"keeplint: {path}: {exc}", file=sys.stderr)
            return 2

    disabled = set(args.disable)
    results = [
        (path, [f for f in lint(text) if f.rule not in disabled]) for path, text in texts
    ]
    formatter = format_json if args.format == "json" else format_text
    sys.stdout.write(formatter(results))
    return 1 if any(findings for _, findings in results) else 0


if __name__ == "__main__":
    sys.exit(main())

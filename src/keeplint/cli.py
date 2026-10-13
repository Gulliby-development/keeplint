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


def _has_stdin_argument(argv: Sequence[str]) -> bool:
    value_follows_option = False
    options_ended = False
    for argument in argv:
        if value_follows_option:
            value_follows_option = False
            continue
        if options_ended:
            if argument == "-":
                return True
            continue
        if argument == "--":
            options_ended = True
        elif argument in ("--format", "--disable"):
            value_follows_option = True
        elif argument == "-":
            return True
    return False


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = list(sys.argv[1:] if argv is None else argv)
        parser = _parser()
        if _has_stdin_argument(arguments):
            args = parser.parse_intermixed_args(arguments)
        else:
            args = parser.parse_args(arguments)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2

    for rule in args.disable:
        if rule not in RULES:
            print(f'keeplint: unknown rule "{rule}"', file=sys.stderr)
            return 2

    if args.files.count("-") > 1:
        print("keeplint: standard input given more than once", file=sys.stderr)
        return 2

    texts: list[tuple[str, str]] = []
    for path in args.files:
        display_path = "<stdin>" if path == "-" else path
        try:
            raw = sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()
            texts.append((display_path, raw.decode("utf-8")))
        except OSError as exc:
            print(f"keeplint: {display_path}: {exc.strerror or exc}", file=sys.stderr)
            return 2
        except UnicodeDecodeError as exc:
            print(f"keeplint: {display_path}: {exc}", file=sys.stderr)
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

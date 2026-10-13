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
    parser.add_argument("--only", action="append", default=[], metavar="RULE")
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
        elif argument in ("--format", "--disable", "--only"):
            value_follows_option = True
        elif argument == "-":
            return True
    return False


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = list(sys.argv[1:] if argv is None else argv)
        parser = _parser()
        has_only_option = any(
            argument == "--only" or argument.startswith("--only=") for argument in arguments
        )
        if _has_stdin_argument(arguments) or has_only_option:
            args = parser.parse_intermixed_args(arguments)
        else:
            args = parser.parse_args(arguments)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2

    for rule in (rule for values in (args.disable, args.only) for rule in values):
        if rule not in RULES:
            hint = f" (did you mean {rule.upper()}?)" if rule.isascii() and rule.upper() in RULES else ""
            print(f'keeplint: unknown rule "{rule}"{hint}', file=sys.stderr)
            return 2

    if args.only and args.disable:
        print("keeplint: --only and --disable cannot be combined", file=sys.stderr)
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
    only = set(args.only)
    results = [
        (path, [f for f in lint(text) if f.rule not in disabled and (not only or f.rule in only)])
        for path, text in texts
    ]
    formatter = format_json if args.format == "json" else format_text
    sys.stdout.write(formatter(results))
    return 1 if any(findings for _, findings in results) else 0


if __name__ == "__main__":
    sys.exit(main())

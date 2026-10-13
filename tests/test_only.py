"""Tests for filtering findings to selected rules."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from keeplint.cli import main

CLEAN = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n\n[1.0.0]: https://x\n"
NO_LINK = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n"
NO_DATE_NO_LINK = b"# Changelog\n\n## [1.0.0]\n- x\n"
README_EXAMPLE = (
    b"# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-02-30\n\n"
    b"### Added\n- First release.\n\n## [1.1.0] - 2026-03-01\n"
    b"- Something.\n\n[1.0.0]: https://example.com/1.0.0\n"
)


def write(tmp_path: Path, name: str, data: bytes) -> str:
    path = tmp_path / name
    path.write_bytes(data)
    return str(path.resolve())


def set_stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    stdin = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", stdin)


def test_only_filters_text_and_clean_results(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "no-date-no-link.md", NO_DATE_NO_LINK)

    assert main([path, "--only", "KL009"]) == 1
    assert capsys.readouterr().out == (
        f"{path}:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"
    )

    assert main([path, "--only", "KL001"]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_only_filters_json_and_keeps_line_order(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "CHANGELOG.md", README_EXAMPLE)

    assert main([path, "--only", "KL004", "--only", "KL003", "--format", "json"]) == 1
    output = capsys.readouterr().out
    expected = {
        "files": [
            {
                "path": path,
                "findings": [
                    {
                        "line": 5,
                        "rule": "KL003",
                        "message": 'invalid date "2026-02-30"',
                    },
                    {
                        "line": 10,
                        "rule": "KL004",
                        "message": "1.1.0 is not lower than 1.0.0",
                    },
                ],
            }
        ],
        "problems": 2,
    }
    assert output == json.dumps(expected, indent=2) + "\n"


def test_only_repeated_ids_and_equals_form(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "CHANGELOG.md", README_EXAMPLE)

    assert main([path, "--only=KL004", "--only", "KL004"]) == 1
    assert capsys.readouterr().out == (
        f"{path}:10: KL004 1.1.0 is not lower than 1.0.0\n1 problem in 1 file\n"
    )


def test_only_options_can_surround_multiple_files(tmp_path: Path, capsys) -> None:
    first = write(tmp_path, "first.md", NO_LINK)
    second = write(tmp_path, "second.md", NO_DATE_NO_LINK)

    assert main(["--only", "KL009", first, second, "--only=KL008"]) == 1
    assert capsys.readouterr().out == (
        f"{first}:3: KL009 missing link definition for [1.0.0]\n"
        f"{second}:3: KL008 missing date for 1.0.0\n"
        f"{second}:3: KL009 missing link definition for [1.0.0]\n"
        "3 problems in 2 files\n"
    )


def test_only_filters_stdin(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    set_stdin(monkeypatch, NO_LINK)

    assert main(["--only", "KL009", "-"]) == 1
    assert capsys.readouterr().out == (
        "<stdin>:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"
    )


def test_only_and_disable_conflict_in_either_order(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "clean.md", CLEAN)

    for arguments in (
        [path, "--only", "KL001", "--disable", "KL002"],
        [path, "--disable", "KL002", "--only", "KL001"],
    ):
        assert main(arguments) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "keeplint: --only and --disable cannot be combined\n"


def test_only_unknown_rules_have_case_hints_only_when_appropriate(
    tmp_path: Path, capsys
) -> None:
    path = write(tmp_path, "clean.md", CLEAN)
    cases = (
        ("Kl008", 'keeplint: unknown rule "Kl008" (did you mean KL008?)\n'),
        ("kl9", 'keeplint: unknown rule "kl9"\n'),
        ("KL999", 'keeplint: unknown rule "KL999"\n'),
        ("", 'keeplint: unknown rule ""\n'),
    )

    for rule, expected_error in cases:
        assert main([path, "--only", rule]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == expected_error


def test_disable_rule_validation_precedes_only_validation_and_conflict(
    tmp_path: Path, capsys
) -> None:
    path = write(tmp_path, "clean.md", CLEAN)

    assert main([path, "--only", "KL999", "--disable", "kl001"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == 'keeplint: unknown rule "kl001" (did you mean KL001?)\n'


def test_rule_errors_and_conflict_precede_duplicate_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    set_stdin(monkeypatch, CLEAN)

    assert main(["-", "-", "--only", "KL999"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == 'keeplint: unknown rule "KL999"\n'

    assert main(["-", "-", "--only", "KL001", "--disable", "KL002"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "keeplint: --only and --disable cannot be combined\n"


def test_only_without_value_is_an_argparse_usage_error(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "clean.md", CLEAN)

    assert main([path, "--only"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err
    assert "argument --only: expected one argument" in captured.err

"""Tests for linting changelogs read from standard input."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from keeplint.cli import main

CLEAN = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n\n[1.0.0]: https://x\n"
NO_LINK = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n"


def set_stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    stdin = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8")
    monkeypatch.setattr("sys.stdin", stdin)


def test_stdin_text_output_and_clean_input(monkeypatch, capsys):
    set_stdin(monkeypatch, NO_LINK)
    assert main(["-"]) == 1
    assert capsys.readouterr().out == (
        "<stdin>:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"
    )

    set_stdin(monkeypatch, CLEAN)
    assert main(["-"]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_stdin_json_output_and_disable(monkeypatch, capsys):
    set_stdin(monkeypatch, NO_LINK)
    assert main(["-", "--format", "json"]) == 1
    expected = {
        "files": [
            {
                "path": "<stdin>",
                "findings": [
                    {
                        "line": 3,
                        "rule": "KL009",
                        "message": "missing link definition for [1.0.0]",
                    }
                ],
            }
        ],
        "problems": 1,
    }
    assert capsys.readouterr().out == json.dumps(expected, indent=2) + "\n"

    set_stdin(monkeypatch, NO_LINK)
    assert main(["--disable", "KL009", "-"]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_stdin_bom_and_crlf(monkeypatch, capsys):
    data = b"\xef\xbb\xbf# Changelog\r\n\r\n## [1.0.0] - 2026-01-01\r\n- x\r\n"
    set_stdin(monkeypatch, data)
    assert main(["-"]) == 1
    assert capsys.readouterr().out == (
        "<stdin>:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"
    )


def test_empty_stdin_is_linted_as_a_file(monkeypatch, capsys):
    set_stdin(monkeypatch, b"")
    assert main(["-"]) == 1
    assert capsys.readouterr().out == (
        '<stdin>:1: KL001 first line must be "# Changelog"\n1 problem in 1 file\n'
    )


def test_stdin_and_files_are_reported_in_argument_order(tmp_path: Path, monkeypatch, capsys):
    clean = tmp_path / "c.md"
    no_link = tmp_path / "o.md"
    clean.write_bytes(CLEAN)
    no_link.write_bytes(NO_LINK)
    set_stdin(monkeypatch, NO_LINK)

    assert main([str(clean), "-", str(no_link)]) == 1
    assert capsys.readouterr().out == (
        "<stdin>:3: KL009 missing link definition for [1.0.0]\n"
        f"{no_link}:3: KL009 missing link definition for [1.0.0]\n"
        "2 problems in 2 files\n"
    )


def test_duplicate_stdin_is_rejected_before_reading_inputs(tmp_path: Path, monkeypatch, capsys):
    missing = str(tmp_path / "missing.md")
    set_stdin(monkeypatch, CLEAN)

    assert main(["-", "-"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "keeplint: standard input given more than once\n"

    assert main([missing, "-", "-"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "keeplint: standard input given more than once\n"


def test_unknown_rule_takes_precedence_over_duplicate_stdin(monkeypatch, capsys):
    set_stdin(monkeypatch, CLEAN)
    assert main(["-", "-", "--disable", "KL999"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == 'keeplint: unknown rule "KL999"\n'


def test_invalid_utf8_stdin_is_reported(monkeypatch, capsys):
    set_stdin(monkeypatch, b"# Changelog\n\xff\xfe\n")
    assert main(["-"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("keeplint: <stdin>: ")


def test_missing_file_before_stdin_is_reported_without_output(
    tmp_path: Path, monkeypatch, capsys
):
    missing = str(tmp_path / "missing.md")
    set_stdin(monkeypatch, CLEAN)
    assert main([missing, "-"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(f"keeplint: {missing}: ")


def test_options_can_be_interspersed_with_stdin_and_files(
    tmp_path: Path, monkeypatch, capsys
):
    clean = tmp_path / "clean.md"
    no_link = tmp_path / "no-link.md"
    clean.write_bytes(CLEAN)
    no_link.write_bytes(NO_LINK)

    set_stdin(monkeypatch, NO_LINK)
    assert main(["-", "--format", "json", str(clean)]) == 1
    json_output = json.loads(capsys.readouterr().out)
    assert [file["path"] for file in json_output["files"]] == ["<stdin>", str(clean)]
    assert json_output["problems"] == 1

    set_stdin(monkeypatch, NO_LINK)
    assert main([str(no_link), "--disable", "KL009", "-", str(clean)]) == 0
    assert capsys.readouterr().out == "ok\n"

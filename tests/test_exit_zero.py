"""Tests for the --exit-zero CLI option."""

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


def test_exit_zero_preserves_readme_findings_output(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "CHANGELOG.md", README_EXAMPLE)
    expected = (
        f'{path}:3: KL009 missing link definition for [Unreleased]\n'
        f"{path}:3: KL010 no entries under Unreleased\n"
        f'{path}:5: KL003 invalid date "2026-02-30"\n'
        f"{path}:10: KL004 1.1.0 is not lower than 1.0.0\n"
        f"{path}:10: KL009 missing link definition for [1.1.0]\n"
        "5 problems in 1 file\n"
    )

    assert main([path]) == 1
    baseline = capsys.readouterr()
    assert baseline.out == expected
    assert baseline.err == ""

    assert main([path, "--exit-zero"]) == 0
    flagged = capsys.readouterr()
    assert flagged.out == baseline.out
    assert flagged.err == baseline.err


def test_exit_zero_preserves_clean_output(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "clean.md", CLEAN)

    assert main([path]) == 0
    baseline = capsys.readouterr()
    assert baseline.out == "ok\n"
    assert baseline.err == ""

    assert main([path, "--exit-zero"]) == 0
    flagged = capsys.readouterr()
    assert flagged.out == baseline.out
    assert flagged.err == baseline.err


def test_exit_zero_preserves_json_output(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "no-link.md", NO_LINK)
    expected = {
        "files": [
            {
                "path": path,
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

    assert main([path, "--format", "json"]) == 1
    baseline = capsys.readouterr()
    assert baseline.out == json.dumps(expected, indent=2) + "\n"
    assert baseline.err == ""

    assert main([path, "--format", "json", "--exit-zero"]) == 0
    flagged = capsys.readouterr()
    assert flagged.out == baseline.out
    assert flagged.err == baseline.err


def test_exit_zero_can_surround_files_and_repeat(
    tmp_path: Path, capsys
) -> None:
    first = write(tmp_path, "first.md", NO_LINK)
    clean = write(tmp_path, "clean.md", CLEAN)
    last = write(tmp_path, "last.md", NO_DATE_NO_LINK)

    assert main(
        ["--exit-zero", first, "--exit-zero", clean, last, "--exit-zero", "--exit-zero"]
    ) == 0
    assert capsys.readouterr().out == (
        f"{first}:3: KL009 missing link definition for [1.0.0]\n"
        f"{last}:3: KL008 missing date for 1.0.0\n"
        f"{last}:3: KL009 missing link definition for [1.0.0]\n"
        "3 problems in 2 files\n"
    )


def test_exit_zero_works_next_to_stdin_and_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    path = write(tmp_path, "no-date-no-link.md", NO_DATE_NO_LINK)
    expected = (
        "<stdin>:3: KL009 missing link definition for [1.0.0]\n"
        f"{path}:3: KL008 missing date for 1.0.0\n"
        f"{path}:3: KL009 missing link definition for [1.0.0]\n"
        "3 problems in 2 files\n"
    )

    set_stdin(monkeypatch, NO_LINK)
    assert main(["-", path]) == 1
    baseline = capsys.readouterr()
    assert baseline.out == expected
    assert baseline.err == ""

    set_stdin(monkeypatch, NO_LINK)
    assert main(["-", "--exit-zero", path]) == 0
    flagged = capsys.readouterr()
    assert flagged.out == baseline.out
    assert flagged.err == baseline.err


def test_exit_zero_works_with_only_and_disable_filters(
    tmp_path: Path, capsys
) -> None:
    path = write(tmp_path, "no-date-no-link.md", NO_DATE_NO_LINK)

    assert main([path, "--exit-zero", "--only", "KL009"]) == 0
    assert capsys.readouterr().out == (
        f"{path}:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"
    )

    assert main(["--disable", "KL008", path, "--exit-zero"]) == 0
    assert capsys.readouterr().out == (
        f"{path}:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"
    )

    assert main([path, "--only", "KL001", "--exit-zero"]) == 0
    assert capsys.readouterr().out == "ok\n"

    assert main([path, "--exit-zero", "--disable", "KL008", "--disable", "KL009"]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_exit_zero_no_files_and_explicit_value_are_usage_errors(
    tmp_path: Path, capsys
) -> None:
    assert main([]) == 2
    baseline = capsys.readouterr()
    assert baseline.out == ""

    assert main(["--exit-zero"]) == 2
    flagged = capsys.readouterr()
    assert flagged.out == ""
    assert flagged.err == baseline.err

    path = write(tmp_path, "clean.md", CLEAN)
    assert main([path, "--exit-zero=1"]) == 2
    invalid_value = capsys.readouterr()
    assert invalid_value.out == ""
    assert "argument --exit-zero: ignored explicit argument '1'" in invalid_value.err


def test_exit_zero_does_not_change_unknown_rule_errors(tmp_path: Path, capsys) -> None:
    path = write(tmp_path, "no-link.md", NO_LINK)

    for option in ("--disable", "--only"):
        assert main([path, option, "KL999"]) == 2
        baseline = capsys.readouterr()
        assert baseline.out == ""
        assert baseline.err == 'keeplint: unknown rule "KL999"\n'

        assert main([path, "--exit-zero", option, "KL999"]) == 2
        flagged = capsys.readouterr()
        assert flagged.out == baseline.out
        assert flagged.err == baseline.err


def test_exit_zero_preserves_conflict_and_duplicate_stdin_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    missing = str((tmp_path / "missing.md").resolve())
    conflict = [missing, "--only", "KL001", "--disable", "KL002"]

    assert main(conflict) == 2
    baseline = capsys.readouterr()
    assert baseline.out == ""
    assert baseline.err == "keeplint: --only and --disable cannot be combined\n"

    assert main([missing, "--exit-zero", "--only", "KL001", "--disable", "KL002"]) == 2
    flagged_conflict = capsys.readouterr()
    assert flagged_conflict.out == baseline.out
    assert flagged_conflict.err == baseline.err

    set_stdin(monkeypatch, CLEAN)
    assert main([missing, "-", "-"]) == 2
    duplicate = capsys.readouterr()
    assert duplicate.out == ""
    assert duplicate.err == "keeplint: standard input given more than once\n"

    set_stdin(monkeypatch, CLEAN)
    assert main([missing, "-", "--exit-zero", "-"]) == 2
    flagged_duplicate = capsys.readouterr()
    assert flagged_duplicate.out == duplicate.out
    assert flagged_duplicate.err == duplicate.err


def test_exit_zero_preserves_missing_and_non_utf8_file_errors(
    tmp_path: Path, capsys
) -> None:
    missing = str((tmp_path / "missing.md").resolve())
    assert main([missing]) == 2
    missing_baseline = capsys.readouterr()
    assert missing_baseline.out == ""
    assert missing_baseline.err.startswith(f"keeplint: {missing}: ")

    assert main([missing, "--exit-zero"]) == 2
    missing_flagged = capsys.readouterr()
    assert missing_flagged.out == missing_baseline.out
    assert missing_flagged.err == missing_baseline.err

    invalid = write(tmp_path, "invalid.md", b"# Changelog\n\xff\xfe\n")
    assert main([invalid]) == 2
    invalid_baseline = capsys.readouterr()
    assert invalid_baseline.out == ""
    assert invalid_baseline.err.startswith(f"keeplint: {invalid}: ")

    assert main([invalid, "--exit-zero"]) == 2
    invalid_flagged = capsys.readouterr()
    assert invalid_flagged.out == invalid_baseline.out
    assert invalid_flagged.err == invalid_baseline.err

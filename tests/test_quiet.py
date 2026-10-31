"""Tests for the --quiet CLI option."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from keeplint.cli import main

CLEAN = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n\n[1.0.0]: https://x\n"
NO_LINK = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n"
README_EXAMPLE = (
    b"# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-02-30\n\n"
    b"### Added\n- First release.\n\n## [1.1.0] - 2026-03-01\n"
    b"- Something.\n\n[1.0.0]: https://example.com/1.0.0\n"
)
EXAMPLE_LINES = (
    "bad.md:3: KL009 missing link definition for [Unreleased]\n"
    "bad.md:3: KL010 no entries under Unreleased\n"
    'bad.md:5: KL003 invalid date "2026-02-30"\n'
    "bad.md:10: KL004 1.1.0 is not lower than 1.0.0\n"
    "bad.md:10: KL009 missing link definition for [1.1.0]\n"
)

# (arguments, exit code, standard output); good.md is clean, bad.md is the README example, nolink.md lacks one link
ROWS = [
    (["good.md"], 0, "ok\n"),
    (["good.md", "--quiet"], 0, ""),
    (["--quiet", "good.md"], 0, ""),
    (["good.md", "--quiet", "good.md"], 0, ""),
    (["bad.md"], 1, EXAMPLE_LINES + "5 problems in 1 file\n"),
    (["bad.md", "--quiet"], 1, EXAMPLE_LINES),
    (["--quiet", "bad.md"], 1, EXAMPLE_LINES),
    (["--quiet", "--quiet", "bad.md"], 1, EXAMPLE_LINES),
    (["good.md", "--quiet", "bad.md"], 1, EXAMPLE_LINES),
    (
        ["nolink.md", "good.md", "--quiet"],
        1,
        "nolink.md:3: KL009 missing link definition for [1.0.0]\n",
    ),
    (
        ["bad.md", "--quiet", "--only", "KL004"],
        1,
        "bad.md:10: KL004 1.1.0 is not lower than 1.0.0\n",
    ),
    (["bad.md", "--only", "KL001", "--quiet"], 0, ""),
    (["bad.md", "--quiet", "--exit-zero"], 0, EXAMPLE_LINES),
    (["bad.md", "--quiet=1"], 2, ""),
    (["bad.md", "--quiet", "--disable", "kl009"], 2, ""),
]


@pytest.fixture(autouse=True)
def files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "good.md").write_bytes(CLEAN)
    (tmp_path / "bad.md").write_bytes(README_EXAMPLE)
    (tmp_path / "nolink.md").write_bytes(NO_LINK)
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize(("arguments", "code", "stdout"), ROWS)
def test_quiet_rows(
    arguments: list[str], code: int, stdout: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(arguments) == code
    assert capsys.readouterr().out == stdout


def test_quiet_leaves_json_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bad.md", "--format", "json"]) == 1
    plain = capsys.readouterr().out
    assert main(["bad.md", "--format", "json", "--quiet"]) == 1
    assert capsys.readouterr().out == plain
    assert json.loads(plain)["problems"] == 5


def test_quiet_reads_standard_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(NO_LINK), encoding="utf-8"))
    assert main(["--quiet", "-"]) == 1
    assert capsys.readouterr().out == "<stdin>:3: KL009 missing link definition for [1.0.0]\n"

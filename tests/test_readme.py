"""Tests for the README example and the LICENSE file."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from keeplint.cli import main

ROOT = Path(__file__).resolve().parents[1]


def _readme() -> str:
    return (ROOT / "README.md").read_bytes().decode("utf-8").replace("\r\n", "\n")


def _example() -> tuple[str, str]:
    readme = _readme()
    changelog = re.search(r"```markdown\n(.*?)```", readme, re.DOTALL)
    output = re.search(r"prints:\n\n```text\n(.*?)```", readme, re.DOTALL)
    assert changelog is not None
    assert output is not None
    return changelog.group(1), output.group(1)


def test_readme_example_matches_cli_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    changelog, expected = _example()
    (tmp_path / "CHANGELOG.md").write_bytes(changelog.encode("utf-8"))
    monkeypatch.chdir(tmp_path)
    code = main(["CHANGELOG.md"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == expected


def test_readme_sections() -> None:
    readme = _readme()
    for heading in ("## Install", "## Usage", "## Rules", "## JSON output", "## Exit codes"):
        assert heading in readme
    assert "## CI" in readme
    assert "## Development" in readme
    assert "pytest" in readme
    assert '"problems"' in readme


def test_readme_rule_table() -> None:
    readme = _readme()
    for number in range(1, 11):
        assert f"| KL{number:03d} |" in readme


def test_license_is_mit() -> None:
    text = (ROOT / "LICENSE").read_bytes().decode("utf-8")
    assert text.startswith("MIT License")
    assert re.search(r"^Copyright \(c\) .+", text, re.MULTILINE)
    assert "Permission is hereby granted, free of charge" in text
    assert 'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND' in text


def test_readme_documents_only_rule_option() -> None:
    readme = _readme()
    assert "keeplint FILE... [--format text|json] [--exit-zero] [--disable RULE]... [--only RULE]..." in readme
    assert "keeplint CHANGELOG.md --only KL004 --only KL009" in readme
    assert "did you mean KL009?" in readme

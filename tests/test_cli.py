"""Tests for the CLI and report output."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from keeplint.cli import main

SRC = Path(__file__).resolve().parents[1] / "src"

CLEAN = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n\n[1.0.0]: https://x\n"
NO_LINK = b"# Changelog\n\n## [1.0.0] - 2026-01-01\n- x\n"
NO_DATE_NO_LINK = b"# Changelog\n\n## [1.0.0]\n- x\n"


def write(tmp_path: Path, name: str, data: bytes) -> str:
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def test_text_singular(tmp_path, capsys):
    p = write(tmp_path, "a.md", NO_LINK)
    assert main([p]) == 1
    out = capsys.readouterr().out
    assert out == f"{p}:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"


def test_text_plural_and_order(tmp_path, capsys):
    a = write(tmp_path, "a.md", NO_LINK)
    b = write(tmp_path, "b.md", NO_DATE_NO_LINK)
    c = write(tmp_path, "c.md", CLEAN)
    assert main([a, b, c]) == 1
    assert capsys.readouterr().out == (
        f"{a}:3: KL009 missing link definition for [1.0.0]\n"
        f"{b}:3: KL008 missing date for 1.0.0\n"
        f"{b}:3: KL009 missing link definition for [1.0.0]\n"
        "3 problems in 2 files\n"
    )


def test_text_ok(tmp_path, capsys):
    p = write(tmp_path, "a.md", CLEAN)
    assert main([p]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_json_output(tmp_path, capsys):
    a = write(tmp_path, "a.md", NO_LINK)
    c = write(tmp_path, "c.md", CLEAN)
    assert main([a, c, "--format", "json"]) == 1
    out = capsys.readouterr().out
    expected = {
        "files": [
            {
                "path": a,
                "findings": [
                    {
                        "line": 3,
                        "rule": "KL009",
                        "message": "missing link definition for [1.0.0]",
                    }
                ],
            },
            {"path": c, "findings": []},
        ],
        "problems": 1,
    }
    assert out == json.dumps(expected, indent=2) + "\n"
    data = json.loads(out)
    assert list(data["files"][0]) == ["path", "findings"]
    assert list(data["files"][0]["findings"][0]) == ["line", "rule", "message"]


def test_disable(tmp_path, capsys):
    p = write(tmp_path, "b.md", NO_DATE_NO_LINK)
    assert main([p, "--disable", "KL008", "--disable", "KL009"]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_disable_unknown_rule(tmp_path, capsys):
    p = write(tmp_path, "b.md", NO_DATE_NO_LINK)
    for rule in ("kl008", "KL999"):
        assert main([p, "--disable", rule]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == f'keeplint: unknown rule "{rule}"\n'


def test_exit_codes_usage(capsys):
    assert main([]) == 2
    assert main(["--bogus"]) == 2
    assert capsys.readouterr().out == ""


def test_missing_file(tmp_path, capsys):
    failing = write(tmp_path, "a.md", NO_LINK)
    missing = str(tmp_path / "nope.md")
    assert main([failing, missing]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(f"keeplint: {missing}: ")


def test_invalid_utf8(tmp_path, capsys):
    failing = write(tmp_path, "a.md", NO_LINK)
    bad = write(tmp_path, "bad.md", b"# Changelog\n\xff\xfe\n")
    assert main([failing, bad]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(f"keeplint: {bad}: ")


def test_bom_crlf(tmp_path, capsys):
    data = b"\xef\xbb\xbf# Changelog\r\n\r\n## [1.0.0] - 2026-01-01\r\n- x\r\n"
    p = write(tmp_path, "a.md", data)
    assert main([p]) == 1
    assert capsys.readouterr().out == (
        f"{p}:3: KL009 missing link definition for [1.0.0]\n1 problem in 1 file\n"
    )


def test_python_m_keeplint(tmp_path, capsys):
    p = write(tmp_path, "a.md", NO_LINK)
    code = main([p])
    expected = capsys.readouterr().out
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    proc = subprocess.run(
        [sys.executable, "-m", "keeplint", p],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == code == 1
    assert proc.stdout == expected

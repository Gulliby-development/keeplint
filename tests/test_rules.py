"""Tests for the rules engine and the library API."""

import ast
import dataclasses
import sys
import tomllib
from pathlib import Path

import pytest

from keeplint import Finding, lint

ROOT = Path(__file__).resolve().parent.parent
HEAD = "# Changelog\n\n"


def hits(text, rule=None):
    return [(f.line, f.rule, f.message) for f in lint(text) if rule is None or f.rule == rule]


def entry(version="1.0.0", date="2026-01-01"):
    """A clean section with its link definition (5 lines)."""
    return f"## [{version}] - {date}\n- x\n\n[{version}]: https://x\n\n"


# --- API ---


def test_finding_is_frozen():
    finding = Finding(1, "KL001", "m")
    assert (finding.line, finding.rule, finding.message) == (1, "KL001", "m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.line = 2  # type: ignore[misc]


def test_pyproject_declares_script():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["scripts"]["keeplint"] == "keeplint.cli:main"
    assert "src" in data["tool"]["pytest"]["ini_options"]["pythonpath"]


def test_source_imports_only_stdlib():
    for path in (ROOT / "src" / "keeplint").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                assert name == "keeplint" or name in sys.stdlib_module_names, (path, name)


def test_clean_file_and_sorting():
    assert lint(HEAD + "## [Unreleased]\n- a\n\n[Unreleased]: https://x\n") == []
    found = lint("# x\n\n## bad\n")
    assert found == sorted(found, key=lambda f: (f.line, f.rule))


# --- KL001 ---


@pytest.mark.parametrize("text", ["", "\n  \n\n", "# Changes\n"])
def test_kl001_fails_at_line_1(text):
    assert hits(text, "KL001") == [(1, "KL001", 'first line must be "# Changelog"')]


def test_kl001_passes_after_blank_lines():
    assert hits("\n\n# Changelog\n", "KL001") == []


def test_kl001_reported_at_first_nonblank_line():
    assert hits("\n\nfoo\n", "KL001") == [(3, "KL001", 'first line must be "# Changelog"')]


# --- KL002 ---


@pytest.mark.parametrize(
    "heading",
    [
        "## [Unreleased]",
        "## [1.2.0] - 2026-02-14",
        "## [1.2.0-rc.1] - 2026-02-01",
        "## [1.1.1] - 2026-01-20 [YANKED]",
        "## [1.3.0]",
    ],
)
def test_kl002_valid_headings(heading):
    assert hits(HEAD + heading + "\n", "KL002") == []


@pytest.mark.parametrize(
    "heading",
    ["## bad", "## [1.0.0]  - 2026-01-01", "## [v1.0.0]", "## [1.0.0+b] - 2026-01-01"],
)
def test_kl002_invalid_headings(heading):
    assert hits(HEAD + heading + "\n", "KL002") == [
        (3, "KL002", f'invalid version heading "{heading[3:]}"')
    ]


def test_invalid_heading_skipped_by_later_rules():
    text = HEAD + "## bad\n### Misc\n"
    assert [f.rule for f in lint(text)] == ["KL002"]


# --- KL003 ---


def test_kl003_valid_dates():
    assert hits(HEAD + "## [1.0.0] - 2028-02-29\n", "KL003") == []
    assert hits(HEAD + "## [1.0.0] - 2026-02-14\n", "KL003") == []


@pytest.mark.parametrize(
    "date", ["2026-02-29", "2026-02-30", "2026-04-31", "2026-13-01", "2026-2-3"]
)
def test_kl003_invalid_dates(date):
    assert hits(HEAD + f"## [1.0.0] - {date}\n", "KL003") == [
        (3, "KL003", f'invalid date "{date}"')
    ]


# --- KL004 ---

ORDER = ["1.0.0", "1.0.0-rc.2", "1.0.0-rc.1", "1.0.0-beta.11", "1.0.0-beta.2", "1.0.0-alpha"]


def test_kl004_descending_order_is_clean():
    text = HEAD + "".join(entry(v) for v in ORDER)
    assert hits(text, "KL004") == []


def test_kl004_swapped_pair():
    text = HEAD + entry("1.0.0") + entry("2.0.0")
    assert hits(text, "KL004") == [(8, "KL004", "2.0.0 is not lower than 1.0.0")]


def test_equal_versions_only_kl006():
    text = HEAD + "## [1.0.0] - 2026-01-01\n## [1.0.0] - 2026-01-01\n"
    assert hits(text, "KL004") == []
    assert hits(text, "KL006") == [(4, "KL006", "duplicate version 1.0.0")]


# --- KL005 / KL006 ---


def test_kl005_and_kl006_together():
    text = HEAD + "## [1.0.0]\n## [Unreleased]\n## [Unreleased]\n"
    msg = "[Unreleased] must be the first version heading"
    assert (4, "KL005", msg) in hits(text, "KL005")
    assert hits(text, "KL006") == [(5, "KL006", "duplicate version Unreleased")]


def test_kl005_kl006_pass():
    text = HEAD + "## [Unreleased]\n## [1.0.0] - 2026-01-01\n"
    assert hits(text, "KL005") == []
    assert hits(text, "KL006") == []


# --- KL007 ---


def test_kl007_failures():
    text = HEAD + "## [Unreleased]\n### Added\n### Added\n### Misc\n### added\n"
    assert hits(text, "KL007") == [
        (5, "KL007", 'duplicate section "Added"'),
        (6, "KL007", 'unknown section "Misc"'),
        (7, "KL007", 'unknown section "added"'),
    ]


def test_kl007_pass_all_names():
    names = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    text = HEAD + "## [Unreleased]\n" + "".join(f"### {n}\n" for n in names)
    assert hits(text, "KL007") == []


def test_kl007_same_name_in_different_sections():
    text = HEAD + "## [Unreleased]\n### Added\n## [1.0.0]\n### Added\n"
    assert hits(text, "KL007") == []


def test_kl007_ignored_before_first_section():
    assert hits(HEAD + "### Misc\n", "KL007") == []


# --- KL008 ---


def test_kl008_failures():
    text = HEAD + "## [Unreleased] - 2026-01-01\n## [1.3.0]\n"
    assert hits(text, "KL008") == [
        (3, "KL008", "[Unreleased] must not have a date"),
        (4, "KL008", "missing date for 1.3.0"),
    ]


def test_kl008_pass():
    text = HEAD + "## [Unreleased]\n## [1.3.0] - 2026-01-01\n"
    assert hits(text, "KL008") == []


# --- KL009 ---


def test_kl009_case_sensitive():
    text = (
        HEAD
        + "## [Unreleased]\n## [1.0.0] - 2026-01-01\n\n"
        + "[1.0.0]: https://x\n[unreleased]: https://x\n"
    )
    assert hits(text, "KL009") == [(3, "KL009", "missing link definition for [Unreleased]")]


@pytest.mark.parametrize("definition", ["[1.0.0]:", "[1.0.0]: ", " [1.0.0]: https://x"])
def test_kl009_empty_or_indented_definition(definition):
    text = HEAD + "## [1.0.0] - 2026-01-01\n" + definition + "\n"
    assert hits(text, "KL009") == [(3, "KL009", "missing link definition for [1.0.0]")]


def test_kl009_pass():
    text = HEAD + "## [1.0.0] - 2026-01-01\n\n[1.0.0]: https://x\n"
    assert hits(text, "KL009") == []


# --- KL010 ---


def test_kl010_items():
    text = (
        HEAD
        + "## [3.0.0] - 2026-03-01\n- a\n"
        + "## [2.0.0] - 2026-02-01\n* b\n"
        + "## [1.0.0] - 2026-01-01\n - c\n"
        + "## [Unreleased]\n"
    )
    assert hits(text, "KL010") == [
        (7, "KL010", "no entries under 1.0.0"),
        (9, "KL010", "no entries under Unreleased"),
    ]


# --- fences, BOM, CRLF ---


def test_fenced_content_is_ignored():
    text = HEAD + "```\n## bad\n[9.9.9]: x\n- item\n```\n## [9.9.9] - 2026-01-01\n"
    assert hits(text) == [
        (8, "KL009", "missing link definition for [9.9.9]"),
        (8, "KL010", "no entries under 9.9.9"),
    ]


def test_tilde_fence_and_indented_fence():
    assert hits(HEAD + "~~~\n## bad\n~~~\n") == []
    text = HEAD + " ```\n## bad\n"
    assert hits(text, "KL002") == [(4, "KL002", 'invalid version heading "bad"')]


def test_unclosed_fence_runs_to_end():
    assert hits(HEAD + "```\n## [1.0.0]\n## bad\n") == []


def test_long_fence_needs_long_closer():
    text = HEAD + "````\n```\n## bad\n````\n" + entry()
    assert hits(text) == []


def test_bom_and_crlf_line_numbers():
    raw = b"\xef\xbb\xbf# Changelog\r\n\r\n## [1.0.0] - 2026-01-01\r\n- x\r\n"
    assert hits(raw.decode("utf-8")) == [(3, "KL009", "missing link definition for [1.0.0]")]


def test_crlf_heading_text_has_no_carriage_return():
    found = hits("# Changelog\r\n\r\n## bad\r\n")
    assert found == [(3, "KL002", 'invalid version heading "bad"')]


def test_empty_file():
    assert lint("") == [Finding(1, "KL001", 'first line must be "# Changelog"')]

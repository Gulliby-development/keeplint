"""The ten keeplint rules and the lint() entry point."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

from keeplint import semver

RULES = (
    "KL001",
    "KL002",
    "KL003",
    "KL004",
    "KL005",
    "KL006",
    "KL007",
    "KL008",
    "KL009",
    "KL010",
)

SECTION_NAMES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")

_FENCE_RE = re.compile(r"(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"## \[([^\]]*)\](?: - (\S+))?(?: \[YANKED\])?")
_DEF_RE = re.compile(r"\[([^\]]+)\]:[ \t]*\S")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


@dataclass(frozen=True)
class Finding:
    line: int
    rule: str
    message: str


@dataclass
class _Section:
    line: int
    version: str | None  # None when the heading is invalid
    date: str | None = None
    body: list[tuple[int, str]] = field(default_factory=list)


def _visible_lines(text: str) -> list[tuple[int, str]]:
    text = text.removeprefix("\ufeff")
    result: list[tuple[int, str]] = []
    fence_char = ""
    fence_len = 0
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.removesuffix("\r")
        if fence_char:
            if line.startswith(fence_char * fence_len):
                fence_char = ""
            continue
        match = _FENCE_RE.match(line)
        if match:
            fence_char = match.group(1)[0]
            fence_len = len(match.group(1))
            continue
        result.append((number, line))
    return result


def _valid_date(date: str) -> bool:
    if not _DATE_RE.fullmatch(date):
        return False
    try:
        datetime.date(int(date[:4]), int(date[5:7]), int(date[8:10]))
    except ValueError:
        return False
    return True


def _first_nonblank(text: str) -> tuple[int, str]:
    text = text.removeprefix("\ufeff")
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.removesuffix("\r")
        if line.strip():
            return number, line
    return 1, ""


def _split_sections(lines: list[tuple[int, str]]) -> list[_Section]:
    sections: list[_Section] = []
    for number, line in lines:
        if line.startswith("## "):
            match = _HEADING_RE.fullmatch(line)
            version = None
            date = None
            if match:
                name = match.group(1)
                if name == "Unreleased" or semver.is_valid(name):
                    version = name
                    date = match.group(2)
            sections.append(_Section(number, version, date))
        elif sections:
            sections[-1].body.append((number, line))
    return sections


def lint(text: str) -> list[Finding]:
    findings: list[Finding] = []
    number, first = _first_nonblank(text)
    if first != "# Changelog":
        findings.append(Finding(number, "KL001", 'first line must be "# Changelog"'))

    lines = _visible_lines(text)
    definitions = set()
    for _, line in lines:
        match = _DEF_RE.match(line)
        if match:
            definitions.add(match.group(1))

    seen: set[str] = set()
    previous: semver.Version | None = None
    valid_index = 0
    for section in _split_sections(lines):
        at = section.line
        if section.version is None:
            heading = next(raw for n, raw in lines if n == at)[3:]
            findings.append(Finding(at, "KL002", f'invalid version heading "{heading}"'))
            continue
        version = section.version
        unreleased = version == "Unreleased"
        if section.date is not None and not _valid_date(section.date):
            findings.append(Finding(at, "KL003", f'invalid date "{section.date}"'))
        if unreleased:
            if valid_index > 0:
                msg = "[Unreleased] must be the first version heading"
                findings.append(Finding(at, "KL005", msg))
        else:
            current = semver.parse(version)
            if previous is not None and semver.compare(current, previous) > 0:
                msg = f"{version} is not lower than {previous}"
                findings.append(Finding(at, "KL004", msg))
            previous = current
        if version in seen:
            findings.append(Finding(at, "KL006", f"duplicate version {version}"))
        seen.add(version)
        valid_index += 1

        names: set[str] = set()
        has_item = False
        for n, line in section.body:
            if line.startswith("### "):
                name = line[4:]
                if name not in SECTION_NAMES:
                    findings.append(Finding(n, "KL007", f'unknown section "{name}"'))
                elif name in names:
                    findings.append(Finding(n, "KL007", f'duplicate section "{name}"'))
                names.add(name)
            elif line.startswith(("- ", "* ")):
                has_item = True

        if unreleased and section.date is not None:
            findings.append(Finding(at, "KL008", "[Unreleased] must not have a date"))
        elif not unreleased and section.date is None:
            findings.append(Finding(at, "KL008", f"missing date for {version}"))
        if version not in definitions:
            findings.append(Finding(at, "KL009", f"missing link definition for [{version}]"))
        if not has_item:
            findings.append(Finding(at, "KL010", f"no entries under {version}"))

    findings.sort(key=lambda f: (f.line, f.rule))
    return findings

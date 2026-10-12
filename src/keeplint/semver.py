"""Strict semantic version parsing and SemVer 2.0.0 precedence comparison."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUM = r"(?:0|[1-9][0-9]*)"
_IDENT = r"(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
_VERSION_RE = re.compile(
    rf"(?P<major>{_NUM})\.(?P<minor>{_NUM})\.(?P<patch>{_NUM})"
    rf"(?:-(?P<pre>{_IDENT}(?:\.{_IDENT})*))?"
)


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    def __str__(self) -> str:
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        return text


def parse(text: str) -> Version:
    """Parse a strict version string; raise ValueError when it is not valid."""
    match = _VERSION_RE.fullmatch(text)
    if match is None:
        raise ValueError(f"invalid version: {text!r}")
    pre = match.group("pre")
    return Version(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        tuple(pre.split(".")) if pre else (),
    )


def is_valid(text: str) -> bool:
    return _VERSION_RE.fullmatch(text) is not None


def _cmp(a, b) -> int:
    return (a > b) - (a < b)


def _is_num(ident: str) -> bool:
    return ident.isascii() and ident.isdigit()


def _cmp_ident(a: str, b: str) -> int:
    a_num, b_num = _is_num(a), _is_num(b)
    if a_num and b_num:
        return _cmp(int(a), int(b))
    if a_num:
        return -1
    if b_num:
        return 1
    return _cmp(a, b)


def compare(a: Version, b: Version) -> int:
    """Return -1, 0 or 1 by SemVer 2.0.0 precedence."""
    for x, y in ((a.major, b.major), (a.minor, b.minor), (a.patch, b.patch)):
        if x != y:
            return _cmp(x, y)
    if not a.prerelease and not b.prerelease:
        return 0
    if not a.prerelease:
        return 1
    if not b.prerelease:
        return -1
    for x, y in zip(a.prerelease, b.prerelease):
        result = _cmp_ident(x, y)
        if result:
            return result
    return _cmp(len(a.prerelease), len(b.prerelease))

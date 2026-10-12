"""Tests for keeplint.semver."""

import itertools

import pytest

from keeplint.semver import Version, compare, is_valid, parse


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.2.0", Version(1, 2, 0)),
        ("1.2.0-rc.1", Version(1, 2, 0, ("rc", "1"))),
        ("0.0.0", Version(0, 0, 0)),
        ("1.0.0-alpha", Version(1, 0, 0, ("alpha",))),
    ],
)
def test_parse_accepted(text, expected):
    assert parse(text) == expected
    assert is_valid(text)
    assert str(parse(text)) == text


@pytest.mark.parametrize(
    "text",
    [
        "v1.0.0",
        "1.0.0+b",
        "1.0.0-rc.1+b",
        "01.0.0",
        "1.0.0-01",
        "1.0",
        "1.0.0-",
        "1.0.0-a..b",
        "",
        " 1.0.0",
    ],
)
def test_parse_rejected(text):
    assert not is_valid(text)
    with pytest.raises(ValueError):
        parse(text)


def test_precedence_order_is_strictly_descending():
    order = [
        "1.0.0",
        "1.0.0-rc.2",
        "1.0.0-rc.1",
        "1.0.0-beta.11",
        "1.0.0-beta.2",
        "1.0.0-alpha",
    ]
    versions = [parse(t) for t in order]
    for higher, lower in itertools.pairwise(versions):
        assert compare(higher, lower) == 1
        assert compare(lower, higher) == -1


def test_prerelease_ordering():
    alpha = parse("1.0.0-alpha")
    alpha1 = parse("1.0.0-alpha.1")
    alpha_beta = parse("1.0.0-alpha.beta")
    assert compare(alpha, alpha1) == -1
    assert compare(alpha1, alpha_beta) == -1
    assert compare(alpha, alpha_beta) == -1


def test_numeric_vs_alphanumeric_and_ascii_order():
    assert compare(parse("1.0.0-1"), parse("1.0.0-a")) == -1
    assert compare(parse("1.0.0-2"), parse("1.0.0-10")) == -1
    assert compare(parse("1.0.0-B"), parse("1.0.0-a")) == -1


def test_core_comparison_and_equality():
    assert compare(parse("1.2.3"), parse("1.2.3")) == 0
    assert compare(parse("1.10.0"), parse("1.9.0")) == 1
    assert compare(parse("2.0.0"), parse("1.99.99")) == 1
    assert compare(parse("1.0.1"), parse("1.0.0")) == 1
    assert compare(parse("1.0.0-rc.1"), parse("1.0.0-rc.1")) == 0

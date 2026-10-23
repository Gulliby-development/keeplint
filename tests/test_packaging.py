"""Tests for the packaging metadata of pyproject.toml and the py.typed marker."""

from __future__ import annotations

import tomllib
from pathlib import Path

import keeplint

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_classifiers_are_exactly_the_documented_list() -> None:
    assert _pyproject()["project"]["classifiers"] == [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Quality Assurance",
        "Typing :: Typed",
    ]


def test_typed_classifier_goes_with_an_empty_marker_file() -> None:
    marker = Path(keeplint.__file__).resolve().parent / "py.typed"
    assert "Typing :: Typed" in _pyproject()["project"]["classifiers"]
    assert marker.is_file()
    assert marker.read_bytes() == b""


def test_marker_file_is_declared_as_package_data() -> None:
    assert _pyproject()["tool"]["setuptools"]["package-data"] == {"keeplint": ["py.typed"]}


def test_python_classifiers_match_requires_python() -> None:
    project = _pyproject()["project"]
    assert project["requires-python"] == ">=3.11"
    assert "Programming Language :: Python :: 3.11" in project["classifiers"]
    assert "Programming Language :: Python :: 3.10" not in project["classifiers"]


def test_existing_metadata_is_unchanged() -> None:
    project = _pyproject()["project"]
    assert project["name"] == "keeplint"
    assert project["version"] == "0.1.0"
    assert project["dependencies"] == []
    assert project["scripts"] == {"keeplint": "keeplint.cli:main"}
    assert _pyproject()["tool"]["setuptools"]["packages"] == {"find": {"where": ["src"]}}

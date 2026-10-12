<p align="center"><img src="docs/logo.svg" width="96" alt="" /></p>

# keeplint

[![CI](https://github.com/Gulliby-development/keeplint/actions/workflows/ci.yml/badge.svg)](https://github.com/Gulliby-development/keeplint/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

`keeplint` is a small linter for `CHANGELOG.md` files written in the
[Keep a Changelog](https://keepachangelog.com/) layout. It checks ten rules, never rewrites a
file, and uses only the Python standard library (Python 3.11+).

## Who it is for

Maintainers who want a consistent changelog, and CI pipelines that should fail when it drifts.

## Install

```text
pip install .
```

This installs the `keeplint` console script. `python -m keeplint` works too. For development
from a checkout, use `pip install -e .`.

## Usage

```text
keeplint FILE... [--format text|json] [--disable RULE]...
```

```text
keeplint CHANGELOG.md
keeplint CHANGELOG.md docs/CHANGELOG.md --format json
keeplint CHANGELOG.md --disable KL008 --disable KL009
python -m keeplint CHANGELOG.md
```

Files are read as UTF-8 (a leading BOM is ignored; LF and CRLF are accepted). Lines inside
fenced code blocks are ignored by every rule. `--disable` is repeatable and rule ids are
case-sensitive.

Library use:

```python
from keeplint import lint

for finding in lint(open("CHANGELOG.md", encoding="utf-8").read()):
    print(finding.line, finding.rule, finding.message)
```

## Rules

| Rule  | Checks |
| ----- | ------ |
| KL001 | The first non-blank line is exactly `# Changelog`. |
| KL002 | Every `## ` line is a valid version heading. |
| KL003 | The date, when present, is a real `YYYY-MM-DD` calendar date. |
| KL004 | Released versions are in strictly descending semver order. |
| KL005 | `[Unreleased]` is the first version heading. |
| KL006 | A version does not appear twice. |
| KL007 | `###` headings are one of Added, Changed, Deprecated, Removed, Fixed, Security, once per section. |
| KL008 | Released versions have a date; `[Unreleased]` has none. |
| KL009 | Every version heading has a `[X]: <text>` link definition. |
| KL010 | Every section has at least one `- ` or `* ` list item. |

## Example

A failing changelog:

```markdown
# Changelog

## [Unreleased]

## [1.0.0] - 2026-02-30

### Added
- First release.

## [1.1.0] - 2026-03-01
- Something.

[1.0.0]: https://example.com/1.0.0
```

Running `keeplint CHANGELOG.md` prints:

```text
CHANGELOG.md:3: KL009 missing link definition for [Unreleased]
CHANGELOG.md:3: KL010 no entries under Unreleased
CHANGELOG.md:5: KL003 invalid date "2026-02-30"
CHANGELOG.md:10: KL004 1.1.0 is not lower than 1.0.0
CHANGELOG.md:10: KL009 missing link definition for [1.1.0]
5 problems in 1 file
```

When there are no findings the only output is `ok`.

## JSON output

`keeplint CHANGELOG.md --format json` prints:

```json
{
  "files": [
    {
      "path": "CHANGELOG.md",
      "findings": [
        {
          "line": 3,
          "rule": "KL009",
          "message": "missing link definition for [Unreleased]"
        },
        {
          "line": 3,
          "rule": "KL010",
          "message": "no entries under Unreleased"
        },
        {
          "line": 5,
          "rule": "KL003",
          "message": "invalid date \"2026-02-30\""
        },
        {
          "line": 10,
          "rule": "KL004",
          "message": "1.1.0 is not lower than 1.0.0"
        },
        {
          "line": 10,
          "rule": "KL009",
          "message": "missing link definition for [1.1.0]"
        }
      ]
    }
  ],
  "problems": 5
}
```

## Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | No findings. |
| 1 | One or more findings. |
| 2 | Usage error (bad option, no files, unknown rule id) or an unreadable or non-UTF-8 file. |

## CI

GitHub Actions step:

```yaml
- name: Lint changelog
  run: |
    pip install .
    keeplint CHANGELOG.md
```

## Development

```text
python -m venv .venv
# activate it: source .venv/bin/activate (Linux, macOS) or .venv\Scriptsctivate (Windows)
pip install -e . pytest ruff
python -m pytest -q
python -m ruff check .
```

## License

MIT, see [LICENSE](LICENSE).

---

Built with BAKED, an open-source coding agent (bench loop round 5, BAKED f207b8b).

"""Text and JSON formatters."""

from __future__ import annotations

import json
from collections.abc import Sequence

from keeplint.rules import Finding

Results = Sequence[tuple[str, Sequence[Finding]]]


def format_text(results: Results) -> str:
    lines: list[str] = []
    total = 0
    with_findings = 0
    for path, findings in results:
        if findings:
            with_findings += 1
        for f in findings:
            total += 1
            lines.append(f"{path}:{f.line}: {f.rule} {f.message}")
    if total == 0:
        return "ok\n"
    problems = "problem" if total == 1 else "problems"
    files = "file" if with_findings == 1 else "files"
    lines.append(f"{total} {problems} in {with_findings} {files}")
    return "\n".join(lines) + "\n"


def format_json(results: Results) -> str:
    files = []
    total = 0
    for path, findings in results:
        total += len(findings)
        files.append(
            {
                "path": path,
                "findings": [
                    {"line": f.line, "rule": f.rule, "message": f.message} for f in findings
                ],
            }
        )
    return json.dumps({"files": files, "problems": total}, indent=2) + "\n"

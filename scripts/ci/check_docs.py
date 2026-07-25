from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ci.classify_changes import changed_paths, is_docs_fast_path


DOC_INDEX = PROJECT_ROOT / "docs" / "DOC_INDEX.md"
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*]\(([^)\n]+)\)")
INDEX_ENTRY = re.compile(r"^\s*-\s+`([^`]+)`", re.MULTILINE)
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:")
MAX_CHANGED_FILE_BYTES = 5 * 1024 * 1024


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")].strip()
    return target.split(maxsplit=1)[0].strip()


def _local_path(markdown_path: Path, raw_target: str) -> Path | None:
    target = _link_target(raw_target)
    lowered = target.lower()
    if not target or target.startswith("#") or lowered.startswith(EXTERNAL_PREFIXES):
        return None
    target = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return None
    if re.match(r"^[A-Za-z]:[\\/]", target):
        return Path(target)
    if target.startswith("/"):
        return PROJECT_ROOT / target.lstrip("/")
    return markdown_path.parent / target


def markdown_link_issues(markdown_path: Path) -> list[str]:
    text = markdown_path.read_text(encoding="utf-8")
    issues: list[str] = []
    for match in MARKDOWN_LINK.finditer(text):
        path = _local_path(markdown_path, match.group(1))
        if path is None:
            continue
        try:
            resolved = path.resolve()
            resolved.relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            issues.append(
                f"{markdown_path.relative_to(PROJECT_ROOT)}: local link escapes repository: "
                f"{match.group(1)}"
            )
            continue
        if not resolved.exists():
            line = text.count("\n", 0, match.start()) + 1
            issues.append(
                f"{markdown_path.relative_to(PROJECT_ROOT)}:{line}: missing local link: "
                f"{match.group(1)}"
            )
    return issues


def doc_index_issues() -> list[str]:
    text = DOC_INDEX.read_text(encoding="utf-8")
    issues: list[str] = []
    for match in INDEX_ENTRY.finditer(text):
        target = match.group(1).strip().replace("\\", "/")
        if any(char in target for char in "*?{}"):
            continue
        path = PROJECT_ROOT / target if target.startswith(("docs/", "outputs/")) else DOC_INDEX.parent / target
        if not path.exists():
            line = text.count("\n", 0, match.start()) + 1
            issues.append(f"docs/DOC_INDEX.md:{line}: indexed path does not exist: {target}")
    return issues


def diff_check(base: str, head: str) -> list[str]:
    from scripts.ci.classify_changes import resolve_diff_base

    resolved_base, resolved_head = resolve_diff_base(base, head)
    result = subprocess.run(
        ["git", "diff", "--check", resolved_base, resolved_head],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode == 0:
        return []
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    return [line for line in output.splitlines() if line.strip()] or [
        f"git diff --check failed with exit code {result.returncode}"
    ]


def large_file_issues(paths: list[str]) -> list[str]:
    issues: list[str] = []
    for relative in paths:
        path = PROJECT_ROOT / relative
        if path.is_file() and path.stat().st_size > MAX_CHANGED_FILE_BYTES:
            issues.append(
                f"{relative}: changed file is {path.stat().st_size} bytes; "
                f"limit is {MAX_CHANGED_FILE_BYTES}"
            )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Run dependency-free documentation checks.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    paths = changed_paths(args.base, args.head)
    issues = diff_check(args.base, args.head)
    issues.extend(large_file_issues(paths))
    for relative in paths:
        path = PROJECT_ROOT / relative
        if (
            is_docs_fast_path(relative)
            and path.is_file()
            and path.suffix.lower() == ".md"
        ):
            issues.extend(markdown_link_issues(path))
    issues.extend(doc_index_issues())
    if issues:
        print("Fast documentation checks failed:")
        for issue in issues:
            print(f"- {issue}")
        return 2
    changed_markdown = sum(
        1
        for relative in paths
        if is_docs_fast_path(relative) and relative.lower().endswith(".md")
    )
    print(f"Fast documentation checks passed; changed_markdown={changed_markdown}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

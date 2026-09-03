"""Build a conservative repository reachability inventory for consolidation review."""
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "repository_consolidation_v1"
TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".md", ".toml", ".csv", ".gitattributes", ".gitignore"}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace").strip()


def tracked() -> set[str]:
    return set(git("ls-files").splitlines())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tracked_paths = tracked()
    # Git is the authoritative complete set; include untracked files only from
    # human-maintained surfaces so runtime caches cannot dominate the scan.
    file_paths = [ROOT / rel for rel in tracked_paths]
    for surface in ("docs", "configs", "scripts", "reports"):
        file_paths.extend(p for p in (ROOT / surface).rglob("*") if p.is_file())
    files = sorted(set(p for p in file_paths if p.is_file() and ".git" not in p.parts))
    rels = [p.relative_to(ROOT).as_posix() for p in files]
    rel_set = set(rels)
    contents: dict[str, str] = {}
    for path, rel in zip(files, rels):
        if (path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitignore", ".gitattributes"}) and (rel.startswith(("docs/", "configs/", "scripts/", "reports/")) or rel in {"README.md", "README.zh-CN.md", "AGENTS.md", ".gitignore", ".gitattributes"}):
            try:
                contents[rel] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                contents[rel] = ""

    # A single HEAD lookup keeps this audit fast; per-file historical blame is
    # intentionally left to targeted follow-up reviews.
    head_commit = git("rev-parse", "HEAD")

    with (OUT / "file_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "file_type", "tracked", "size_bytes", "sha256", "last_commit"])
        writer.writeheader()
        for path, rel in zip(files, rels):
            try:
                last = head_commit if rel in tracked_paths else ""
                size = path.stat().st_size
                # Large runtime caches/outputs are inventoried by size only; hashing
                # them would make a static consolidation audit unnecessarily heavy.
                digest = sha256(path) if size <= 100 * 1024 * 1024 else "SKIPPED_LARGE_FILE"
            except OSError:
                last, digest, size = "", "", 0
            writer.writerow({"path": rel, "file_type": path.suffix.lower().lstrip(".") or "directoryless", "tracked": rel in tracked_paths, "size_bytes": size, "sha256": digest, "last_commit": last})

    with (OUT / "reference_edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "target", "edge_type"])
        writer.writeheader()
        for source, body in contents.items():
            # Resolve explicit slash-delimited repository paths found in text. This
            # keeps the audit bounded even when outputs contain many binary files.
            tokens = set(re.findall(r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", body))
            for target in sorted(tokens & rel_set):
                if target == source:
                    continue
                edge_type = "path_string"
                if source.endswith(".py") and target.endswith(".py"):
                    edge_type = "python_path_or_import"
                elif source.endswith((".yaml", ".yml")):
                    edge_type = "yaml_path"
                elif source.endswith(".json"):
                    edge_type = "json_path"
                elif source.endswith(".md"):
                    edge_type = "markdown_path"
                writer.writerow({"source": source, "target": target, "edge_type": edge_type})

    pinned_tokens = ("qualification", "manifest", "receipt", "artifact", "lineage", "reference", "canonical", "forward")
    with (OUT / "classification.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "classification", "reason"])
        writer.writeheader()
        for rel in rels:
            inbound = [src for src, body in contents.items() if src != rel and rel in body]
            if rel.startswith(("docs/", "README")) and "/_archive/" in rel:
                cls, reason = "ARCHIVED", "historical documentation archive"
            elif inbound or any(token in rel.lower() for token in pinned_tokens) or rel.startswith(("artifacts/", "outputs/", "reports/")):
                cls, reason = "PINNED_REFERENCE", "reachable or evidence-sensitive; retained in place"
            else:
                cls, reason = "ACTIVE", "default working surface or unclassified source"
            writer.writerow({"path": rel, "classification": cls, "reason": reason})

    with (OUT / "dead_code_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "candidate_reason"])
        writer.writeheader()
        for rel in rels:
            if rel.startswith("scripts/") and rel.endswith(".py") and not any(rel in body for body in contents.values()):
                writer.writerow({"path": rel, "candidate_reason": "no textual repository references; review manually, do not auto-delete"})

    stamp = datetime.now(timezone.utc).isoformat()
    (OUT / "AUDIT_METADATA.txt").write_text(f"generated_at_utc={stamp}\nroot={ROOT}\ntracked_files={len(tracked_paths)}\nscanned_files={len(files)}\n", encoding="utf-8")


if __name__ == "__main__":
    main()

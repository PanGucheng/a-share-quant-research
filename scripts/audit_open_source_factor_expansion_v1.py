from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/open_source_factor_expansion_audit_v1.yaml")
LICENSE_FILES = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "DESCRIPTION"]
LICENSE_HINTS = {
    "apache license": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "mit license": "MIT",
    "permission is hereby granted": "MIT",
    "bsd": "BSD",
    "gnu general public license": "GPL-3.0",
    "gpl-3": "GPL-3.0",
}


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def git_head(path: Path) -> str:
    if not (path / ".git").exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


def detect_license(path: Path, configured: str) -> tuple[str, str]:
    if not path.exists():
        return configured or "unknown", ""
    for name in LICENSE_FILES:
        candidate = path / name
        if not candidate.exists():
            continue
        text = read_text(candidate).lower()
        for hint, license_name in LICENSE_HINTS.items():
            if hint in text:
                return license_name, portable_path(candidate)
    return configured or "unknown", ""


def source_file_status(path: Path, files: list[str]) -> tuple[str, int, int, str]:
    if not path.exists():
        return "missing_local_path", 0, len(files), ""
    existing = []
    missing = []
    for item in files:
        target = path / item
        if target.exists():
            existing.append(item)
        else:
            matches = list(path.glob(item))
            if matches:
                existing.append(item)
            else:
                missing.append(item)
    if not files:
        return "no_declared_files", 0, 0, ""
    if not missing:
        status = "pass"
    elif existing:
        status = "partial"
    else:
        status = "missing"
    return status, len(existing), len(missing), ";".join(missing)


def count_code_files(path: Path) -> int:
    if not path.exists():
        return 0
    suffixes = {".py", ".r", ".cpp", ".h", ".ipynb"}
    return sum(1 for item in path.rglob("*") if item.is_file() and item.suffix.lower() in suffixes)


def count_candidate_rows(path: Path, candidate_id: str) -> int | None:
    if not path.exists():
        return None
    if candidate_id == "china_ashare_equity_characteristics" and (path / "char_list.csv").exists():
        return int(len(pd.read_csv(path / "char_list.csv")))
    if candidate_id == "multi_factor_fundamental_formulas" and (path / "factor_code").exists():
        return int(len(list((path / "factor_code").glob("*.py"))))
    if candidate_id == "techfactor_gtja191":
        return 191
    if candidate_id == "qlib_alpha360":
        return 360
    return None


def score_candidate(row: dict[str, Any], policy: dict[str, Any]) -> tuple[int, str, str]:
    compatible = set(str(item) for item in policy.get("compatible_licenses", []))
    license_name = str(row["detected_license"])
    data_fit = str(row["data_fit"])
    complexity = str(row["adapter_complexity"])
    source_status = str(row["source_file_status"])
    reuse_mode = str(row["reuse_mode"])

    score = 0
    reasons = []
    if row["local_status"] == "available":
        score += 2
        reasons.append("local_available")
    if source_status == "pass":
        score += 2
        reasons.append("source_files_pass")
    elif source_status == "partial":
        score += 1
        reasons.append("source_files_partial")

    if license_name in compatible:
        score += 3
        reasons.append("compatible_license")
    elif license_name == "GPL-3.0":
        score -= 2
        reasons.append("gpl_reference_only")
    else:
        score -= 1
        reasons.append("license_review_required")

    if data_fit == "high":
        score += 3
        reasons.append("qlib_data_fit_high")
    elif data_fit == "medium":
        score += 1
        reasons.append("data_fit_medium")
    elif data_fit == "external":
        reasons.append("external_series_not_stock_panel")
    else:
        score -= 1
        reasons.append("data_audit_required")

    if complexity == "low":
        score += 2
        reasons.append("low_adapter_complexity")
    elif complexity == "medium":
        score += 1
        reasons.append("medium_adapter_complexity")
    else:
        score -= 1
        reasons.append("high_adapter_complexity")

    if "direct" in reuse_mode and license_name in compatible and data_fit == "high":
        recommendation = "direct_adapter_next"
    elif license_name in compatible and data_fit == "medium":
        recommendation = "data_audit_next"
    elif license_name in compatible:
        recommendation = "watch_after_data_audit"
    elif license_name == "GPL-3.0":
        recommendation = "reference_only_due_gpl"
    else:
        recommendation = "reference_only_until_license_review"
    return score, recommendation, "|".join(reasons)


def audit_candidate(candidate: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    path = resolve_path(candidate.get("local_path", ""))
    local_status = "available" if path.exists() else "missing"
    configured_license = str(candidate.get("license", "unknown"))
    detected_license, license_file = detect_license(path, configured_license)
    files = [str(item) for item in candidate.get("source_files", [])]
    file_status, existing_count, missing_count, missing_files = source_file_status(path, files)
    commit = git_head(path) or str(candidate.get("commit", ""))
    row = {
        "candidate_id": candidate["id"],
        "name": candidate.get("name", candidate["id"]),
        "url": candidate.get("url", ""),
        "local_path": portable_path(path),
        "local_status": local_status,
        "configured_commit": candidate.get("commit", ""),
        "local_commit": commit,
        "configured_license": configured_license,
        "detected_license": detected_license,
        "license_file": license_file,
        "source_type": candidate.get("source_type", ""),
        "planned_role": candidate.get("planned_role", ""),
        "reuse_mode": candidate.get("reuse_mode", ""),
        "data_fit": candidate.get("data_fit", ""),
        "adapter_complexity": candidate.get("adapter_complexity", ""),
        "source_file_status": file_status,
        "source_files_declared": len(files),
        "source_files_existing": existing_count,
        "source_files_missing": missing_count,
        "missing_source_files": missing_files,
        "code_file_count": count_code_files(path),
        "candidate_item_count": count_candidate_rows(path, str(candidate["id"])),
        "notes": candidate.get("notes", ""),
    }
    score, recommendation, reasons = score_candidate(row, policy)
    row["priority_score"] = score
    row["recommendation"] = recommendation
    row["score_reasons"] = reasons
    return row


def build_next_steps(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if candidates.empty:
        return pd.DataFrame()
    direct = candidates[candidates["recommendation"].eq("direct_adapter_next")].sort_values(
        ["priority_score", "candidate_id"], ascending=[False, True]
    )
    data_audit = candidates[candidates["recommendation"].eq("data_audit_next")].sort_values(
        ["priority_score", "candidate_id"], ascending=[False, True]
    )
    reference = candidates[candidates["recommendation"].astype(str).str.startswith("reference_only")].sort_values(
        ["priority_score", "candidate_id"], ascending=[False, True]
    )
    if not direct.empty:
        top = direct.iloc[0]
        rows.append(
            {
                "step_order": 1,
                "candidate_id": top["candidate_id"],
                "action": "build_adapter_smoke_plan",
                "reason": "Best compatible high-fit source for immediate factor-pool expansion.",
            }
        )
    if not data_audit.empty:
        top = data_audit.iloc[0]
        rows.append(
            {
                "step_order": 2,
                "candidate_id": top["candidate_id"],
                "action": "build_data_capability_audit",
                "reason": "Useful for industry/style/fundamental expansion but requires data mapping first.",
            }
        )
    if not reference.empty:
        rows.append(
            {
                "step_order": 3,
                "candidate_id": ",".join(reference["candidate_id"].head(3).tolist()),
                "action": "keep_reference_only",
                "reason": "License, runtime, or data assumptions are not safe for direct import yet.",
            }
        )
    return pd.DataFrame(rows)


def write_report(output_dir: Path, candidates: pd.DataFrame, next_steps: pd.DataFrame, policy: dict[str, Any]) -> None:
    recommendation_counts = candidates.groupby("recommendation").size().reset_index(name="count")
    top_view = candidates[
        [
            "candidate_id",
            "detected_license",
            "data_fit",
            "adapter_complexity",
            "priority_score",
            "recommendation",
            "candidate_item_count",
            "source_file_status",
        ]
    ].sort_values(["priority_score", "candidate_id"], ascending=[False, True])
    lines = [
        "# Open Source Factor Expansion Audit V1",
        "",
        "- Scope: source and data-family audit only; no model training, no strategy tuning, no direct GPL/unknown-license code import.",
        "- Boundary: every future source still needs data_quality, tradability, adapter smoke, V4 batch, promotion/holdout, screening, and judgement.",
        "",
        "## Policy",
        "",
        markdown_table(pd.DataFrame([{
            "compatible_licenses": ",".join(policy.get("compatible_licenses", [])),
            "caution_licenses": ",".join(policy.get("caution_licenses", [])),
            "required_prefilter": ",".join(policy.get("required_prefilter", [])),
        }])),
        "",
        "## Recommendation Counts",
        "",
        markdown_table(recommendation_counts),
        "",
        "## Candidate Ranking",
        "",
        markdown_table(top_view),
        "",
        "## Next Steps",
        "",
        markdown_table(next_steps),
        "",
        "## Output Files",
        "",
        "- `open_source_factor_source_candidates.csv`",
        "- `open_source_factor_expansion_next_steps.csv`",
        "- `open_source_factor_expansion_manifest.json`",
        "- `open_source_factor_expansion_report.md`",
    ]
    (output_dir / "open_source_factor_expansion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> Path:
    config = load_yaml(config_path)
    output_dir = resolve_path(config.get("output_dir", "outputs/open_source_factor_expansion_audit_v1/current"))
    output_dir.mkdir(parents=True, exist_ok=True)
    policy = config.get("policy", {}) or {}
    rows = [audit_candidate(candidate, policy) for candidate in config.get("candidates", [])]
    candidates = pd.DataFrame(rows).sort_values(["priority_score", "candidate_id"], ascending=[False, True])
    next_steps = build_next_steps(candidates)
    candidates.to_csv(output_dir / "open_source_factor_source_candidates.csv", index=False, encoding="utf-8-sig")
    next_steps.to_csv(output_dir / "open_source_factor_expansion_next_steps.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "policy": policy,
        "candidate_count": int(len(candidates)),
        "recommendation_counts": candidates.groupby("recommendation").size().to_dict() if not candidates.empty else {},
        "records": candidates.where(pd.notna(candidates), None).to_dict(orient="records"),
    }
    (output_dir / "open_source_factor_expansion_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    write_report(output_dir, candidates, next_steps, policy)
    print(f"Open-source factor expansion audit outputs written to {output_dir}", flush=True)
    print(f"Candidates: {len(candidates)}", flush=True)
    if not next_steps.empty:
        print(f"Next candidate: {next_steps.iloc[0]['candidate_id']}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit open-source factor/data sources for the next expansion stage.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()

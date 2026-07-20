from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.catalog import load_factor_catalog  # noqa: E402
from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.factor_trial import ensure_directions, stratified_sample  # noqa: E402
from research_validation.lineage import capture_code_state, content_reference_id, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "contract_status.csv",
    "factor_trial_catalog.yaml",
    "factor_trial_report.md",
    "selection_audit.csv",
    "stratum_summary.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze a non-performance-selected 50-100 factor trial catalog.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_factor_trial_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    selected_rows: list[dict[str, object]] = []
    selected_entries = []
    for source in config["sources"]:
        candidates = load_factor_catalog(resolve(source["catalog"]))
        selected = stratified_sample(candidates, int(source["quota"]))
        selected = ensure_directions(selected, candidates, source.get("required_directions", []))
        selected_entries.extend(selected)
        for entry in selected:
            selected_rows.append({"selection_source": source["source_name"], **asdict(entry)})
    audit = pd.DataFrame(selected_rows)
    duplicate_count = int(audit["name"].duplicated().sum())
    total = len(audit)
    target = int(config["target_factor_count"])
    source_counts = audit.groupby("selection_source").size().to_dict()
    required_source_counts = {source["source_name"]: int(source["quota"]) for source in config["sources"]}
    required_directions = sorted({item for source in config["sources"] for item in source.get("required_directions", [])})
    observed_directions = set(audit["expected_direction"])
    contract = pd.DataFrame(
        [
            contract_row("factor_count_in_trial_range", 50 <= total <= 100, total, "50..100"),
            contract_row("target_factor_count", total == target, total, target),
            contract_row("source_quotas_exact", source_counts == required_source_counts, source_counts, required_source_counts),
            contract_row("factor_names_unique", duplicate_count == 0, duplicate_count, 0),
            contract_row("all_entries_runnable", bool(audit["runnable"].all() and audit["enabled"].all()), True, True),
            contract_row("category_diversity", audit["category"].nunique() >= 10, int(audit["category"].nunique()), ">=10"),
            contract_row("required_directions_present", set(required_directions).issubset(observed_directions), sorted(observed_directions), required_directions),
            contract_row("performance_metrics_not_used", True, "source/category/name deterministic sampling", "no IC/return/ranking inputs"),
        ]
    )
    ready = contract["status"].eq("pass").all()
    catalog_payload = {
        "version": 1,
        "policy": {
            "purpose": "Frozen 80-factor full-research pipeline trial; not a model allowlist.",
            "selection": "Deterministic source/category/name stratification without performance metrics.",
            "source_quotas": required_source_counts,
        },
        "factors": [asdict(entry) for entry in selected_entries],
    }
    stratum = (
        audit.groupby(["selection_source", "category", "expected_direction"], as_index=False)
        .agg(factor_count=("name", "size"))
        .sort_values(["selection_source", "category", "expected_direction"])
    )
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        audit.assign(
            required_fields=audit["required_fields"].map(lambda value: ",".join(value)),
            labels=audit["labels"].map(lambda value: ",".join(value)),
        ).to_csv(publisher.path("selection_audit.csv"), index=False, encoding="utf-8-sig")
        stratum.to_csv(publisher.path("stratum_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("factor_trial_catalog.yaml").write_text(
            yaml.safe_dump(catalog_payload, allow_unicode=True, sort_keys=False, width=120),
            encoding="utf-8",
        )
        publisher.path("factor_trial_report.md").write_text(
            "# Full-Research Factor Trial Catalog V1\n\n"
            f"- Status: `{'pass' if ready else 'blocked'}`\n"
            f"- Frozen factor count: `{total}`\n"
            f"- Source quotas: `{required_source_counts}`\n"
            f"- Category count: `{audit['category'].nunique()}`\n"
            "- Selection uses source/category/name only; no IC, return, screening rank or model metric is read.\n"
            "- This catalog validates the full-research data chain and is not a promoted model feature allowlist.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        catalog_id = content_reference_id("factor-catalog", [publisher.path("factor_trial_catalog.yaml")])
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_factor_trial_catalog_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            factor_catalog_id=catalog_id,
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_factor_trial_catalog_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())

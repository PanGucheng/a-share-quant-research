from __future__ import annotations

import argparse
import math
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
from research_validation.lineage import capture_code_state, content_reference_id, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = ["artifact_manifest.json", "batch_plan.csv", "contract_status.csv", "factor_catalog_669.yaml", "factor_catalog_report.md", "factor_inventory.csv", "source_summary.csv"]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze all 669 promoted runnable factors without performance reselection.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_factor_catalog_669_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    rows: list[dict[str, object]] = []
    entries = []
    source_rows: list[dict[str, object]] = []
    batch_rows: list[dict[str, object]] = []
    maximum = int(config["maximum_partition_factor_count"])
    for source in config["sources"]:
        candidates = sorted(
            (entry for entry in load_factor_catalog(resolve(source["catalog"])) if entry.enabled and entry.runnable),
            key=lambda entry: (entry.category, entry.name),
        )
        entries.extend(candidates)
        source_rows.append({"source": source["source_name"], "factor_count": len(candidates), "expected_count": int(source["expected_count"]), "catalog": source["catalog"]})
        for index, entry in enumerate(candidates):
            partition_index = index // maximum + 1
            batch_id = f"{source['source_name']}_{partition_index:03d}"
            rows.append({"source": source["source_name"], "batch_id": batch_id, **asdict(entry)})
        for partition_index in range(1, math.ceil(len(candidates) / maximum) + 1):
            batch_entries = candidates[(partition_index - 1) * maximum:partition_index * maximum]
            batch_rows.append({
                "batch_id": f"{source['source_name']}_{partition_index:03d}", "source": source["source_name"],
                "factor_count": len(batch_entries), "first_factor": batch_entries[0].name, "last_factor": batch_entries[-1].name,
                "status": "frozen",
            })
    inventory = pd.DataFrame(rows)
    source_summary = pd.DataFrame(source_rows)
    batch_plan = pd.DataFrame(batch_rows)
    duplicate_count = int(inventory["name"].duplicated().sum())
    target = int(config["target_factor_count"])
    source_counts_match = bool(source_summary["factor_count"].eq(source_summary["expected_count"]).all())
    contract = pd.DataFrame([
        contract_row("factor_count_exact", len(inventory) == target, len(inventory), target),
        contract_row("source_counts_exact", source_counts_match, source_summary.set_index("source")["factor_count"].to_dict(), source_summary.set_index("source")["expected_count"].to_dict()),
        contract_row("factor_names_unique", duplicate_count == 0, duplicate_count, 0),
        contract_row("all_entries_runnable", bool(inventory["runnable"].all() and inventory["enabled"].all()), True, True),
        contract_row("partition_size_bounded", bool(batch_plan["factor_count"].le(maximum).all()), int(batch_plan["factor_count"].max()), f"<={maximum}"),
        contract_row("partition_coverage_exact", int(batch_plan["factor_count"].sum()) == target, int(batch_plan["factor_count"].sum()), target),
        contract_row("performance_metrics_not_used", True, "all enabled+runnable catalog entries in deterministic category/name order", "no IC/return/ranking inputs"),
    ])
    ready = contract["status"].eq("pass").all()
    payload = {
        "version": 1,
        "policy": {
            "purpose": "Frozen 669-factor full-research scale run; not a model allowlist.",
            "selection": "All promoted enabled+runnable entries; no performance reselection.",
            "source_counts": source_summary.set_index("source")["factor_count"].to_dict(),
            "maximum_partition_factor_count": maximum,
        },
        "factors": [asdict(entry) for entry in entries],
    }
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        inventory.assign(
            required_fields=inventory["required_fields"].map(lambda value: ",".join(value)),
            labels=inventory["labels"].map(lambda value: ",".join(value)),
        ).to_csv(publisher.path("factor_inventory.csv"), index=False, encoding="utf-8-sig")
        source_summary.to_csv(publisher.path("source_summary.csv"), index=False, encoding="utf-8-sig")
        batch_plan.to_csv(publisher.path("batch_plan.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("factor_catalog_669.yaml").write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
        publisher.path("factor_catalog_report.md").write_text(
            "# Full-Research 669-Factor Catalog V1\n\n"
            f"- Status: `{'pass' if ready else 'blocked'}`\n- Factors: `{len(inventory)}` / `{target}`\n"
            f"- Sources: `{source_summary.set_index('source')['factor_count'].to_dict()}`\n"
            f"- Partitions: `{len(batch_plan)}`, maximum `{maximum}` factors each.\n"
            "- All promoted runnable factors are included without IC, return, rank, or model-based reselection.\n"
            "- This is the PR #4 scale-run catalog, not the frozen model feature allowlist.\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="full_research_factor_catalog_669_v1", config=config,
            output_dir=publisher.staging_dir, output_files=files, code_state=code_state,
            factor_catalog_id=content_reference_id("factor-catalog", [publisher.path("factor_catalog_669.yaml")]),
            missing_lineage_fields=[], artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_full_factor_catalog_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())

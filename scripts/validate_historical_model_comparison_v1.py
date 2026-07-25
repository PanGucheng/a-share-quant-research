from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


def main() -> None:
    output_dir = PROJECT_ROOT / "outputs/historical_model_comparison_v1/current"
    manifest = load_artifact_manifest(output_dir / "artifact_manifest.json")
    assert manifest["stage_id"] == "historical_model_comparison_v1"
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    assert not validate_manifest_outputs(manifest, output_dir)

    contracts = pd.read_csv(output_dir / "contract_status.csv")
    assert contracts["status"].eq("pass").all()
    metrics = pd.read_csv(output_dir / "split_metrics.csv")
    assert len(metrics) == 15
    assert set(metrics["method"]) == {
        "equal_weight",
        "stability_weight",
        "ridge",
        "elastic_net",
        "lightgbm",
    }
    daily = pd.read_csv(output_dir / "daily_ic.csv")
    assert len(daily) == 1840
    assert daily["status"].eq("pass").all()
    pairwise = pd.read_csv(
        output_dir / "pairwise_daily_ic_differences.csv"
    )
    assert len(pairwise) == 30

    leader = json.loads(
        (output_dir / "historical_research_leader.json").read_text(
            encoding="utf-8"
        )
    )
    assert leader["historical_oos_research_leader"] == "lightgbm"
    assert leader["production_model_selected"] is False
    assert leader["unbiased_final_estimate"] is False
    readiness = pd.read_csv(output_dir / "readiness_summary.csv").iloc[0]
    assert bool(readiness["historical_oos_model_comparison_complete"])
    assert not bool(
        readiness["five_method_historical_portfolio_comparison_complete"]
    )
    assert readiness["portfolio_comparison_status"] == (
        "blocked_execution_capability"
    )
    print("historical model comparison v1 validation passed")


if __name__ == "__main__":
    main()

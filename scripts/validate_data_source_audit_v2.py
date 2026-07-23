from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import load_artifact_manifest, validate_manifest_outputs


def main() -> int:
    directory = PROJECT_ROOT / "outputs" / "data_source_audit_v2" / "current"
    manifest = load_artifact_manifest(directory / "artifact_manifest.json")
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    assert not manifest["code_dirty"]
    assert not validate_manifest_outputs(manifest, directory)
    contracts = pd.read_csv(directory / "contract_status.csv")
    assert contracts.loc[contracts["severity"].eq("critical"), "status"].eq("pass").all()
    readiness = pd.read_csv(directory / "readiness_summary.csv").iloc[0]
    assert bool(readiness["data_source_audit_v2_ready"])
    assert readiness["source_decision"] == "Decision B"
    assert bool(readiness["community_core_ohlc_reliable"])
    assert bool(readiness["community_unit_semantics_correction_required"])
    assert float(readiness["baostock_source_coverage"]) == 1.0
    assert float(readiness["akshare_eastmoney_source_coverage"]) == 0.02
    assert not bool(readiness["akshare_endpoint_stable"])
    assert not bool(readiness["execution_semantics_accuracy_ready"])
    comparison = pd.read_csv(directory / "comparison_summary.csv")
    bao = comparison.loc[
        comparison["left_source"].eq("community")
        & comparison["right_source"].eq("baostock")
    ].iloc[0]
    for field in [
        "close_tolerance_match_rate",
        "volume_tolerance_match_rate",
        "amount_tolerance_match_rate",
    ]:
        assert float(bao[field]) == 1.0
    receipts = pd.read_csv(directory / "source_query_receipts.csv")
    assert len(receipts) == 450
    assert receipts.loc[receipts["source"].eq("baostock"), "http_or_api_status"].eq("success").all()
    assert (
        receipts.loc[receipts["source"].eq("akshare_eastmoney"), "http_or_api_status"]
        .str.contains("ProxyError")
        .sum()
        == 147
    )
    central = pd.read_csv(
        PROJECT_ROOT / "outputs/accuracy_correction_v1/current/readiness_summary.csv"
    ).iloc[0]
    assert (
        central["accuracy_correction_status"]
        == "execution_unit_semantics_corrected_authoritative_state_blocked"
    )
    assert bool(central["execution_semantics_accuracy_ready"])
    assert not bool(central["market_cache_v2_ready"])
    assert bool(central["market_cache_v3_ready"])
    assert bool(central["execution_unit_semantics_ready"])
    assert bool(central["model_entry_hard_stop_active"])
    print("Data Source Audit V2 Decision B receipts pass; V1.2 unit correction is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

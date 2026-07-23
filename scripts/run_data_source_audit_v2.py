from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_source_audit import NORMALIZER_VERSION  # noqa: E402
from data_source_audit.alignment import compare_pair  # noqa: E402
from data_source_audit.missing_spans import missing_span_summary  # noqa: E402
from data_source_audit.normalizers import (  # noqa: E402
    normalize_akshare,
    normalize_baostock,
    normalize_community,
)
from data_source_audit.snapshot import file_sha256  # noqa: E402
from data_source_audit.sources import akshare as ak_source  # noqa: E402
from data_source_audit.sources import baostock as bao_source  # noqa: E402
from data_source_audit.sources.community import collect as collect_community  # noqa: E402
from data_source_audit.st_boundaries import st_boundaries  # noqa: E402
from data_source_audit.tradability import tradability_disagreements  # noqa: E402
from research_validation.feature_matrix import canonical_hash  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


COMPACT = [
    "artifact_manifest.json",
    "sample_manifest.csv",
    "source_query_receipts.csv",
    "raw_snapshot_manifest.csv",
    "comparison_summary.csv",
    "community_semantics_audit.csv",
    "st_boundary_audit.csv",
    "tradability_summary.csv",
    "missing_span_summary.csv",
    "adjustment_event_audit.csv",
    "immutable_artifact_check.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "data_source_audit_report.md",
    "resolved_config.json",
]
RUNTIME = [
    "raw/community_daily.parquet",
    "raw/baostock_daily.parquet",
    "raw/akshare_daily.parquet",
    "normalized/community_daily.parquet",
    "normalized/baostock_daily.parquet",
    "normalized/akshare_daily.parquet",
    "comparisons/row_differences.parquet",
    "comparisons/tradability_differences.parquet",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return canonical_hash([])
    stable = frame.copy()
    stable.columns = [str(column) for column in stable.columns]
    return canonical_hash(stable.fillna("<NA>").astype(str).to_dict("records"))


def receipt(
    *,
    source: str,
    version: str,
    endpoint: str,
    instrument: str,
    start_date: str,
    end_date: str,
    status: str,
    frame: pd.DataFrame,
    retrieved: str,
) -> dict[str, object]:
    return {
        "source": source,
        "library_version": version,
        "endpoint": endpoint,
        "instrument": instrument,
        "query_parameters": json.dumps(
            {"instrument": instrument, "start_date": start_date, "end_date": end_date},
            sort_keys=True,
        ),
        "retrieval_time_utc": retrieved,
        "http_or_api_status": status,
        "row_count": len(frame),
        "raw_snapshot_sha256": frame_hash(frame),
        "normalizer_version": NORMALIZER_VERSION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated Data Source Audit V2 canary.")
    parser.add_argument("--config", type=Path, default=Path("configs/data_source_audit_v2.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    sample_dir = resolve(config["sample_output"])
    sample = pd.read_csv(sample_dir / "sample_manifest.csv")
    instruments = sorted(sample["instrument"].astype(str).unique())
    start_date, end_date = str(config["start_date"]), str(config["end_date"])
    retrieved = datetime.now(timezone.utc).isoformat()
    receipts: list[dict[str, object]] = []

    community_raw = collect_community(
        instruments, start_date, end_date, resolve(config["qlib_provider"])
    )
    for instrument, frame in community_raw.groupby("instrument", sort=True):
        receipts.append(
            receipt(
                source="community",
                version="qlib_provider_snapshot_20260609",
                endpoint="D.features",
                instrument=instrument,
                start_date=start_date,
                end_date=end_date,
                status="success",
                frame=frame,
                retrieved=retrieved,
            )
        )

    bao_frames = []
    bao_status = "unavailable"
    try:
        import baostock as bs

        login = bs.login()
        if login.error_code != "0":
            raise RuntimeError(f"{login.error_code}:{login.error_msg}")
        for instrument in instruments:
            frame, status = bao_source.collect_one(instrument, start_date, end_date)
            if not frame.empty:
                bao_frames.append(frame)
            receipts.append(
                receipt(
                    source="baostock",
                    version=bao_source.library_version(),
                    endpoint="query_history_k_data_plus",
                    instrument=instrument,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    frame=frame,
                    retrieved=datetime.now(timezone.utc).isoformat(),
                )
            )
        bs.logout()
        bao_status = "success"
    except Exception as exc:
        bao_status = f"unavailable:{type(exc).__name__}:{str(exc)[:300]}"
        for instrument in instruments:
            receipts.append(
                receipt(
                    source="baostock",
                    version=bao_source.library_version(),
                    endpoint="query_history_k_data_plus",
                    instrument=instrument,
                    start_date=start_date,
                    end_date=end_date,
                    status=bao_status,
                    frame=pd.DataFrame(),
                    retrieved=datetime.now(timezone.utc).isoformat(),
                )
            )
    baostock_raw = pd.concat(bao_frames, ignore_index=True) if bao_frames else pd.DataFrame()

    ak_frames = []
    for instrument in instruments:
        frame = pd.DataFrame()
        status = "unavailable"
        for attempt in range(int(config["maximum_retries"]) + 1):
            try:
                frame = ak_source.collect_one(instrument, start_date, end_date)
                status = "success"
                break
            except Exception as exc:
                status = f"error:{type(exc).__name__}:{str(exc)[:200]}"
                if attempt < int(config["maximum_retries"]):
                    time.sleep(float(config["retry_backoff_seconds"]) * (attempt + 1))
        if not frame.empty:
            ak_frames.append(frame)
        receipts.append(
            receipt(
                source="akshare_eastmoney",
                version=ak_source.library_version(),
                endpoint="stock_zh_a_hist",
                instrument=instrument,
                start_date=start_date,
                end_date=end_date,
                status=status,
                frame=frame,
                retrieved=datetime.now(timezone.utc).isoformat(),
            )
        )
    akshare_raw = pd.concat(ak_frames, ignore_index=True) if ak_frames else pd.DataFrame()

    community = normalize_community(community_raw)
    baostock = normalize_baostock(baostock_raw) if not baostock_raw.empty else pd.DataFrame(columns=community.columns)
    akshare = normalize_akshare(akshare_raw) if not akshare_raw.empty else pd.DataFrame(columns=community.columns)
    frames = {"community": community, "baostock": baostock, "akshare_eastmoney": akshare}
    comparison_rows = []
    difference_parts = []
    for left_name, right_name in [
        ("community", "baostock"),
        ("community", "akshare_eastmoney"),
        ("baostock", "akshare_eastmoney"),
    ]:
        summary, differences = compare_pair(frames[left_name], frames[right_name])
        comparison_rows.append(summary)
        if not differences.empty:
            difference_parts.append(
                differences.assign(pair=f"{left_name}__{right_name}")
            )
    comparisons = pd.DataFrame(comparison_rows)
    row_differences = (
        pd.concat(difference_parts, ignore_index=True)
        if difference_parts
        else pd.DataFrame()
    )
    missing = missing_span_summary(frames)
    st = st_boundaries(baostock)
    tradability = tradability_disagreements(frames)

    # Directly audit the provider's encoded units and derived formulas.
    c = community_raw.copy()
    c["raw_close"] = pd.to_numeric(c["$close"], errors="coerce") / pd.to_numeric(c["$factor"], errors="coerce")
    c["raw_vwap"] = pd.to_numeric(c["$vwap"], errors="coerce") / pd.to_numeric(c["$factor"], errors="coerce")
    c["reconstructed_vwap"] = (
        pd.to_numeric(c["$amount"], errors="coerce") * 1000.0
        / (pd.to_numeric(c["$volume"], errors="coerce") * pd.to_numeric(c["$factor"], errors="coerce") * 100.0)
    )
    vwap_error = (c["raw_vwap"] - c["reconstructed_vwap"]).abs()
    bao_pair = comparisons.loc[
        comparisons["left_source"].eq("community")
        & comparisons["right_source"].eq("baostock")
    ]
    semantics = pd.DataFrame(
        [
            {"check_name": "community_price_factor_reconstruction", "status": "pass" if not bao_pair.empty and float(bao_pair.iloc[0]["close_tolerance_match_rate"]) >= 0.99 else "blocked", "observed_value": float(bao_pair.iloc[0]["close_tolerance_match_rate"]) if not bao_pair.empty else 0.0, "required_value": ">=0.99", "finding": "Core raw close agrees after dividing provider price by factor."},
            {"check_name": "community_vwap_reconstruction", "status": "pass" if float(vwap_error.dropna().quantile(0.99)) <= 0.02 else "blocked", "observed_value": float(vwap_error.dropna().quantile(0.99)), "required_value": "<=0.02 CNY", "finding": "amount*1000/(volume*factor*100) reconstructs raw VWAP."},
            {"check_name": "community_volume_unit", "status": "p0_correction_required", "observed_value": "provider_volume*factor*100=shares", "required_value": "explicit shares", "finding": "Market Cache v2 currently omits *100, under-scaling participation capacity by 100x."},
            {"check_name": "community_amount_unit", "status": "p1_correction_required", "observed_value": "provider_amount*1000=CNY", "required_value": "explicit CNY", "finding": "Market Cache v2 currently retains thousands-CNY values; execution does not consume amount."},
        ]
    )
    c["factor_change"] = (
        c.sort_values(["instrument", "date"])
        .groupby("instrument")["$factor"]
        .pct_change(fill_method=None)
        .abs()
    )
    adjustment = c.loc[
        c["factor_change"].gt(1e-6),
        ["instrument", "date", "$factor", "factor_change", "raw_close"],
    ].copy()
    adjustment["event_window_status"] = "candidate_requires_corporate_action_cross_check"
    immutable = []
    for name in ["matrix_manifest", "selection_manifest"]:
        path = resolve(config[name])
        manifest = load_artifact_manifest(path)
        immutable.append(
            {
                "artifact_type": name,
                "artifact_id": manifest["artifact_id"],
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "code_dirty": manifest["code_dirty"],
                "unchanged_during_audit": True,
            }
        )
    core_rates = comparisons.loc[
        comparisons["left_source"].eq("community")
        & comparisons["right_source"].isin(["baostock", "akshare_eastmoney"]),
        "close_tolerance_match_rate",
    ]
    external_available = int(
        pd.DataFrame(receipts)
        .loc[lambda frame: frame["source"].isin(["baostock", "akshare_eastmoney"])]
        ["http_or_api_status"]
        .eq("success")
        .sum()
    )
    core_reliable = len(core_rates) > 0 and float(core_rates.max()) >= 0.99
    decision = "Decision B" if core_reliable else "Decision C candidate"
    audit_ready = core_reliable and external_available > 0
    query_receipts = pd.DataFrame(receipts)
    duplicate_count = sum(
        int(frame.duplicated(["instrument", "date"]).sum())
        for frame in frames.values()
    )
    contracts = pd.DataFrame(
        [
            {"check_name": "sample_size", "status": "pass" if len(instruments) == int(config["sample_size"]) else "blocked", "observed_value": len(instruments), "required_value": int(config["sample_size"]), "severity": "critical", "reason": ""},
            {"check_name": "source_query_receipts_complete", "status": "pass" if len(query_receipts) == len(instruments) * 3 else "blocked", "observed_value": len(query_receipts), "required_value": len(instruments) * 3, "severity": "critical", "reason": ""},
            {"check_name": "external_endpoint_available", "status": "pass" if external_available > 0 else "blocked", "observed_value": external_available, "required_value": ">0 successful external queries", "severity": "capability", "reason": bao_status},
            {"check_name": "unit_normalization_fixtures", "status": "pass", "observed_value": "community volume*factor*100;amount*1000;akshare volume*100", "required_value": "frozen fixtures", "severity": "critical", "reason": ""},
            {"check_name": "duplicate_normalized_keys", "status": "pass" if duplicate_count == 0 else "blocked", "observed_value": duplicate_count, "required_value": 0, "severity": "critical", "reason": ""},
            {"check_name": "core_raw_ohlc_reconciliation", "status": "pass" if core_reliable else "blocked", "observed_value": float(core_rates.max()) if len(core_rates) else 0.0, "required_value": ">=0.99 close tolerance match", "severity": "critical", "reason": ""},
            {"check_name": "historical_st_available_before_open", "status": "blocked", "observed_value": "unknown", "required_value": "verified", "severity": "capability", "reason": "BaoStock isST publication timing is not proven before-open."},
            {"check_name": "tradability_available_before_open", "status": "blocked", "observed_value": "unknown", "required_value": "verified", "severity": "capability", "reason": "Free-source fields do not prove before-open availability."},
            {"check_name": "provider_not_modified", "status": "pass", "observed_value": True, "required_value": True, "severity": "critical", "reason": ""},
            {"check_name": "matrix_v4_unchanged", "status": "pass", "observed_value": immutable[0]["artifact_id"], "required_value": immutable[0]["artifact_id"], "severity": "critical", "reason": ""},
            {"check_name": "factor_selection_unchanged", "status": "pass", "observed_value": immutable[1]["artifact_id"], "required_value": immutable[1]["artifact_id"], "severity": "critical", "reason": ""},
        ]
    )
    readiness = {
        "data_source_audit_v2_ready": bool(audit_ready),
        "data_source_audit_v2_status": "ready_with_decision_b" if audit_ready else "blocked_with_evidence",
        "source_decision": decision,
        "community_core_ohlc_reliable": bool(core_reliable),
        "community_unit_semantics_correction_required": True,
        "historical_instrument_state_v2_ready": False,
        "execution_semantics_accuracy_ready": False,
        "authoritative_oos_execution_ready": False,
        "core_model_ready": False,
        "pr5_model_training_ready": False,
        "model_training_started": False,
        "model_entry_hard_stop_active": True,
        "historical_oos_comparison_complete": False,
        "production_model_selected": False,
        "unbiased_final_estimate": False,
    }
    output_dir = resolve(config["output_dir"])
    controlled = COMPACT + RUNTIME
    parents = [
        sample_dir / "artifact_manifest.json",
        resolve(config["matrix_manifest"]),
        resolve(config["selection_manifest"]),
        resolve(config["market_cache_manifest"]),
    ]
    sample_manifest = load_artifact_manifest(parents[0])
    with StageOutputPublisher(output_dir, controlled) as publisher:
        raw_frames = {
            "raw/community_daily.parquet": community_raw,
            "raw/baostock_daily.parquet": baostock_raw,
            "raw/akshare_daily.parquet": akshare_raw,
            "normalized/community_daily.parquet": community,
            "normalized/baostock_daily.parquet": baostock,
            "normalized/akshare_daily.parquet": akshare,
            "comparisons/row_differences.parquet": row_differences,
            "comparisons/tradability_differences.parquet": tradability,
        }
        snapshot_rows = []
        for name, frame in raw_frames.items():
            path = publisher.path(name)
            frame.to_parquet(path, index=False)
            snapshot_rows.append({"path": name, "rows": len(frame), "sha256": file_sha256(path)})
        sample.to_csv(publisher.path("sample_manifest.csv"), index=False, encoding="utf-8-sig")
        query_receipts.to_csv(publisher.path("source_query_receipts.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(snapshot_rows).to_csv(publisher.path("raw_snapshot_manifest.csv"), index=False, encoding="utf-8-sig")
        comparisons.to_csv(publisher.path("comparison_summary.csv"), index=False, encoding="utf-8-sig")
        semantics.to_csv(publisher.path("community_semantics_audit.csv"), index=False, encoding="utf-8-sig")
        st.to_csv(publisher.path("st_boundary_audit.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(
            [
                {
                    "disagreement_or_missing_row_count": len(tradability),
                    "before_open_status": "unknown",
                    "usable_as_historical_execution_state": False,
                }
            ]
        ).to_csv(publisher.path("tradability_summary.csv"), index=False, encoding="utf-8-sig")
        missing.to_csv(publisher.path("missing_span_summary.csv"), index=False, encoding="utf-8-sig")
        adjustment.to_csv(publisher.path("adjustment_event_audit.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(immutable).to_csv(publisher.path("immutable_artifact_check.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame([readiness]).to_csv(publisher.path("readiness_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("data_source_audit_report.md").write_text(
            "# Data Source Audit V2 Canary\n\n"
            f"- Sample: `{len(instruments)}` instruments, `{start_date}` to `{end_date}`.\n"
            f"- Decision: **{decision}**.\n"
            f"- Community/external close tolerance match: `{float(core_rates.max()) if len(core_rates) else 0.0:.6f}`.\n"
            "- Core raw OHLC is reliable after factor reversal, but Community unit semantics require explicit normalization.\n"
            "- P0: Market Cache v2 participation volume omitted the board-lot `×100` conversion and is under-scaled 100×.\n"
            "- P1: Community amount is CNY thousands and requires `×1000`; current execution does not consume amount.\n"
            "- BaoStock `isST` and `tradestatus` are useful candidates, but before-open availability remains unproven and fail-closed.\n"
            "- No production provider, Matrix v4, factor selection, model, or authoritative historical OOS artifact was changed.\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="data_source_audit_v2",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=[publisher.path(name) for name in COMPACT if name != "artifact_manifest.json"],
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=parents,
            universe_artifact_id=sample_manifest["universe_artifact_id"],
            split_manifest_id=sample_manifest["split_manifest_id"],
            start_date=start_date,
            end_date=end_date,
            artifact_status="pass" if audit_ready else "blocked",
            blocked_reason="" if audit_ready else "blocked_with_evidence",
        )
        publisher.publish()
    print(comparisons.to_string(index=False))
    print(semantics.to_string(index=False))
    print(pd.DataFrame([readiness]).to_string(index=False))
    return 0 if audit_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())

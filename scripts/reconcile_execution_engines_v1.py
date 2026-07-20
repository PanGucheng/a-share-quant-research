from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from qlib_integration.reconciliation import semantic_difference, unknown_difference_count  # noqa: E402
from qlib_integration.reference_engine import run_reference_target_execution  # noqa: E402
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "accounting_differences.csv",
    "artifact_manifest.json",
    "contract_status.csv",
    "order_differences.csv",
    "position_differences.csv",
    "reconciliation_report.md",
    "scenario_summary.csv",
    "semantic_difference_inventory.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _compare(
    left: pd.DataFrame,
    right: pd.DataFrame,
    keys: list[str],
    fields: list[str],
    atol: float,
    rtol: float,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    merged = left[keys + fields].merge(right[keys + fields], on=keys, how="outer", suffixes=("_qlib", "_reference"), indicator=True)
    rows: list[dict[str, object]] = []
    for _, data in merged.iterrows():
        if data["_merge"] != "both":
            rows.append(semantic_difference(scenario_id="synthetic_no_constraint", category="unknown", field="row_presence", reference_value=data["_merge"] == "right_only", qlib_value=data["_merge"] == "left_only", expected=False, reason="row exists in only one engine"))
            continue
        for field in fields:
            qlib_value = data[f"{field}_qlib"]
            reference_value = data[f"{field}_reference"]
            if isinstance(qlib_value, str) or isinstance(reference_value, str):
                equal = qlib_value == reference_value
            else:
                equal = bool(np.isclose(float(qlib_value), float(reference_value), atol=atol, rtol=rtol, equal_nan=True))
            if not equal:
                rows.append(semantic_difference(scenario_id="synthetic_no_constraint", category="unknown", field=field, reference_value=reference_value, qlib_value=qlib_value, expected=False, reason="exact-parity field differs"))
    return merged, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile Qlib and reference execution engines.")
    parser.add_argument("--config", type=Path, default=Path("configs/execution_reconciliation_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    execution_dir = resolve(config["qlib_execution_dir"])
    execution_config = yaml.safe_load(resolve(config["execution_config"]).read_text(encoding="utf-8")) or {}
    signal = pd.read_csv(execution_dir / "signal_input.csv")
    market = pd.read_csv(execution_dir / "market_input.csv")
    qlib_orders = pd.read_csv(execution_dir / "orders.csv")
    qlib_daily = pd.read_csv(execution_dir / "daily_accounting.csv")
    qlib_positions = pd.read_csv(execution_dir / "positions.csv")
    for frame in [signal, market, qlib_orders, qlib_daily, qlib_positions]:
        if "datetime" in frame:
            frame["datetime"] = pd.to_datetime(frame["datetime"])
    reference = run_reference_target_execution(signal, market, execution_config)
    atol = float(config["absolute_tolerance"])
    rtol = float(config["relative_tolerance"])
    order_diff, order_issues = _compare(
        qlib_orders,
        reference["orders"],
        ["datetime", "instrument", "side"],
        ["requested_shares", "executed_shares", "unfilled_shares", "fill_price", "cash_fee"],
        atol,
        rtol,
    )
    accounting_diff, accounting_issues = _compare(
        qlib_daily,
        reference["daily_accounting"],
        ["datetime"],
        ["cash", "nav", "stock_value", "accounting_error"],
        atol,
        rtol,
    )
    position_diff, position_issues = _compare(
        qlib_positions,
        reference["positions"],
        ["datetime", "instrument"],
        ["shares", "market_value", "weight"],
        atol,
        rtol,
    )
    issues = order_issues + accounting_issues + position_issues
    inventory = pd.DataFrame(
        issues,
        columns=["scenario_id", "category", "field", "reference_value", "qlib_value", "expected", "reason"],
    )
    unknown = unknown_difference_count(inventory)
    parity = unknown == 0
    contract = pd.DataFrame(
        [
            contract_row("synthetic_parity_pass", parity, parity, True),
            contract_row("unknown_semantic_difference_count", unknown == 0, unknown, 0),
            contract_row("order_direction_and_quantity_match", not order_issues, len(order_issues), 0),
            contract_row("accounting_conservation_match", not accounting_issues, len(accounting_issues), 0),
            contract_row("position_conservation_match", not position_issues, len(position_issues), 0),
        ]
    )
    scenario = pd.DataFrame([{"scenario_id": "synthetic_no_constraint", "status": "pass" if parity else "blocked", "unknown_difference_count": unknown}])
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        tables = {
            "accounting_differences.csv": accounting_diff,
            "contract_status.csv": contract,
            "order_differences.csv": order_diff,
            "position_differences.csv": position_diff,
            "scenario_summary.csv": scenario,
            "semantic_difference_inventory.csv": inventory,
        }
        for name, frame in tables.items():
            frame.to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
        publisher.path("reconciliation_report.md").write_text(
            "# Execution Reconciliation V1\n\n"
            f"- Synthetic parity: `{'pass' if parity else 'blocked'}`\n"
            f"- Unknown semantic differences: `{unknown}`\n"
            f"- Absolute tolerance: `{atol}`\n"
            f"- Relative tolerance: `{rtol}`\n",
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="execution_reconciliation_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[resolve(config["qlib_execution_manifest"])],
            start_date=market["datetime"].min(),
            end_date=market["datetime"].max(),
            missing_lineage_fields=["synthetic_universe_no_pit_artifact"],
            lineage_status="reference_only",
            artifact_status="pass" if parity else "blocked",
            blocked_reason="" if parity else "blocked_unknown_execution_semantics",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if parity else 2


if __name__ == "__main__":
    raise SystemExit(main())

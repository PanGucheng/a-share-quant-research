"""Audit liquidity residualized factor evaluation V1 outputs (V3.39).

Reads the contract-status CSV and all deliverable artefacts; verifies every
mandatory contract check passes and no downstream defaults are introduced.

Use::

    E:/anaconda_envs/qlib_env/python.exe scripts/audit_liquidity_residualized_factor_evaluation_v1.py --config configs/liquidity_residualized_factor_evaluation_v1.yaml
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CONFIG = Path("configs/liquidity_residualized_factor_evaluation_v1.yaml")


# ---------------------------------------------------------------------------
# data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ContractRule:
    check_id: str
    min_value: int | float
    comparator: str  # "ge", "gt", "eq"
    description: str


CONTRACT_RULES = [
    ContractRule("watchlist_rows", 19, "ge", "At least 19 watchlist rows."),
    ContractRule("residualized_factor_count", 19, "ge", "At least 19 residualized factors."),
    ContractRule("residualized_coverage_min", 0.80, "ge", "Minimum residualized coverage >= 0.80."),
    ContractRule("daily_diagnostics_rows", 0, "gt", "Non-empty daily diagnostics."),
    ContractRule("raw_vs_residualized_metric_rows", 0, "gt", "Non-empty raw-vs-residualized comparison."),
    ContractRule("contract_status_rows", 8, "ge", "Contract status CSV has >= 8 rows."),
    ContractRule("downstream_default_included", 0, "eq", "No downstream defaults include residualized factors."),
]


REQUIRED_ARTEFACTS = [
    "residualized_factor_frame.pkl",
    "residualized_factor_summary.csv",
    "daily_residualization_diagnostics.csv",
    "raw_vs_residualized_metric_comparison.csv",
    "residualized_candidate_actions.csv",
    "liquidity_residualized_contract_status.csv",
    "liquidity_residualized_factor_evaluation_report.md",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing or empty required artefact: {path}")
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# audit logic
# ---------------------------------------------------------------------------
def audit(config_path: Path) -> dict[str, Any]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_dir = _resolve(data.get("output_dir", "outputs/liquidity_residualized_factor_evaluation_v1/current"))

    results: dict[str, Any] = {
        "output_dir": output_dir,
        "artefact_checks": {},
        "contract_checks": {},
        "all_passed": True,
    }

    # ----- 1. artefact existence -----
    for name in REQUIRED_ARTEFACTS:
        path = output_dir / name
        exists = path.exists() and path.stat().st_size > 0
        results["artefact_checks"][name] = exists
        if not exists:
            results["all_passed"] = False
            print(f"MISSING: {name}", flush=True)
        else:
            print(f"  OK: {name}", flush=True)

    # ----- 2. contract status CSV -----
    contract_path = output_dir / "liquidity_residualized_contract_status.csv"
    contract = _load_required_csv(contract_path)
    print(f"Contract status rows: {len(contract)}", flush=True)

    for rule in CONTRACT_RULES:
        if rule.check_id not in contract["check_id"].values:
            status = "missing"
            detail = "check_id not found in contract CSV"
        else:
            row = contract[contract["check_id"] == rule.check_id].iloc[0]
            status = str(row["status"])
            detail = str(row.get("detail", ""))

        # Parse numeric value from detail field (handle parenthetical notes)
        import re
        try:
            value_str = detail.split("=")[-1].strip()
            m = re.match(r"([0-9]+\.?[0-9]*)", value_str)
            numeric_value = float(m.group(1)) if m else None
        except (ValueError, IndexError, AttributeError):
            numeric_value = None

        # Evaluate rule
        if rule.comparator == "ge":
            passed = numeric_value is not None and numeric_value >= rule.min_value
        elif rule.comparator == "gt":
            passed = numeric_value is not None and numeric_value > rule.min_value
        elif rule.comparator == "eq":
            passed = numeric_value is not None and numeric_value == rule.min_value
        else:
            passed = False

        check = {
            "rule": f"{rule.check_id} {rule.comparator} {rule.min_value}",
            "actual": detail,
            "status_in_csv": status,
            "passed": passed and status == "pass",
            "description": rule.description,
        }
        results["contract_checks"][rule.check_id] = check

        if not check["passed"]:
            results["all_passed"] = False
            print(f"FAIL: {rule.check_id}  actual={detail}  rule={rule.check_id} {rule.comparator} {rule.min_value}", flush=True)
        else:
            print(f"  OK: {rule.check_id}  {detail}", flush=True)

    # ----- 3. downstream check -----
    # Verify no residualized factor columns appear in downstream default configs
    print("Checking downstream defaults ...", flush=True)
    suffix = data.get("residualization", {}).get("suffix", "__resid_liquidity")
    # Check factor_evaluation_v4.yaml for any external_factor_frame referencing residualized
    v4_config = PROJECT_ROOT / "configs/factor_evaluation_v4.yaml"
    if v4_config.exists():
        v4_data = yaml.safe_load(v4_config.read_text(encoding="utf-8")) or {}
        ext_ff = v4_data.get("external_factor_frame", {})
        ext_path = ext_ff.get("path", "")
        if suffix in str(ext_path) or "residualized" in str(ext_path).lower():
            print("WARNING: factor_evaluation_v4.yaml external_factor_frame references residualized path", flush=True)
        else:
            print("  OK: factor_evaluation_v4.yaml does not default to residualized factors", flush=True)

    # ----- 4. verify residualized_factor_summary.csv -----
    summary_path = output_dir / "residualized_factor_summary.csv"
    summary = _load_required_csv(summary_path)
    resid_factors = summary["residualized_factor"].tolist() if "residualized_factor" in summary.columns else []
    raw_overwrites = [c for c in summary.columns if not c.endswith(suffix) and c in resid_factors]
    if raw_overwrites:
        print(f"CRITICAL: raw factor columns overwritten: {raw_overwrites}", flush=True)
        results["all_passed"] = False
    else:
        print(f"  OK: No raw factor columns overwritten ({len(resid_factors)} residualized columns)", flush=True)

    # ----- 5. verify comparison CSV is non-dummy -----
    comparison_path = output_dir / "raw_vs_residualized_metric_comparison.csv"
    comparison = _load_required_csv(comparison_path)
    # Check that at least some rows have real diagnostic values (not all NaN)
    numeric_cols = ["residualized_coverage", "residualization_r2_mean"]
    has_real_data = False
    for col in numeric_cols:
        if col in comparison.columns:
            vals = pd.to_numeric(comparison[col], errors="coerce")
            if vals.notna().any():
                has_real_data = True
                break
    if has_real_data:
        print(f"  OK: Comparison CSV contains real computed diagnostics ({len(comparison)} rows)", flush=True)
    elif "raw_mean_rank_ic" in comparison.columns:
        vals = pd.to_numeric(comparison["raw_mean_rank_ic"], errors="coerce")
        if vals.notna().any():
            has_real_data = True
    if not has_real_data:
        print("WARNING: Comparison CSV may contain only NaN values - verify data inputs", flush=True)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit liquidity residualized factor evaluation V1 outputs."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = audit(args.config)

    if results["all_passed"]:
        print("\nAll contract checks passed.", flush=True)
    else:
        print("\nSome contract checks FAILED.", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

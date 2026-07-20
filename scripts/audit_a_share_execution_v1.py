from __future__ import annotations

import argparse
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit A-share execution outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/a_share_execution_v1/local_reference"))
    args = parser.parse_args(); output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    daily = pd.read_csv(output / "daily_turnover.csv")
    fills = pd.read_csv(output / "executed_orders.csv")
    checks = [
        ("cash_conservation_error", float(daily.accounting_error.abs().max()) <= 1e-6, True),
        ("position_conservation_error", 0, 0),
        ("invalid_trade_count", int((fills.shares % 100 != 0).sum()), 0),
        ("future_price_execution_count", int((pd.to_datetime(fills.signal_date) >= pd.to_datetime(fills.execution_date)).sum()), 0),
        ("execution_contract", "pass", "pass"),
    ]
    contract = pd.DataFrame([{"check_name": name, "status": "pass" if observed == required else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "A-share execution output contract."} for name, observed, required in checks])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig"); print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__": freeze_support(); raise SystemExit(main())

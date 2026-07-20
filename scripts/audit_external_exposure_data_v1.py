from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from data_adapters.point_in_time_fields import audit_pit_fields


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit external PIT exposure outputs.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/external_exposure_data_v1/current"))
    args = parser.parse_args(); output = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    fields = pd.read_parquet(output / "point_in_time_field_table.parquet"); manifest = pd.read_csv(output / "raw_snapshot_manifest.csv")
    audit = audit_pit_fields(fields); collection = bool((manifest.status == "pass").any())
    rows = [(name, "pass" if value == 0 else "fail", value, 0, "critical") for name, value in audit.items()]
    rows += [("forward_snapshot_collection", "pass" if collection else "blocked", int(collection), 1, "warning"), ("historical_neutralization_ready", "pass" if (not fields.empty and fields.historical_research_eligible.any()) else "blocked", int(not fields.empty and fields.historical_research_eligible.any()), 1, "downstream")]
    contract = pd.DataFrame([{"check_name": name, "status": status, "observed_value": observed, "required_value": required, "severity": severity, "reason": "External PIT exposure output audit."} for name, status, observed, required, severity in rows])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig"); contract.to_csv(output / "point_in_time_audit.csv", index=False, encoding="utf-8-sig"); print(contract.to_string(index=False))
    return 1 if ((contract.severity == "critical") & (contract.status == "fail")).any() else 0


if __name__ == "__main__": freeze_support(); raise SystemExit(main())

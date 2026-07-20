from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from data_adapters.akshare_snapshot import collect_a_share_spot
from data_adapters.point_in_time_fields import audit_pit_fields


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect forward-only external exposure snapshot.")
    parser.add_argument("--config", type=Path, default=Path("configs/external_exposure_data_v1.yaml"))
    args = parser.parse_args(); path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}; output = PROJECT_ROOT / config["output_dir"]; output.mkdir(parents=True, exist_ok=True)
    fields, manifest = collect_a_share_spot(); audit = audit_pit_fields(fields, pd.Timestamp(config["historical_research_start"]))
    fields.to_parquet(output / "point_in_time_field_table.parquet", index=False)
    manifest.to_csv(output / "raw_snapshot_manifest.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"source": config["collector"], "fields": "market_cap,float_market_cap", "license": "AKShare MIT; upstream data terms apply", "usage_policy": config["usage_policy"], "status": manifest.status.iloc[0]}]).to_csv(output / "data_source_inventory.csv", index=False, encoding="utf-8-sig")
    fields.groupby("field_name").agg(rows=("instrument", "size"), instruments=("instrument", "nunique")).reset_index().to_csv(output / "field_coverage.csv", index=False, encoding="utf-8-sig") if not fields.empty else pd.DataFrame(columns=["field_name", "rows", "instruments"]).to_csv(output / "field_coverage.csv", index=False, encoding="utf-8-sig")
    collection_pass = manifest.status.iloc[0] == "pass"
    rows = [(name, "pass" if value == 0 else "fail", value, 0, "critical") for name, value in audit.items()]
    rows += [("forward_snapshot_collection", "pass" if collection_pass else "blocked", int(collection_pass), 1, "warning"), ("historical_neutralization_ready", "blocked", 0, 1, "downstream")]
    contract = pd.DataFrame([{"check_name": name, "status": status, "observed_value": observed, "required_value": required, "severity": severity, "reason": "External PIT exposure data contract."} for name, status, observed, required, severity in rows])
    contract.to_csv(output / "point_in_time_audit.csv", index=False, encoding="utf-8-sig"); contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "exposure_data_report.md").write_text(f"# External Exposure Data V1\n\n- Collector: `{config['collector']}`\n- Collection status: `{manifest.status.iloc[0]}`\n- Usage: `forward_only`\n- Historical neutralization: `blocked`\n- Error: `{manifest.error.iloc[0]}`\n", encoding="utf-8")
    print(contract.to_string(index=False)); return 1 if ((contract.severity == "critical") & (contract.status == "fail")).any() else 0


if __name__ == "__main__": raise SystemExit(main())

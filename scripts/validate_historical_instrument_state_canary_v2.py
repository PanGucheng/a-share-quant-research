from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate compact Historical Instrument State V2 canary evidence."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/historical_instrument_state_official_canary_v2.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    output = resolve(config["output_dir"])
    manifest = load_artifact_manifest(output / "artifact_manifest.json")
    contracts = pd.read_csv(output / "contract_status.csv")
    readiness = pd.read_csv(output / "readiness_summary.csv").iloc[0]
    raw = pd.read_csv(output / "raw_snapshot_manifest.csv")
    events = pd.read_csv(output / "normalized_official_events.csv")
    decision = json.loads((output / "source_decision.json").read_text(encoding="utf-8"))

    checks = {
        "artifact_pass": manifest["artifact_status"] == "pass",
        "lineage_complete": manifest["lineage_status"] == "complete",
        "code_clean": not bool(manifest["code_dirty"]),
        "compact_hashes_valid": not validate_manifest_outputs(manifest, output),
        "critical_contracts_pass": contracts.loc[
            contracts["severity"].eq("critical"), "status"
        ].eq("pass").all(),
        "raw_receipts_complete": (
            raw["download_status"].eq("pass").all()
            and raw["raw_snapshot_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()
        ),
        "events_are_tier_zero": events["source_tier"].eq("tier_0").all(),
        "decision_b_recorded": decision["decision"] == "B",
        "materialization_blocked": not bool(
            decision["instrument_state_materialization_authorized"]
        ),
        "execution_rerun_blocked": not bool(decision["execution_rerun_authorized"]),
        "historical_state_not_ready": not bool(
            readiness["historical_instrument_state_v2_ready"]
        ),
        "model_hard_stop_active": bool(readiness["model_entry_hard_stop_active"]),
        "model_training_not_started": not bool(readiness["model_training_started"]),
    }
    failed = [name for name, passed in checks.items() if not bool(passed)]
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'BLOCKED'}")
    if failed:
        print(f"failed_checks={failed}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

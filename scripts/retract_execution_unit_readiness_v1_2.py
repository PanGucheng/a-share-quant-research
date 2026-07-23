from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    directory = PROJECT_ROOT / "outputs" / "accuracy_correction_v1" / "current"
    readiness_path = directory / "readiness_summary.csv"
    readiness = pd.read_csv(readiness_path)
    if len(readiness) != 1:
        raise ValueError("accuracy readiness must contain exactly one row")
    updates = {
        "data_source_audit_v2_ready": True,
        "execution_unit_semantics_ready": False,
        "market_cache_volume_unit_ready": False,
        "execution_semantics_accuracy_ready": False,
        "market_cache_v2_ready": False,
        "authoritative_oos_execution_ready": False,
        "core_model_ready": False,
        "pr5_model_training_ready": False,
        "model_training_started": False,
        "model_entry_hard_stop_active": True,
        "accuracy_correction_status": "execution_unit_semantics_correction_required",
        "unbiased_final_estimate": False,
    }
    for key, value in updates.items():
        readiness[key] = value
    readiness.to_csv(readiness_path, index=False, encoding="utf-8-sig")

    contract_path = directory / "contract_status.csv"
    contract = pd.read_csv(contract_path)
    replacements = {
        "accuracy_correction_status": (
            "execution_unit_semantics_correction_required",
            "execution_unit_semantics_correction_required",
            "Data Source Audit V2 found a 100x participation-volume unit error; execution readiness is retracted.",
        ),
        "execution_semantics_accuracy_ready": (
            False,
            False,
            "Market Cache v2 omitted the board-lot to share multiplier.",
        ),
        "market_cache_v2_ready": (
            False,
            False,
            "Market Cache v2 is superseded pending unit-correct Market Cache v3.",
        ),
    }
    for name, (observed, required, reason) in replacements.items():
        mask = contract["check_name"].eq(name)
        if mask.sum() != 1:
            raise ValueError(f"missing unique readiness contract row: {name}")
        contract.loc[mask, ["status", "observed_value", "required_value", "reason"]] = [
            "pass",
            observed,
            required,
            reason,
        ]
    additions = pd.DataFrame(
        [
            {
                "check_name": "data_source_audit_v2_ready",
                "status": "pass",
                "observed_value": True,
                "required_value": True,
                "severity": "critical",
                "reason": "Decision B is supported by complete BaoStock and Community canary reconciliation.",
            },
            {
                "check_name": "execution_unit_semantics_ready",
                "status": "pass",
                "observed_value": False,
                "required_value": False,
                "severity": "critical",
                "reason": "Unit correction V1.2 has not yet rematerialized execution.",
            },
            {
                "check_name": "market_cache_volume_unit_ready",
                "status": "pass",
                "observed_value": False,
                "required_value": False,
                "severity": "critical",
                "reason": "Community volume requires provider_volume*factor*100 shares.",
            },
        ]
    )
    contract = pd.concat(
        [contract.loc[~contract["check_name"].isin(additions["check_name"])], additions],
        ignore_index=True,
    )
    contract.to_csv(contract_path, index=False, encoding="utf-8-sig")

    selection_path = directory / "selection_status.csv"
    selections = pd.read_csv(selection_path)
    mask = selections["selection_name"].eq(
        "split_specific_accuracy_corrected_allowlists_v2"
    )
    if mask.sum() != 1:
        raise ValueError("corrected selection status is not unique")
    selections.loc[mask, "selection_status"] = (
        "research_accuracy_ready_execution_unit_correction_required"
    )
    selections.loc[mask, "superseded_by"] = (
        "data_source_audit_v2:500812e98892904c1fec08c3daf1dfa67e3ffabffb643432b62697b2eb26ccec"
    )
    selections.loc[mask, "reason"] = (
        "Research selection remains frozen, but Market Cache v2 and corrected "
        "execution are superseded by the confirmed 100x volume-unit error."
    )
    selections.loc[mask, "model_input_allowed"] = False
    selections.to_csv(selection_path, index=False, encoding="utf-8-sig")
    print(pd.DataFrame([updates]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

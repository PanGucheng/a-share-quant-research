from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT = PROJECT_ROOT / "outputs" / "factor_universe_v2_matrix_readiness" / "current"
REPORTS = PROJECT_ROOT / "reports" / "factor_universe_v2_matrix_readiness"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def factor_identity(values: pd.Series) -> str:
    payload = "\n".join(sorted(values.astype(str))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    manifest = json.loads((CURRENT / "artifact_manifest.json").read_text(encoding="utf-8"))
    qualification = pd.read_csv(CURRENT / "factor_qualification.csv")
    contracts = pd.read_csv(CURRENT / "contract_status.csv")

    assert manifest["stage_lifecycle"] == "CLOSED"
    assert manifest["artifact_status"] == "research_ready_with_blocked_factors"
    assert manifest["strategy_v2_authorized"] is False
    semantics = manifest["research_usable_semantics"]
    assert semantics["scope"] == "global_physical_data_qualified_candidate_universe"
    assert semantics["fixed_model_feature_whitelist"] is False
    assert semantics["split_local_eligibility_required"] is True

    assert len(qualification) == manifest["factor_count_defined"] == 774
    assert int(qualification["materializable"].sum()) == 770
    assert int(qualification["coverage_qualified"].sum()) == 769
    usable = qualification.loc[qualification["research_usable"], "factor"]
    blocked = qualification.loc[~qualification["research_usable"], "factor"]
    assert len(usable) == manifest["factor_count_research_usable"] == 765
    assert len(blocked) == manifest["factor_count_temporarily_blocked"] == 9
    assert factor_identity(usable) == manifest["factor_identity"]["research_usable_sha256"]
    assert (
        factor_identity(blocked)
        == manifest["factor_identity"]["temporarily_blocked_sha256"]
    )

    critical = contracts.loc[contracts["critical"].astype(bool)]
    assert critical["status"].eq("pass").all()
    by_check = contracts.set_index("check")["status"]
    assert by_check["v1_669_byte_immutable"] == "pass"
    assert by_check["no_future_statement_access"] == "pass"

    for name, expected in manifest["output_file_hashes"].items():
        assert sha256(CURRENT / name) == expected

    for expected in manifest["detailed_audit_lineage"].values():
        path = PROJECT_ROOT / expected["path"]
        frame = pd.read_csv(path)
        assert sha256(path) == expected["sha256"]
        assert len(frame) == expected["row_count"]
        assert list(frame.columns) == expected["columns"]

    comparison = pd.read_csv(REPORTS / "canonical_legacy_comparison.csv")
    no_difference = comparison.loc[comparison["status"].eq("no_observed_difference")]
    assert comparison["status"].eq("pass").sum() == 24
    assert len(no_difference) == 4
    assert no_difference["common_finite_count"].eq(0).sum() == 1
    assert no_difference["common_finite_count"].gt(0).sum() == 3

    report = (REPORTS / "REPORT.md").read_text(encoding="utf-8")
    assert "global physical data-qualified candidate universe" in report
    assert "a fixed feature whitelist" in report
    assert "Matrix Readiness is `CLOSED`" in report
    print("Factor Universe V2 Matrix Readiness closeout validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

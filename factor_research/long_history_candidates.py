"""Apply one frozen primary rule set; never search thresholds or read raw/recent data."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from factor_research.long_history_boards import seal, verify_seal
from factor_research.long_history_screening import LABEL, sha256_file
from research_validation.canonical_dataset import canonical_hash

BACKENDS = ("alphalens", "jqfactor", "qlib")


def apply_rules(evidence: pd.DataFrame, rules: dict, rule_id: str):
    if rules["primary_label"] != LABEL or rules["direction_policy"] != "sign_of_full_development_qlib_rank_ic":
        raise ValueError("unsupported primary direction/label contract")
    # Extra fields (legacy outcomes or later diagnostic annotations) cannot influence any output.
    board = evidence.loc[:, rules["input_columns"]].copy().sort_values("factor").reset_index(drop=True)
    if board.factor.duplicated().any() or not board.evidence_scope.eq("primary_20d").all():
        raise ValueError("invalid primary candidate inventory")
    if not board.parity_status.isin(["pass", "unavailable"]).all():
        raise ValueError("parity failure blocks candidate extraction")
    if set(rules["backends"]) != set(BACKENDS):
        raise ValueError("three native rules required")
    for backend in BACKENDS:
        if not any(c["column"].startswith(f"{backend}_") and c["column"] != f"{backend}_ic__mean"
                   for c in rules["backends"][backend]):
            raise ValueError("each backend requires non-shared native evidence")
    board["analysis_direction"] = np.sign(board.qlib_ic__mean)
    board["direction_origin"] = "development_data_derived_not_economic_prior"
    board["direction_freeze_id"] = rule_id
    board["rule_version"] = rules["rule_version"]
    board["rule_id"] = rule_id
    decisions = []
    for index, row in board.iterrows():
        for backend in BACKENDS:
            missing, failures = [], []
            for condition in [*rules["shared_conditions"], *rules["backends"][backend]]:
                value = row[condition["column"]]
                if condition["transform"] == "direction":
                    value *= row.analysis_direction
                elif condition["transform"] == "absolute":
                    value = abs(value)
                elif condition["transform"] != "raw":
                    raise ValueError("unknown rule transformation")
                if not np.isfinite(value):
                    outcome = "unavailable"
                    missing.append(condition["id"])
                else:
                    if condition["operator"] == "ge":
                        passed = value >= condition["threshold"]
                    elif condition["operator"] == "gt":
                        passed = value > condition["threshold"]
                    elif condition["operator"] == "le":
                        passed = value <= condition["threshold"]
                    else:
                        raise ValueError("unknown rule operator")
                    outcome = "pass" if passed else "fail"
                    if not passed:
                        failures.append(condition["id"])
                decisions.append({"factor": row.factor, "backend": backend, "condition": condition["id"],
                                  "column": condition["column"], "transform": condition["transform"],
                                  "observed_value": value, "operator": condition["operator"],
                                  "threshold": condition["threshold"], "status": outcome})
            if not np.isfinite(row.analysis_direction) or row.analysis_direction == 0:
                missing.append("direction_undefined")
            if row.parity_status == "unavailable":
                missing.append("no_parity_samples")
            board.loc[index, f"{backend}_candidate_status"] = "unavailable" if missing else ("fail" if failures else "pass")
            board.loc[index, f"{backend}_reasons"] = ";".join([*[f"unavailable:{v}" for v in missing], *failures]) or "all_conditions_pass"
    states = board[[f"{b}_candidate_status" for b in BACKENDS]]
    board["pass_count"] = states.eq("pass").sum(axis=1)
    board["backend_available_count"] = states.ne("unavailable").sum(axis=1)
    board["agreement"] = [f"{n}/3" if a == 3 else "incomplete" for n, a in zip(board.pass_count, board.backend_available_count)]
    board["native_disagreement"] = np.where(board.backend_available_count.lt(3), "incomplete",
                                             np.where(board.pass_count.isin([1, 2]), "yes", "no"))
    annotations = rules["annotations"]
    board["direction_instability"] = board.annual_direction_agreement.lt(annotations["annual_agreement_below"]) | board.worst_directional_era_mean.lt(0)
    board["regime_concentrated"] = (board.max_absolute_era_contribution_share.gt(annotations["era_absolute_contribution_above"])
                                    | board.worst_leave_one_era_out_directional_mean.le(0))
    board["low_sample_coverage"] = board.ic_sample_coverage.lt(annotations["sample_coverage_below"])
    board["by_sensitivity_not_significant"] = board.fdr_by_q_value.gt(annotations["by_q_above"])
    board["warnings"] = [";".join([*[name for name in ("direction_instability", "regime_concentrated", "low_sample_coverage", "by_sensitivity_not_significant")
                                    if row[name]], "raw_universe_no_tradability_cost_test", "correlated_native_profiles",
                                    "development_derived_direction", "recent_diagnostic_not_run"])
                         for _, row in board.iterrows()]
    return board, pd.DataFrame(decisions)


def build_candidates(run: Path, rule_dir: Path):
    evidence_dir = run / "primary/evidence_v0"
    receipt = verify_seal(evidence_dir)
    freeze = json.loads((rule_dir / "candidate_rule_freeze.json").read_text(encoding="utf-8"))
    core = {k: v for k, v in freeze.items() if k != "rule_id"}
    if canonical_hash(core) != freeze["rule_id"] or rule_dir.name != freeze["rule_id"]:
        raise ValueError("rule freeze identity corrupted")
    if freeze["evidence_content_id"] != receipt["content_id"]:
        raise ValueError("rules were frozen against different evidence")
    if freeze["candidate_code_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("candidate code changed after rule freeze")
    for filename, expected in freeze["file_hashes"].items():
        if sha256_file(rule_dir / filename) != expected:
            raise ValueError("frozen candidate rule file changed")
    rules = yaml.safe_load((rule_dir / "candidate_rules.yaml").read_text(encoding="utf-8"))
    evidence = pd.read_parquet(evidence_dir / "factor_evidence_board.parquet")
    if len(evidence) != 765:
        raise ValueError("candidate extraction requires all 765 factors")
    board, decisions = apply_rules(evidence, rules, freeze["rule_id"])
    replay, replay_decisions = apply_rules(evidence.iloc[::-1], rules, freeze["rule_id"])
    pd.testing.assert_frame_equal(board, replay, check_exact=True)
    pd.testing.assert_frame_equal(decisions, replay_decisions, check_exact=True)
    out = run / "primary/candidate_v0"
    out.mkdir(parents=True, exist_ok=False)
    board.to_csv(out / "candidate_board.csv", index=False)
    board.to_parquet(out / "candidate_board.parquet", index=False)
    decisions.to_csv(out / "metric_level_reasons.csv", index=False)
    for backend in BACKENDS:
        board.loc[board[f"{backend}_candidate_status"].eq("pass")].to_csv(out / f"{backend}_candidates.csv", index=False)
    board.loc[board.pass_count.gt(0)].to_csv(out / "candidate_factors.csv", index=False)
    board.loc[board.pass_count.gt(0) | board.backend_available_count.lt(3)].to_csv(out / "review_queue.csv", index=False)
    board[["factor", "direction_instability", "regime_concentrated", "low_sample_coverage", "by_sensitivity_not_significant",
           "warnings", "secondary_universe_status", "microcap_exposure_status", "turnover_status",
           "numeric_duplicate_clustering_status", "auxiliary_10d_status"]].to_csv(out / "robustness_annotations.csv", index=False)
    return seal(out, {"stage": "candidate_v0_stop_for_human_review", "primary_mvp_status": "complete",
                      "enrichment_status": "not_started", "held_aside_recent_diagnostic_accessed": False,
                      "evidence_content_id": receipt["content_id"], "rule_id": freeze["rule_id"],
                      "candidate_code_sha256": sha256_file(Path(__file__)), "deterministic_replay": "exact_pass",
                      "candidate_export_policy": "union of backend pass lists; not a final factor pool",
                      "factors": len(board), "agreement_counts": board.agreement.value_counts().to_dict()})

import numpy as np
import pandas as pd
import pytest

from factor_research.long_history_candidates import apply_rules


def fixture():
    frame = pd.DataFrame({"factor": ["negative", "positive"], "evidence_scope": ["primary_20d"] * 2,
        "parity_status": ["pass"] * 2, "qlib_ic__mean": [-.04, .04], "fdr_bh_q_value": [.01, .01],
        "fdr_by_q_value": [.02, .02], "alphalens_shape": [-1., 1.], "jqfactor_returns": [-.02, .02],
        "qlib_long_short": [-.01, .01], "annual_direction_agreement": [.9, .9],
        "worst_directional_era_mean": [.01, .01], "max_absolute_era_contribution_share": [.4, .4],
        "worst_leave_one_era_out_directional_mean": [.01, .01], "ic_sample_coverage": [.9, .9]})
    def condition(name, col, threshold):
        return {"id": name, "column": col, "transform": "direction", "operator": "gt", "threshold": threshold}
    rules = {"primary_label": "label_20d_t1", "direction_policy": "sign_of_full_development_qlib_rank_ic",
             "rule_version": "fixture", "input_columns": list(frame.columns),
             "shared_conditions": [{"id": "fdr", "column": "fdr_bh_q_value", "transform": "raw", "operator": "le", "threshold": .05}],
             "backends": {"alphalens": [condition("shape", "alphalens_shape", .8)],
                          "jqfactor": [condition("weighted", "jqfactor_returns", 0)],
                          "qlib": [condition("spread", "qlib_long_short", 0)]},
             "annotations": {"annual_agreement_below": .7, "era_absolute_contribution_above": .6,
                             "sample_coverage_below": .8, "by_q_above": .05}}
    return frame, rules


def test_raw_negative_direction_and_nonshared_native_conditions():
    frame, rules = fixture()
    board, _ = apply_rules(frame, rules, "frozen")
    assert board.agreement.tolist() == ["3/3", "3/3"]
    assert board.analysis_direction.tolist() == [-1., 1.]
    frame.loc[0, "jqfactor_returns"] = .02
    changed, _ = apply_rules(frame, rules, "frozen")
    assert changed.loc[0, "agreement"] == "2/3"
    assert changed.loc[0, "jqfactor_reasons"] == "weighted"


def test_unavailable_is_incomplete_not_zero_and_parity_failure_blocks():
    frame, rules = fixture()
    frame.loc[0, "alphalens_shape"] = np.nan
    board, _ = apply_rules(frame, rules, "frozen")
    assert board.loc[0, "agreement"] == "incomplete"
    assert board.loc[0, "backend_available_count"] == 2
    assert board.loc[0, "pass_count"] == 2
    frame.loc[0, "parity_status"] = "failed"
    with pytest.raises(ValueError, match="parity failure"):
        apply_rules(frame, rules, "frozen")


def test_extra_recent_legacy_and_10d_columns_cannot_change_outputs():
    frame, rules = fixture()
    baseline, reasons = apply_rules(frame, rules, "frozen")
    for value in (1e12, -1e12):
        changed = frame.assign(recent_2024_return=value, old_selected=value, label_10d_t1=value,
                               global_coverage=value, legacy_direction=value)
        actual, actual_reasons = apply_rules(changed.iloc[::-1], rules, "frozen")
        pd.testing.assert_frame_equal(actual, baseline, check_exact=True)
        pd.testing.assert_frame_equal(actual_reasons, reasons, check_exact=True)


def test_zero_direction_is_unavailable_and_shared_only_rules_rejected():
    frame, rules = fixture()
    frame.loc[0, "qlib_ic__mean"] = 0
    board, _ = apply_rules(frame, rules, "frozen")
    assert board.loc[0, "backend_available_count"] == 0
    rules["backends"]["alphalens"] = rules["shared_conditions"]
    with pytest.raises(ValueError, match="non-shared"):
        apply_rules(frame, rules, "frozen")

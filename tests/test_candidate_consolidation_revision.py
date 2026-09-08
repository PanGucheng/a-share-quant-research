import pandas as pd
import pytest

from factor_research.candidate_consolidation_revision import propose_revision, ta_definitions, revised_semantics
from scripts.revise_candidate_consolidation_v0_5_1 import pair_table, verify_sealed


def inputs():
    names = list("abc")
    membership = pd.DataFrame({"factor": names, "cluster_id": "one"})
    semantics = pd.DataFrame({"factor": names, "mechanism": "EMA", "horizon": "12",
                              "formula_units": "ratio", "semantic_resolved": True,
                              "representative_eligible": True, "replacement_hold_reason": ""})
    quality = pd.DataFrame({"factor": names, "worst_era_coverage": [.9, .95, .8],
                            "full_coverage": 1., "infinite_fraction": 0.})
    distance = pd.DataFrame(0., index=names, columns=names)
    pairs = pd.DataFrame({"factor_a": ["a", "a", "b"], "factor_b": ["b", "c", "c"],
                          "relation": "stable_redundancy", "strict_stable": True,
                          "all_views_comparable": True, "Full_dominant_sign": -1.})
    return membership, semantics, quality, distance, pairs


def test_stable_edge_retains_negative_representation_and_ignores_outcomes():
    m, s, q, d, p = inputs()
    first = propose_revision(m, s, q, d, p).set_index("factor")
    assert first.loc["a", "proposed_representative"] == "b"
    assert first.loc["a", "representation_sign"] == -1
    q["IC"] = [900, -900, 100]
    s["formula_token_count"] = [0, 999, 0]
    pd.testing.assert_frame_equal(first, propose_revision(m.iloc[::-1], s, q, d, p).set_index("factor"))


@pytest.mark.parametrize("relation,comparable", [("regime_dependent", True), ("insufficient_overlap", False), ("no_stable_redundancy", True)])
def test_unstable_leader_pair_cannot_be_replaced_via_transitive_chain(relation, comparable):
    m, s, q, d, p = inputs()
    # a-c and b-c remain stable, but a-b is not; c cannot serve as a bridge.
    p.loc[0, ["relation", "strict_stable", "all_views_comparable"]] = [relation, False, comparable]
    x = propose_revision(m, s, q, d, p).set_index("factor")
    assert x.loc["a", "proposed_representative"] == "a"
    assert x.loc["a", "proposal_role"] == "retain_pair_not_stable"


def test_unknown_windows_and_different_windows_never_alias():
    m, s, q, d, p = inputs()
    s.loc[0, "horizon"] = "26"
    x = propose_revision(m, s, q, d, p).set_index("factor")
    assert x.loc["a", "proposed_representative"] == "a"
    # Even a caller erroneously marking unknown strings resolved cannot bypass the gate.
    s["horizon"] = "unspecified"
    x = propose_revision(m, s, q, d, p)
    assert x.proposal_role.eq("deferred").all()
    assert x.proposed_representative.isna().all()


def test_singletons_distinguish_unknown_comparisons():
    m, s, q, d, p = inputs()
    m["cluster_id"] = m.factor
    p.loc[0, "all_views_comparable"] = False
    x = propose_revision(m, s, q, d, p).set_index("factor")
    assert x.loc["a", "proposal_role"] == "retain_unmerged_with_unknown_pairs"
    assert x.loc["a", "unknown_pair_count"] == 1
    assert x.loc["c", "proposal_role"] == "retain_unmerged_all_pairs_comparable"


def test_source_parameters_not_smoke_text_and_canonical_kama(tmp_path):
    ta = tmp_path / "ta"
    ta.mkdir()
    (ta / "trend.py").write_text('''class EMAIndicator:
    def __init__(self, close, window=14, fillna=False): pass
    def ema_indicator(self): pass
''')
    (ta / "wrapper.py").write_text('''def add_trend_ta(df, close, fillna=False, colprefix=""):
    df[f"{colprefix}trend_ema_fast"] = EMAIndicator(close=df[close], window=12, fillna=fillna).ema_indicator()
    df[f"{colprefix}trend_ema_slow"] = EMAIndicator(close=df[close], window=26, fillna=fillna).ema_indicator()
''')
    definitions = ta_definitions(tmp_path)
    assert definitions["ta_trend_ema_fast"]["horizon"] != definitions["ta_trend_ema_slow"]["horizon"]
    inventory = pd.DataFrame({"factor": ["ta_trend_ema_fast", "ta_trend_ema_slow", "ta_momentum_kama"],
                              "source": "ta", "definition": "Generated from ta wrapper smoke; coverage=.99",
                              "mechanism": "trend", "economic_family": "Trend", "primary_family": "Trend",
                              "active": True, "research_usable": True})
    definitions["ta_momentum_kama"] = {**definitions["ta_trend_ema_fast"]}
    x = revised_semantics(inventory, definitions).set_index("factor")
    assert "formula_token_count" not in x
    assert not x.representative_eligible.any()  # unresolved provider price scale
    assert "2000-01-04" in x.loc["ta_momentum_kama", "horizon"]
    assert "np.roll" not in x.loc["ta_momentum_kama", "definition"]


def test_full_median_cannot_override_era_sign_or_mask():
    names = ["a", "b"]
    row = {"comparable": True, "valid_dates": 100, "valid_date_fraction": 1., "q10_n_common": 100,
           "q10_common_coverage": 1., "median_abs_rho": .99, "q10_abs_rho": .99,
           "median_signed_rho": .99, "dominant_sign": 1., "sign_consistency": 1.}
    views = {k: pd.DataFrame([row]) for k in ["Full", "A", "B", "C", "D"]}
    relation = pd.DataFrame({"factor_a": ["a"], "factor_b": ["b"], "relation": ["regime_dependent"]})
    views["D"]["dominant_sign"] = -1
    assert not pair_table(names, views, relation, .95).strict_stable.iloc[0]
    relation["relation"] = "stable_redundancy"
    with pytest.raises(ValueError, match="disagrees"):
        pair_table(names, views, relation, .95)


def test_sealed_input_tampering_fails_before_writing(tmp_path):
    import json
    root = tmp_path
    report = root / "reports/candidate_consolidation_v0_5"
    report.mkdir(parents=True)
    (report / "REPORT.md").write_text("tampered")
    (report / "PROPOSAL_RECEIPT.json").write_text(json.dumps({"report_hashes": {"REPORT.md": "bad"}}))
    with pytest.raises(ValueError, match="sealed source changed"):
        verify_sealed(root, root / "out")

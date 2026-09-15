"""Synthetic high-risk search boundaries, cap/queue semantics and scalar oracle."""
import math
import random

import pandas as pd
import pytest

from model_research.economic_e3_parameter_structure import (
    candidates, adjacency, ranked_calendar, project, summarize, validate_spec,
)
from scripts.verify_e3_parameter_research import oracle


def test_frozen_sparse_space_and_neighbors():
    specs = candidates()
    assert len(specs) == len({s["id"] for s in specs}) == 30
    assert {s["interval"] for s in specs} == {1, 3, 5, 10}
    assert {s["k"] for s in specs} == {5, 8, 10}
    assert any(s["id"] == "k8_h16_d5_c1" for s in specs)
    edges = adjacency(specs)
    assert {"a": "k8_h16_d1_c1", "b": "k8_h16_d1_c2", "dimension": "cap"} in edges
    assert not any(e["a"] == "k8_h16_d1_c1" and e["b"] == "k8_h16_d1_c4" for e in edges)


@pytest.mark.parametrize("spec", candidates(), ids=lambda s: s["id"])
def test_all_candidates_independent_cross_year(spec):
    days = pd.bdate_range("2015-11-02", periods=101).strftime("%Y-%m-%d").tolist()
    rng = random.Random(761)
    universe = [f"S{i:02}" for i in range(35)]
    rankings = [rng.sample(universe, 30) for _ in days]  # missing held symbols must exit, not disappear
    rows, spells, episodes = project(days, rankings, spec)
    assert (rows, spells, episodes) == oracle(days, rankings, spec)
    assert all(len(r["after"]) <= spec["k"] for r in rows)
    assert not rows[0]["after"] and rows[1]["scheduled"]
    assert sum(r["scheduled"] for r in rows) == math.ceil((len(days) - 1) / spec["interval"])
    for i, r in enumerate(rows[2:], 2):
        assert len(r["exits"]) <= (spec["cap"] or spec["k"])
        assert set(r["entries"]) <= set(rankings[i - 1][:spec["k"]])
    summary = summarize(rows, spells, episodes, spec)
    assert summary["actual_R1"] is None and summary["economic_metrics"] is None
    assert sum(a["exits"] for a in summary["annual"]) == summary["target_exits"]


def test_deferred_recovers_then_new_episode_is_censored():
    spec = dict(k=2, hold=2, interval=1, cap=1)
    days = pd.bdate_range("2015-01-05", periods=5).strftime("%Y-%m-%d").tolist()
    ranks = [list("ABCD"), list("CDAB"), list("ACBD"), list("BDCA"), list("ABCD")]
    rows, spells, episodes = project(days, ranks, spec)
    assert rows[2]["exits"] == ["B"] and rows[2]["queue"] == [dict(instrument="A", rank=3, age_sessions=0)]
    assert episodes[0] == dict(instrument="A", start=days[2], end=days[3], age_sessions=1, resolution="recovered")
    assert episodes[-1]["resolution"] == "right_censored"
    assert (rows, spells, episodes) == oracle(days, ranks, spec)


def test_uncapped_daily_buffer_is_not_force_topk():
    days = ["2015-01-05", "2015-01-06", "2015-01-07"]
    rows, _, _ = project(days, [list("ABCD"), list("CDAB"), list("ABCD")], dict(k=2, hold=4, interval=1, cap=None))
    assert rows[2]["scheduled"] and rows[2]["after"] == ["A", "B"]
    assert not rows[2]["exits"] and not rows[2]["entries"]


def test_phase_uses_previous_score_and_no_final_forced_liquidation():
    days = ["2023-12-27", "2023-12-28", "2023-12-29"]
    rows, spells, _ = project(days, [list("ABC"), list("BAC"), list("CAB")], dict(k=1, hold=1, interval=1, cap=1))
    assert rows[-1]["after"] == ["B"] and any(s["right_censored"] for s in spells)
    assert not any("C" in r["after"] for r in rows)


def test_reader_rejects_outcomes_duplicates_gap_and_future():
    days = pd.to_datetime(["2015-01-05", "2015-01-06"])
    frame = pd.DataFrame(dict(datetime=list(days) * 2, instrument=["B", "B", "A", "A"], score=[1.] * 4))
    assert ranked_calendar(frame, days)[1] == [["A", "B"], ["A", "B"]]
    for bad in (frame.assign(label=0), pd.concat([frame, frame.iloc[:1]]), frame.iloc[:1], frame.assign(score=float("nan"))):
        with pytest.raises(ValueError):
            ranked_calendar(bad, days)
    with pytest.raises(ValueError):
        ranked_calendar(frame, pd.to_datetime(["2023-12-29", "2024-01-02"]))
    with pytest.raises(ValueError):
        validate_spec(dict(k=8, hold=7, interval=1, cap=1))


def test_target_control_matches_original_frozen_semantics_on_synthetic():
    from model_research.economic_e3_projection import project as original
    days = pd.bdate_range("2015-01-05", periods=70)
    rng = random.Random(21)
    frame = pd.DataFrame([(d, f"S{i}", rng.random()) for d in days for i in range(30)],
                         columns=["datetime", "instrument", "score"])
    old, _ = original(frame, days)
    dates, ranking = ranked_calendar(frame, days)
    rows, _, _ = project(dates, ranking, dict(k=8, hold=16, interval=5, cap=1))
    for a, b in zip(old, rows):
        assert a["after"] == b["after"] and a["exit_backlog"] == len(b["queue"])
        assert set(a["entries"]) == set(b["entries"]) and a["exits"] == b["exits"]


def test_fixed_warmup_bridge_excludes_current_volume_and_preserves_missingness():
    from scripts.audit_e3_parameter_inputs import first_market_packet
    dates = pd.bdate_range("2014-12-04", "2014-12-31").strftime("%Y-%m-%d").tolist()
    calendar = dates + ["2015-01-05", "2015-01-06"]
    warm = pd.DataFrame(dict(date=dates, instrument="S", volume=[100000.] + [10.] * 19))
    daily = pd.DataFrame(dict(date=calendar[-2:], instrument="S", raw_volume=[30., 999999.],
                              quote_status="cross_source_agreed"))
    packet = first_market_packet(daily, warm, calendar, "S", "a" * 64, "b" * 64)
    assert packet["A"][1].fact.value == 11
    assert "b" * 64 in packet["A"][1].fact.source
    bad = warm.copy()
    bad.loc[3, "volume"] = float("nan")
    assert len(first_market_packet(daily, bad, calendar, "S", "a" * 64, "b" * 64)["A"]) == 1
    with pytest.raises(ValueError):
        first_market_packet(daily, warm.assign(date="2014-12-03"), calendar, "S", "a" * 64, "b" * 64)

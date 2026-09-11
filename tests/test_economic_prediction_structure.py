import json

import numpy as np
import pandas as pd
import pytest

from model_research import economic_prediction_structure as e


def fixture_scores():
    days = pd.bdate_range("2022-12-01", periods=45)
    rows = []
    for i, d in enumerate(days):
        for j in range(120):
            # Turnover, ties, a year boundary and a changing lifecycle.
            stock = f"S{j:03}" if j != 119 or i < 20 else "NEW"
            rows.append((d, stock, float(((j + i * 3) % 120) // 2)))
    return pd.DataFrame(rows, columns=e.KEYS + ["score"]), days


def test_full_structural_oracle_and_censoring():
    frame, days = fixture_scores()
    result = e.study(frame, days)
    verified = e.independent_verify(frame, days, result)
    assert verified["status"] == "verified"
    assert result["rank_lags"].cross_model.any()
    assert result["spells"].right_censored.any()
    assert set(result["migration"].lag) == set(e.MIGRATION_LAGS)
    assert not e.summarize(result).empty
    assert result["turnover"].query("cold_start").membership_churn.eq(0.5).all()
    assert result["spells"].query("right_censored").exit_date.isna().all()


def test_hand_calculated_membership_and_ties():
    assert e.overlap({"a", "b"}, {"b", "c"})["jaccard"] == pytest.approx(1 / 3)
    assert e.membership_churn({"a", "b"}, {"b", "c"}) == 0.5
    assert e.membership_churn(set(), {"a", "b"}) == 0.5  # cold start explicitly distinct
    f = pd.DataFrame(
        [(pd.Timestamp("2023-01-03"), s, v) for s, v in [("b", 2), ("a", 2), ("c", 0)]],
        columns=e.KEYS + ["score"],
    )
    _, p, ordered, sets = e.rank_day(f)
    assert ordered == ["a", "b", "c"] and p.a == p.b
    assert sets[10] == {"a"}


@pytest.mark.parametrize("bad", ["label", "price", "close", "nav"])
def test_forbidden_columns(bad):
    f, days = fixture_scores()
    f[bad] = 0
    with pytest.raises(ValueError, match="economic columns"):
        e.study(f, days)


def test_dates_missing_nonfinite_and_duplicates_fail():
    f, days = fixture_scores()
    with pytest.raises(ValueError, match="missing/extra"):
        e.study(f[f.datetime != days[3]], days)
    with pytest.raises(ValueError, match="boundary"):
        e.study(f, pd.bdate_range("2024-01-01", periods=45))
    f.loc[0, "score"] = np.nan
    with pytest.raises(ValueError, match="finite-score"):
        e.study(f, days)
    f.loc[0, "score"] = 1
    with pytest.raises(ValueError, match="duplicate"):
        e.study(pd.concat([f, f.iloc[:1]]), days)


def test_closed_reader_rejects_paths_before_io(tmp_path):
    inv = {
        "role": "E1_B_scores_keys_only",
        "calendar": ["2023-01-03"],
        "folds": {"2023": {"scores": {"path": "labels.parquet"}}},
    }
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(inv))
    reader = e.BoundedScores(tmp_path, path)
    with pytest.raises(ValueError, match="fixed B"):
        reader.read(2023, "scores")
    for year, kind in [(2024, "scores"), (2023, "labels"), (2023, "R")]:
        with pytest.raises(ValueError, match="denied"):
            reader.read(year, kind)


@pytest.mark.parametrize(
    "table,column,error",
    [
        ("turnover", "entries", "state machine"),
        ("rank_lags", "full_pool_percentile_pearson", "full-pool percentile"),
    ],
)
def test_corrupted_replay_is_detected(table, column, error):
    f, days = fixture_scores()
    result = e.study(f, days)
    result[table].loc[3, column] += 1
    with pytest.raises(ValueError, match=error):
        e.independent_verify(f, days, result)


def test_cli_seal_and_independent_replay_on_synthetic_only(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from scripts import study_economic_e1 as cli

    data, days = fixture_scores()
    monkeypatch.setattr(cli, "OUT", tmp_path / "e1_synthetic")
    monkeypatch.setattr(
        e,
        "BoundedScores",
        lambda **kwargs: SimpleNamespace(
            inventory={"canonical_dataset_id": "synthetic"}, calendar=days, load=lambda: data
        ),
    )
    cli.run()
    cli.verify()
    cli.run()
    assert (
        json.loads((cli.OUT / "independent_replay.json").read_text())["result"]["status"]
        == "verified"
    )
    assert not {"nav.parquet", "prices.parquet", "labels.parquet"}.intersection(
        p.name for p in cli.OUT.iterdir()
    )


def test_delivery_binding_guard_before_values(tmp_path, monkeypatch):
    from scripts import study_economic_e1 as cli

    path = tmp_path / "delivery.json"
    monkeypatch.setattr(cli, "DELIVERY", path)
    value = cli.binding()
    path.write_text(json.dumps({"e1_execution_binding": value}))
    cli.check_delivery_binding()
    value["buffer"] = [10, 30]
    path.write_text(json.dumps({"e1_execution_binding": value}))
    with pytest.raises(ValueError, match="before score access"):
        cli.check_delivery_binding()

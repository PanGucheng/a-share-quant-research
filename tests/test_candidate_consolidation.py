from __future__ import annotations

import json
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pytest
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from factor_research.candidate_consolidation import (
    canary_dates, cluster_distance, exact_duplicate_groups, read_panel, select_working_set,
)
from factor_research.factor_similarity import daily_pairwise_spearman, pair_spearman_reference
from qlib_baseline.io import atomic_write_json
from scripts.run_candidate_consolidation_v0_5 import completed_chunk, execute, run_lock


def panel_fixture(tmp_path):
    days = pd.to_datetime(["2023-12-28", "2023-12-29", "2024-01-02"])
    data = pd.DataFrame([{"datetime": d, "instrument": f"s{i}", "a": float(i), "b": float(90-i)}
                         for d in days for i in range(80)])
    path = tmp_path / "parent.parquet"
    data.to_parquet(path, index=False)
    return pd.DataFrame([{"partition_path": str(path), "effective_start": "2023-12-28",
                          "effective_end": "2024-01-02", "factors": "a,b", "output_sha256": "test"}])


@pytest.mark.parametrize("engine", ["grouped", "pandas", "auto"])
def test_exact_mask_ties_constants_and_infinities(engine):
    rng = np.random.default_rng(917)
    x = rng.integers(-4, 5, size=(80, 9)).astype(float)
    x[:15, 0] = np.nan
    x[12:25, 1] = np.inf
    x[:, 2] = 1
    x[:, 3] = np.nan
    x[:, 4] = x[:, 0]
    x[:, 5] = -x[:, 0]
    x[:, 6] = np.exp(x[:, 0])
    x[:, 7] = x[:, 0] ** 2
    x[:, 8] = x[:, 1] > 0
    result = daily_pairwise_spearman(x, 50, engine=engine)
    for i in range(9):
        for j in range(9):
            rho, n, reason = pair_spearman_reference(x[:, i], x[:, j])
            np.testing.assert_allclose(result["rho"][i, j], rho, atol=1e-12, rtol=0)
            assert result["n_common"][i, j] == n
            assert result["reason"][i, j] == reason
    assert result["rho"][0, 5] == pytest.approx(-1)
    assert abs(result["rho"][0, 7]) < .9


def test_rerank_intersection_not_global_rank():
    a = np.array([1, 2, 3, 4, 5, 6.])
    b = np.array([1, np.nan, np.nan, 2, 4, 3.])
    result = daily_pairwise_spearman(np.column_stack([a, b]), 3, engine="grouped")
    wrong = pd.Series(a).rank()[np.isfinite(b)].corr(pd.Series(b).rank()[np.isfinite(b)])
    assert abs(result["rho"][0, 1] - wrong) > .01
    assert result["rho"][0, 1] == pytest.approx(pair_spearman_reference(a, b, 3)[0])


def test_reader_bounds_before_io_and_key_mismatch(tmp_path, monkeypatch):
    partitions = panel_fixture(tmp_path)
    original = pd.read_parquet
    calls = []
    def guard(path, **kwargs):
        calls.append(kwargs)
        assert kwargs["filters"][1][2] <= pd.Timestamp("2023-12-29")
        return original(path, **kwargs)
    monkeypatch.setattr(pd, "read_parquet", guard)
    access = []
    data = read_panel(partitions, ["b", "a"], "2023-12-28", "2023-12-29", access=access)
    assert len(data) == 160 and len(calls) == 1
    assert data.columns.tolist() == ["datetime", "instrument", "a", "b"]
    assert access[0]["end"] == "2023-12-29"
    with pytest.raises(ValueError, match="outside development"):
        read_panel(partitions, ["a"], "2024-01-02", "2024-01-02", access=[])
    assert len(calls) == 1
    broken = data.iloc[:-1][["datetime", "instrument", "b"]]
    broken.to_parquet(tmp_path / "broken.parquet", index=False)
    split = partitions.copy()
    split.loc[0, "factors"] = "a"
    second = partitions.copy()
    second.loc[0, "factors"] = "b"
    second.loc[0, "partition_path"] = str(tmp_path / "broken.parquet")
    with pytest.raises(ValueError, match="axis mismatch"):
        read_panel(pd.concat([split, second]), ["a", "b"], "2023-12-28", "2023-12-29", access=[])


def test_alias_scope_hash_equality_and_mask_conflict():
    frame = pd.DataFrame({"datetime": pd.Timestamp("2020-01-02"), "instrument": list("abcd"),
                          "A": [1., 2, 3, np.nan], "B": [1., 2, 3, np.nan],
                          "C": [-1., -2, -3, np.nan], "D": [1., 2, 3, 4]})
    aliases = exact_duplicate_groups(frame, list("ABCD"))
    assert [(x["factor_a"], x["factor_b"]) for x in aliases] == [("A", "B")]
    assert aliases == exact_duplicate_groups(frame.iloc[::-1], list("DCBA"))


@pytest.mark.parametrize("method", ["complete", "average"])
def test_cluster_scipy_parity_order_and_cut(method):
    x = np.array([[0, .1, .6], [.1, 0, .2], [.6, .2, 0]])
    d = pd.DataFrame(x, index=list("abc"), columns=list("abc"))
    ours = cluster_distance(d, .3, method=method)
    labels = fcluster(linkage(squareform(x), method=method), .3, criterion="distance")
    for i in range(3):
        for j in range(3):
            assert (ours.cluster_id.iloc[i] == ours.cluster_id.iloc[j]) == (labels[i] == labels[j])
    pd.testing.assert_frame_equal(ours, cluster_distance(d.loc[list("cba"), list("cba")], .3, method=method))
    assert len(cluster_distance(d.iloc[:1, :1], .3)) == 1
    d.iloc[0, 2] = d.iloc[2, 0] = np.nan
    if method == "average":
        with pytest.raises(ValueError, match="fully known"):
            cluster_distance(d, .3, method=method)
    else:
        assert cluster_distance(d, .3).cluster_id.nunique() == 2


def test_working_set_ignores_outcome_columns():
    board = pd.DataFrame({"factor": [f"f{i:03d}" for i in range(765)], "source": "test",
                          "agreement": ["2/3"] * 494 + ["0/3"] * 271,
                          "pass_count": [2] * 494 + [0] * 271, "IC": 100., "analysis_direction": 1})
    expected = select_working_set(board)
    board["IC"] = -999
    board["analysis_direction"] = -1
    pd.testing.assert_frame_equal(expected, select_working_set(board.iloc[::-1]))
    with pytest.raises(ValueError):
        select_working_set(board.iloc[:-1])


def test_canary_is_fixed_era_calendar_only():
    days = pd.date_range("2010-01-29", "2023-12-29", freq="B")
    result = canary_dates(days)
    assert len(result) == 12 and result[-1] == pd.Timestamp("2023-12-29")


def test_spawn_resume_receipt_and_partial_staging(tmp_path):
    partitions = panel_fixture(tmp_path)
    config = {"minimum_pair_observations": 50, "engine": "grouped", "parity_atol": 1e-12}
    jobs = [("2023-12-28", [pd.Timestamp("2023-12-28")]), ("2023-12-29", [pd.Timestamp("2023-12-29")])]
    serial, _, _ = execute(jobs, partitions, ["a", "b"], config, tmp_path / "one", "test", 1, True)
    parallel, _, _ = execute(jobs, partitions, ["a", "b"], config, tmp_path / "eight", "test", 8, True)
    for a, b in zip(serial, parallel):
        for field in ["rho", "reason", "n_common"]:
            np.testing.assert_array_equal(np.load(tmp_path / "one" / a["job"] / (field + ".npy")),
                                          np.load(tmp_path / "eight" / b["job"] / (field + ".npy")))
    _, _, new = execute(jobs, partitions, ["a", "b"], config, tmp_path / "one", "test", 1)
    assert new == 0
    (tmp_path / "one" / ".staging_interrupted").mkdir()
    assert completed_chunk(tmp_path / "one" / "missing", "test") is None
    path = tmp_path / "one" / jobs[0][0] / "rho.npy"
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="corrupted"):
        completed_chunk(path.parent, "test")
    with pytest.raises(ValueError, match="invalid receipt"):
        completed_chunk(path.parent, "other")


def test_os_lock_excludes_second_writer(tmp_path):
    with run_lock(tmp_path / "run.lock"):
        with pytest.raises(OSError):
            with run_lock(tmp_path / "run.lock"):
                pass
    with run_lock(tmp_path / "run.lock"):
        atomic_write_json(tmp_path / "released.json", {"ok": True})
    assert json.loads((tmp_path / "released.json").read_text())["ok"]


def test_process_death_releases_lock_and_unpublished_chunk_resumes(tmp_path):
    marker = tmp_path / "ready"
    source = (
        "from pathlib import Path\nimport time\n"
        "from scripts.run_candidate_consolidation_v0_5 import run_lock\n"
        f"p=Path({str(tmp_path)!r})\n"
        "with run_lock(p/'run.lock'):\n"
        " (p/'.staging_dead').mkdir()\n"
        " (p/'.staging_dead'/'rho.npy').write_bytes(b'partial')\n"
        " (p/'ready').write_text('ready')\n"
        " time.sleep(60)\n"
    )
    child = subprocess.Popen([sys.executable, "-c", source])
    try:
        deadline = time.monotonic() + 15
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.05)
        assert marker.exists()
        child.kill()
        child.wait(timeout=10)
        with run_lock(tmp_path / "run.lock"):
            partitions = panel_fixture(tmp_path)
            jobs = [("2023-12-28", [pd.Timestamp("2023-12-28")])]
            config = {"minimum_pair_observations": 50, "engine": "grouped", "parity_atol": 1e-12}
            _, _, new = execute(jobs, partitions, ["a", "b"], config, tmp_path, "test", 1)
            assert new == 1
        assert (tmp_path / ".staging_dead" / "rho.npy").read_bytes() == b"partial"
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)


def test_many_masks_and_minimum_boundary():
    rng = np.random.default_rng(119)
    x = rng.normal(size=(65, 70))
    x[rng.random(x.shape) < .15] = np.nan
    grouped = daily_pairwise_spearman(x, 50, engine="grouped")
    fallback = daily_pairwise_spearman(x, 50, engine="auto")
    assert fallback["engine"] == "pandas"
    np.testing.assert_allclose(grouped["rho"], fallback["rho"], rtol=0, atol=1e-12)
    np.testing.assert_array_equal(grouped["reason"], fallback["reason"])
    assert np.isnan(grouped["rho"][grouped["n_common"] < 50]).all()

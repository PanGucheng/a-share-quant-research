import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from scripts import run_long_history_primary_full as runner


def test_resume_requires_unchanged_contract_and_detects_output_corruption(tmp_path):
    contract = {"source": "fixed", "end": pd.Timestamp("2023-12-29")}
    digest = runner.bind_contract(tmp_path, contract)
    stage = tmp_path / "staging"
    stage.mkdir()
    (stage / "metric.csv").write_text("x\n1\n")
    target = tmp_path / "chunks" / "2010" / "x"
    runner.publish_chunk(stage, target, {"parity_status": "pass"}, digest)
    assert runner.bind_contract(tmp_path, contract) == digest
    assert runner.completed_chunk(target, digest)["execution_status"] == "complete"
    with pytest.raises(ValueError, match="contract changed"):
        runner.bind_contract(tmp_path, {**contract, "source": "modified"})
    (target / "metric.csv").write_text("x\n2\n")
    with pytest.raises(ValueError, match="corrupted"):
        runner.completed_chunk(target, digest)
    # Interrupted staging directories never count as completed outputs.
    assert runner.completed_chunk(tmp_path / "chunks" / "2011" / "x", digest) is None


def test_os_lock_excludes_second_process_and_releases_after_exit(tmp_path):
    path = tmp_path / "run.lock"
    code = (
        "from pathlib import Path\n"
        "from scripts.run_long_history_primary_full import run_lock\n"
        "import sys\n"
        "with run_lock(Path(sys.argv[1])): print('acquired')\n"
    )
    with runner.run_lock(path):
        child = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, text=True)
        assert child.returncode != 0
    child = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, text=True)
    assert child.returncode == 0, child.stderr
    assert "acquired" in child.stdout


def test_aggregate_requires_every_year_and_uses_raw_quantiles_and_ic(tmp_path, monkeypatch):
    calendar = pd.bdate_range("2010-01-29", "2023-12-29")
    inventory = pd.DataFrame({"factor": ["x"], "research_usable": [True]})
    config = {"signal_eras": {"A": ["2010-01-29", "2014-12-31"],
                              "B": ["2015-01-01", "2017-12-31"],
                              "C": ["2018-01-01", "2020-12-31"],
                              "D": ["2021-01-01", "2023-12-29"]},
              "universe": "canonical_practical_raw", "bootstrap": {"samples": 1000, "block_length": 20, "seed": 20260907}}
    digest = runner.bind_contract(tmp_path, config)
    with pytest.raises(ValueError, match="missing required job"):
        runner.aggregate(tmp_path, inventory, calendar, config, digest)
    expected = []
    for year in range(2010, 2024):
        stage = tmp_path / f"stage-{year}"
        stage.mkdir()
        dates = calendar[calendar.year == year][:2]
        values = pd.Series([year - 2015., year - 2014.], index=dates, name="qlib_ic")
        expected.append(values)
        values.to_frame().to_parquet(stage / "qlib_ic.parquet")
        index = pd.MultiIndex.from_product([range(1, 6), dates], names=["factor_quantile", "date"])
        pd.DataFrame({"20D": np.repeat(np.arange(1., 6.), 2)}, index=index).to_parquet(stage / "alphalens_quantile.parquet")
        runner.publish_chunk(stage, tmp_path / "chunks" / str(year) / "x", {}, digest)

    def fdr_spy(inv, daily, cal, **kwargs):
        pd.testing.assert_series_equal(daily["x"], pd.concat(expected), check_freq=False)
        assert kwargs == {"samples": 1000, "block_length": 20, "seed": 20260907}
        return pd.DataFrame({"factor": ["x"], "raw_p_value": [1.]})

    monkeypatch.setattr(runner, "primary_fdr", fdr_spy)
    runner.aggregate(tmp_path, inventory, calendar, config, digest)
    data = pd.read_parquet(tmp_path / "aggregate" / "period_metrics.parquet")
    full = data.loc[data.period_type.eq("full")].set_index("metric")
    assert full.loc["qlib_ic", "mean"] == pd.concat(expected).mean()
    assert full.loc["alphalens_q5_minus_q1", "mean"] == 4.
    assert full.loc["jqfactor_returns", "status"] == "unavailable"
    assert runner.completed_chunk(tmp_path / "aggregate", digest) is not None

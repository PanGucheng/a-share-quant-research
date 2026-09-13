import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import resume_e2_hard_history as recovery


def setup_case(tmp_path, monkeypatch):
    starts = {"SH600000": "2015-01-05", "SH600143": "2015-01-05"}
    days = ["2015-01-05"]
    parent = tmp_path / "full_states"
    parent.mkdir()
    put = recovery.original.put
    put(parent / "scope.json", dict(days=days, starts=starts, mode="states", code_lf={}))
    pd.DataFrame({"date": days}).to_parquet(parent / "SH600000.parquet", index=False)
    put(
        parent / "SH600000.json",
        dict(
            status="complete",
            rows=1,
            files={"SH600000.parquet": recovery.original.sha(parent / "SH600000.parquet")},
        ),
    )
    put(parent / "SH600143.json", dict(status="failed", error_type="RuntimeError", files={}))
    monkeypatch.setattr(recovery, "BASE", tmp_path)
    monkeypatch.setattr(recovery, "code_binding", lambda: {"synthetic": "same"})
    monkeypatch.setattr(recovery.original, "scope_inventory", lambda: (days, starts))
    monkeypatch.setattr(recovery, "close_bao_socket", lambda: None)
    monkeypatch.setattr(recovery.time, "sleep", lambda _: None)
    return parent


def test_parent_completed_and_failed_receipts_preserved(tmp_path, monkeypatch):
    parent = setup_case(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in parent.iterdir()}
    calls = []

    def fetch(mode, key, start):
        calls.append(key)
        assert (mode, key, start) == ("states", "SH600143", "2015-01-05")
        return pd.DataFrame({"date": ["2015-01-05"]}), "success"

    monkeypatch.setattr(recovery, "fetch", fetch)
    recovery.resume("states")
    assert calls == ["SH600143"]
    assert before == {p.name: p.read_bytes() for p in parent.iterdir()}
    result = json.loads((tmp_path / "recovery_states_v1/complete.json").read_text())
    assert result["chunks"] == 2 and result["rows"] == 2 and not result["e2_ready"]
    with pytest.raises(ValueError, match="already complete"):
        recovery.resume("states")


@pytest.mark.parametrize("error", [RuntimeError("source status 10002007"), KeyboardInterrupt()])
def test_retry_keeps_failed_or_interrupted_attempt(tmp_path, monkeypatch, error):
    setup_case(tmp_path, monkeypatch)

    def fail(*_):
        raise error

    monkeypatch.setattr(recovery, "fetch", fail)
    with pytest.raises(type(error)):
        recovery.resume("states")
    old = tmp_path / "recovery_states_v1/SH600143/attempt_0001/receipt.json"
    before = old.read_bytes()
    monkeypatch.setattr(
        recovery, "fetch", lambda *_: (pd.DataFrame({"date": ["2015-01-05"]}), "success")
    )
    recovery.resume("states")
    assert old.read_bytes() == before
    assert (old.parent.parent / "attempt_0002/receipt.json").exists()


def test_parent_tamper_fails_before_network(tmp_path, monkeypatch):
    parent = setup_case(tmp_path, monkeypatch)
    (parent / "SH600000.parquet").write_bytes(b"tampered")

    def forbidden(*_):
        pytest.fail("source must not be called after parent corruption")

    monkeypatch.setattr(recovery, "fetch", forbidden)
    with pytest.raises(ValueError, match="evidence changed"):
        recovery.resume("states")


def test_recovery_rejects_future_response_before_parquet(tmp_path, monkeypatch):
    setup_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        recovery, "fetch", lambda *_: (pd.DataFrame({"date": ["2024-01-02"]}), "success")
    )
    with pytest.raises(ValueError, match="date coverage"):
        recovery.resume("states")
    assert not list(Path(tmp_path / "recovery_states_v1").rglob("data.parquet"))


def test_dividend_resume_reuses_parent_date(tmp_path, monkeypatch):
    setup_case(tmp_path, monkeypatch)
    days = ["2015-01-05", "2015-01-06"]
    starts = {"SH600000": "2015-01-05"}
    monkeypatch.setattr(recovery.original, "scope_inventory", lambda: (days, starts))
    parent = tmp_path / "full_dividends"
    parent.mkdir()
    recovery.original.put(
        parent / "scope.json", dict(days=days, starts=starts, mode="dividends", code_lf={})
    )
    pd.DataFrame({"ex_date": ["20150105"]}).to_parquet(parent / "2015-01-05.parquet")
    recovery.original.put(
        parent / "2015-01-05.json",
        dict(
            status="complete",
            rows=1,
            files={"2015-01-05.parquet": recovery.original.sha(parent / "2015-01-05.parquet")},
        ),
    )

    def fetch(mode, key, start):
        assert (mode, key, start) == ("dividends", "2015-01-06", None)
        return pd.DataFrame({"ex_date": ["20150106"]}), "success"

    monkeypatch.setattr(recovery, "fetch", fetch)
    recovery.resume("dividends")
    result = json.loads((tmp_path / "recovery_dividends_v1/complete.json").read_text())
    assert result["chunks"] == 2 and result["rows"] == 2

import json

import pytest
import requests

from scripts import retry_e2_hard_history as retry
from tests.test_e2_history_recovery import setup_case


def test_real_resume_retry_preserves_failed_attempt_and_skips_completed(tmp_path, monkeypatch):
    import pandas as pd

    parent = setup_case(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in parent.iterdir()}
    calls = []
    waits = []
    closed = []

    def fetch(mode, key, start):
        calls.append(key)
        if len(calls) == 1:
            return pd.DataFrame(), "10002007:network receive error"
        return pd.DataFrame({"date": ["2015-01-05"]}), "success"

    monkeypatch.setattr(retry.recovery, "fetch", fetch)
    monkeypatch.setattr(retry.recovery, "close_bao_socket", lambda: closed.append(True))
    monkeypatch.setattr(retry.time, "sleep", waits.append)
    retry.run("states")
    assert calls == ["SH600143", "SH600143"] and len(closed) == 2
    assert 30 in waits
    assert before == {p.name: p.read_bytes() for p in parent.iterdir()}
    attempts = tmp_path / "recovery_states_v1/SH600143"
    assert json.loads((attempts / "attempt_0001/receipt.json").read_text())["status"] == "failed"
    assert json.loads((attempts / "attempt_0002/receipt.json").read_text())["status"] == "complete"


def test_backoff_budget_and_cap(tmp_path, monkeypatch):
    setup_case(tmp_path, monkeypatch)
    calls = []
    waits = []

    def fail(mode):
        calls.append(mode)
        raise requests.exceptions.ReadTimeout()

    monkeypatch.setattr(retry.recovery, "resume", fail)
    monkeypatch.setattr(retry.time, "sleep", waits.append)
    with pytest.raises(requests.exceptions.ReadTimeout):
        retry.run("states", max_retries=4)
    assert len(calls) == 5 and waits == [30, 60, 120, 120]


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("hash mismatch"),
        RuntimeError("source status denied_code_40203"),
        RuntimeError("source status 100020070"),
        KeyboardInterrupt(),
    ],
)
def test_non_network_failures_and_user_interrupt_never_retry(tmp_path, monkeypatch, exc):
    setup_case(tmp_path, monkeypatch)

    def fail(mode):
        raise exc

    monkeypatch.setattr(retry.recovery, "resume", fail)
    monkeypatch.setattr(retry.time, "sleep", lambda _: pytest.fail("must not retry"))
    with pytest.raises(type(exc)):
        retry.run("states")


def test_interrupt_during_wait_stops_without_new_attempt(tmp_path, monkeypatch):
    setup_case(tmp_path, monkeypatch)
    calls = []

    def fail(mode):
        calls.append(mode)
        raise RuntimeError("Bao login code 10002007")

    def interrupt(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(retry.recovery, "resume", fail)
    monkeypatch.setattr(retry.time, "sleep", interrupt)
    with pytest.raises(KeyboardInterrupt):
        retry.run("states")
    assert len(calls) == 1

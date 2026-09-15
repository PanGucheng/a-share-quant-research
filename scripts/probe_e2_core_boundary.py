"""Synthetic diagnosis of scope/legacy wiring; no historical values or sessions."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import socket
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def probe():
    def deny(*args, **kwargs):
        raise AssertionError("core probe denies network/provider values")

    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    socket.create_connection = deny
    from qlib.data import D
    from qlib_integration.economic_event_position import EventPosition
    from qlib_integration.economic_mvp_scope import scope_account, visible_fact
    from qlib_integration.execution_readiness import require_continuity

    D.features = deny
    fixture = runpy.run_path(str(ROOT / "tests/test_economic_mvp_scope.py"))
    position = EventPosition(
        cash=1000.0, position_dict={"SH600000": {"amount": 100.0, "price": 10.0}}
    )
    account = SimpleNamespace(current_position=position)
    before = deepcopy(position.__dict__)
    mark = {"SH600000": {"date": "2020-07-16", "price": 10.0, "source": "synthetic"}}
    cases = []
    for name, candidates, states in (
        ("bad_unheld_candidate", ["SH600999"], {"SH600000": fixture["state"]()}),
        ("held_carry_without_trade_state", [], {}),
    ):
        result = scope_account(
            account, candidates, fixture["AT"], {"SH600000": fixture["held_facts"]()}, states
        )
        assert result["account_action"] == "PREFLIGHT_PASSED"
        assert result["holdings"]["SH600000"].action == "CARRY_ONLY"
        if candidates:
            assert result["entries"][candidates[0]].action == "NO_NEW_ENTRY"
        try:
            require_continuity(
                candidates, position.get_stock_amount_dict(), states, fixture["AT"], mark
            )
        except ValueError as exc:
            legacy_error = str(exc)
        else:
            raise AssertionError("legacy behavior changed; reassess Core boundary")
        assert position.__dict__ == before
        cases.append(dict(case=name, scope="PREFLIGHT_PASSED", legacy_error=legacy_error))
    assert visible_fact([fixture["fact"](True, known_at=None)], fixture["AT"]) is None
    paths = [
        "scripts/probe_e2_core_boundary.py",
        "tests/test_economic_mvp_scope.py",
        "qlib_integration/economic_mvp_scope.py",
        "qlib_integration/execution_readiness.py",
        "qlib_integration/economic_event_position.py",
        "qlib_integration/economic_exchange.py",
        "qlib_integration/economic_semantic_reconciliation.py",
    ]
    return dict(
        status="PASS: current integration gaps reproduced, not Core Ready",
        cases=cases,
        unknown_known_at_rejected=True,
        account_unchanged=True,
        fixture_kind="synthetic; existing scope test fixtures",
        historical_values_read=False,
        exchange_session_or_strategy_run=False,
        code_sha256_lf={
            p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p in paths
        },
    )


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))

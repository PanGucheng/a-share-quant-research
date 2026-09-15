# ruff: noqa: E402
"""Fixed E3 target-only structure plus first-decision bounded dependency audit."""

import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from model_research.economic_prediction_structure import BoundedScores, sha, json_text, require
from model_research.economic_e3_projection import project, summarize
from qlib_integration.economic_strategy_membership import rank_scores
from qlib_integration.economic_mvp_scope import entry_eligibility, Fact

REPORT = ROOT / "reports/economic_translation_mvp/e3_freeze_v1"
OUT = ROOT / "outputs/economic_translation_mvp/e3_preflight_v2"
CODE = ["model_research/economic_e3_projection.py", "model_research/economic_prediction_structure.py",
        "qlib_integration/economic_strategy_membership.py", "qlib_integration/economic_strategy_budget.py",
        "qlib_integration/economic_mvp_scope.py", "scripts/preflight_e3_structure.py",
        "scripts/verify_e3_structure.py"]


def state_data_path(state_receipt, record, stock):
    files = record.get("files", {})
    require(record.get("status") == "complete" and len(files) == 1, "incomplete/ambiguous state receipt")
    name = next(iter(files))
    require(name in {stock + ".parquet", "data.parquet"}, "unexpected state data path")
    return state_receipt.parent / name, files[name]


def first_dependency_probe(top8, signal, session, audit):
    """Only two date rows per Top8 ID; no open/close/returns or retrospective exclusions."""
    base = ROOT / "outputs/economic_translation_mvp/e2_semantic_v1"
    receipt = json.loads((base / "receipt.json").read_text(encoding="utf-8"))
    hard = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"
    refs = json.loads((hard / "recovery_states_v1/complete.json").read_text(encoding="utf-8"))["references"]
    source_path = ROOT / "reports/economic_translation_mvp/e2_readiness_v2/provider_probe_receipts.json"
    probes = json.loads(source_path.read_text(encoding="utf-8"))
    limit_metadata = [r for r in probes if r.get("api") == "stk_limit"]
    for p in (base / "receipt.json", hard / "recovery_states_v1/complete.json", source_path):
        audit.append(dict(role="E3_source_inventory", path=str(p.relative_to(ROOT)), sha256=sha(p), columns="metadata_only"))
    rows = []
    for stock in top8:
        path = base / "daily" / (stock + ".parquet")
        require(sha(path) == receipt["daily\\" + stock + ".parquet"], "semantic daily hash changed")
        columns = ["date", "instrument", "asset_id", "execution_code_reference", "board", "quote_status"]
        daily = pd.read_parquet(path, columns=columns, filters=[("date", ">=", signal), ("date", "<=", session)])
        audit.append(dict(role="E3_first_entry", path=str(path.relative_to(ROOT)), sha256=sha(path),
                          columns=columns, start=signal, end=session, rows=len(daily)))
        ref = refs[stock]
        state_receipt = hard / ref["path"]
        require(sha(state_receipt) == ref["sha256"], "state receipt hash changed")
        r = json.loads(state_receipt.read_text(encoding="utf-8"))
        state_path, expected = state_data_path(state_receipt, r, stock)
        require(sha(state_path) == expected, "state hash changed")
        audit.append(dict(role="E3_state_receipt", path=str(state_receipt.relative_to(ROOT)),
                          sha256=sha(state_receipt), columns="metadata_only"))
        cols = ["date", "code", "tradestatus", "isST"]
        states = pd.read_parquet(state_path, columns=cols, filters=[("date", "==", session)])
        audit.append(dict(role="E3_first_entry", path=str(state_path.relative_to(ROOT)), sha256=sha(state_path),
                          columns=cols, start=session, end=session, rows=len(states)))
        current = daily[daily.date.eq(session)]
        identity = current.iloc[0].asset_id if len(current) == 1 else None
        facts = {}
        if isinstance(identity, str) and identity:
            facts["asset_id"] = [Fact(identity, session, session, session, None, str(path),
                                      "historical_session_effective")]
        # Do not manufacture other A facts from missing provider coverage or EOD diagnostics.
        decision = entry_eligibility(stock, session + " 09:00", facts, None, historical=True)
        matching = [r for r in limit_metadata if r.get("parameters", {}).get("trade_date") == session.replace("-", "")
                    and r.get("parameters", {}).get("ts_code") == stock[2:] + "." + stock[:2]]
        rows.append(dict(instrument=stock, asset_id=identity, daily_rows=len(daily), state_rows=len(states),
                         independent_limit_receipts=len(matching), action=decision.action,
                         reasons=list(decision.reasons), classification="INPUT_ASSEMBLY_PENDING_NOT_EXCHANGE_REJECTION"))
    return dict(signal=signal, session=session, original_top8=top8, rows=rows,
                status="ACTUAL_PATH_NOT_STARTED", actual_sessions=0, actual_R1=None, actual_R2=None, actual_R3=None,
                later_sessions="NOT_REACHED", no_entry_is_not_acceptance=True,
                missing="source-bound A assembly (limits, strict ADV, current event review); personal fee/conditional cash integration")


def main():
    def deny(*args, **kwargs):
        raise RuntimeError("E3 preflight is offline")
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    require(sha(REPORT / "freeze.json") == (REPORT / "freeze.sha256").read_text().strip(), "freeze changed")
    freeze = json.loads((REPORT / "freeze.json").read_text(encoding="utf-8"))
    # This implementation supports exactly the frozen definition, not a tunable grid.
    require(sha(REPORT / "freeze.json") == "6dcd4bbe70f21d615d2d28659c629bd1543825dc940e65c3593980652691e8c2", "unsupported strategy version")
    OUT.mkdir(exist_ok=False)
    audit = []

    def put(name, value):
        with (OUT / name).open("x", encoding="utf-8", newline="\n") as f:
            f.write(json_text(value))
    try:
        put("started.json", dict(freeze_sha256=sha(REPORT / "freeze.json"), role="one_target_projection_plus_bounded_dependency_probe"))
        reader = BoundedScores(audit=audit)
        require(sha(ROOT / "reports/economic_translation_mvp/e1_inputs.json") == freeze["sources"]["scores"]["sha256"], "score inventory changed")
        data = reader.load()  # Existing closed B/keys reader; does not rerun E1 study.
        for item in audit:
            item["role"] = "E3_reuse_closed_B_reader"
        rows, spells = project(data, reader.calendar)
        put("target_days.json", rows)
        put("target_spells.json", spells)
        put("target_summary.json", summarize(rows, spells))
        first = data[data.datetime.eq(reader.calendar[0])]
        top = rank_scores(list(first[["instrument", "score"]].itertuples(index=False, name=None)))[:8]
        put("actual_dependency_probe.json", first_dependency_probe(top, str(reader.calendar[0].date()),
            str(reader.calendar[1].date()), audit))
        put("access.json", audit)
        put("binding.json", dict(freeze_sha256=sha(REPORT / "freeze.json"),
            code_sha256_lf={name: __import__("hashlib").sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for name in CODE},
            outcomes=False, actual_path_passed=False, status="E3 STRATEGY FROZEN / PATH PREFLIGHT PENDING"))
        put("receipt.json", {p.name: sha(p) for p in OUT.iterdir() if p.is_file()})
        print("Single target projection complete; actual path remains PENDING; no account/outcomes")
    except Exception as exc:
        put("failure.json", dict(error=type(exc).__name__, message=str(exc), access=audit))
        raise


if __name__ == "__main__":
    main()

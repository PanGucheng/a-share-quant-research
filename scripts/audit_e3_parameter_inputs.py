# ruff: noqa: E402
"""Bounded first Top10 source intake; not a simulated flat account or path HALT."""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from model_research.economic_prediction_structure import sha, require
from scripts.preflight_e3_structure import state_data_path
from qlib_integration.economic_core_inputs import Evidence, adapt_phase
from qlib_integration.economic_historical_inputs import known_event_records
from qlib_integration.economic_mvp_scope import Fact, entry_eligibility
from qlib_integration.execution_readiness import adv20_with_warmup


def first_market_packet(daily, warm, calendar, stock, daily_hash, warm_hash):
    """Bridge the existing explicitly approved warmup function to historical A.

    The general market adapter deliberately rejects 2014. Do not relax its global
    boundary: only this fixed first-session volume packet uses the warmup exception.
    """
    require(calendar[-2:] == ["2015-01-05", "2015-01-06"] and len(calendar) == 22
            and calendar == sorted(set(calendar)) and calendar[0] == "2014-12-04"
            and calendar[-3] == "2014-12-31", "fixed first-session calendar required")
    require(set(daily.date) == {"2015-01-05", "2015-01-06"} and not daily.date.duplicated().any()
            and daily.instrument.eq(stock).all(), "daily window/identity mismatch")
    require(warm.instrument.eq(stock).all() and not warm.date.duplicated().any()
            and set(warm.date) <= set(calendar[:20]), "warmup window/identity mismatch")
    prior = calendar[1:-1]  # 19 December sessions + Jan 5; never Jan 6 volume
    values = pd.concat([warm.set_index("date").volume,
                        daily.set_index("date").raw_volume])
    rows = []
    day = "2015-01-06"

    def rec(name, value):
        return Evidence(stock, name, "A", Fact(value, "2015-01-05", day, day, None,
            "sealed daily overlay#" + daily_hash + ";approved warmup overlay#" + warm_hash),
            daily_hash, phase_basis="prior_session_eod")

    rows.append(rec("quote_quality", daily.set_index("date").loc["2015-01-05", "quote_status"] == "cross_source_agreed"))
    try:
        adv = adv20_with_warmup(values, prior, order_date=day)
    except ValueError:
        # Scope/identity/calendar already validated; missing volume cannot be filled.
        adv = None
    if adv is not None:
        rows.append(rec("adv20_shares", adv))
    return {"A": rows}


def audit_first(top10, audit):
    require(len(top10) == 10 and len(set(top10)) == 10, "fixed original Top10 required")
    base = ROOT / "outputs/economic_translation_mvp/e2_semantic_v1"
    hard = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"

    def metadata(path):
        audit.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), columns="metadata"))
        return json.loads(path.read_text(encoding="utf-8"))

    sealed = metadata(base / "receipt.json")
    refs = metadata(hard / "recovery_states_v1/complete.json")["references"]
    warm_receipt = metadata(hard / "analysis/receipt.json")
    probes = metadata(ROOT / "reports/economic_translation_mvp/e2_readiness_v2/provider_probe_receipts.json")

    def read(path, expected, columns, filters):
        require(sha(path) == expected, "sealed source changed: " + str(path))
        f = pd.read_parquet(path, columns=columns, filters=filters)
        audit.append(dict(path=str(path.relative_to(ROOT)), sha256=expected, columns=columns,
                          filters=filters, rows=len(f)))
        return f

    warm = read(hard / "analysis/warmup_volume_overlay.parquet", warm_receipt["warmup_volume_overlay.parquet"],
        ["instrument", "date", "volume"], [("instrument", "in", top10), ("date", ">=", "2014-12-04"), ("date", "<=", "2014-12-31")])
    calendar_meta = metadata(hard / "canary/warmup_access.json")
    dates = calendar_meta[0]["dates"]
    require(len(dates) == 20 and dates == sorted(set(dates)) and dates[0] == "2014-12-04"
            and dates[-1] == "2014-12-31", "sealed warmup calendar mismatch")
    calendar = dates + ["2015-01-05", "2015-01-06"]
    result = []
    day = "2015-01-06"
    for stock in top10:
        name = "daily\\" + stock + ".parquet"
        daily = read(base / "daily" / (stock + ".parquet"), sealed[name],
            ["date", "instrument", "asset_id", "execution_code_reference", "board", "quote_status", "raw_volume", "valuation_mark"],
            [("date", ">=", "2015-01-05"), ("date", "<=", day)])
        ref = refs[stock]
        rp = hard / ref["path"]
        require(sha(rp) == ref["sha256"], "state receipt changed")
        record = metadata(rp)
        path, expected = state_data_path(rp, record, stock)
        states = read(path, expected, ["date", "code", "tradestatus", "isST", "open", "preclose"], [("date", "==", day)])
        w = warm[warm.instrument.eq(stock)]
        # Only the latest actual prior-session quote quality is consumed. Warmup
        # rows supply volume only; no invented quote-quality/state certificates.
        current = daily[daily.date.eq(day)]
        today = states.iloc[0] if len(states) == 1 else None
        packet = first_market_packet(daily, w, calendar, stock, sealed[name], warm_receipt["warmup_volume_overlay.parquet"])
        events = read(base / "events.parquet", sealed["events.parquet"],
            ["asset_id", "event_id", "record_date", "ex_date", "implementation_known_date"],
            [[("asset_id", "==", stock), ("record_date", "==", "20150106")],
             [("asset_id", "==", stock), ("ex_date", "==", "20150106")]])
        events = events[events.implementation_known_date.isna() | events.implementation_known_date.le("20150106")]
        review = dict(instrument=stock, session=day, source="flat-start known session-distribution review only",
            sha256=sealed["events.parquet"], event_ids=events.event_id.tolist(),
            status="unresolved" if len(events) else "no_known_blocking",
            reviewed_sources=[dict(path="e2_semantic_v1/events.parquet", sha256=sealed["events.parquet"])])
        packet["A"] += known_event_records(instrument=stock, date=day, review=review)["A"]
        phase = adapt_phase(packet["A"], date=day, at=day + " 09:00", phase="A", mode="historical")
        identity = current.iloc[0].asset_id if len(current) == 1 else None
        if isinstance(identity, str) and identity:
            phase.facts.setdefault(stock, {})["asset_id"] = [Fact(identity, day, day, day, None,
                "sealed identity#" + sealed[name], "historical_session_effective")]
        facts = phase.facts.get(stock, {})
        gate = entry_eligibility(stock, phase.at, facts, None, historical=True)
        matching = [r for r in probes if r.get("api") == "stk_limit"
                    and r.get("parameters", {}).get("trade_date") == "20150106"
                    and r.get("parameters", {}).get("ts_code") == stock[2:] + "." + stock[:2]]
        adv = facts.get("adv20_shares", [])
        quality = facts.get("quote_quality", [])
        result.append(dict(instrument=stock, asset_id=identity, bounded_identity_consistent=bool(
            len(current) == 1 and identity == stock and current.iloc[0].execution_code_reference == stock),
            state_rows=len(states), raw_state_values=None if today is None else dict(st=str(today.isST), active=str(today.tradestatus)),
            adv20=adv[0].value if adv else None, prior_quote_quality=quality[0].value if quality else None,
            open_reference_available=bool(today is not None and math.isfinite(float(today.open)) and float(today.open) > 0),
            scoped_session_distribution_rows=len(events), complete_event_coverage=False,
            matching_existing_independent_limits=len(matching), entry_action=gate.action, reasons=list(gate.reasons),
            early_sh_par_evidence="NOT_ASSEMBLED" if stock.startswith("SH") else "NOT_APPLICABLE",
            phase_issues=phase.issues))
    return dict(status="ACTUAL_PATH_NOT_STARTED_SOURCE_INTAKE_BLOCKED", session=day, original_top10=top10,
        rows=result, actual_R1=None, actual_R2=None, actual_R3=None, actual_sessions=0,
        not_actual_gate_rejections=True,
        source_limit="absence checked only in existing C1 independent-limit receipt inventory",
        event_limit="first flat-start record/ex-date review only; no held-event or full-family certification",
        remaining=["independent session limits / ordinary-state certification for touched entries",
                   "strategy-specific multi-sale and actual-cash/personal-fee Core integration",
                   "daily held-event/valuation/identity path and independent account validation"])

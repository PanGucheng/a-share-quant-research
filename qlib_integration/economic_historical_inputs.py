"""Bounded historical session evidence; no live receipts or complete-event claims."""

import math

from .economic_core_inputs import Evidence
from .economic_mvp_scope import Fact
from .economic_execution_contract import bounded_date, price_bounds
from .market_semantics import infer_board


def session_state_records(*, instrument, date, states, limits, identity,
                          state_hash, limit_hash, identity_hash):
    """Seasoned daily state + independent dated limits, never same-day OHLC tests.

    Prior observed sessions establish only a lower bound on age. They do not
    certify absence of relisting. The independent ordinary limits and an explicit
    known-risk review are the MVP approximation; known special cases still deny.
    Caller passes exactly the bounded source slice and a reconciled identity row.
    """
    date = str(bounded_date(date).date())
    if (states.date.duplicated().any() or not states.code.eq(instrument[:2].lower() + "." + instrument[2:]).all()
            or any(str(bounded_date(d).date()) != d or d > date for d in states.date)):
        raise ValueError("historical state source identity/date conflict")
    today = states[states.date.eq(date)]
    if len(today) != 1 or len(limits) != 1:
        raise ValueError("missing/conflicting session state or independent limit")
    row, bound = today.iloc[0], limits.iloc[0]
    if (bound.ts_code != instrument[2:] + "." + instrument[:2]
            or bound.trade_date != date.replace("-", "")):
        raise ValueError("independent limit identity/session mismatch")
    if (identity.get("instrument") != instrument or identity.get("date") != date
            or identity.get("asset_id") != instrument or identity.get("execution_code_reference") != instrument):
        raise ValueError("missing/ambiguous identity; explicit alias reconciliation required")
    board = infer_board(instrument)
    if identity.get("board") != board or board not in {"main", "chinext", "star"}:
        raise ValueError("historical board conflict")
    st, active = float(row.isST), float(row.tradestatus)
    if st not in {0.0, 1.0} or active not in {0.0, 1.0}:
        raise ValueError("missing daily ST/suspension")
    reference = float(bound.pre_close)
    if (not all(math.isfinite(float(v)) for v in (reference, row.preclose, bound.down_limit, bound.up_limit))
            or reference <= 0 or abs(reference - float(row.preclose)) > 0.001):
        raise ValueError("independent reference conflict")
    ratio = 0.2 if board == "star" or (board == "chinext" and date >= "2020-08-24") else 0.05 if st else 0.1
    lo, hi = price_bounds(reference, ratio)
    if abs(float(bound.down_limit) - lo) > 1e-8 or abs(float(bound.up_limit) - hi) > 1e-8:
        raise ValueError("special/unresolved independent session limits")
    prior = states[states.date.lt(date)]
    # Do not count missing state rows as observed trading sessions.
    count = sum(prior.tradestatus.astype(str).isin(["1", "1.0"]))
    state = dict(instrument=instrument, date=date, board=board, listed=True, st=bool(st),
                 suspended=not bool(active), ordinary_session=True, special_session="none",
                 limit_ratio=ratio, lower_limit=lo, upper_limit=hi, limit_reference=reference,
                 effective_from=date, effective_to=date, evidence_level="cross_source",
                 prior_session_count=int(count), regime_basis="independent_dated_limits_with_prior_sessions")
    source = f"sealed daily state#{state_hash};independent dated limits#{limit_hash}"
    result = {"A": [], "C": []}
    for phase in result:
        result[phase].append(Evidence(instrument, "asset_id", phase,
            Fact(instrument, date, date, date, None, "sealed identity overlay"), identity_hash,
            phase_basis="historical_session_effective"))
    result["A"].append(Evidence(instrument, "state", "A",
        Fact(state, date, date, date, None, source), state_hash, phase_basis="historical_session_effective"))
    result["A"].append(Evidence(instrument, "reference_mark", "A",
        Fact(reference, date, date, date, None, "independent dated session reference; not an opening fill"),
        limit_hash, phase_basis="historical_session_effective"))
    return result


def known_event_records(*, instrument, date, review):
    """Review is mandatory even if its known-event set is empty.

    No-known-blocking is a scoped source observation, not complete absence.
    Registered holding rights must still be included on each subsequent session.
    Source adapters must supply active known events and explicitly unresolved cases.
    """
    date = str(bounded_date(date).date())
    if (review.get("instrument") != instrument or review.get("session") != date
            or not review.get("source") or not review.get("reviewed_sources")
            or review.get("status") not in {"no_known_blocking", "known_handled", "known_blocking", "unresolved"}):
        raise ValueError("dated known-event review required")
    coverage = dict(start=date, end=date, semantics="known_session_events", coverage_complete=False,
                    event_ids=review["event_ids"], status=review["status"], review_asof=date,
                    reviewed_sources=review["reviewed_sources"], basis=review["source"])
    return {phase: [Evidence(instrument, "events_clear", phase,
            Fact(review["status"] in {"no_known_blocking", "known_handled"}, date, date, date,
                 None, review["source"]), review["sha256"], coverage,
            phase_basis="historical_session_effective")] for phase in ("A", "C")}

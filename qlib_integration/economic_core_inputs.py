"""Source-bound, phase-separated E2 inputs. No provider, score or strategy reader."""

from copy import deepcopy
from dataclasses import dataclass, field
import math
import re

import pandas as pd

from .economic_execution_contract import bounded_date, execution_day, causal_adv20
from .economic_exchange import validate_prepared
from .economic_mvp_scope import Fact, visible_fact
from .execution_readiness import execution_state

PHASE_FIELDS = {
    "A": {"asset_id", "quote_quality", "adv20_shares", "events_clear", "state", "reference_mark", "distribution"},
    "B": {"raw_open", "open_evidence"},
    "C": {"asset_id", "events_clear", "close_mark"},
}
EVENT_FAMILIES = {"distribution", "rights", "conversion", "terminal", "identity"}


@dataclass(frozen=True)
class Evidence:
    instrument: str
    name: str
    phase: str
    fact: Fact
    sha256: str
    coverage: dict | None = None
    phase_basis: str = "source"


@dataclass
class PhaseInputs:
    date: str
    at: str
    phase: str
    facts: dict = field(default_factory=dict)
    states: dict = field(default_factory=dict)
    values: dict = field(default_factory=dict)
    distributions: dict = field(default_factory=dict)
    covered_events: dict = field(default_factory=dict)
    issues: dict = field(default_factory=dict)
    approximations: list = field(default_factory=list)


def adapt_phase(records, *, date, at, phase):
    """Reject malformed evidence per instrument; never infer absence from an empty table.

    The caller supplies only the currently available phase, not a future daily row.
    Publication assumptions must be recorded by the source, never synthesized here.
    """
    date = str(bounded_date(date).date())
    cutoff = pd.Timestamp(at)
    if phase not in PHASE_FIELDS or cutoff.tz is not None or str(cutoff.date()) != date:
        raise ValueError("phase/date boundary")
    clock = cutoff.strftime("%H:%M:%S")
    if not {"A": clock < "09:25:00", "B": "09:25:00" <= clock <= "09:30:00", "C": clock > "15:00:00"}[phase]:
        raise ValueError("phase clock boundary")
    result = PhaseInputs(date, str(cutoff), phase)
    groups, invalid = {}, set()
    for rec in records:
        if not re.fullmatch(r"(?:SH|SZ)\d{6}", rec.instrument):
            raise ValueError("invalid evidence instrument")
        try:
            if rec.phase != phase or rec.name not in PHASE_FIELDS[phase]:
                raise ValueError("field belongs to another phase or is not allowed")
            if not re.fullmatch(r"[a-f0-9]{64}", rec.sha256):
                raise ValueError("source hash missing")
            if not isinstance(rec.fact.source, str) or not rec.fact.source:
                raise ValueError("source identity missing")
            if rec.phase_basis != "source":
                # Explicit clocks for existing daily-data MVP approximations only.
                # Never reconstruct a state/announcement/rights clearance timestamp.
                permitted = {
                    "prior_session_eod": ("A", {"asset_id", "quote_quality", "adv20_shares"}),
                    "daily_open_reference": ("B", {"raw_open", "open_evidence"}),
                    "daily_close_observation": ("C", {"close_mark"}),
                }
                if rec.phase_basis not in permitted or (phase, rec.name) not in {
                    (ph, name) for ph, names in [permitted[rec.phase_basis]] for name in names
                } or rec.fact.known_at is not None:
                    raise ValueError("unsupported availability approximation")
                observed = str(bounded_date(rec.fact.observed_on).date())
                if rec.phase_basis == "prior_session_eod" and observed >= date:
                    raise ValueError("prior EOD must precede session")
                clock = {"prior_session_eod": "23:59:59", "daily_open_reference": "09:25:00", "daily_close_observation": "15:01:00"}[rec.phase_basis]
                result.approximations.append(f"{rec.instrument}:{rec.name}:{rec.phase_basis}; source_known_at=null")
                rec = Evidence(rec.instrument, rec.name, rec.phase, Fact(**{
                    **rec.fact.__dict__, "known_at": observed + " " + clock, "precision": "timestamp",
                    "source": rec.fact.source + ";MODEL_PHASE_CLOCK:" + rec.phase_basis + ";source_known_at=null",
                }), rec.sha256, rec.coverage)
            # Filter unavailable versions before inspecting their business terms.
            # A future malformed event must not become a retrospective exclusion.
            if visible_fact([rec.fact], cutoff, prior_session=rec.name in {"quote_quality", "adv20_shares"}) is None:
                result.issues.setdefault(rec.instrument, []).append(f"{rec.name}: unavailable version")
                continue
            if rec.name in {"reference_mark", "close_mark", "raw_open", "open_evidence"}:
                if rec.fact.observed_on != date:
                    raise ValueError("dated market evidence required")
            if rec.name == "events_clear":
                c = rec.coverage or {}
                if (
                    not c.get("start", "~") <= date <= c.get("end", "")
                    or set(c.get("families", ())) != EVENT_FAMILIES
                    or not isinstance(c.get("event_ids"), list)
                    or not c.get("basis")
                    or type(rec.fact.value) is not bool
                ):
                    raise ValueError("event coverage/absence semantics missing")
                if any(str(pd.Timestamp(c[k]).date()) != c[k] for k in ("start", "end")):
                    raise ValueError("invalid event coverage dates")
                if len(set(c["event_ids"])) != len(c["event_ids"]) or any(
                    not isinstance(key, str) or not key for key in c["event_ids"]
                ):
                    raise ValueError("invalid covered event identifiers")
            key = rec.name
            if key == "distribution":
                rec.fact.value.validate()
                if rec.fact.value.instrument != rec.instrument:
                    raise ValueError("event identity mismatch")
                key += ":" + rec.fact.value.event_id
            groups.setdefault((rec.instrument, key), []).append(rec)
        except (ValueError, TypeError) as exc:
            invalid.add(rec.instrument)
            result.issues.setdefault(rec.instrument, []).append(str(exc))
    for (stock, name), entries in groups.items():
        name = name.split(":", 1)[0]
        if stock in invalid:
            continue
        facts = [e.fact for e in entries]
        selected = visible_fact(facts, cutoff, prior_session=name in {"quote_quality", "adv20_shares"})
        if selected is None:
            result.issues.setdefault(stock, []).append(f"{name}: unavailable/conflicting")
            continue
        chosen = [e for e in entries if e.fact == selected]
        if name == "events_clear" and len({repr(e.coverage) for e in chosen}) != 1:
            result.issues.setdefault(stock, []).append("event coverage conflict")
            continue
        # Preserve source binding in the Fact consumed by the original scope gate.
        bound = Fact(**{**selected.__dict__, "source": f"{selected.source}#sha256={chosen[0].sha256}"})
        if name == "state":
            state = deepcopy(bound.value)
            if not isinstance(state, dict) or state.get("instrument") != stock or state.get("date") != date:
                result.issues.setdefault(stock, []).append("state identity/date mismatch")
                continue
            state.update(known_at=bound.known_at, publication_precision=bound.precision, source=bound.source)
            result.states[stock] = state
            try:
                ordinary = execution_state(state, cutoff) == "ordinary_known"
            except (ValueError, TypeError):
                ordinary = False
            result.facts.setdefault(stock, {})["voluntary_trade_ready"] = [Fact(**{**bound.__dict__, "value": ordinary})]
        elif name == "distribution":
            event = bound.value
            if event.instrument != stock or event.announced_date > str(pd.Timestamp(bound.known_at).date()):
                raise ValueError("event identity/announcement mismatch")
            result.distributions.setdefault(stock, []).append(event)
        elif name in {"raw_open", "open_evidence"}:
            result.values.setdefault(stock, {})[name] = bound.value
        else:
            target = "valuation_mark" if name in {"reference_mark", "close_mark"} else name
            result.facts.setdefault(stock, {})[target] = [bound]
            if name == "events_clear":
                result.covered_events[stock] = tuple(chosen[0].coverage["event_ids"])
    for stock, facts in result.facts.items():
        ready = facts.get("voluntary_trade_ready")
        if ready:
            adv = visible_fact(facts.get("adv20_shares", ()), cutoff, prior_session=True)
            quality = visible_fact(facts.get("quote_quality", ()), cutoff, prior_session=True)
            usable = (adv is not None and not isinstance(adv.value, bool)
                      and isinstance(adv.value, (int, float)) and math.isfinite(adv.value) and adv.value > 0
                      and quality is not None and quality.value is True)
            facts["voluntary_trade_ready"] = [Fact(**{**ready[0].__dict__, "value": bool(ready[0].value and usable)})]
    return result


def prepared_rows(before, opening, instruments, calendar):
    """Only ordinary traded objects enter legacy prepared schema; carry has no row."""
    if before.phase != "A" or opening.phase != "B" or before.date != opening.date:
        raise ValueError("prepared phases mismatch")
    if pd.Timestamp(opening.at) <= pd.Timestamp(before.at):
        raise ValueError("opening must follow frozen intents")
    days = pd.DatetimeIndex(calendar)
    day = bounded_date(before.date)
    index = days.get_loc(day)
    if index == 0 or execution_day(days[index - 1], days)[0] != day:
        raise ValueError("next-session signal missing")
    rows = []
    for stock in sorted(instruments):
        state = before.states.get(stock)
        if execution_state(state, before.at) != "ordinary_known":
            raise ValueError("nonordinary instrument cannot have a prepared trade row")
        f = before.facts.get(stock, {})
        adv = visible_fact(f.get("adv20_shares", ()), before.at, prior_session=True)
        if adv is None or isinstance(adv.value, bool) or not math.isfinite(adv.value) or adv.value <= 0:
            raise ValueError("ordinary order lacks lagged ADV")
        b = opening.values.get(stock, {})
        price = b.get("raw_open", float("nan"))
        evidence = b.get("open_evidence") is True
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            price, evidence = float("nan"), False
        rows.append(dict(
            datetime=day, instrument=stock, raw_open=price, raw_close=float("nan"),
            previous_close=state["limit_reference"], adv20_shares=float(adv.value),
            upper_limit=state["upper_limit"], lower_limit=state["lower_limit"],
            can_buy_known=not state["st"], can_sell_known=True, suspended_known=False,
            open_evidence=evidence, board=state["board"], signal_time=days[index - 1] + pd.Timedelta(hours=15),
            known_at=adv.known_at, state_known_at=state["known_at"], adv_asof=adv.observed_on,
            order_time=before.at, executable_at=opening.at, valuation_time=day + pd.Timedelta(hours=15),
            source_id=adv.source + ";" + state["source"],
        ))
    return validate_prepared(pd.DataFrame(rows)) if rows else None


def market_phase_records(daily, *, instrument, date, calendar, sha256, opening_reference=None):
    """Consume the existing sealed semantic overlay, without upgrading daily states.

    The returned market records are usable inputs, not an ordinary-regime or
    event-absence certificate. Those require separately bound Evidence records.
    """
    date = str(bounded_date(date).date())
    f = daily.copy()
    if not f.instrument.eq(instrument).all() or f.date.duplicated().any():
        raise ValueError("overlay identity or duplicate dates")
    if not f.date.map(lambda d: str(bounded_date(d).date())).eq(f.date).all():
        raise ValueError("overlay date format")
    days = pd.DatetimeIndex(calendar)
    index = days.get_loc(pd.Timestamp(date))
    prior = days[:index][-20:]
    allowed = {str(x.date()) for x in prior} | {date}
    if not set(f.date) <= allowed or len(prior) != 20:
        raise ValueError("market adapter requires bounded prior-20 plus session slice")
    f = f.set_index("date")
    prev = str(prior[-1].date())
    source = "sealed semantic daily overlay; original source timestamps not supplied"

    def rec(name, value, phase, observed, basis):
        return Evidence(instrument, name, phase, Fact(value, observed, date, date, None, source),
                        sha256, phase_basis=basis)

    result = {"A": [], "B": [], "C": []}
    if prev in f.index:
        result["A"].append(rec("quote_quality", f.loc[prev, "quote_status"] == "cross_source_agreed", "A", prev, "prior_session_eod"))
    volumes = f.raw_volume.copy()
    volumes.index = pd.to_datetime(volumes.index)
    try:
        adv = causal_adv20(volumes, days, date)
    except ValueError:
        adv = None
    if adv is not None:
        result["A"].append(rec("adv20_shares", adv, "A", prev, "prior_session_eod"))
    if date in f.index:
        row = f.loc[date]
        result["C"] = [rec("close_mark", float(row.valuation_mark), "C", date, "daily_close_observation")]
    # Semantic raw_open is filtered using later daily diagnostics: never use it
    # here. Opening input comes from a separately fixed raw source, open field only.
    if opening_reference is not None:
        if opening_reference["instrument"] != instrument or opening_reference["date"] != date:
            raise ValueError("opening reference identity/date mismatch")
        raw_open = float(opening_reference["raw_open"])
        for name, value in [("raw_open", raw_open), ("open_evidence", math.isfinite(raw_open) and raw_open > 0)]:
            result["B"].append(Evidence(instrument, name, "B",
                Fact(value, date, date, date, None, opening_reference["source"]),
                opening_reference["sha256"], phase_basis="daily_open_reference"))
    return result

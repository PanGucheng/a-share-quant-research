"""Score-blind reconciliation of sealed historical data; never an account runner."""

import hashlib
import json

import numpy as np
import pandas as pd

from .economic_execution_contract import bounded_date, dated_limit_rule, price_bounds
from .market_semantics import infer_board

QUOTE_FIELDS = ["open", "high", "low", "close", "volume", "amount"]
ENTITLEMENT_FIELDS = ["cash_div_tax", "stk_div", "pay_date", "div_listdate"]


def distribution_from_semantic(row, instrument, *, tax_policy):
    """Opt-in gross-account bridge, never silently labels gross amounts as net."""
    from .economic_event_position import Distribution

    if tax_policy != "before_dividend_income_tax" or row["status"] != "resolved_gross_entitlement":
        raise ValueError("unresolved event or unsupported income-tax basis")
    if economic_asset(instrument) != row["asset_id"]:
        raise ValueError("event identity mismatch")

    def date(value):
        return str(pd.Timestamp(value).date()) if pd.notna(value) else ""

    event = Distribution(
        event_id=row["event_id"],
        instrument=instrument,
        record_date=date(row["record_date"]),
        ex_date=date(row["ex_date"]),
        pay_date=date(row["pay_date"]),
        listable_date=date(row["listable_date"]),
        net_cash_per_share=0.0,
        gross_cash_per_share=row["gross_cash_per_share"],
        bonus_per_share=row["bonus_per_share"],
        announced_date=date(row["implementation_known_date"]),
        source=row["source_row_ids"],
        tax_policy=tax_policy,
    )
    event.validate()
    return event


def economic_asset(stock):
    return "SH601313_SH601360" if stock in ("SH601313", "SH601360") else stock


def reconcile_events(frame):
    """Collapse equivalent implemented entitlements, retaining every input row ID.

    Missing fields may be corroborated by another compatible implemented record;
    conflicting non-null values never select a winner or average quantities.
    """
    f = frame.copy().replace("", None)
    f["instrument"] = f.ts_code.str[-2:] + f.ts_code.str[:6]
    f["asset_id"] = f.instrument.map(economic_asset)
    rows = []
    for (asset, record, ex), group in f.groupby(
        ["asset_id", "record_date", "ex_date"], dropna=False, sort=True
    ):
        bounded_date(ex)
        selected = group[group.div_proc.eq("实施")]
        conflicts = []
        missing = []
        values = {}
        for col in ENTITLEMENT_FIELDS:
            distinct = selected[col].dropna().unique()
            values[col] = distinct[0] if len(distinct) == 1 else None
            if len(distinct) > 1:
                conflicts.append(col)
        if selected.empty:
            status = "not_implemented"
            known = None
        else:
            dates = selected.imp_ann_date.dropna().tolist()
            known = max(dates) if dates else None
            for col in ("cash_div_tax", "stk_div"):
                if values[col] is None:
                    missing.append(col)
                elif not np.isfinite(values[col]) or values[col] < 0:
                    conflicts.append("invalid_" + col)
            cash, bonus = values["cash_div_tax"], values["stk_div"]
            if cash is not None and cash > 0 and not values["pay_date"]:
                missing.append("pay_date")
            if bonus is not None and bonus > 0 and not values["div_listdate"]:
                missing.append("div_listdate")
            if not known or pd.isna(record) or not known <= record < ex:
                conflicts.append("announcement_record_order")
            for col in ("pay_date", "div_listdate"):
                if values[col] and values[col] < ex:
                    conflicts.append(col + "_before_ex")
            status = "unresolved" if conflicts or missing else "resolved_gross_entitlement"
        event_id = hashlib.sha256(f"{asset}|{record}|{ex}".encode()).hexdigest()[:24]
        row = dict(
            event_id=event_id,
            asset_id=asset,
            record_date=record,
            ex_date=ex,
            implementation_known_date=known,
            status=status,
            source_row_ids=json.dumps(group.source_row_id.tolist()),
            source_rows=len(group),
            implemented_rows=len(selected),
            ignored_nonimplemented_rows=len(group) - len(selected),
            conflicts="|".join(sorted(set(conflicts))),
            missing="|".join(sorted(set(missing))),
            gross_cash_per_share=values["cash_div_tax"],
            bonus_per_share=values["stk_div"],
            pay_date=values["pay_date"],
            listable_date=values["div_listdate"],
            corroborated_cash_missing_rows=int(selected.cash_div_tax.isna().sum())
            if status == "resolved_gross_entitlement"
            else 0,
            source_instruments="|".join(sorted(group.instrument.unique())),
        )
        rows.append(row)
    return pd.DataFrame(rows)


def valid_quote(frame):
    finite = np.isfinite(frame[QUOTE_FIELDS]).all(axis=1)
    positive = frame[QUOTE_FIELDS].gt(0).all(axis=1)
    ohlc = (
        frame.high.ge(frame.low)
        & frame.open.between(frame.low - 0.001, frame.high + 0.001)
        & frame.close.between(frame.low - 0.001, frame.high + 0.001)
    )
    vwap = frame.amount / frame.volume.where(frame.volume.gt(0))
    return finite & positive & ohlc & vwap.between(frame.low * 0.998, frame.high * 1.002)


def reconcile_stock(stock, quotes, source, dates, events):
    """One possible held ID, every canonical session through the boundary.

    End-of-day observations and provisional bounds are separate from preopen
    authority. Never infer delisting, cash proceeds, or new-entry permission.
    """
    for d in dates:
        bounded_date(d)
    if dates != sorted(set(dates)):
        raise ValueError("invalid held calendar")
    q = quotes.copy().reindex(dates)
    q.index.name = "date"
    if stock == "SH601313":
        q["volume"] /= 100
        q["amount"] /= 1000
    s = source.copy().reindex(dates)
    for col in QUOTE_FIELDS + ["preclose", "tradestatus", "isST"]:
        s[col] = pd.to_numeric(s[col], errors="coerce") if col in s else np.nan
    local_valid = valid_quote(q) & np.isfinite(q.factor) & q.factor.gt(0)
    source_valid = valid_quote(s)
    agreement = pd.Series(
        np.isclose(q[QUOTE_FIELDS], s[QUOTE_FIELDS], rtol=2e-5, atol=0.001).all(axis=1),
        index=q.index,
    )
    conflicting = local_valid & source_valid & ~agreement
    suspended = s.tradestatus.eq(0)
    active = s.tradestatus.eq(1)
    unknown_state = ~s.tradestatus.isin([0, 1]) | ~s.isST.isin([0, 1])
    result = pd.DataFrame(index=q.index)
    result["instrument"] = stock
    result["asset_id"] = economic_asset(stock)
    result["source"] = "baostock:" + source.attrs.get("source_hash", "synthetic")
    result["quote_source"] = "community:" + quotes.attrs.get("source_hash", "synthetic")
    result["execution_code_reference"] = stock
    if stock in ("SH601313", "SH601360"):
        result["execution_code_reference"] = np.where(
            result.index < "2018-02-28", "SH601313", "SH601360"
        )
    result["quote_status"] = "unresolved"
    result.loc[local_valid & source_valid & agreement & active, "quote_status"] = (
        "cross_source_agreed"
    )
    result.loc[~local_valid & source_valid & active, "quote_status"] = "source_only_valid_overlay"
    result.loc[local_valid & ~source_valid & active, "quote_status"] = "local_only_valid_overlay"
    result.loc[conflicting, "quote_status"] = "source_conflict"
    result.loc[suspended, "quote_status"] = "known_suspension_no_fill"
    # Missing local data can use an explicitly named valid raw vendor quote.
    usable = result.quote_status.isin(
        ["cross_source_agreed", "source_only_valid_overlay", "local_only_valid_overlay"]
    )
    for col in QUOTE_FIELDS:
        result["raw_" + col] = np.where(usable, np.where(source_valid, s[col], q[col]), np.nan)
    result["source_reference"] = s.preclose.where(s.preclose.gt(0))
    result["st_observed"] = s.isST.astype("Int64")
    result["suspended_observed"] = s.tradestatus.eq(0).where(s.tradestatus.notna())
    result["board"] = infer_board(stock)
    result["observed_status"] = np.select(
        [unknown_state, suspended, s.isST.eq(1) & active, active],
        ["unresolved", "suspended", "ST", "ordinary"],
        default="unresolved",
    )
    # Only regular-family candidate limits; actual listing/relisting/special
    # evidence and publication timing are not contained in daily vendor flags.
    ratios = []
    for d, st in zip(dates, s.isST):
        if pd.isna(st) or infer_board(stock) == "unknown":
            ratios.append(np.nan)
            continue
        board = infer_board(stock)
        try:
            ratio = dated_limit_rule(
                d, board, bool(st), 6, "registration" if board == "star" else "approval"
            )["limit_ratio"]
        except ValueError:
            ratio = np.nan
        ratios.append(ratio)
    result["regular_family_ratio"] = ratios
    limits = [
        price_bounds(ref, ratio)
        if np.isfinite(ref) and np.isfinite(ratio) and ref > 0
        else (np.nan, np.nan)
        for ref, ratio in zip(result.source_reference, ratios)
    ]
    result["provisional_lower"] = [x[0] for x in limits]
    result["provisional_upper"] = [x[1] for x in limits]
    special = (
        active
        & source_valid
        & (s.low.lt(result.provisional_lower - 0.011) | s.high.gt(result.provisional_upper + 0.011))
    )
    result.loc[special, "observed_status"] = "special_or_rule_conflict"
    result["ordinary_regime_certified"] = False
    result["known_at"] = None
    result["publication_precision"] = "unknown"
    result["state_available_phase"] = "day_end_observation_only"
    result["can_buy_preopen"] = False
    result["can_sell_preopen"] = False
    result["needs_preopen_evidence"] = True
    # A suspended source close is an explicitly supplied dated mark, not ffill.
    suspended_mark = suspended & np.isfinite(s.close) & s.close.gt(0)
    result["valuation_mark"] = result.raw_close
    result.loc[suspended_mark, "valuation_mark"] = s.loc[suspended_mark, "close"]
    result["valuation_basis"] = np.where(
        suspended_mark,
        "vendor_suspension_mark_provisional",
        np.where(usable, "raw_close", "unresolved"),
    )
    result["stale_sessions"] = result.groupby((~suspended).cumsum()).cumcount().where(suspended, 0)
    present = s.tradestatus.notna()
    tail = (
        (result.index > s[present].index.max())
        if present.any()
        else np.ones(len(result), dtype=bool)
    )
    result["terminal_candidate_gap"] = tail & unknown_state
    result["event_unresolved"] = False
    result["event_ids"] = ""
    bridges = []
    previous = (
        s.close.where(s.close.gt(0)).ffill().shift(1)
    )  # diagnostic only, never execution mark
    for e in events.itertuples():
        ex = str(pd.Timestamp(e.ex_date).date())
        record = str(pd.Timestamp(e.record_date).date()) if pd.notna(e.record_date) else ex
        if ex not in result.index or e.status == "not_implemented":
            continue
        result.loc[ex, "event_ids"] += e.event_id + "|"
        if e.status != "resolved_gross_entitlement" and record >= dates[0]:
            result.loc[result.index >= max(record, dates[0]), "event_unresolved"] = True
        ref = result.loc[ex, "source_reference"]
        prev = previous.loc[ex]
        expected = (
            (prev - e.gross_cash_per_share) / (1 + e.bonus_per_share)
            if e.status == "resolved_gross_entitlement"
            else np.nan
        )
        match = bool(np.isfinite(expected) and np.isfinite(ref) and abs(expected - ref) <= 0.015)
        bridges.append(
            dict(
                instrument=stock,
                event_id=e.event_id,
                ex_date=ex,
                reference_bridge_match=match,
                comparable=bool(np.isfinite(expected) & np.isfinite(ref)),
                expected_reference=expected,
                source_reference=ref,
            )
        )
        if np.isfinite(expected) and np.isfinite(ref) and not match and record >= dates[0]:
            result.loc[result.index >= record, "event_unresolved"] = True
    result["unexplained_reference_reset"] = (
        (previous - result.source_reference).abs().gt(0.015) & result.event_ids.eq("") & active
    )
    result["factor_change_without_event"] = (
        q.factor.div(q.factor.shift()).sub(1).abs().gt(2e-5) & result.event_ids.eq("") & active
    )
    result["account_gap"] = (
        result.valuation_mark.isna()
        | unknown_state
        | conflicting
        | result.event_unresolved
        | result.unexplained_reference_reset
    )
    result["execution_special_gap"] = special
    return result.reset_index(), pd.DataFrame(bridges)


def segments(frame, column):
    """Canonical consecutive segments retain holes, not a first/last-date hull."""
    f = frame[["date", column]].copy()
    group = f[column].ne(f[column].shift()).cumsum()
    return [
        dict(
            reason=str(g[column].iloc[0]),
            start=g.date.iloc[0],
            end=g.date.iloc[-1],
            sessions=len(g),
        )
        for _, g in f.groupby(group, sort=False)
    ]

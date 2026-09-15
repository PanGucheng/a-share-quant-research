"""One frozen target projection. A target is never an actual fill or exposure."""

import pandas as pd

from model_research.economic_prediction_structure import KEYS, START, END, require
from qlib_integration.economic_mvp_scope import Decision
from qlib_integration.economic_strategy_membership import (
    rank_scores, plan_membership, eligible_buys, confirm_membership,
)


def project(data, calendar):
    require(set(data.columns) == set(KEYS + ["score"]), "only B score/keys allowed")
    days = pd.DatetimeIndex(calendar)
    require(len(days) > 1 and days.is_unique and days.is_monotonic_increasing
            and days.min() >= START and days.max() <= END, "invalid bounded calendar")
    require(not data.duplicated(KEYS).any(), "duplicate score key")
    groups = dict(tuple(data.groupby("datetime", sort=True)))
    require(set(groups) == set(days), "missing score day; never compress calendar")
    slots, rows, spells, begins = (), [], [], {}
    for i, date in enumerate(days):
        before = {s.instrument for s in slots}
        scheduled = i > 0 and (i - 1) % 5 == 0
        buffer, backlog, target_exit = 0, 0, None
        if scheduled:
            frame = groups[days[i - 1]]
            ranked = rank_scores(list(frame[["instrument", "score"]].itertuples(index=False, name=None)))
            # Ideal target role only: these synthetic permissions are NOT E2 source evidence.
            identities = {s: s for s in ranked}
            plan = plan_membership(ranked, slots,
                {s: Decision("ALLOW_ENTRY", ("target_projection_only",)) for s in ranked[:8]},
                {s.instrument: Decision("ORDINARY_EXECUTION_CANDIDATE", ("target_only",)) for s in slots},
                identities, first_decision=i == 1)
            full = plan.sell is not None
            buys = eligible_buys(plan, slots, full_sale_confirmed=full)
            slots = confirm_membership(plan, slots, identities, full_sale_confirmed=full, bought=buys)
            buffer, backlog, target_exit = plan.buffer_retained, plan.exit_backlog, plan.sell
        after = {s.instrument for s in slots}
        for stock in before - after:
            begin = begins.pop(stock)
            spells.append(dict(instrument=stock, start=str(days[begin].date()),
                               end_exclusive=str(date.date()), sessions=i - begin, right_censored=False))
        for stock in after - before:
            begins[stock] = i
        rows.append(dict(date=str(date.date()), signal_date=str(days[i - 1].date()) if i else None,
                         scheduled=scheduled, first_decision=i == 1, target_exit=target_exit,
                         entries=sorted(after - before), exits=sorted(before - after),
                         before=sorted(before), after=sorted(after), buffer_retained=buffer,
                         exit_backlog=backlog, slots=len(after), empty_slots=8 - len(after),
                         churn_fixed_slots=(len(after - before) + len(before - after)) / 16,
                         model_boundary=i > 1 and days[i - 2].year != days[i - 1].year))
    for stock, begin in sorted(begins.items()):
        spells.append(dict(instrument=stock, start=str(days[begin].date()), end_exclusive=None,
                           sessions=len(days) - begin, right_censored=True))
    return rows, spells


def summarize(rows, spells):
    import statistics
    annual = []
    for year in sorted({r["date"][:4] for r in rows}):
        part = [r for r in rows if r["date"].startswith(year)]
        decisions = [r for r in part if r["scheduled"]]
        annual.append(dict(year=int(year), scheduled=len(decisions),
                           target_exits=sum(len(r["exits"]) for r in part),
                           target_entries=sum(len(r["entries"]) for r in part),
                           cap_backlog_decisions=sum(r["exit_backlog"] > 0 for r in decisions)))
    closed = [s["sessions"] for s in spells if not s["right_censored"]]
    noninitial = [r for r in rows if r["signal_date"] and not r["first_decision"]]
    selected = [r for r in rows if r["scheduled"]]
    retained_den = sum(len(r["before"]) for r in selected)
    longest_empty, streak = 0, 0
    for r in rows[1:]:
        streak = streak + 1 if r["empty_slots"] else 0
        longest_empty = max(longest_empty, streak)
    return dict(role="IDEAL_TARGET_PROJECTION_NOT_ACTUAL_EXPOSURE", dates=len(rows), annual=annual,
                scheduled=sum(r["scheduled"] for r in rows),
                target_closed_spells=len(closed), right_censored_spells=len(spells) - len(closed),
                target_closed_spell_mean=statistics.mean(closed) if closed else None,
                target_closed_spell_median=statistics.median(closed) if closed else None,
                target_daily_churn_ex_initial=statistics.mean(r["churn_fixed_slots"] for r in noninitial),
                buffer_retained_fraction=sum(r["buffer_retained"] for r in selected) / retained_den if retained_den else None,
                cap_backlog_decisions=sum(r["exit_backlog"] > 0 for r in selected),
                minimum_target_slots_after_initial=min(r["slots"] for r in rows[1:]),
                longest_target_underfilled_sessions=longest_empty,
                model_boundaries=sum(r["model_boundary"] for r in rows),
                actual_membership_churn=None, actual_holding_spells=None, actual_unfilled_duration=None,
                actual_blocked_exits=None, actual_cash_idle=None, actual_R1=None, actual_R2=None, actual_R3=None)

"""Predeclared portfolio parameter target diagnostics, never an execution engine."""

import math
import statistics

import pandas as pd

from .economic_prediction_structure import START, END, KEYS, require
from qlib_integration.economic_strategy_membership import rank_scores


def candidates():
    specs = [(8, 16, d, c) for d in (1, 3, 5, 10) for c in (1, 2, 4, None)]
    specs += [(8, h, 1, c) for h in (8, 12, 20) for c in (4, None)]
    specs += [(k, h, 1, c) for k, h in ((5, 8), (5, 10), (10, 15), (10, 20))
              for c in (math.ceil(k / 2), None)]
    return [dict(id=f"k{k}_h{h}_d{d}_c{c if c else 'none'}", k=k, hold=h,
                 interval=d, cap=c) for k, h, d, c in specs]


def validate_spec(spec):
    for key in ("k", "hold", "interval"):
        require(type(spec[key]) is int and spec[key] > 0, "invalid parameter")
    require(spec["hold"] >= spec["k"], "hold below entry band")
    require(spec["cap"] is None or (type(spec["cap"]) is int and 0 < spec["cap"] <= spec["k"]),
            "invalid cap")


def ranked_calendar(data, calendar):
    require(set(data.columns) == set(KEYS + ["score"]), "only closed score/keys")
    days = pd.DatetimeIndex(calendar)
    require(len(days) > 1 and days.is_unique and days.is_monotonic_increasing
            and days.min() >= START and days.max() <= END, "bounded calendar required")
    require(not data.duplicated(KEYS).any(), "duplicate score key")
    groups = dict(tuple(data.groupby("datetime", sort=True)))
    require(set(groups) == set(days), "missing score session; no calendar compression")
    return [str(d.date()) for d in days], [rank_scores(list(groups[d][["instrument", "score"]]
        .itertuples(index=False, name=None))) for d in days]


def project(days, rankings, spec):
    """All conversions idealized. No source gate, prices, shares, cash or outcomes."""
    validate_spec(spec)
    dates = pd.DatetimeIndex(days)
    require(len(days) == len(rankings) and len(days) > 1 and dates.is_unique
            and dates.is_monotonic_increasing and dates.min() >= START and dates.max() <= END,
            "invalid target calendar")
    require(all(len(r) == len(set(r)) and len(r) >= spec["k"] for r in rankings), "invalid ranking")
    k, hold, interval = (spec[key] for key in ("k", "hold", "interval"))
    cap = spec["cap"] if spec["cap"] is not None else k
    held, starts, delayed = set(), {}, {}
    rows, spells, episodes = [], [], []
    for i, date in enumerate(days):
        before = set(held)
        ranks = {s: j + 1 for j, s in enumerate(rankings[i - 1])} if i else {}
        scheduled = i > 0 and (i - 1) % interval == 0
        exits, entries, queue, buffer = [], [], [], 0
        stale = sorted(s for s in held if ranks.get(s, math.inf) > hold)
        if scheduled:
            worst = sorted(stale, key=lambda s: (-ranks.get(s, math.inf), s))
            exits = worst[:cap]
            buffer = sum(k < ranks.get(s, math.inf) <= hold for s in held)
            for stock in list(delayed):
                if stock in exits or stock not in stale:
                    begin = delayed.pop(stock)
                    episodes.append(dict(instrument=stock, start=days[begin], end=date,
                        age_sessions=i - begin, resolution="sold" if stock in exits else "recovered"))
            held.difference_update(exits)
            entries = [s for s in rankings[i - 1][:k] if s not in held][:min(k if i == 1 else cap, k - len(held))]
            held.update(entries)
            for stock in sorted(set(stale) - set(exits)):
                delayed.setdefault(stock, i)
                queue.append(dict(instrument=stock, rank=ranks.get(stock),
                                  age_sessions=i - delayed[stock]))
        for stock in sorted(before - held):
            begin = starts.pop(stock)
            spells.append(dict(instrument=stock, start=days[begin], end_exclusive=date,
                               sessions=i - begin, right_censored=False))
        for stock in sorted(held - before):
            starts[stock] = i
        rows.append(dict(date=date, scheduled=scheduled, before=sorted(before), after=sorted(held),
            entries=entries, exits=exits, buffer_retained=buffer, queue=queue,
            cap_binding=scheduled and len(stale) > cap,
            stale_after=[dict(instrument=s, rank=ranks.get(s)) for s in sorted(held)
                         if ranks.get(s, math.inf) > hold],
            churn=(len(entries) + len(exits)) / (2 * k)))
    for stock, begin in sorted(starts.items()):
        spells.append(dict(instrument=stock, start=days[begin], end_exclusive=None,
                           sessions=len(days) - begin, right_censored=True))
    for stock, begin in sorted(delayed.items()):
        episodes.append(dict(instrument=stock, start=days[begin], end=None,
                             age_sessions=len(days) - 1 - begin, resolution="right_censored"))
    return rows, spells, episodes


def distribution(values):
    values = sorted(values)
    if not values:
        return dict(n=0, mean=None, median=None, p90=None, max=None)
    return dict(n=len(values), mean=statistics.mean(values), median=statistics.median(values),
                p90=values[math.ceil(0.9 * len(values)) - 1], max=max(values))


def summarize(rows, spells, episodes, spec):
    decisions = [r for r in rows[2:] if r["scheduled"]]
    depth = [len(r["queue"]) for r in decisions]
    bound = sum(r["cap_binding"] for r in decisions)
    den = sum(len(r["before"]) for r in decisions)
    stale = [s["rank"] for r in rows[1:] for s in r["stale_after"]]
    annual = []
    for year in sorted({r["date"][:4] for r in rows}):
        part = [r for r in rows if r["date"].startswith(year)]
        ds = [r for r in decisions if r["date"].startswith(year)]
        annual.append(dict(year=int(year), decisions=sum(r["scheduled"] for r in part),
            exits=sum(len(r["exits"]) for r in part), entries=sum(len(r["entries"]) for r in part),
            cap_binding=sum(r["cap_binding"] for r in ds), subsequent_decisions=len(ds),
            target_slot_churn=sum(r["churn"] for r in part if r["date"] != rows[1]["date"])))
    streak = longest = 0
    for r in rows[1:]:
        streak = streak + 1 if len(r["after"]) < spec["k"] else 0
        longest = max(longest, streak)
    resolved = [e for e in episodes if e["resolution"] != "right_censored"]
    return dict(candidate=spec, role="IDEAL_TARGET_NOT_EXECUTABLE_ACCOUNT", sessions=len(rows),
        decisions=sum(r["scheduled"] for r in rows), subsequent_decisions=len(decisions),
        trade_decision_fraction=sum(bool(r["entries"] or r["exits"]) for r in decisions) / len(decisions) if decisions else None,
        target_exits=sum(len(r["exits"]) for r in rows),
        cap_binding_frequency=bound / len(decisions) if decisions else None,
        cap_binding_count=bound, queue_depth=distribution(depth),
        queue_age=distribution([s["age_sessions"] for r in decisions for s in r["queue"]]),
        episodes={v: sum(e["resolution"] == v for e in episodes) for v in ("sold", "recovered", "right_censored")},
        recovery_fraction_resolved=sum(e["resolution"] == "recovered" for e in resolved) / len(resolved) if resolved else None,
        max_episode_age=max((e["age_sessions"] for e in episodes), default=None),
        stale_rank=distribution([x for x in stale if x is not None]), stale_absent_observations=stale.count(None),
        buffer_fraction=sum(r["buffer_retained"] for r in decisions) / den if den else None,
        closed_holding_sessions=distribution([s["sessions"] for s in spells if not s["right_censored"]]),
        right_censored_spells=sum(s["right_censored"] for s in spells),
        target_daily_churn_ex_initial=statistics.mean(r["churn"] for r in rows[2:]) if len(rows) > 2 else None,
        min_target_slots=min(len(r["after"]) for r in rows[1:]), longest_target_underfill=longest,
        annual=annual, flags=["PERSISTENT_CAP_BACKLOG"] if decisions and bound / len(decisions) >= 0.8 else [],
        economic_eligible=True, actual_path_status="NOT_STARTED", actual_R1=None, actual_R2=None, actual_R3=None,
        actual_cash_idle=None, actual_turnover=None, economic_metrics=None)


def adjacency(specs):
    edges = []
    keys = ("k", "hold", "interval", "cap")
    for i, a in enumerate(specs):
        for b in specs[i + 1:]:
            changed = [key for key in keys if a[key] != b[key]]
            if len(changed) != 1:
                continue
            key = changed[0]
            def value(x):
                return math.inf if x[key] is None else x[key]
            low, high = sorted((value(a), value(b)))
            if not any(all(c[j] == a[j] for j in keys if j != key) and low < value(c) < high for c in specs):
                edges.append(dict(a=a["id"], b=b["id"], dimension=key))
    return edges

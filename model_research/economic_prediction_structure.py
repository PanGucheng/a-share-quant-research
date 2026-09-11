"""E1: B494 scores/keys only. No market, label, strategy or evaluation imports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "reports/economic_translation_mvp/e1_inputs.json"
LAGS = (1, 2, 5, 10, 20)
MIGRATION_LAGS = (1, 5, 10, 20)
PCTS = (5, 10, 20)
KEYS = ["datetime", "instrument"]
START, END = pd.Timestamp("2015-01-01"), pd.Timestamp("2023-12-29")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def require(ok, message):
    if not ok:
        raise ValueError(message)


class BoundedScores:
    """A closed table inventory, not an arbitrary-path Parquet reader.

    Hash reads are permitted only for fixed, exclusively development B/keys files.
    Parquet materialization projects the allowlisted columns; no broad provider.
    """

    def __init__(self, root=ROOT, inventory=INPUTS, audit=None):
        self.root = Path(root).resolve()
        self.inventory = json.loads(Path(inventory).read_text(encoding="utf-8"))
        self.audit = audit if audit is not None else []
        require(self.inventory["role"] == "E1_B_scores_keys_only", "wrong access role")
        self.calendar = pd.DatetimeIndex(self.inventory["calendar"])
        require(
            self.calendar.is_unique
            and self.calendar.is_monotonic_increasing
            and len(self.calendar) > 0
            and self.calendar.min() >= START
            and self.calendar.max() <= END,
            "calendar boundary/integrity",
        )

    def read(self, year, kind):
        require(kind in ("scores", "keys") and year in range(2015, 2024), "E1 access denied")
        record = self.inventory["folds"][str(year)][kind]
        expected = (
            f"outputs/research_protocol_v3_precompute/v3_precompute_broad494_strict332_20260909_v1/"
            f"Broad494/annual_{year}/engineering_predictions.parquet"
            if kind == "scores"
            else f"outputs/research_protocol_v3_mvp/v3_recompute_audit_20260909_v1/audit/{year}/keys.parquet"
        )
        require(record["path"] == expected, "not a fixed B/keys path")
        path = (self.root / expected).resolve()
        require(path.is_relative_to(self.root), "path escapes root")
        columns = KEYS + (["score"] if kind == "scores" else [])
        self.audit.append(
            dict(
                role="E1",
                operation="request",
                path=expected,
                columns=columns,
                start=f"{year}-01-01",
                end=min(f"{year}-12-31", "2023-12-29"),
            )
        )
        require(sha(path) == record["sha256"], "sealed input bytes changed")
        table = pq.read_table(
            path,
            columns=columns,
            filters=[
                ("datetime", ">=", pd.Timestamp(f"{year}-01-01")),
                ("datetime", "<=", min(pd.Timestamp(f"{year}-12-31"), END)),
            ],
        )
        frame = table.to_pandas()
        require(len(frame) == record["rows"], "unexpected rows or out-of-bound source rows")
        require(
            not frame[KEYS].isna().any().any() and not frame.duplicated(KEYS).any(), "invalid keys"
        )
        require(frame.datetime.isin(self.calendar).all(), "off-calendar score")
        self.audit.append(dict(role="E1", operation="complete", path=expected, rows=len(frame)))
        return frame.sort_values(KEYS).reset_index(drop=True)

    def load(self):
        frames = []
        for year in range(2015, 2024):
            scores, keys = self.read(year, "scores"), self.read(year, "keys")
            pd.testing.assert_frame_equal(scores[KEYS], keys, check_dtype=False)
            frames.append(scores)
        data = pd.concat(frames, ignore_index=True)
        require(
            pd.DatetimeIndex(data.datetime.unique()).equals(self.calendar), "missing scheduled date"
        )
        return data


def era(year):
    return "2015-17" if year <= 2017 else "2018-20" if year <= 2020 else "2021-23"


def rank_day(frame):
    require(set(frame.columns) == set(KEYS + ["score"]), "only score and keys accepted")
    require(not frame.duplicated(KEYS).any(), "duplicate score key")
    series = frame.set_index("instrument").score.astype("float64")
    require(np.isfinite(series).all(), "sealed finite-score integrity failure")
    require(len(series) >= 2 and series.nunique() > 1, "unscoreable ranking")
    # Stable ID tie-break for selection, averaged ties for correlations.
    ordered = series.sort_index().sort_values(ascending=False, kind="stable").index.tolist()
    ranks = series.rank(ascending=False, method="average")
    percentile = (ranks - 0.5) / len(series)
    sets = {p: set(ordered[: int(np.ceil(p * len(series) / 100))]) for p in PCTS}
    return series, percentile, ordered, sets


def overlap(previous, current):
    both = len(previous & current)
    return dict(
        previous_n=len(previous),
        current_n=len(current),
        retained=both,
        entries=len(current - previous),
        exits=len(previous - current),
        retention=both / len(previous) if previous else np.nan,
        entry_rate=len(current - previous) / len(current) if current else np.nan,
        exit_rate=len(previous - current) / len(previous) if previous else np.nan,
        jaccard=both / len(previous | current) if previous | current else np.nan,
    )


def membership_churn(previous, current):
    return 0.5 * sum(
        abs((1 / len(current) if s in current else 0) - (1 / len(previous) if s in previous else 0))
        for s in previous | current
    )


def study(data, calendar):
    """Pure structural computation; its only numeric input is score."""
    require(set(data.columns) == set(KEYS + ["score"]), "E1 rejects economic columns")
    calendar = pd.DatetimeIndex(calendar)
    require(
        calendar.is_unique
        and calendar.is_monotonic_increasing
        and calendar.min() >= START
        and calendar.max() <= END,
        "calendar boundary",
    )
    grouped = dict(tuple(data.groupby("datetime", sort=True)))
    require(set(grouped) == set(calendar), "missing/extra trading date; never compress gaps")
    days, ranks, members, migrations, turnover, ages, spells = [], [], [], [], [], [], []
    history, states = [], {"top5": set(), "top10": set(), "top20": set(), "buffer10_20": set()}
    starts = {name: {} for name in states}
    for i, date in enumerate(calendar):
        score, pct, ordered, top = rank_day(grouped[date])
        stamp = dict(datetime=date, year=date.year, era=era(date.year))
        days.append(
            dict(
                **stamp,
                candidates=len(score),
                finite=len(score),
                tie_fraction=1 - score.nunique() / len(score),
                model_switch=i > 0 and calendar[i - 1].year != date.year,
            )
        )
        for lag in LAGS:
            if i < lag:
                continue
            prev_score, prev_pct, _, prev_top = history[i - lag]
            ids = score.index.intersection(prev_score.index).sort_values()
            cross = calendar[i - lag].year != date.year
            # Spearman re-ranks on the intersection, distinct from full-day percentiles.
            x, y = prev_score.loc[ids].rank(), score.loc[ids].rank()
            valid = len(ids) >= 100 and x.nunique() > 1 and y.nunique() > 1
            ranks.append(
                dict(
                    **stamp,
                    previous_date=calendar[i - lag],
                    lag=lag,
                    cross_model=cross,
                    pairs=len(ids),
                    scoreable=valid,
                    spearman=x.corr(y) if valid else np.nan,
                    full_pool_percentile_pearson=prev_pct.loc[ids].corr(pct.loc[ids])
                    if valid
                    else np.nan,
                    universe_entries=len(score.index.difference(prev_score.index)),
                    universe_exits=len(prev_score.index.difference(score.index)),
                )
            )
            for p in PCTS:
                members.append(
                    dict(
                        **stamp,
                        lag=lag,
                        percent=p,
                        role="primary" if p == 10 else "context_only",
                        cross_model=cross,
                        **overlap(prev_top[p], top[p]),
                    )
                )
            if lag in MIGRATION_LAGS:
                base = prev_top[10]
                counts = {
                    "top10": len(base & top[10]),
                    "top10_20": len(base & (top[20] - top[10])),
                    "outside_top20": len((base & set(score.index)) - top[20]),
                    "absent": len(base - set(score.index)),
                }
                require(sum(counts.values()) == len(base), "migration conservation")
                migrations.extend(
                    dict(
                        **stamp,
                        lag=lag,
                        destination=k,
                        count=v,
                        denominator=len(base),
                        fraction=v / len(base),
                        cross_model=cross,
                    )
                    for k, v in counts.items()
                )
        k = len(top[10])
        kept = states["buffer10_20"] & top[20]
        # Capacity contraction exception is fixed worst-rank removal, never search.
        kept = set([s for s in ordered if s in kept][:k])
        new = [s for s in ordered if s in top[10] and s not in kept][: max(0, k - len(kept))]
        now = {"top5": top[5], "top10": top[10], "top20": top[20], "buffer10_20": kept | set(new)}
        for name, current in now.items():
            previous = states[name]
            for s in previous - current:
                begin = starts[name].pop(s)
                spells.append(
                    dict(
                        series=name,
                        instrument=s,
                        entry_date=calendar[begin],
                        last_member_date=calendar[i - 1],
                        exit_date=date,
                        duration=i - begin,
                        right_censored=False,
                        left_boundary=begin == 0,
                    )
                )
            for s in current - previous:
                starts[name][s] = i
            duration = [i - starts[name][s] + 1 for s in current]
            ages.append(
                dict(
                    **stamp,
                    series=name,
                    members=len(current),
                    age_mean=float(np.mean(duration)),
                    age_median=float(np.median(duration)),
                    age_max=max(duration),
                )
            )
            if name in ("top10", "buffer10_20"):
                turnover.append(
                    dict(
                        **stamp,
                        series=name,
                        cold_start=i == 0,
                        target_slots=k,
                        membership_churn=membership_churn(previous, current),
                        **overlap(previous, current),
                    )
                )
        states = now
        history.append((score, pct, ordered, top))
    for name, current in states.items():
        for s in sorted(current):
            begin = starts[name][s]
            spells.append(
                dict(
                    series=name,
                    instrument=s,
                    entry_date=calendar[begin],
                    last_member_date=calendar[-1],
                    exit_date=pd.NaT,
                    duration=len(calendar) - begin,
                    right_censored=True,
                    left_boundary=begin == 0,
                )
            )
    result = {
        name: pd.DataFrame(rows)
        for name, rows in dict(
            daily=days,
            rank_lags=ranks,
            membership=members,
            migration=migrations,
            turnover=turnover,
            ages=ages,
            spells=spells,
        ).items()
    }
    result["spells"] = (
        result["spells"].sort_values(["series", "entry_date", "instrument"]).reset_index(drop=True)
    )
    return result


def summarize(tables):
    rows = []
    for name in ("rank_lags", "membership", "migration", "turnover", "ages"):
        frame = tables[name]
        groups = {
            "rank_lags": ["lag", "cross_model"],
            "membership": ["percent", "lag"],
            "migration": ["lag", "destination"],
            "turnover": ["series", "cold_start"],
            "ages": ["series"],
        }[name]
        metrics = {
            "rank_lags": ["spearman", "pairs", "full_pool_percentile_pearson"],
            "membership": ["retention", "entry_rate", "exit_rate", "jaccard"],
            "migration": ["fraction"],
            "turnover": ["membership_churn", "entries", "exits", "retention"],
            "ages": ["age_mean", "age_median", "age_max"],
        }[name]
        if frame.empty:
            continue
        for scope, part in (
            [("all", frame)]
            + [(f"year:{k}", g) for k, g in frame.groupby("year")]
            + [(f"era:{k}", g) for k, g in frame.groupby("era")]
        ):
            for key, group in part.groupby(groups, dropna=False):
                for metric in metrics:
                    values = group[metric].dropna()
                    rows.append(
                        dict(
                            table=name,
                            scope=scope,
                            group=str(key),
                            metric=metric,
                            observations=len(values),
                            possible=len(group),
                            mean=values.mean(),
                            median=values.median(),
                            p10=values.quantile(0.1),
                            p90=values.quantile(0.9),
                        )
                    )
    for name, frame in tables["spells"].groupby("series"):
        for censor, group in frame.groupby("right_censored"):
            values = group.duration
            rows.append(
                dict(
                    table="spells",
                    scope="all",
                    group=f"{name};right_censored={censor}",
                    metric="observed_duration",
                    observations=len(values),
                    possible=len(values),
                    mean=values.mean(),
                    median=values.median(),
                    p10=values.quantile(0.1),
                    p90=values.quantile(0.9),
                )
            )
    return pd.DataFrame(rows)


def independent_verify(data, calendar, tables):
    """Independent replay: pandas Spearman + scalar set/state reconstruction.

    Does not call rank_day, study, overlap or membership_churn.
    Checks every scheduled rank lag, migration and membership transition.
    """
    lookup, sets, full_percentiles = {}, {}, {}
    for date, frame in data.groupby("datetime"):
        s = frame.set_index("instrument").score
        lookup[date] = s
        full_percentiles[date] = (s.rank(ascending=False, method="average") - 0.5) / len(s)
        ordered = sorted(s.index, key=lambda x: (-s[x], x))
        sets[date] = {p: set(ordered[: int(np.ceil(len(s) * p / 100))]) for p in PCTS}
    calendar = list(pd.DatetimeIndex(calendar))
    expected_pairs = sum(max(0, len(calendar) - lag) for lag in LAGS)
    require(
        len(tables["rank_lags"]) == expected_pairs
        and len(tables["membership"]) == 3 * expected_pairs,
        "independent scheduled pair coverage",
    )
    require(
        len(tables["migration"]) == 4 * sum(max(0, len(calendar) - lag) for lag in MIGRATION_LAGS),
        "migration row coverage",
    )
    require(
        len(tables["turnover"]) == 2 * len(calendar) and len(tables["daily"]) == len(calendar),
        "daily row coverage",
    )
    max_error = 0.0
    expected_schedule = {
        (calendar[i], calendar[i - lag], lag) for lag in LAGS for i in range(lag, len(calendar))
    }
    require(
        set(
            tables["rank_lags"][["datetime", "previous_date", "lag"]].itertuples(
                index=False, name=None
            )
        )
        == expected_schedule,
        "independent rank date schedule",
    )
    for row in tables["rank_lags"].itertuples():
        left, right = lookup[row.previous_date], lookup[row.datetime]
        merged = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
        require(len(merged) == row.pairs, "independent pair count")
        valid = len(merged) >= 100 and merged.left.nunique() > 1 and merged.right.nunique() > 1
        require(bool(row.scoreable) == valid, "independent scoreability")
        if row.scoreable:
            expected = merged.left.corr(merged.right, method="spearman")
            max_error = max(max_error, abs(row.spearman - expected))
            require(np.isclose(row.spearman, expected, atol=2e-12, rtol=0), "independent Spearman")
            expected_full = (
                full_percentiles[row.previous_date]
                .loc[merged.index]
                .corr(full_percentiles[row.datetime].loc[merged.index])
            )
            require(
                np.isclose(row.full_pool_percentile_pearson, expected_full, atol=2e-12, rtol=0),
                "independent full-pool percentile correlation",
            )
        else:
            require(
                pd.isna(row.spearman) and pd.isna(row.full_pool_percentile_pearson),
                "unscoreable correlation must remain missing",
            )
    calendar = list(pd.DatetimeIndex(calendar))
    index = {d: i for i, d in enumerate(calendar)}
    for row in tables["membership"].itertuples():
        prior, current = (
            sets[calendar[index[row.datetime] - row.lag]][row.percent],
            sets[row.datetime][row.percent],
        )
        require(
            row.retained == len(prior.intersection(current))
            and row.entries == len(current - prior)
            and row.exits == len(prior - current),
            "independent membership",
        )
        for actual, expected in [
            (row.retention, len(prior & current) / len(prior)),
            (row.entry_rate, len(current - prior) / len(current)),
            (row.exit_rate, len(prior - current) / len(prior)),
            (row.jaccard, len(prior & current) / len(prior | current)),
        ]:
            require(abs(actual - expected) < 2e-12, "independent membership rate")
    for row in tables["migration"].itertuples():
        prior = sets[calendar[index[row.datetime] - row.lag]][10]
        now = sets[row.datetime]
        counts = dict(top10=0, top10_20=0, outside_top20=0, absent=0)
        for stock in prior:
            state = (
                "absent"
                if stock not in lookup[row.datetime].index
                else "top10"
                if stock in now[10]
                else "top10_20"
                if stock in now[20]
                else "outside_top20"
            )
            counts[state] += 1
        require(
            counts[row.destination] == row.count
            and row.denominator == len(prior)
            and abs(row.fraction - row.count / len(prior)) < 2e-12,
            "independent migration",
        )
    buffer = set()
    replay_members = {f"top{p}": [sets[d][p] for d in calendar] for p in PCTS}
    replay_members["buffer10_20"] = []
    for row in tables["turnover"].itertuples():
        i = index[row.datetime]
        current_top = sets[row.datetime][10]
        if row.series == "top10":
            prev = sets[calendar[i - 1]][10] if i else set()
            now = current_top
        else:
            prev = buffer.copy()
            score = lookup[row.datetime]
            retained = sorted(buffer & sets[row.datetime][20], key=lambda x: (-score[x], x))[
                : len(current_top)
            ]
            now = set(retained)
            for stock in sorted(current_top, key=lambda x: (-score[x], x)):
                if len(now) < len(current_top):
                    now.add(stock)
            buffer = now.copy()
            replay_members["buffer10_20"].append(now.copy())
        require(
            row.entries == len(now - prev)
            and row.exits == len(prev - now)
            and row.current_n == len(now),
            "independent state machine",
        )
        expected = (
            sum(
                abs(
                    (int(s in now) / len(now) if now else 0)
                    - (int(s in prev) / len(prev) if prev else 0)
                )
                for s in now | prev
            )
            / 2
        )
        require(abs(expected - row.membership_churn) < 2e-12, "independent churn")
    # Independent contiguous-spell replay, including IDs, dates and both boundaries.
    replay_spells = []
    for name, sequence in replay_members.items():
        active = {}
        for i, current in enumerate(sequence + [set()]):
            for stock in list(active):
                if stock not in current:
                    begin = active.pop(stock)
                    replay_spells.append(
                        dict(
                            series=name,
                            instrument=stock,
                            entry_date=calendar[begin],
                            last_member_date=calendar[i - 1],
                            exit_date=calendar[i] if i < len(calendar) else pd.NaT,
                            duration=i - begin,
                            right_censored=i == len(calendar),
                            left_boundary=begin == 0,
                        )
                    )
            for stock in current:
                active.setdefault(stock, i)
            if i < len(calendar):
                ages = [i - active[s] + 1 for s in current]
                row = tables["ages"].loc[
                    (tables["ages"].series == name) & (tables["ages"].datetime == calendar[i])
                ]
                require(
                    len(row) == 1 and row.iloc[0].members == len(current),
                    "independent age coverage",
                )
                require(
                    abs(row.iloc[0].age_mean - np.mean(ages)) < 2e-12
                    and row.iloc[0].age_median == np.median(ages)
                    and row.iloc[0].age_max == max(ages),
                    "independent membership age",
                )
    expected = (
        pd.DataFrame(replay_spells)
        .sort_values(["series", "entry_date", "instrument"])
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(tables["spells"], expected, check_dtype=False)
    # Every observed member-day must belong to exactly one contiguous spell.
    member_days = tables["ages"].groupby("series").members.sum().to_dict()
    for name, group in tables["spells"].groupby("series"):
        require(group.duration.sum() == member_days[name], "spell/member-day conservation")
    return dict(
        status="verified",
        rank_pairs=len(tables["rank_lags"]),
        max_spearman_error=max_error,
        membership_rows=len(tables["membership"]),
        migration_rows=len(tables["migration"]),
        transitions=len(tables["turnover"]),
        economic_values_read=False,
    )

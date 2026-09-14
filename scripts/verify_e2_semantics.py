"""Independent closed-file verification; no reconciliation/collection imports."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import socket

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/economic_translation_mvp/e2_semantic_v1"
BASE = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify():
    def denied(*args, **kwargs):
        raise RuntimeError("independent verification is offline")

    socket.socket.connect = denied
    receipt = read_json(OUT / "receipt.json")
    for name, expected in receipt.items():
        path = (OUT / name).resolve()
        assert path.is_relative_to(OUT.resolve()) and digest(path) == expected, name
    inputs = read_json(OUT / "input_hashes.json")
    for name, expected in inputs.items():
        path = (BASE / name).resolve()
        assert path.is_relative_to(BASE.resolve()) and digest(path) == expected, name
    run_scope = read_json(OUT / "scope.json")
    for name, expected in run_scope["code_lf"].items():
        assert (
            hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            == expected
        )
    scope = read_json(BASE / "full_quotes/scope.json")
    summary = read_json(OUT / "summary.json")
    stocks = pd.read_csv(OUT / "stock_summary.csv")
    assert set(stocks.instrument) == set(scope["starts"]) and len(stocks) == 4416
    assert len(list((OUT / "daily").glob("*.parquet"))) == 4416
    raw = pd.read_parquet(OUT / "event_source_versions.parquet")
    events = pd.read_parquet(OUT / "events.parquet")
    assert len(raw) == 28681 and raw.source_row_id.is_unique and events.event_id.is_unique
    by_id = raw.set_index("source_row_id")
    used = []
    for e in events.itertuples():
        ids = json.loads(e.source_row_ids)
        used.extend(ids)
        original = by_id.loc[ids]
        assert len(original) == e.source_rows
        assert original.record_date.eq(e.record_date).all() and original.ex_date.eq(e.ex_date).all()
        selected = original[original.div_proc.eq("实施")]
        assert len(selected) == e.implemented_rows
        assert len(original) - len(selected) == e.ignored_nonimplemented_rows
        if e.status == "resolved_gross_entitlement":
            assert len(selected) and e.implementation_known_date <= e.record_date < e.ex_date
            for source, target in [
                ("cash_div_tax", "gross_cash_per_share"),
                ("stk_div", "bonus_per_share"),
            ]:
                values = selected[source].dropna().unique()
                assert len(values) == 1 and values[0] == getattr(e, target) and values[0] >= 0
            if e.gross_cash_per_share > 0:
                assert e.pay_date >= e.ex_date
            if e.bonus_per_share > 0:
                assert e.listable_date >= e.ex_date
    assert Counter(used) == Counter(raw.source_row_id), "lost or duplicated source versions"
    # Count the original differing-content groups independently of output grouping.
    original_columns = [c for c in raw if c != "source_row_id"]
    differing = []
    for key, g in raw.groupby(["ts_code", "record_date", "ex_date"], dropna=False):
        if len(g) > 1 and len(g[original_columns].drop_duplicates()) > 1:
            instrument = key[0][-2:] + key[0][:6]
            asset = "SH601313_SH601360" if instrument in ("SH601313", "SH601360") else instrument
            row = events[
                (events.asset_id == asset)
                & (events.record_date == key[1])
                & (events.ex_date == key[2])
            ]
            assert len(row) == 1
            differing.append(
                dict(
                    instrument=instrument,
                    record_date=key[1],
                    ex_date=key[2],
                    status=row.status.iloc[0],
                )
            )
    assert len(differing) == 682
    quote_counts, gap_counts, state_counts = Counter(), Counter(), Counter()
    sample_rows, issues, special_rows = [], [], []
    sessions = 0
    segments = pd.read_parquet(OUT / "segments.parquet")
    grouped_segments = {k: g for k, g in segments.groupby("instrument")}
    selected_ids = {"SH601313", "SH601360", *sorted(scope["starts"])[::400]}
    for i, stock in enumerate(sorted(scope["starts"])):
        f = pd.read_parquet(OUT / f"daily/{stock}.parquet")
        dates = [d for d in scope["days"] if d >= scope["starts"][stock]]
        assert f.date.tolist() == dates and f.instrument.eq(stock).all()
        assert f.date.between("2015-01-05", "2023-12-29").all()
        assert not f.can_buy_preopen.any() and not f.can_sell_preopen.any()
        assert not f.ordinary_regime_certified.any() and f.known_at.isna().all()
        unknown = f.observed_status.eq("unresolved")
        assert f.loc[unknown | f.valuation_mark.isna(), "account_gap"].all()
        assert f.loc[f.quote_status.eq("source_conflict"), "raw_close"].isna().all()
        for kind, seg in grouped_segments[stock].groupby("kind"):
            position = 0
            for s in seg.itertuples():
                part = f.iloc[position : position + s.sessions]
                assert (
                    len(part) == s.sessions
                    and part.date.iloc[0] == s.start
                    and part.date.iloc[-1] == s.end
                )
                assert part[kind].astype(str).eq(s.reason).all()
                position += s.sessions
            assert position == len(f)
        sessions += len(f)
        quote_counts.update(f.quote_status.value_counts().to_dict())
        state_counts.update(f.observed_status.value_counts().to_dict())
        for col in summary["gap_counts"]:
            gap_counts[col] += int(f[col].sum())
            assert int(f[col].sum()) == int(stocks.loc[stocks.instrument.eq(stock), col].iloc[0])
        anomaly = (
            f.quote_status.isin(
                [
                    "source_conflict",
                    "unresolved",
                    "local_only_valid_overlay",
                    "source_only_valid_overlay",
                ]
            )
            | f.unexplained_reference_reset
        )
        if anomaly.any():
            issues.append(
                f.loc[
                    anomaly,
                    [
                        "instrument",
                        "date",
                        "quote_status",
                        "observed_status",
                        "terminal_candidate_gap",
                        "unexplained_reference_reset",
                    ],
                ]
            )
        if f.execution_special_gap.any():
            special_rows.append(
                f.loc[
                    f.execution_special_gap,
                    [
                        "instrument",
                        "date",
                        "raw_low",
                        "raw_high",
                        "source_reference",
                        "provisional_lower",
                        "provisional_upper",
                    ],
                ]
            )
        if stock in selected_ids:
            # Direct source comparison, without production helpers or adapters.
            q = pd.read_parquet(BASE / f"full_quotes/{stock}.parquet")
            chosen = f[f.quote_status.eq("cross_source_agreed")].iloc[::97]
            for row in chosen.itertuples():
                native = q.loc[row.date]
                for col in ("open", "high", "low", "close", "volume", "amount"):
                    expected = native[col]
                    if stock == "SH601313" and col in ("volume", "amount"):
                        expected /= 100 if col == "volume" else 1000
                    assert np.isclose(expected, getattr(row, "raw_" + col), rtol=2e-5, atol=0.001)
                sample_rows.append((stock, row.date))
        if i % 600 == 0:
            print(f"independent closed-file verification {i + 1}/4416", flush=True)
    assert sessions == summary["sessions"] == 7429962
    assert (
        dict(quote_counts) == summary["quote_status"] and dict(gap_counts) == summary["gap_counts"]
    )
    assets = set(scope["starts"]) - {"SH601313", "SH601360"} | {"SH601313_SH601360"}
    candidate = events[events.asset_id.isin(assets)]
    unresolved = candidate[candidate.status.eq("unresolved")]
    resolved = candidate[candidate.status.eq("resolved_gross_entitlement")]
    fractional = resolved[
        (resolved.bonus_per_share * 100 - (resolved.bonus_per_share * 100).round()).abs().gt(1e-8)
    ]
    bridge = pd.read_parquet(OUT / "event_reference_bridges.parquet")
    comparable = bridge[bridge.comparable]
    expected_matches = (comparable.expected_reference - comparable.source_reference).abs().le(0.015)
    assert np.array_equal(expected_matches.to_numpy(), comparable.reference_bridge_match.to_numpy())
    verification = dict(
        status="PASS",
        production_receipt_sha256=digest(OUT / "receipt.json"),
        bound_input_files=len(inputs),
        bound_output_files=len(receipt),
        exact_calendar_sessions=sessions,
        quote_status=dict(quote_counts),
        observed_status=dict(state_counts),
        independent_quote_sample_rows=len(sample_rows),
        independent_quote_sample_stocks=len(selected_ids),
        source_versions_preserved=len(used),
        differing_duplicate_groups=len(differing),
        differing_duplicate_group_status=dict(Counter(r["status"] for r in differing)),
        nonimplemented_versions=int(events.ignored_nonimplemented_rows.sum()),
        candidate_unresolved_events=len(unresolved),
        candidate_unresolved_assets=int(unresolved.asset_id.nunique()),
        candidate_corroborated_cash_missing_rows=int(
            candidate.corroborated_cash_missing_rows.sum()
        ),
        candidate_missing_cash_events=int(unresolved["missing"].str.contains("cash_div_tax").sum()),
        candidate_missing_listable_events=int(
            unresolved["missing"].str.contains("div_listdate").sum()
        ),
        candidate_fractional_bonus_per_100_events=len(fractional),
        candidate_fractional_bonus_per_100_assets=int(fractional.asset_id.nunique()),
        comparable_reference_bridges=len(comparable),
        reference_bridge_mismatches=int((~expected_matches).sum()),
        reference_bridge_uncomparable=int((~bridge.comparable).sum()),
        special_limit_stock_days=sum(len(f) for f in special_rows),
        research_values_after_2023=False,
        scores_read=False,
        account_or_outcomes_run=False,
        e2_status="E2 STILL BLOCKED",
    )
    dest = OUT / "independent_verification"
    dest.mkdir(exist_ok=False)
    pd.DataFrame(differing).to_csv(dest / "duplicate_groups.csv", index=False)
    unresolved.to_csv(dest / "unresolved_candidate_events.csv", index=False)
    fractional.to_csv(dest / "fractional_bonus_terms.csv", index=False)
    pd.concat(issues, ignore_index=True).to_parquet(
        dest / "quote_state_issues.parquet", index=False
    )
    pd.concat(special_rows, ignore_index=True).to_csv(dest / "special_limit_days.csv", index=False)
    bridge[bridge.comparable & ~bridge.reference_bridge_match].to_csv(
        dest / "reference_bridge_mismatches.csv", index=False
    )
    (dest / "verification.json").write_text(
        json.dumps(verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    hashes = {p.name: digest(p) for p in dest.iterdir() if p.is_file()}
    hashes["verifier_code_lf"] = hashlib.sha256(
        Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    (dest / "receipt.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verification, indent=2), flush=True)


if __name__ == "__main__":
    verify()

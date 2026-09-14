# ruff: noqa: E402
"""Offline semantic reconciliation only. Never invokes collection or backtests."""

from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from qlib_integration.economic_semantic_reconciliation import (
    economic_asset,
    reconcile_events,
    reconcile_stock,
    segments,
)

BASE = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


class SealedInputs:
    def __init__(self, base):
        self.base = base.resolve()
        self.access = {}
        self.scope = self.read_json(base / "full_quotes/scope.json")
        assert self.scope["days"][0] == "2015-01-05" and self.scope["days"][-1] == "2023-12-29"
        self.refs = {}
        for mode in ("states", "dividends"):
            summary = self.read_json(base / f"recovery_{mode}_v1/complete.json")
            parent = self.read_json(base / f"full_{mode}/scope.json")
            assert parent["days"] == self.scope["days"] and parent["starts"] == self.scope["starts"]
            expected = self.scope["starts"] if mode == "states" else self.scope["days"]
            assert set(summary["references"]) == set(expected)
            self.refs[mode] = summary["references"]
        quotes = self.read_json(base / "full_quotes/complete.json")
        assert quotes["chunks"] == len(self.scope["starts"]) == 4416

    def read_json(self, path):
        path = path.resolve()
        if not path.is_relative_to(self.base):
            raise ValueError("unapproved input path")
        self.access[str(path.relative_to(self.base))] = sha(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def frame(self, mode, key):
        if mode == "quotes":
            if key not in self.scope["starts"]:
                raise ValueError("unapproved quote ID")
            path = self.base / f"full_quotes/{key}.json"
        else:
            ref = self.refs[mode][key]
            path = self.base / ref["path"]
            if sha(path) != ref["sha256"]:
                raise ValueError("receipt changed")
        receipt = self.read_json(path)
        if receipt["status"] != "complete":
            raise ValueError("incomplete input")
        parquet = []
        for name, digest in receipt["files"].items():
            if Path(name).name != name:
                raise ValueError("unsafe receipt filename")
            p = path.parent / name
            if sha(p) != digest:
                raise ValueError("input data changed")
            self.access[str(p.relative_to(self.base))] = digest
            if p.suffix == ".parquet":
                parquet.append(p)
        if len(parquet) != 1:
            raise ValueError("ambiguous sealed data")
        # Only these already sealed, date-bounded scan outputs are loadable.
        f = pd.read_parquet(parquet[0])
        assert len(f) == receipt["rows"]
        if mode == "quotes":
            assert f.index.tolist() == [
                d for d in self.scope["days"] if d >= self.scope["starts"][key]
            ]
            assert f.instrument.eq(key).all()
        elif mode == "states" and len(f):
            assert (
                f.date.between(self.scope["starts"][key], "2023-12-29").all()
                and not f.date.duplicated().any()
            )
            assert f.code.eq(key[:2].lower() + "." + key[2:]).all() and f.adjustflag.eq("3").all()
        elif mode == "dividends" and len(f):
            assert f.ex_date.eq(key.replace("-", "")).all()
        f.attrs["source_hash"] = receipt["files"][parquet[0].name]
        return f


def run(canary=False):
    def denied(*args, **kwargs):
        raise RuntimeError("offline reconciliation forbids network")

    socket.socket.connect = denied
    source = SealedInputs(BASE)
    out = (
        ROOT
        / "outputs/economic_translation_mvp"
        / ("e2_semantic_canary_v2" if canary else "e2_semantic_v1")
    )
    out.mkdir(exist_ok=False)
    code = [
        "scripts/reconcile_e2_semantics.py",
        "qlib_integration/economic_semantic_reconciliation.py",
        "qlib_integration/economic_execution_contract.py",
        "qlib_integration/market_semantics.py",
    ]
    put(
        out / "scope.json",
        dict(
            input_scans="sealed existing Quotes/States/Dividends only",
            canary=canary,
            dates=["2015-01-05", "2023-12-29"],
            code_lf={
                p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                for p in code
            },
            score_access=False,
            outcome_access=False,
            collection_run=False,
        ),
    )
    frames = []
    for date in source.scope["days"]:
        f = source.frame("dividends", date)
        if len(f):
            f["source_row_id"] = [f"{f.attrs['source_hash']}:{i}" for i in range(len(f))]
            frames.append(f)
    raw_events = pd.concat(frames, ignore_index=True)
    events = reconcile_events(raw_events)
    events.to_parquet(out / "events.parquet", index=False)
    raw_events.to_parquet(out / "event_source_versions.parquet", index=False)
    known_assets = {economic_asset(s) for s in source.scope["starts"]}
    events["candidate_asset"] = events.asset_id.isin(known_assets)
    eventgroups = {s: g for s, g in events.groupby("asset_id")}
    summary = []
    intervals = []
    bridges = []
    totals = Counter()
    status = Counter()
    terminal = []
    stock_list = (
        ["SH600000", "SH601313", "SH601360", "SZ000912", "SZ000155", "SZ002260"]
        if canary
        else sorted(source.scope["starts"])
    )
    (out / "daily").mkdir()
    alias_source = source.frame("states", "SH601360").set_index("date")
    for i, stock in enumerate(stock_list):
        quotes = source.frame("quotes", stock)
        state = alias_source if stock == "SH601313" else source.frame("states", stock)
        if stock != "SH601313":
            state = state.set_index("date") if len(state) else pd.DataFrame()
        dates = [d for d in source.scope["days"] if d >= source.scope["starts"][stock]]
        es = eventgroups.get(economic_asset(stock), events.iloc[:0])
        result, bridge = reconcile_stock(stock, quotes, state, dates, es)
        result.to_parquet(out / f"daily/{stock}.parquet", index=False, compression="zstd")
        if len(bridge):
            bridges.append(bridge)
        counts = {
            c: int(result[c].sum())
            for c in [
                "terminal_candidate_gap",
                "event_unresolved",
                "unexplained_reference_reset",
                "factor_change_without_event",
                "account_gap",
                "execution_special_gap",
            ]
        }
        totals.update(counts)
        status.update(result.quote_status.value_counts().to_dict())
        first = result.loc[result.account_gap, "date"]
        summary.append(
            dict(
                instrument=stock,
                asset_id=economic_asset(stock),
                start=dates[0],
                end=dates[-1],
                sessions=len(result),
                **counts,
                first_account_gap=first.iloc[0] if len(first) else None,
                state_missing_days=int(result.observed_status.eq("unresolved").sum()),
                suspended_days=int(result.observed_status.eq("suspended").sum()),
                st_days=int(result.st_observed.eq(1).sum()),
                events_in_window=int(
                    es.ex_date.between(dates[0].replace("-", ""), dates[-1].replace("-", "")).sum()
                ),
            )
        )
        for col in ["quote_status", "observed_status", "account_gap"]:
            intervals.extend(dict(instrument=stock, kind=col, **r) for r in segments(result, col))
        if result.terminal_candidate_gap.any():
            g = result[result.terminal_candidate_gap]
            terminal.append(
                dict(
                    instrument=stock,
                    asset_id=economic_asset(stock),
                    first_missing=g.date.iloc[0],
                    last_missing=g.date.iloc[-1],
                    sessions=len(g),
                    classification="terminal_or_vendor_coverage_gap_not_confirmed_delisting",
                    confirmed_cash_event=False,
                )
            )
        if i % 200 == 0:
            print(f"offline semantic reconciliation {i + 1}/{len(stock_list)}", flush=True)
    pd.DataFrame(summary).to_csv(out / "stock_summary.csv", index=False)
    pd.DataFrame(intervals).to_parquet(out / "segments.parquet", index=False)
    allbridges = pd.concat(bridges, ignore_index=True) if bridges else pd.DataFrame()
    allbridges.to_parquet(out / "event_reference_bridges.parquet", index=False)
    pd.DataFrame(terminal).to_csv(out / "terminal_candidates.csv", index=False)
    candidates = events[events.candidate_asset]
    put(
        out / "summary.json",
        dict(
            stocks=len(stock_list),
            sessions=sum(r["sessions"] for r in summary),
            quote_status=dict(status),
            gap_counts=dict(totals),
            stocks_with_account_gap=sum(r["account_gap"] > 0 for r in summary),
            terminal_candidate_stocks=len(terminal),
            confirmed_delisting_cash_count=None,
            confirmed_rights_issue_count=None,
            confirmed_generic_conversion_count=None,
            known_same_share_code_migration_count=1,
            events_raw_rows=len(raw_events),
            economic_event_keys=len(events),
            event_status=events.status.value_counts().to_dict(),
            candidate_asset_event_status=candidates.status.value_counts().to_dict(),
            cash_missing_rows_corroborated=int(events.corroborated_cash_missing_rows.sum()),
            full_preopen_state_certified=False,
            e2_ready=False,
        ),
    )
    put(out / "input_hashes.json", source.access)
    put(
        out / "receipt.json",
        {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file()},
    )
    print((out / "summary.json").read_text(encoding="utf-8"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--canary", action="store_true")
    run(parser.parse_args().canary)

"""Fixed E2 data-closure canary. No strategy runner or prediction values."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from qlib_integration.economic_readiness_closure import (
    ClosureQuoteReader,
    quote_checks,
    static_ew_feasibility,
)
from qlib_integration.economic_data_readiness import FIELDS
from qlib_integration.market_semantics import convert_community_market_units

OUT = ROOT / "outputs/economic_translation_mvp/e2_closure_v1/local"
PROVIDER = ROOT.parent / "qlib_data/cn_data_community_20260609_derived"
INVENTORY = ROOT / "reports/economic_translation_mvp/e1_inputs.json"


def dump(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    calendar = pd.DatetimeIndex(inv["calendar"])
    requests = defaultdict(set)
    sample_groups = []
    extents = {}
    snapshots = {}
    keys_receipts = []
    for year in range(2015, 2024):
        rec = inv["folds"][str(year)]["keys"]
        expected = f"outputs/research_protocol_v3_mvp/v3_recompute_audit_20260909_v1/audit/{year}/keys.parquet"
        assert rec["path"] == expected
        path = ROOT / expected
        assert sha(path) == rec["sha256"]
        frame = pq.read_table(
            path,
            columns=["datetime", "instrument"],
            filters=[
                ("datetime", ">=", pd.Timestamp(f"{year}-01-01")),
                ("datetime", "<=", pd.Timestamp(f"{year}-12-31") if year < 2023 else calendar[-1]),
            ],
        ).to_pandas()
        assert len(frame) == rec["rows"] and frame.datetime.isin(calendar).all()
        keys_receipts.append(
            dict(
                path=expected,
                sha256=rec["sha256"],
                columns=["datetime", "instrument"],
                rows=len(frame),
            )
        )
        for stock, g in frame.groupby("instrument", sort=False):
            lo, hi = g.datetime.min(), g.datetime.max()
            prior = extents.get(stock, (lo, hi))
            extents[stock] = (min(lo, prior[0]), max(hi, prior[1]))
        date = calendar[(calendar >= f"{year}-08-28") & (calendar.year == year)][0]
        prior = calendar[calendar < date][-20:]
        names = sorted(frame.loc[frame.datetime.eq(date), "instrument"])
        if year in (2015, 2020, 2023):
            selected = names
            snapshots[str(date.date())] = names
        else:
            selected = sorted(names, key=lambda s: hashlib.sha256(s.encode()).hexdigest())[:32]
        dates = [str(d.date()) for d in [*prior, date]]
        for stock in selected:
            requests[stock.lower()].update(dates)
        sample_groups.append(
            dict(
                kind="full_pool" if year in (2015, 2020, 2023) else "fixed_hash32",
                year=year,
                date=str(date.date()),
                names=selected,
                dates=dates,
            )
        )
        previous = set()
        for d, g in frame.groupby("datetime", sort=True):
            current = set(g.instrument)
            gone = previous - current
            if gone and d <= pd.Timestamp(f"{year}-11-30"):
                selected = sorted(gone)[:2]
                dates = [str(x.date()) for x in calendar[calendar >= d][:20]]
                for stock in selected:
                    requests[stock.lower()].update(dates)
                sample_groups.append(
                    dict(
                        kind="left_signal_universe",
                        year=year,
                        date=str(d.date()),
                        names=selected,
                        dates=dates,
                    )
                )
                break
            previous = current
    # Pre-value scope publication: fixed dates, all candidate identities, no ranks.
    dump(
        OUT / "scope.json",
        dict(
            canonical=inv["canonical_dataset_id"],
            keys=keys_receipts,
            request_dates_by_stock={s: sorted(ds) for s, ds in requests.items()},
            groups=sample_groups,
            fields=list(FIELDS),
            selection="three full-pool August snapshots; other years deterministic hash32; first two ID-sorted annual departures, next20 sessions",
            not_full_nine_year_value_scan=True,
            no_2014_warmup_access=True,
        ),
    )
    reader = ClosureQuoteReader(PROVIDER, requests.keys(), sorted(set().union(*requests.values())))
    metadata = []
    for stock, (lo, hi) in sorted(extents.items()):
        for field in FIELDS:
            path = PROVIDER / "features" / stock.lower() / f"{field}.day.bin"
            row = dict(
                instrument=stock,
                field=field,
                candidate_first=str(lo.date()),
                candidate_last=str(hi.date()),
                exists=path.exists(),
                extent_covers_candidate_dates=False,
            )
            if path.exists():
                with path.open("rb") as f:
                    raw = f.read(4)
                start = struct.unpack("<f", raw)[0]
                assert np.isfinite(start) and start >= 0 and int(start) == start
                size = path.stat().st_size
                assert size >= 4 and size % 4 == 0
                end = int(start) + (size - 4) // 4 - 1
                row.update(
                    header_offset=int(start),
                    byte_size=size,
                    extent_covers_candidate_dates=int(start) <= reader.offsets[str(lo.date())]
                    and end >= reader.offsets[str(hi.date())],
                )
            metadata.append(row)
    pd.DataFrame(metadata).to_csv(OUT / "candidate_field_extents.csv", index=False)
    all_rows = []
    try:
        for i, (stock, dates) in enumerate(sorted(requests.items())):
            f = pd.DataFrame({field: reader.read(stock, field, sorted(dates)) for field in FIELDS})
            factor = f.factor.where(f.factor.gt(0))
            for field in ("open", "high", "low", "close"):
                f[field] = f[field] / factor
            f["volume"], f["amount"] = convert_community_market_units(
                f.volume,
                factor,
                f.amount,
                volume_lot_to_shares_multiplier=100,
                amount_to_cny_multiplier=1000,
            )
            f["instrument"] = stock.upper()
            f.index.name = "date"
            all_rows.append(f.reset_index())
            if i % 500 == 0:
                print(f"approved quote slices: {i}/{len(requests)} stocks", flush=True)
        data = pd.concat(all_rows, ignore_index=True)
        data.to_parquet(OUT / "bounded_raw_units.parquet", index=False)
        groups = []
        for spec in sample_groups:
            sub = data[data.instrument.isin(spec["names"]) & data.date.isin(spec["dates"])]
            groups.append(
                dict(kind=spec["kind"], year=spec["year"], date=spec["date"], **quote_checks(sub))
            )
        pd.DataFrame(groups).to_csv(OUT / "quote_checks.csv", index=False)
        feas = []
        for date, names in snapshots.items():
            pos = calendar.get_loc(pd.Timestamp(date))
            prior = [str(d.date()) for d in calendar[pos - 20 : pos]]
            current = data[data.date.eq(date) & data.instrument.isin(names)].set_index("instrument")
            past = data[data.date.isin(prior) & data.instrument.isin(names)]
            vols = past.pivot(index="date", columns="instrument", values="volume").reindex(prior)
            # Unknown/negative days block ADV; zeros are still unverified suspension.
            adv = vols.mean().where(vols.notna().all() & np.isfinite(vols).all() & vols.ge(0).all())
            current["adv20"] = adv
            current["reference_close"] = data[data.date.eq(prior[-1])].set_index("instrument").close
            current["board"] = [
                "star" if s.startswith("SH688") else "chinext" if s.startswith("SZ30") else "main"
                for s in current.index
            ]
            current = current.reset_index()
            assert len(current) == len(names)
            for aum in (1_000_000, 5_000_000, 10_000_000):
                feas.append(static_ew_feasibility(current, date, aum))
        pd.DataFrame(feas).to_csv(OUT / "static_ew_feasibility.csv", index=False)
        dump(
            OUT / "summary.json",
            dict(
                candidate_union=len(extents),
                candidate_field_files=len(metadata),
                absent_files=sum(not r["exists"] for r in metadata),
                extent_not_covering=sum(not r["extent_covers_candidate_dates"] for r in metadata),
                sampled_security_days=len(data),
                sampled_stocks=data.instrument.nunique(),
                quote_checks=quote_checks(data),
                first_2015_adv20_execution_date=str(calendar[20].date()),
                earlier_sessions_without_approved_adv=20,
                full_history_value_coverage_certified=False,
                full_market_execution_ready=False,
            ),
        )
    finally:
        dump(OUT / "access.json", reader.audit)
    dump(OUT / "receipt.json", {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file()})
    print("Bounded E2 canary complete; not an E2 READY decision.", flush=True)


if __name__ == "__main__":
    main()

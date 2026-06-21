from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


DEFAULT_PROVIDER = Path("E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
DEFAULT_OUTPUT = Path("outputs/data_inventory/provider_v3_6")
DEFAULT_SAMPLE = ["SH600000", "SZ000001", "SH600519"]


def read_nonempty_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def collect_field_presence(provider: Path) -> pd.DataFrame:
    features_dir = provider / "features"
    instrument_dirs = sorted(path for path in features_dir.iterdir() if path.is_dir())
    counts: Counter[str] = Counter()
    for instrument_dir in instrument_dirs:
        fields = {path.name.rsplit(".", 2)[0] for path in instrument_dir.glob("*.day.bin")}
        counts.update(fields)
    total = len(instrument_dirs)
    rows = [
        {
            "field": field,
            "instrument_count": count,
            "feature_instrument_count": total,
            "file_presence_rate": count / total if total else 0.0,
        }
        for field, count in sorted(counts.items())
    ]
    return pd.DataFrame(rows)


def collect_instrument_lists(provider: Path) -> pd.DataFrame:
    rows = []
    for path in sorted((provider / "instruments").glob("*.txt")):
        lines = read_nonempty_lines(path)
        rows.append(
            {
                "instrument_list": path.stem,
                "row_count": len(lines),
                "has_lifecycle_intervals": any(len(line.split("\t")) >= 3 for line in lines[:100]),
                "path": path.as_posix(),
            }
        )
    return pd.DataFrame(rows)


def collect_sample_coverage(
    provider: Path,
    instruments: list[str],
    fields: list[str],
    start: str,
    end: str,
) -> pd.DataFrame:
    import qlib
    from qlib.config import C
    from qlib.data import D

    qlib.init(provider_uri=str(provider), region="cn")
    C.kernels = 1
    C.joblib_backend = "sequential"
    expressions = [f"${field}" for field in fields]
    frame = D.features(instruments, expressions, start_time=start, end_time=end)
    rows = []
    for instrument in instruments:
        try:
            sample = frame.xs(instrument, level="instrument")
        except KeyError:
            sample = pd.DataFrame(columns=expressions)
        for field, expression in zip(fields, expressions):
            valid = int(pd.to_numeric(sample.get(expression), errors="coerce").notna().sum()) if expression in sample else 0
            total = int(len(sample))
            rows.append(
                {
                    "instrument": instrument,
                    "field": field,
                    "start": start,
                    "end": end,
                    "valid_rows": valid,
                    "total_rows": total,
                    "coverage": valid / total if total else 0.0,
                }
            )
    return pd.DataFrame(rows)


def build_capability_inventory(
    provider: Path,
    fields: pd.DataFrame,
    instrument_lists: pd.DataFrame,
) -> pd.DataFrame:
    available_fields = set(fields["field"]) if not fields.empty else set()
    available_lists = set(instrument_lists["instrument_list"]) if not instrument_lists.empty else set()
    feature_dirs = provider / "features"

    def field_status(required: set[str]) -> str:
        return "available" if required <= available_fields else "missing"

    index_files = sorted(available_lists & {"csi300", "csi500", "csi800", "csi1000", "csiall"})
    benchmark_codes = {
        "CSI300": feature_dirs / "sh000300",
        "CSI500": feature_dirs / "sh000905",
        "CSI1000": feature_dirs / "sh000852",
    }
    benchmark_available = [name for name, path in benchmark_codes.items() if path.exists()]
    industry_candidates = sorted((provider / "instruments").glob("*industry*.txt")) + sorted(
        (provider / "instruments").glob("sw*.txt")
    )
    market_cap_fields = sorted(available_fields & {"market_cap", "mktcap", "float_market_cap", "circ_mv"})

    rows = [
        {
            "capability": "price_ohlc",
            "status": field_status({"open", "high", "low", "close"}),
            "available_items": ",".join(sorted(available_fields & {"open", "high", "low", "close"})),
            "use": "price, momentum, reversal, volatility, drawdown factors",
            "next_action": "ready",
        },
        {
            "capability": "volume_liquidity",
            "status": field_status({"volume", "amount"}),
            "available_items": ",".join(sorted(available_fields & {"volume", "amount", "vwap"})),
            "use": "liquidity, price-volume, turnover proxies",
            "next_action": "ready",
        },
        {
            "capability": "adjustment",
            "status": "available" if {"factor", "adjclose"} & available_fields else "missing",
            "available_items": ",".join(sorted(available_fields & {"factor", "adjclose"})),
            "use": "corporate-action-aware price research",
            "next_action": "validate semantics before custom adjusted factors",
        },
        {
            "capability": "index_membership",
            "status": "available" if index_files else "missing",
            "available_items": ",".join(index_files),
            "use": "universe stability and cross-universe factor evaluation",
            "next_action": "ready",
        },
        {
            "capability": "benchmark_returns",
            "status": "available" if benchmark_available else "missing",
            "available_items": ",".join(benchmark_available),
            "use": "benchmark-relative factor and portfolio diagnostics",
            "next_action": "add benchmark adapter",
        },
        {
            "capability": "listing_lifecycle",
            "status": "available" if not instrument_lists.empty and instrument_lists["has_lifecycle_intervals"].any() else "missing",
            "available_items": "instrument start/end intervals",
            "use": "listing age and point-in-time universe eligibility",
            "next_action": "derive listing_age_days",
        },
        {
            "capability": "industry_classification",
            "status": "available" if industry_candidates else "needs_external_source",
            "available_items": ",".join(path.name for path in industry_candidates),
            "use": "industry IC, industry-neutral returns, group analysis",
            "next_action": "select point-in-time industry data source",
        },
        {
            "capability": "market_cap",
            "status": "available" if market_cap_fields else "needs_external_source",
            "available_items": ",".join(market_cap_fields),
            "use": "size exposure, cap weighting, size-neutral evaluation",
            "next_action": "select total/float market-cap data source",
        },
        {
            "capability": "fundamentals",
            "status": "needs_external_source",
            "available_items": "",
            "use": "value, quality, profitability, growth factors",
            "next_action": "defer until source/licensing decision",
        },
        {
            "capability": "tradability_constraints",
            "status": "available_external_layer",
            "available_items": "can_buy,can_sell,liquidity_bucket,tradability_score,data_quality_status",
            "use": "mandatory prefilter before all factor evaluation",
            "next_action": "continue reusing outputs/tradability and outputs/data_quality_tradability",
        },
    ]
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join("---" for _ in view.columns) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in view.itertuples(index=False, name=None))
    return "\n".join(lines)


def write_report(
    provider: Path,
    capabilities: pd.DataFrame,
    fields: pd.DataFrame,
    instrument_lists: pd.DataFrame,
    sample_coverage: pd.DataFrame,
    output: Path,
) -> None:
    coverage_summary = (
        sample_coverage.groupby("field")["coverage"].agg(["mean", "min", "max"]).reset_index()
        if not sample_coverage.empty
        else pd.DataFrame()
    )
    lines = [
        "# Provider Data Capability Inventory",
        "",
        f"- Provider: `{provider.as_posix()}`",
        "- Purpose: decide which open-source factor evaluation capabilities can be enabled without inventing missing data.",
        "",
        "## Capability Inventory",
        "",
        markdown_table(capabilities),
        "",
        "## Feature File Presence",
        "",
        markdown_table(fields),
        "",
        "## Sample Coverage",
        "",
        markdown_table(coverage_summary),
        "",
        "## Instrument Lists",
        "",
        markdown_table(instrument_lists),
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    provider = args.provider_uri
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    fields = collect_field_presence(provider)
    instrument_lists = collect_instrument_lists(provider)
    available_fields = fields.loc[fields["instrument_count"].gt(0), "field"].tolist()
    sample_fields = [field for field in args.fields if field in set(available_fields)]
    sample_coverage = collect_sample_coverage(
        provider,
        args.instruments,
        sample_fields,
        args.start,
        args.end,
    )
    capabilities = build_capability_inventory(provider, fields, instrument_lists)

    fields.to_csv(output_dir / "provider_field_inventory.csv", index=False, encoding="utf-8-sig")
    instrument_lists.to_csv(output_dir / "instrument_list_inventory.csv", index=False, encoding="utf-8-sig")
    sample_coverage.to_csv(output_dir / "provider_sample_coverage.csv", index=False, encoding="utf-8-sig")
    capabilities.to_csv(output_dir / "data_capability_inventory.csv", index=False, encoding="utf-8-sig")
    write_report(
        provider,
        capabilities,
        fields,
        instrument_lists,
        sample_coverage,
        output_dir / "provider_field_inventory_report.md",
    )
    metadata = {
        "provider_uri": provider.as_posix(),
        "sample_instruments": args.instruments,
        "sample_start": args.start,
        "sample_end": args.end,
        "sample_fields": sample_fields,
    }
    (output_dir / "inventory_run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Provider field inventory written to {output_dir}")
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect Qlib provider fields and factor evaluation data capabilities.")
    parser.add_argument("--provider-uri", type=Path, default=DEFAULT_PROVIDER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--instruments", nargs="+", default=DEFAULT_SAMPLE)
    parser.add_argument(
        "--fields",
        nargs="+",
        default=["open", "high", "low", "close", "volume", "amount", "vwap", "factor", "adjclose"],
    )
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2023-12-29")
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()


import argparse
from collections import Counter
from pathlib import Path


def parse_prefixes(value: str) -> tuple[str, ...]:
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def symbol_prefix(symbol: str) -> str:
    symbol = symbol.upper()
    for prefix in ("SH", "SZ", "BJ"):
        if symbol.startswith(prefix):
            return prefix
    return "OTHER"


def is_index_symbol(symbol: str) -> bool:
    symbol = symbol.upper()
    return symbol.startswith("SH000") or symbol.startswith("SZ399")


def should_keep(
    symbol: str,
    include_prefixes: tuple[str, ...],
    exclude_prefixes: tuple[str, ...],
    exclude_index_symbols: bool,
) -> bool:
    prefix = symbol_prefix(symbol)
    if include_prefixes and prefix not in include_prefixes:
        return False
    if exclude_prefixes and prefix in exclude_prefixes:
        return False
    if exclude_index_symbols and is_index_symbol(symbol):
        return False
    return True


def create_filtered_universe(
    source: Path,
    output: Path,
    include_prefixes: tuple[str, ...],
    exclude_prefixes: tuple[str, ...],
    exclude_index_symbols: bool,
) -> dict:
    input_counts: Counter[str] = Counter()
    output_counts: Counter[str] = Counter()
    input_index_rows = 0
    output_index_rows = 0
    input_rows = 0
    output_rows = 0
    output_lines = []

    with source.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            symbol = stripped.split()[0].upper()
            prefix = symbol_prefix(symbol)
            input_counts[prefix] += 1
            if is_index_symbol(symbol):
                input_index_rows += 1
            input_rows += 1
            if should_keep(symbol, include_prefixes, exclude_prefixes, exclude_index_symbols):
                output_lines.append(stripped)
                output_counts[prefix] += 1
                if is_index_symbol(symbol):
                    output_index_rows += 1
                output_rows += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(output_lines) + ("\n" if output_lines else ""), encoding="utf-8")
    return {
        "source": str(source),
        "output": str(output),
        "include_prefixes": list(include_prefixes),
        "exclude_prefixes": list(exclude_prefixes),
        "exclude_index_symbols": exclude_index_symbols,
        "input_rows": input_rows,
        "output_rows": output_rows,
        "input_index_rows": input_index_rows,
        "output_index_rows": output_index_rows,
        "input_prefix_rows": dict(sorted(input_counts.items())),
        "output_prefix_rows": dict(sorted(output_counts.items())),
    }


def write_summary(path: Path, summary: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Filtered Universe Summary",
        "",
        f"- Source: `{summary['source']}`",
        f"- Output: `{summary['output']}`",
        f"- Include prefixes: `{', '.join(summary['include_prefixes'])}`",
        f"- Exclude prefixes: `{', '.join(summary['exclude_prefixes'])}`",
        f"- Exclude index symbols: `{summary['exclude_index_symbols']}`",
        f"- Input rows: `{summary['input_rows']}`",
        f"- Output rows: `{summary['output_rows']}`",
        f"- Input index-like rows: `{summary['input_index_rows']}`",
        f"- Output index-like rows: `{summary['output_index_rows']}`",
        "",
        "## Prefix Rows",
        "",
        "| prefix | input rows | output rows |",
        "| --- | ---: | ---: |",
    ]
    prefixes = sorted(set(summary["input_prefix_rows"]) | set(summary["output_prefix_rows"]))
    for prefix in prefixes:
        lines.append(
            f"| {prefix} | {summary['input_prefix_rows'].get(prefix, 0)} | {summary['output_prefix_rows'].get(prefix, 0)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Create a filtered qlib instrument universe file.")
    parser.add_argument("--source", required=True, help="Source instrument file, for example provider/instruments/all.txt.")
    parser.add_argument("--output", required=True, help="Filtered instrument file path.")
    parser.add_argument("--include-prefixes", default="", help="Comma-separated prefixes to include, for example SH,SZ.")
    parser.add_argument("--exclude-prefixes", default="", help="Comma-separated prefixes to exclude, for example BJ.")
    parser.add_argument(
        "--exclude-index-symbols",
        action="store_true",
        help="Exclude common index symbols such as SH000* and SZ399*.",
    )
    parser.add_argument("--summary-output", help="Optional markdown summary path.")
    args = parser.parse_args()

    summary = create_filtered_universe(
        Path(args.source),
        Path(args.output),
        parse_prefixes(args.include_prefixes),
        parse_prefixes(args.exclude_prefixes),
        args.exclude_index_symbols,
    )
    if args.summary_output:
        write_summary(Path(args.summary_output), summary)

    print(f"Wrote filtered universe to {args.output}")


if __name__ == "__main__":
    main()

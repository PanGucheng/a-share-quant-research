import argparse
import re
from pathlib import Path


def replace_line(pattern: str, replacement: str, text: str, description: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected exactly one {description} line, found {count}.")
    return updated


def create_config(template: Path, output: Path, provider_uri: str, market: str | None, benchmark: str | None):
    text = template.read_text(encoding="utf-8")
    provider_uri = provider_uri.replace("\\", "/")

    text = replace_line(
        r'^(\s*provider_uri:\s*).*$',
        rf'\1"{provider_uri}"',
        text,
        "provider_uri",
    )

    if market:
        text = replace_line(
            r"^market:\s*&market\s+.*$",
            f"market: &market {market}",
            text,
            "market anchor",
        )

    if benchmark:
        text = replace_line(
            r"^benchmark:\s*&benchmark\s+.*$",
            f"benchmark: &benchmark {benchmark}",
            text,
            "benchmark anchor",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Create a qrun workflow config from an existing template.")
    parser.add_argument("--template", required=True, help="Template workflow YAML path.")
    parser.add_argument("--output", required=True, help="Output workflow YAML path.")
    parser.add_argument("--provider-uri", required=True, help="Provider URI to write into qlib_init.provider_uri.")
    parser.add_argument("--market", help="Optional market/universe name for the market anchor.")
    parser.add_argument("--benchmark", help="Optional benchmark symbol for the benchmark anchor.")
    args = parser.parse_args()

    create_config(
        template=Path(args.template),
        output=Path(args.output),
        provider_uri=args.provider_uri,
        market=args.market,
        benchmark=args.benchmark,
    )
    print(f"Wrote workflow config to {args.output}")


if __name__ == "__main__":
    main()

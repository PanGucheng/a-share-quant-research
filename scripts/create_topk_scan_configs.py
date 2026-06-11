import argparse
import re
from pathlib import Path


def replace_scalar(text: str, key: str, value: int) -> str:
    pattern = rf"^(\s*{re.escape(key)}:\s*)\d+\s*$"
    updated, count = re.subn(pattern, rf"\g<1>{value}", text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected exactly one {key} line, found {count}.")
    return updated


def create_config(template: Path, output_dir: Path, topk: int, n_drop: int, suffix: str) -> Path:
    text = template.read_text(encoding="utf-8")
    text = replace_scalar(text, "topk", topk)
    text = replace_scalar(text, "n_drop", n_drop)

    stem = template.stem
    output = output_dir / f"{stem}_topk{topk}_drop{n_drop}{suffix}.yaml"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output


def parse_pairs(values: list[str]) -> list[tuple[int, int]]:
    pairs = []
    for value in values:
        left, right = value.split(":", 1)
        pairs.append((int(left), int(right)))
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Create TopK/n_drop scan configs from one qrun YAML template.")
    parser.add_argument("--template", required=True, help="Base workflow YAML.")
    parser.add_argument("--output-dir", default="configs", help="Directory for generated configs.")
    parser.add_argument(
        "--pair",
        action="append",
        required=True,
        help="TopK and n_drop pair in topk:n_drop format. Can be passed multiple times.",
    )
    parser.add_argument("--suffix", default="", help="Optional suffix before .yaml.")
    args = parser.parse_args()

    outputs = []
    for topk, n_drop in parse_pairs(args.pair):
        outputs.append(create_config(Path(args.template), Path(args.output_dir), topk, n_drop, args.suffix))

    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()

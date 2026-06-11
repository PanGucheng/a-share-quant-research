import argparse
import csv
from datetime import datetime
from pathlib import Path


METRICS = [
    "IC",
    "ICIR",
    "Rank IC",
    "Rank ICIR",
    "1day.excess_return_with_cost.annualized_return",
    "1day.excess_return_with_cost.information_ratio",
    "1day.excess_return_with_cost.max_drawdown",
    "1day.excess_return_without_cost.annualized_return",
    "1day.excess_return_without_cost.information_ratio",
    "1day.excess_return_without_cost.max_drawdown",
]


STATUS_NAME = {
    "1": "scheduled",
    "2": "running",
    "3": "finished",
    "4": "failed",
    "5": "killed",
}


def parse_meta(path: Path) -> dict:
    meta = {}
    if not path.exists():
        return meta
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("'\"")
    return meta


def format_epoch_ms(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromtimestamp(int(value) / 1000).isoformat(sep=" ", timespec="seconds")
    except ValueError:
        return value


def read_metric(path: Path) -> str:
    if not path.exists():
        return ""
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return ""
    parts = lines[-1].split()
    return parts[1] if len(parts) >= 2 else ""


def iter_runs(mlruns: Path):
    for experiment_dir in sorted(p for p in mlruns.iterdir() if p.is_dir()):
        experiment_id = experiment_dir.name
        for run_dir in sorted(p for p in experiment_dir.iterdir() if p.is_dir()):
            meta_path = run_dir / "meta.yaml"
            if not meta_path.exists():
                continue
            meta = parse_meta(meta_path)
            metrics_dir = run_dir / "metrics"
            row = {
                "experiment_id": meta.get("experiment_id", experiment_id),
                "run_id": meta.get("run_id", run_dir.name),
                "status": STATUS_NAME.get(meta.get("status", ""), meta.get("status", "")),
                "start_time": format_epoch_ms(meta.get("start_time", "")),
                "end_time": format_epoch_ms(meta.get("end_time", "")),
            }
            for metric in METRICS:
                row[metric] = read_metric(metrics_dir / metric)
            yield row


def main():
    parser = argparse.ArgumentParser(description="Summarize Qlib MLflow file-store metrics.")
    parser.add_argument("--mlruns", default="outputs/mlruns_validated", help="MLflow file-store root.")
    parser.add_argument("--output", default="outputs/reports/baseline_summary.csv", help="Output CSV path.")
    args = parser.parse_args()

    mlruns = Path(args.mlruns)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    rows = list(iter_runs(mlruns))
    fieldnames = ["experiment_id", "run_id", "status", "start_time", "end_time", *METRICS]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} run summaries to {output}")


if __name__ == "__main__":
    main()

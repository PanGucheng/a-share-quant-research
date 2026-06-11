import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def collect_snapshot(provider_uri: Path, sample_size: int = 20) -> dict:
    calendars_dir = provider_uri / "calendars"
    instruments_dir = provider_uri / "instruments"
    features_dir = provider_uri / "features"

    calendar_files = sorted(calendars_dir.glob("*.txt"))
    calendars = {}
    for path in calendar_files:
        values = read_lines(path)
        calendars[path.name] = {
            "count": len(values),
            "start": values[0] if values else "",
            "end": values[-1] if values else "",
        }

    instrument_files = sorted(instruments_dir.glob("*.txt"))
    instruments = {}
    for path in instrument_files:
        values = read_lines(path)
        instruments[path.name] = {
            "count": len(values),
            "sample": values[:3],
        }

    instrument_dirs = sorted([p for p in features_dir.iterdir() if p.is_dir()]) if features_dir.exists() else []
    field_counter = Counter()
    sample_instruments = []
    for instrument_dir in instrument_dirs[:sample_size]:
        fields = sorted(path.name.rsplit(".", 2)[0] for path in instrument_dir.glob("*.day.bin"))
        field_counter.update(fields)
        sample_instruments.append({"instrument": instrument_dir.name, "fields": fields})

    all_fields = sorted(
        {
            path.name.rsplit(".", 2)[0]
            for instrument_dir in instrument_dirs
            for path in instrument_dir.glob("*.day.bin")
        }
    )

    archive_files = sorted(provider_uri.glob("*.zip"))
    archives = [
        {
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "modified_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(sep=" ", timespec="seconds"),
        }
        for path in archive_files
    ]

    total_bytes = sum(path.stat().st_size for path in provider_uri.rglob("*") if path.is_file())

    return {
        "provider_uri": str(provider_uri),
        "exists": provider_uri.exists(),
        "total_size_bytes": total_bytes,
        "total_size_mb": round(total_bytes / 1024 / 1024, 2),
        "calendar_files": calendars,
        "instrument_files": instruments,
        "feature_instrument_count": len(instrument_dirs),
        "fields": all_fields,
        "field_presence_in_sample": dict(sorted(field_counter.items())),
        "sample_instruments": sample_instruments,
        "archives": archives,
    }


def write_markdown(snapshot: dict, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Qlib Data Snapshot",
        "",
        f"- Provider URI: `{snapshot['provider_uri']}`",
        f"- Exists: `{snapshot['exists']}`",
        f"- Total size: `{snapshot['total_size_mb']} MB`",
        f"- Feature instrument count: `{snapshot['feature_instrument_count']}`",
        f"- Fields: `{', '.join(snapshot['fields'])}`",
        "",
        "## Calendars",
        "",
        "| file | count | start | end |",
        "| --- | ---: | --- | --- |",
    ]
    for name, info in snapshot["calendar_files"].items():
        lines.append(f"| {name} | {info['count']} | {info['start']} | {info['end']} |")

    lines.extend(["", "## Instruments", "", "| file | count | sample |", "| --- | ---: | --- |"])
    for name, info in snapshot["instrument_files"].items():
        sample = "<br>".join(info["sample"])
        lines.append(f"| {name} | {info['count']} | {sample} |")

    lines.extend(["", "## Field Presence In Sample", "", "| field | sample instrument count |", "| --- | ---: |"])
    for field, count in snapshot["field_presence_in_sample"].items():
        lines.append(f"| {field} | {count} |")

    lines.extend(["", "## Sample Instruments", ""])
    for item in snapshot["sample_instruments"]:
        lines.append(f"- `{item['instrument']}`: `{', '.join(item['fields'])}`")

    lines.extend(["", "## Archives", "", "| file | size bytes | modified time |", "| --- | ---: | --- |"])
    for archive in snapshot["archives"]:
        lines.append(f"| {archive['name']} | {archive['size_bytes']} | {archive['modified_time']} |")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Inspect a qlib-format data directory.")
    parser.add_argument("--provider-uri", required=True, help="Path to qlib data provider directory.")
    parser.add_argument("--output", required=True, help="Output markdown report path.")
    parser.add_argument("--json-output", help="Optional output JSON path.")
    parser.add_argument("--sample-size", type=int, default=20, help="Number of instrument directories to sample.")
    args = parser.parse_args()

    snapshot = collect_snapshot(Path(args.provider_uri), sample_size=args.sample_size)
    write_markdown(snapshot, Path(args.output))

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote data snapshot to {args.output}")


if __name__ == "__main__":
    main()

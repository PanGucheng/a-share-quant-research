from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

from .lineage import canonical_json, sha256_file, sha256_text


def normalized_required_fields(values: Iterable[object]) -> list[str]:
    fields: set[str] = set()
    for value in values:
        if pd.isna(value):
            continue
        fields.update(item.strip() for item in str(value).split(",") if item.strip())
    return sorted(fields)


def _hash_path(path: Path) -> tuple[int, str]:
    return path.stat().st_size, sha256_file(path)


def provider_file_inventory(
    provider_root: Path,
    instruments: Sequence[str],
    fields: Sequence[str],
    *,
    calendar_files: Sequence[str],
    instrument_files: Sequence[str],
    workers: int = 8,
) -> pd.DataFrame:
    specifications: list[dict[str, object]] = []
    for relative in calendar_files:
        specifications.append(
            {"file_role": "calendar", "instrument": "", "field": "", "relative_path": Path(relative).as_posix()}
        )
    for relative in instrument_files:
        specifications.append(
            {"file_role": "instrument", "instrument": "", "field": "", "relative_path": Path(relative).as_posix()}
        )
    for instrument in sorted({str(item).upper() for item in instruments}):
        for field in sorted(set(fields)):
            normalized = str(field).removeprefix("$").lower()
            relative = Path("features") / instrument.lower() / f"{normalized}.day.bin"
            specifications.append(
                {
                    "file_role": "feature",
                    "instrument": instrument,
                    "field": field,
                    "relative_path": relative.as_posix(),
                }
            )

    paths = [provider_root / str(item["relative_path"]) for item in specifications]
    existing = [path if path.is_file() else None for path in paths]
    hashes: dict[Path, tuple[int, str]] = {}
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        futures = {path: pool.submit(_hash_path, path) for path in existing if path is not None}
        for path, future in futures.items():
            hashes[path] = future.result()

    rows = []
    for spec, path in zip(specifications, paths):
        size, digest = hashes.get(path, (0, ""))
        rows.append({**spec, "exists": path in hashes, "size_bytes": size, "sha256": digest})
    return pd.DataFrame(rows).sort_values(["file_role", "relative_path"], kind="stable").reset_index(drop=True)


def inventory_tree_hash(inventory: pd.DataFrame) -> str:
    columns = ["file_role", "instrument", "field", "relative_path", "exists", "size_bytes", "sha256"]
    return sha256_text(canonical_json(inventory[columns].to_dict("records")))


def git_output(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(arguments)} failed for {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def git_repo_receipt(repo: Path, dependency_paths: Sequence[str]) -> dict[str, object]:
    normalized_dependencies = sorted({Path(item).as_posix() for item in dependency_paths})
    dirty_lines = [line for line in git_output(repo, "status", "--porcelain=v1", "--untracked-files=all").splitlines() if line]
    dirty_paths = sorted({line[3:].replace("\\", "/") for line in dirty_lines})
    affected = sorted(set(dirty_paths).intersection(normalized_dependencies))
    remote_lines = git_output(repo, "remote", "-v").splitlines()
    remote = remote_lines[0].split()[1] if remote_lines else ""
    return {
        "repo_path": repo.as_posix(),
        "commit": git_output(repo, "rev-parse", "HEAD"),
        "commit_tree": git_output(repo, "rev-parse", "HEAD^{tree}"),
        "remote_url": remote,
        "repo_clean": not dirty_paths,
        "dirty_paths": dirty_paths,
        "dependency_dirty_paths": affected,
    }


def source_file_inventory(
    source: str,
    root: Path,
    files: Mapping[str, str],
) -> pd.DataFrame:
    rows = []
    for role, relative in sorted(files.items()):
        path = root / relative
        rows.append(
            {
                "source": source,
                "file_role": role,
                "relative_path": Path(relative).as_posix(),
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.is_file() else 0,
                "sha256": sha256_file(path) if path.is_file() else "",
            }
        )
    return pd.DataFrame(rows)


def source_tree_hash(inventory: pd.DataFrame) -> str:
    columns = ["source", "file_role", "relative_path", "exists", "size_bytes", "sha256"]
    return sha256_text(canonical_json(inventory[columns].sort_values(columns[:3]).to_dict("records")))


def verify_file_inventory(root: Path, inventory: pd.DataFrame, *, workers: int = 8) -> pd.DataFrame:
    paths = [(root / str(relative)).resolve() for relative in inventory["relative_path"]]
    existing = [path if path.is_file() else None for path in paths]
    hashes: dict[Path, tuple[int, str]] = {}
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        futures = {path: pool.submit(_hash_path, path) for path in existing if path is not None}
        for path, future in futures.items():
            hashes[path] = future.result()
    rows = []
    for row, path in zip(inventory.to_dict("records"), paths):
        size, digest = hashes.get(path, (0, ""))
        rows.append(
            {
                **row,
                "current_exists": path in hashes,
                "current_size_bytes": size,
                "current_sha256": digest,
                "current_match": bool(
                    path in hashes
                    and bool(row.get("exists"))
                    and int(row.get("size_bytes", 0)) == size
                    and str(row.get("sha256", "")) == digest
                ),
            }
        )
    return pd.DataFrame(rows)


def raw_parquet_receipt(path: Path, required_columns: Sequence[str]) -> tuple[dict[str, object], dict[str, object]]:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    columns = schema.names
    key_table = pq.read_table(path, columns=["datetime", "instrument"])
    datetime_column = key_table.column("datetime").combine_chunks()
    instrument_column = key_table.column("instrument").combine_chunks()
    duplicate_count: int | None
    try:
        keys = pd.DataFrame(
            {
                "datetime": datetime_column.to_pandas(),
                "instrument": instrument_column.to_pandas(),
            }
        )
        duplicate_count = int(keys.duplicated(["datetime", "instrument"]).sum())
    finally:
        keys = None
    metadata = {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "row_count": parquet.metadata.num_rows,
        "row_group_count": parquet.metadata.num_row_groups,
        "instrument_count": int(pc.count_distinct(instrument_column).as_py()),
        "instrument_set_sha256": sha256_text(
            canonical_json(sorted(str(item).upper() for item in pc.unique(instrument_column).to_pylist()))
        ),
        "date_min": str(pc.min(datetime_column).as_py()),
        "date_max": str(pc.max(datetime_column).as_py()),
        "duplicate_key_count": duplicate_count,
        "columns": columns,
        "required_columns": list(required_columns),
        "missing_required_columns": sorted(set(required_columns) - set(columns)),
    }
    field_schema = {
        "columns": [{"name": field.name, "dtype": str(field.type), "nullable": field.nullable} for field in schema],
        "column_order": columns,
    }
    return metadata, field_schema

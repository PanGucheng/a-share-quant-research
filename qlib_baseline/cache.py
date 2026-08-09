from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import platform
import re
import subprocess
import textwrap
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qlib_baseline.io import atomic_output_path, atomic_write_json


CACHE_FORMAT = "parquet"
CACHE_SCHEMA_VERSION = 2


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_value(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _DocstringStripper(ast.NodeTransformer):
    def _strip(self, node: ast.AST) -> ast.AST:
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body.pop(0)
        return node

    def visit_Module(self, node: ast.Module) -> ast.AST:
        self.generic_visit(node)
        return self._strip(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        return self._strip(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        self.generic_visit(node)
        return self._strip(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.generic_visit(node)
        return self._strip(node)


def normalized_source_ast(source: str) -> str:
    tree = ast.parse(textwrap.dedent(source))
    normalized = _DocstringStripper().visit(tree)
    ast.fix_missing_locations(normalized)
    return ast.dump(normalized, annotate_fields=True, include_attributes=False)


def normalized_source_ast_hash(source: str) -> str:
    return hashlib.sha256(normalized_source_ast(source).encode("utf-8")).hexdigest()


def normalized_callable_ast_hash(*functions: Callable[..., object]) -> str:
    payload = [
        {
            "callable": f"{function.__module__}.{function.__qualname__}",
            "ast": normalized_source_ast(inspect.getsource(function)),
        }
        for function in functions
    ]
    return sha256_value(payload)


def build_cache_fingerprint(
    cache_name: str,
    *,
    data: Mapping[str, Any],
    computation: Mapping[str, Any],
    request: Mapping[str, Any],
    schema_version: int = CACHE_SCHEMA_VERSION,
) -> dict[str, Any]:
    schema = {
        "name": cache_name,
        "version": int(schema_version),
        "format": CACHE_FORMAT,
    }
    components = {
        "cache_schema": schema,
        "data_fingerprint": json.loads(canonical_json(data)),
        "computation_fingerprint": json.loads(canonical_json(computation)),
        "request_fingerprint": json.loads(canonical_json(request)),
    }
    component_hashes = {name: sha256_value(value) for name, value in components.items()}
    return {
        **components,
        "component_hashes": component_hashes,
        "cache_key": sha256_value(component_hashes),
    }


def cache_path(
    cache_dir: str | Path, prefix: str, fingerprint: Mapping[str, Any]
) -> Path:
    return Path(cache_dir) / f"{prefix}_{str(fingerprint['cache_key'])[:16]}.parquet"


def cache_metadata_path(path: str | Path) -> Path:
    return Path(path).with_suffix(".meta.json")


def _git_output(repo: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _find_git_root(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def package_engine_identity(distribution: str, module: str) -> dict[str, Any]:
    try:
        version = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        version = None
    spec = importlib.util.find_spec(module)
    origin = Path(spec.origin).resolve() if spec is not None and spec.origin else None
    repo = _find_git_root(origin) if origin is not None else None
    identity: dict[str, Any] = {
        "distribution": distribution,
        "version": version,
        "module": module,
        "origin": origin.as_posix() if origin is not None else None,
        "git_commit": (
            _git_output(repo, "rev-parse", "HEAD") if repo is not None else None
        ),
    }
    if repo is not None:
        diff = _git_output(
            repo, "diff", "--no-ext-diff", "--binary", "HEAD", "--", module
        )
        identity["dirty_diff_sha256"] = (
            hashlib.sha256(diff.encode("utf-8")).hexdigest() if diff else None
        )
    return identity


def _small_file_receipt(path: Path, root: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": path.relative_to(root).as_posix(), "exists": False}
    return {
        "path": path.relative_to(root).as_posix(),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def _market_instruments(path: Path) -> list[str]:
    if not path.is_file():
        return []
    instruments = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.split("\t", 1)[0].strip().lower()
        if value:
            instruments.append(value)
    return sorted(set(instruments))


def provider_data_fingerprint(
    provider_uri: str | Path,
    *,
    market: str,
    fields: Sequence[str],
) -> dict[str, Any]:
    normalized_uri = str(provider_uri).replace("\\", "/")
    normalized_fields = sorted(
        {str(field).removeprefix("$").lower() for field in fields}
    )
    root = Path(provider_uri).expanduser()
    if not root.is_dir():
        return {
            "provider_uri": normalized_uri,
            "provider_available": False,
            "market": market,
            "fields": normalized_fields,
        }

    calendar_path = root / "calendars" / "day.txt"
    instrument_path = root / "instruments" / f"{market.lower()}.txt"
    instruments = _market_instruments(instrument_path)
    if not instruments:
        feature_root = root / "features"
        instruments = (
            sorted(
                path.name.lower() for path in feature_root.iterdir() if path.is_dir()
            )
            if feature_root.is_dir()
            else []
        )

    feature_root = root / "features"
    feature_paths = [
        feature_root / instrument / f"{field}.day.bin"
        for instrument in instruments
        for field in normalized_fields
    ]
    existing_paths = [path for path in feature_paths if path.is_file()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        feature_hashes = dict(
            zip(existing_paths, pool.map(file_sha256, existing_paths), strict=True)
        )
    feature_inventories: dict[str, list[list[Any]]] = {
        field: [] for field in normalized_fields
    }
    for instrument in instruments:
        for field in normalized_fields:
            path = feature_root / instrument / f"{field}.day.bin"
            digest = feature_hashes.get(path)
            feature_inventories[field].append(
                [
                    path.relative_to(root).as_posix(),
                    path.stat().st_size if digest is not None else None,
                    digest,
                ]
            )
    field_hashes = {
        field: sha256_value(inventory)
        for field, inventory in feature_inventories.items()
    }
    field_counts = {
        field: sum(item[1] is not None for item in inventory)
        for field, inventory in feature_inventories.items()
    }

    return {
        "provider_uri": normalized_uri,
        "provider_available": True,
        "market": market,
        "fields": normalized_fields,
        "calendar": _small_file_receipt(calendar_path, root),
        "instruments": _small_file_receipt(instrument_path, root),
        "instrument_count": len(instruments),
        "feature_file_count": sum(field_counts.values()),
        "feature_file_count_by_field": field_counts,
        "feature_content_sha256_by_field": field_hashes,
        "feature_content_inventory_sha256": sha256_value(field_hashes),
    }


def select_provider_fingerprint_fields(
    snapshot: Mapping[str, Any],
    fields: Sequence[str],
) -> dict[str, Any]:
    normalized_fields = sorted(
        {str(field).removeprefix("$").lower() for field in fields}
    )
    missing = sorted(set(normalized_fields) - set(snapshot.get("fields", [])))
    if missing:
        raise ValueError(f"provider fingerprint missing requested fields: {missing}")
    selected = dict(snapshot)
    selected["fields"] = normalized_fields
    if not snapshot.get("provider_available"):
        return selected
    counts = snapshot["feature_file_count_by_field"]
    hashes = snapshot["feature_content_sha256_by_field"]
    selected_counts = {field: counts[field] for field in normalized_fields}
    selected_hashes = {field: hashes[field] for field in normalized_fields}
    selected["feature_file_count"] = sum(selected_counts.values())
    selected["feature_file_count_by_field"] = selected_counts
    selected["feature_content_sha256_by_field"] = selected_hashes
    selected["feature_content_inventory_sha256"] = sha256_value(selected_hashes)
    return selected


def expression_fields(expressions: Sequence[str]) -> list[str]:
    return sorted(
        {
            match.group(0)
            for expression in expressions
            for match in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*", str(expression))
        }
    )


def diagnostic_metadata(producer_paths: Sequence[str | Path]) -> dict[str, Any]:
    paths = [Path(path).resolve() for path in producer_paths]
    existing = [path for path in paths if path.is_file()]
    repo = _find_git_root(existing[0]) if existing else None
    versions: dict[str, str | None] = {}
    for distribution in ("pandas", "numpy", "pyarrow", "pyqlib"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "producer_files": [
            {"path": path.as_posix(), "sha256": file_sha256(path)} for path in existing
        ],
        "git_commit": (
            _git_output(repo, "rev-parse", "HEAD") if repo is not None else None
        ),
        "environment": {
            "python": platform.python_version(),
            "packages": versions,
        },
    }


def write_dataframe_cache(
    path: str | Path,
    frame: Any,
    fingerprint: Mapping[str, Any],
    *,
    diagnostics: Mapping[str, Any],
) -> Path:
    target = Path(path)
    cache_metadata_path(target).unlink(missing_ok=True)
    with atomic_output_path(target) as temporary:
        frame.to_parquet(temporary, index=False, compression="zstd")
    metadata = {
        "fingerprint": fingerprint,
        "frame": {
            "row_count": int(len(frame)),
            "columns": [str(column) for column in frame.columns],
            "dtypes": {
                str(column): str(dtype) for column, dtype in frame.dtypes.items()
            },
        },
        "diagnostics": diagnostics,
    }
    atomic_write_json(cache_metadata_path(target), metadata)
    return target


def read_dataframe_cache(
    path: str | Path,
    fingerprint: Mapping[str, Any],
) -> Any | None:
    import pandas as pd

    target = Path(path)
    metadata_path = cache_metadata_path(target)
    if not target.is_file() or not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        actual_fingerprint = metadata["fingerprint"]
        if actual_fingerprint.get("cache_key") != fingerprint.get("cache_key"):
            return None
        if actual_fingerprint.get("component_hashes") != fingerprint.get(
            "component_hashes"
        ):
            return None
        frame = pd.read_parquet(target)
        expected_frame = metadata["frame"]
        if int(expected_frame["row_count"]) != len(frame):
            return None
        if list(expected_frame["columns"]) != [str(column) for column in frame.columns]:
            return None
        expected_dtypes = {
            str(key): str(value) for key, value in expected_frame["dtypes"].items()
        }
        if expected_dtypes != {
            str(column): str(dtype) for column, dtype in frame.dtypes.items()
        }:
            return None
        return frame
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return None

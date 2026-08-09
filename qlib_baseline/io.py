from __future__ import annotations

import json
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def atomic_output_path(path: str | Path) -> Iterator[Path]:
    """Yield a same-directory temporary path and atomically replace the target."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        yield temporary
        temporary.replace(target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(
    path: str | Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> Path:
    target = Path(path)
    with atomic_output_path(target) as temporary:
        temporary.write_text(text, encoding=encoding)
    return target


def atomic_write_json(
    path: str | Path,
    payload: Mapping[str, Any],
    *,
    ensure_ascii: bool = False,
    indent: int = 2,
    sort_keys: bool = True,
) -> Path:
    text = json.dumps(
        payload,
        ensure_ascii=ensure_ascii,
        indent=indent,
        sort_keys=sort_keys,
        default=str,
    ) + "\n"
    return atomic_write_text(path, text)

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Iterable


class StageOutputPublisher:
    """Publish a controlled stage output set without mixing old and new runs."""

    def __init__(self, output_dir: Path, controlled_outputs: Iterable[str]):
        self.output_dir = output_dir.resolve()
        self.controlled_outputs = tuple(sorted({Path(item).as_posix() for item in controlled_outputs}))
        self.staging_dir = self.output_dir.parent / f".{self.output_dir.name}.staging-{uuid.uuid4().hex[:8]}"

    def __enter__(self) -> "StageOutputPublisher":
        self.staging_dir.mkdir(parents=True, exist_ok=False)
        return self

    def path(self, relative: str) -> Path:
        normalized = Path(relative).as_posix()
        if normalized not in self.controlled_outputs:
            raise ValueError(f"not a controlled stage output: {relative}")
        path = (self.staging_dir / relative).resolve()
        if self.staging_dir.resolve() not in path.parents:
            raise ValueError(f"staging path escapes output directory: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def publish(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for relative in self.controlled_outputs:
            source = self.staging_dir / relative
            target = (self.output_dir / relative).resolve()
            if self.output_dir not in target.parents:
                raise ValueError(f"target escapes output directory: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_file():
                source.replace(target)
            elif source.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                source.replace(target)
            elif target.is_file() or target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
        self.discard()

    def discard(self) -> None:
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            self.discard()

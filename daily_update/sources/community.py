from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


COMMUNITY_REPOSITORY = "https://github.com/chenditc/investment_data"


@dataclass(frozen=True)
class CommunityRelease:
    tag: str
    target_trade_date: date
    manifest_url: str
    archive_url: str
    archive_size: int
    archive_sha256: str


def _request(url: str):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "qlib-baseline-daily-update-v1"},
    )
    return urllib.request.urlopen(request, timeout=60)


def latest_community_release() -> CommunityRelease:
    # The redirect is not rate limited like GitHub's anonymous API.
    with _request(f"{COMMUNITY_REPOSITORY}/releases/latest") as response:
        tag = response.geturl().rstrip("/").rsplit("/", 1)[-1]
    manifest_url = f"{COMMUNITY_REPOSITORY}/releases/download/{tag}/qlib_bin.manifest.json"
    with _request(manifest_url) as response:
        payload = json.load(response)
    digest = str(payload["archive_sha256"]).removeprefix("sha256:")
    return CommunityRelease(
        tag=str(payload["release_tag"]),
        target_trade_date=date.fromisoformat(str(payload["target_trade_date"])),
        manifest_url=manifest_url,
        archive_url=f"{COMMUNITY_REPOSITORY}/releases/download/{tag}/qlib_bin.tar.gz",
        archive_size=int(payload["archive_size_bytes"]),
        archive_sha256=digest,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_community_provider(release: CommunityRelease, cache_dir: Path) -> Path:
    root = cache_dir / "community" / release.tag
    ready = root / ".ready"
    if ready.is_file():
        provider = Path(ready.read_text(encoding="utf-8").strip())
        if (provider / "calendars/day.txt").is_file():
            return provider
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "qlib_bin.tar.gz"
    if not archive.is_file() or archive.stat().st_size != release.archive_size:
        partial = archive.with_suffix(".partial")
        with _request(release.archive_url) as response, partial.open("wb") as stream:
            shutil.copyfileobj(response, stream, length=1024 * 1024)
        partial.replace(archive)
    if _sha256(archive) != release.archive_sha256:
        raise ValueError("Community archive sha256 mismatch")
    extract_root = root / "extracted"
    if not extract_root.is_dir():
        stage = root / "extracting"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir()
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(stage, filter="data")
        stage.replace(extract_root)
    candidates = [
        extract_root,
        *[p for p in extract_root.rglob("calendars") if p.is_dir()],
    ]
    provider = next(
        (
            p if p.name != "calendars" else p.parent
            for p in candidates
            if (p / "day.txt").is_file()
            or (p / "calendars/day.txt").is_file()
        ),
        None,
    )
    if provider is None:
        raise ValueError("Community archive does not contain a Qlib provider")
    ready.write_text(str(provider.resolve()) + "\n", encoding="utf-8")
    return provider


def community_daily(provider: Path, target: date, instruments: list[str]) -> pd.DataFrame:
    fields = ["$open", "$high", "$low", "$close", "$volume", "$amount", "$factor"]
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(
        instruments,
        fields,
        start_time=target.isoformat(),
        end_time=target.isoformat(),
        freq="day",
    ).reset_index()
    factor = pd.to_numeric(frame["$factor"], errors="coerce")
    result = pd.DataFrame(
        {
            "date": frame["datetime"],
            "symbol": frame["instrument"].astype(str).str.upper(),
        }
    )
    for name in ("open", "high", "low", "close"):
        result[f"raw_{name}"] = pd.to_numeric(frame[f"${name}"], errors="coerce") / factor
    result["raw_volume"] = pd.to_numeric(frame["$volume"], errors="coerce") * factor * 100.0
    result["raw_amount"] = pd.to_numeric(frame["$amount"], errors="coerce") * 1000.0
    result["factor"] = factor
    return result.dropna(
        subset=[
            "raw_open",
            "raw_high",
            "raw_low",
            "raw_close",
            "raw_volume",
            "raw_amount",
        ]
    )

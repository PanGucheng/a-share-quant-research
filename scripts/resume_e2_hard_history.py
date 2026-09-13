# ruff: noqa: E402
"""Resume network inventories without changing any parent or failed receipt."""

from pathlib import Path
import argparse
import hashlib
import json
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import scan_e2_hard_history as original

BASE = original.BASE


def code_binding():
    paths = [
        "scripts/resume_e2_hard_history.py",
        "scripts/scan_e2_hard_history.py",
        "scripts/probe_e2_hard_blockers.py",
        "data_source_audit/sources/baostock.py",
        "qlib_integration/economic_readiness_closure.py",
        "qlib_integration/economic_data_readiness.py",
    ]
    return {
        p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for p in paths
    }


def close_bao_socket():
    # A failed session must not poison the next login. No network logout on a
    # broken connection: vendor logout itself may wait for another timeout.
    import baostock.common.context as context

    sock = getattr(context, "default_socket", None)
    if sock is not None:
        sock.close()
        context.default_socket = None


def fetch(mode, key, start):
    if mode == "dividends":
        return original.query("dividend", dict(ex_date=key.replace("-", "")), original.DIV_FIELDS)
    import baostock as bs
    import baostock.common.context as context

    socket.setdefaulttimeout(20)
    if getattr(context, "default_socket", None) is None:
        login = bs.login()
        if login.error_code != "0":
            raise RuntimeError(f"Bao login code {login.error_code}")
    return original.collect_one(key, start, "2023-12-29")


def checked_receipt(path):
    r = json.loads(path.read_text(encoding="utf-8"))
    if r.get("status") != "complete":
        return None
    if not r.get("files"):
        raise ValueError(f"empty completed receipt: {path}")
    for name, digest in r["files"].items():
        if Path(name).name != name or original.sha(path.parent / name) != digest:
            raise ValueError(f"completed evidence changed: {path}")
    return r


def resume(mode):
    if mode not in ("states", "dividends"):
        raise ValueError("network recovery only; completed quotes must not rerun")
    days, starts = original.scope_inventory()
    parent = BASE / f"full_{mode}"
    scope_path = parent / "scope.json"
    old = json.loads(scope_path.read_text(encoding="utf-8"))
    if old["days"] != days or old["starts"] != starts or old["mode"] != mode:
        raise ValueError("parent scope mismatch")
    for p, digest in old["code_lf"].items():
        if hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != digest:
            raise ValueError("parent code binding changed; do not rewrite scope")
    if (parent / "complete.json").exists():
        raise ValueError("parent already complete; do not rerun")
    out = BASE / f"recovery_{mode}_v1"
    binding = dict(
        mode=mode,
        parent_scope_sha256=original.sha(scope_path),
        code_lf=code_binding(),
        end="2023-12-29",
        outcome_access=False,
        e2_ready=False,
    )
    if out.exists():
        if json.loads((out / "scope.json").read_text(encoding="utf-8")) != binding:
            raise ValueError("recovery scope changed; preserve existing attempts")
    else:
        out.mkdir()
        original.put(out / "scope.json", binding)
    if (out / "complete.json").exists():
        raise ValueError("recovery already complete; do not rerun")
    jobs = sorted(starts) if mode == "states" else days
    selected = {}
    adopted = 0
    try:
        for i, key in enumerate(jobs):
            parent_path = parent / f"{key}.json"
            if parent_path.exists() and checked_receipt(parent_path):
                selected[key] = parent_path
                adopted += 1
                continue
            stock_dir = out / key
            stock_dir.mkdir(exist_ok=True)
            completed = [
                p for p in sorted(stock_dir.glob("attempt_*/receipt.json")) if checked_receipt(p)
            ]
            if len(completed) > 1:
                raise ValueError("multiple completed attempts require review")
            if completed:
                selected[key] = completed[0]
                continue
            attempt_no = 1 + max(
                [int(p.name.split("_")[1]) for p in stock_dir.glob("attempt_*")], default=0
            )
            attempt = stock_dir / f"attempt_{attempt_no:04d}"
            attempt.mkdir()
            original.put(
                attempt / "request.json",
                dict(
                    key=key,
                    start=starts[key] if mode == "states" else key,
                    end="2023-12-29" if mode == "states" else key,
                    previous_receipt_sha256=original.sha(parent_path)
                    if parent_path.exists()
                    else None,
                ),
            )
            try:
                f, status = fetch(mode, key, starts.get(key))
                if status != "success":
                    raise RuntimeError(f"source status {status}")
                if mode == "states" and len(f):
                    if (
                        not f.date.between(starts[key], "2023-12-29").all()
                        or f.date.duplicated().any()
                    ):
                        raise ValueError("state date coverage contradiction")
                if mode == "dividends":
                    if len(f) >= 2000 or (len(f) and not f.ex_date.eq(key.replace("-", "")).all()):
                        raise ValueError("dividend truncation/date contradiction")
                f.to_parquet(attempt / "data.parquet", index=False)
                original.put(
                    attempt / "receipt.json",
                    dict(
                        status="complete",
                        rows=len(f),
                        files={"data.parquet": original.sha(attempt / "data.parquet")},
                    ),
                )
            except BaseException as exc:
                # No token-bearing HTTP bodies are printed or stored. Source
                # statuses above contain only Bao status or Tushare error code.
                detail = (
                    str(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__
                )
                original.put(
                    attempt / "receipt.json",
                    dict(
                        status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                        error_type=type(exc).__name__,
                        detail=detail,
                        files={},
                    ),
                )
                raise
            selected[key] = attempt / "receipt.json"
            print(f"{mode}: {i + 1}/{len(jobs)}; parent reused={adopted}; saved {key}", flush=True)
            time.sleep(0.25)  # modest request pacing, no automatic error retries
        rows = 0
        references = {}
        for key, path in selected.items():
            receipt = checked_receipt(path)
            if receipt is None:
                raise ValueError("selected incomplete receipt")
            rows += receipt["rows"]
            references[key] = dict(path=str(path.relative_to(BASE)), sha256=original.sha(path))
        original.put(
            out / "complete.json",
            dict(
                mode=mode,
                chunks=len(selected),
                rows=rows,
                references=references,
                e2_ready=False,
                coverage="network inventory only; not execution readiness",
            ),
        )
        print(f"{mode} recovery inventory complete; E2 remains BLOCKED", flush=True)
    finally:
        if mode == "states":
            close_bao_socket()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["states", "dividends"])
    resume(parser.parse_args().mode)

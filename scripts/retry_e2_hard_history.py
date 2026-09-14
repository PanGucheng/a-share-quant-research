# ruff: noqa: E402
"""Bounded transport retries around the unchanged, hash-bound E2 resume entry."""

from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import re
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import requests
from scripts import resume_e2_hard_history as recovery


def transient_network_error(exc):
    if isinstance(exc, requests.exceptions.SSLError):
        return False
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    # Exact vendor receive error only; permissions, validation, hash failures,
    # arbitrary RuntimeError and user interruption are deliberately excluded.
    return (
        type(exc) is RuntimeError
        and re.fullmatch(r"(?:source status|Bao login code) 10002007(?::[^\r\n]*)?", str(exc))
        is not None
    )


def run(mode, *, max_retries=100, retry_delay=30, max_delay=120):
    if mode not in ("states", "dividends") or not 0 <= max_retries <= 100:
        raise ValueError("invalid retry mode/budget")
    if not 1 <= retry_delay <= max_delay <= 600:
        raise ValueError("invalid retry delay")
    folder = recovery.BASE / "retry_sessions" / uuid4().hex
    folder.mkdir(parents=True)
    put = recovery.original.put
    put(
        folder / "scope.json",
        dict(
            mode=mode,
            max_retries=max_retries,
            retry_delay=retry_delay,
            max_delay=max_delay,
            started_at=datetime.now(timezone.utc).isoformat(),
            wrapper_sha256_lf=hashlib.sha256(
                Path(__file__).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest(),
            recovery_code_lf=recovery.code_binding(),
            policy="whole-invocation retry budget; immutable attempts; no automatic stage switch",
        ),
    )
    try:
        for attempt in range(max_retries + 1):
            try:
                # resume() closes a failed Bao connection in finally. Its next
                # invocation revalidates saved chunks and logs in afresh.
                recovery.resume(mode)
            except Exception as exc:
                retryable = transient_network_error(exc)
                will_retry = retryable and attempt < max_retries
                delay = min(retry_delay * 2**attempt, max_delay) if will_retry else 0
                put(
                    folder / f"attempt_{attempt + 1:03d}.json",
                    dict(
                        status="failed",
                        error_type=type(exc).__name__,
                        retryable=retryable,
                        will_retry=will_retry,
                        wait_seconds=delay,
                    ),
                )
                if not will_retry:
                    raise
                print(
                    f"{mode}: network failure; retry {attempt + 1}/{max_retries} in {delay}s. "
                    "Saved chunks retained; reconnecting on resume.",
                    flush=True,
                )
                time.sleep(delay)
            else:
                put(folder / f"attempt_{attempt + 1:03d}.json", dict(status="complete"))
                put(folder / "result.json", dict(status="complete", retries_used=attempt))
                return
    except BaseException as exc:
        put(
            folder / "result.json",
            dict(
                status="interrupted" if isinstance(exc, KeyboardInterrupt) else "stopped",
                error_type=type(exc).__name__,
            ),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["states", "dividends"])
    parser.add_argument("--max-retries", type=int, default=100)
    parser.add_argument("--retry-delay", type=int, default=30)
    parser.add_argument("--max-delay", type=int, default=120)
    args = parser.parse_args()
    run(
        args.mode,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        max_delay=args.max_delay,
    )

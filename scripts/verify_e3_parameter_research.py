# ruff: noqa: E402
"""Independent scalar membership/queue oracle, using original sealed B scores."""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model_research.economic_prediction_structure import BoundedScores, sha, json_text, require


def oracle(days, rankings, spec):
    k, h, d = spec["k"], spec["hold"], spec["interval"]
    limit = k if spec["cap"] is None else spec["cap"]
    owned, deferred, since = [], {}, {}
    rows, spells, episodes = [], [], []
    for t, day in enumerate(days):
        before = sorted(owned)
        ranking = rankings[t - 1] if t else []
        positions = {s: ranking.index(s) + 1 for s in owned if s in ranking}
        is_decision = t >= 1 and (t - 1) % d == 0
        sell, buy, queue, buffer = [], [], [], 0
        stale = [s for s in owned if positions.get(s, math.inf) > h]
        if is_decision:
            # Walk ranking in reverse, with absent symbols ordered first.
            ordered = sorted(s for s in stale if s not in positions)
            ordered += [s for s in reversed(ranking) if s in stale]
            sell = ordered[:limit]
            buffer = len([s for s in owned if k < positions.get(s, math.inf) <= h])
            for s, start in list(deferred.items()):
                resolution = "sold" if s in sell else "recovered" if s not in stale else None
                if resolution:
                    episodes.append(dict(instrument=s, start=days[start], end=day,
                                         age_sessions=t - start, resolution=resolution))
                    del deferred[s]
            for s in sell:
                owned.remove(s)
            for s in ranking[:k]:
                if s not in owned and len(owned) < k and len(buy) < (k if t == 1 else limit):
                    owned.append(s)
                    buy.append(s)
            for s in sorted(stale):
                if s not in sell:
                    if s not in deferred:
                        deferred[s] = t
                    queue.append(dict(instrument=s, rank=positions.get(s), age_sessions=t - deferred[s]))
        for s in sorted(set(before) - set(owned)):
            start = since.pop(s)
            spells.append(dict(instrument=s, start=days[start], end_exclusive=day,
                               sessions=t - start, right_censored=False))
        for s in sorted(set(owned) - set(before)):
            since[s] = t
        rows.append(dict(date=day, scheduled=is_decision, before=before, after=sorted(owned),
            entries=buy, exits=sell, buffer_retained=buffer, queue=queue,
            cap_binding=is_decision and len(stale) > limit,
            stale_after=[dict(instrument=s, rank=ranking.index(s) + 1 if s in ranking else None)
                for s in sorted(owned) if s not in ranking or ranking.index(s) + 1 > h],
            churn=(len(buy) + len(sell)) / (2 * k)))
    for s, start in sorted(since.items()):
        spells.append(dict(instrument=s, start=days[start], end_exclusive=None,
                           sessions=len(days) - start, right_censored=True))
    for s, start in sorted(deferred.items()):
        episodes.append(dict(instrument=s, start=days[start], end=None,
                             age_sessions=len(days) - 1 - start, resolution="right_censored"))
    return rows, spells, episodes


def verify(root, out, contract):
    receipt = json.loads((out / "receipt.json").read_text(encoding="utf-8"))
    for name, expected in receipt["files"].items():
        require(sha(out / name) == expected, f"changed result: {name}")
    require(sha(contract) == receipt["search_sha256"], "search mismatch")
    import hashlib
    for name, expected in receipt["code_lf"].items():
        require(hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected,
                f"code changed: {name}")
    search = json.loads(contract.read_text(encoding="utf-8"))
    reader = BoundedScores(root=root, inventory=root / "reports/economic_translation_mvp/e1_inputs.json")
    data = reader.load()
    days, ranks = [], []
    for date, frame in data.groupby("datetime", sort=True):
        pairs = list(zip(frame.instrument, frame.score))
        require(all(math.isfinite(float(v)) for _, v in pairs), "nonfinite score")
        pairs.sort(key=lambda x: (-float(x[1]), x[0]))
        days.append(str(date.date()))
        ranks.append([s for s, _ in pairs])
    for spec in search["candidates"]:
        actual = json.loads((out / (spec["id"] + ".json")).read_text(encoding="utf-8"))
        rows, spells, episodes = oracle(days, ranks, spec)
        require(actual == dict(rows=rows, spells=spells, episodes=episodes), "independent target mismatch: " + spec["id"])
    access = json.loads((out / "access.json").read_text(encoding="utf-8"))
    for row in access:
        if "sha256" in row:
            require(sha(root / row["path"]) == row["sha256"], "dependency source changed")
    result = dict(status="PASS_ALL_TARGET_ROWS_SPELLS_QUEUES", candidates=len(search["candidates"]),
        sessions=len(days), original_scores_independently_sorted=True,
        source_inputs_hash_verified=True, actual_path_verified=False,
        summary_scope="production aggregations over independently matched raw diagnostics; not economic validation",
        receipt_sha256=sha(out / "receipt.json"), search_sha256=sha(contract))
    with (out / "independent_verification.json").open("x", encoding="utf-8", newline="\n") as f:
        f.write(json_text(result))
    return result


if __name__ == "__main__":
    from scripts.study_e3_parameter_research import OUT, CONTRACT, offline
    offline()
    print(json_text(verify(ROOT, OUT, CONTRACT)))

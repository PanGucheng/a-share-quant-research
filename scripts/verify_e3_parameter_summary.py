# ruff: noqa: E402
"""Independent aggregation check of every published structural summary field."""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from model_research.economic_prediction_structure import sha, json_text


def check_equal(a, b):
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            check_equal(a[key], b[key])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            check_equal(x, y)
    elif isinstance(a, float):
        assert b is not None and math.isclose(a, b, rel_tol=1e-13, abs_tol=1e-13)
    else:
        assert a == b


def dist(values):
    if not values:
        return dict(n=0, mean=None, median=None, p90=None, max=None)
    v = np.asarray(values)
    return dict(n=len(v), mean=float(v.mean()), median=float(np.median(v)),
                p90=float(np.quantile(v, .9, method="inverted_cdf")), max=float(v.max()))


def verify_summary(out):
    summaries = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    for s in summaries:
        obj = json.loads((out / (s["candidate"]["id"] + ".json")).read_text(encoding="utf-8"))
        rows, spells, episodes = (obj[k] for k in ("rows", "spells", "episodes"))
        decisions = [r for r in rows if r["scheduled"]][1:]
        nq = sum(bool(r["queue"]) for r in decisions)
        den = sum(len(r["before"]) for r in decisions)
        resolved = [e for e in episodes if e["end"] is not None]
        finite_rank = [a["rank"] for r in rows[1:] for a in r["stale_after"] if a["rank"] is not None]
        annual = []
        for year in sorted({r["date"][:4] for r in rows}):
            part = [r for r in rows if r["date"][:4] == year]
            ds = [r for r in decisions if r["date"][:4] == year]
            annual.append(dict(year=int(year), decisions=sum(r["scheduled"] for r in part),
                exits=sum(len(r["exits"]) for r in part), entries=sum(len(r["entries"]) for r in part),
                cap_binding=sum(bool(r["queue"]) for r in ds), subsequent_decisions=len(ds),
                target_slot_churn=sum((len(r["entries"]) + len(r["exits"])) / (2 * s["candidate"]["k"])
                    for r in part if r["date"] != rows[1]["date"])))
        longest = n = 0
        for r in rows[1:]:
            n = n + 1 if len(r["after"]) < s["candidate"]["k"] else 0
            longest = max(longest, n)
        expected = dict(candidate=s["candidate"], role="IDEAL_TARGET_NOT_EXECUTABLE_ACCOUNT",
            sessions=len(rows), decisions=1 + len(decisions), subsequent_decisions=len(decisions),
            trade_decision_fraction=sum(r["before"] != r["after"] for r in decisions) / len(decisions),
            target_exits=sum(len(r["exits"]) for r in rows), cap_binding_frequency=nq / len(decisions),
            cap_binding_count=nq, queue_depth=dist([len(r["queue"]) for r in decisions]),
            queue_age=dist([a["age_sessions"] for r in decisions for a in r["queue"]]),
            episodes={v: sum(e["resolution"] == v for e in episodes) for v in ("sold", "recovered", "right_censored")},
            recovery_fraction_resolved=sum(e["resolution"] == "recovered" for e in resolved) / len(resolved) if resolved else None,
            max_episode_age=max((e["age_sessions"] for e in episodes), default=None),
            stale_rank=dist(finite_rank), stale_absent_observations=sum(a["rank"] is None for r in rows[1:] for a in r["stale_after"]),
            buffer_fraction=sum(r["buffer_retained"] for r in decisions) / den,
            closed_holding_sessions=dist([a["sessions"] for a in spells if not a["right_censored"]]),
            right_censored_spells=sum(a["right_censored"] for a in spells),
            target_daily_churn_ex_initial=float(np.mean([r["churn"] for r in rows[2:]])),
            min_target_slots=min(len(r["after"]) for r in rows[1:]), longest_target_underfill=longest,
            annual=annual, flags=["PERSISTENT_CAP_BACKLOG"] if nq / len(decisions) >= .8 else [],
            economic_eligible=True, actual_path_status="NOT_STARTED", actual_R1=None, actual_R2=None, actual_R3=None,
            actual_cash_idle=None, actual_turnover=None, economic_metrics=None)
        check_equal(s, expected)
    return dict(status="PASS_ALL_30_SUMMARIES_INDEPENDENT_AGGREGATION", summary_sha256=sha(out / "summary.json"),
                candidates=len(summaries), economic_validation=False)


if __name__ == "__main__":
    out = ROOT / "outputs/economic_translation_mvp/e3_parameter_research_v2"
    result = verify_summary(out)
    result.update(code_sha256_lf=__import__("hashlib").sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                  raw_oracle_sha256=sha(out / "independent_verification.json"), receipt_sha256=sha(out / "receipt.json"))
    with (out / "summary_verification.json").open("x", encoding="utf-8", newline="\n") as f:
        f.write(json_text(result))
    print(json_text(result))

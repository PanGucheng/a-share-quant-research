# ruff: noqa: E402
"""Independent scalar target oracle; no production E3 strategy/projection imports."""

import hashlib
import json
from pathlib import Path
import socket
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model_research.economic_prediction_structure import BoundedScores, sha, json_text

OUT = ROOT / "outputs/economic_translation_mvp/e3_preflight_v2"
REPORT = ROOT / "reports/economic_translation_mvp/e3_freeze_v1"


def verify_targets(data, calendar, rows, spells, summary):
    groups = {str(date.date()): dict(zip(group.instrument, group.score)) for date, group in data.groupby("datetime")}
    dates = [str(d.date()) for d in calendar]
    assert len(rows) == len(dates) and [r["date"] for r in rows] == dates
    held, start, expected_spells = set(), {}, []
    for i, date in enumerate(dates):
        row = rows[i]
        before = held.copy()
        scheduled = i > 0 and (i - 1) % 5 == 0
        assert row["scheduled"] == scheduled and row["first_decision"] == (i == 1)
        assert row["signal_date"] == (dates[i - 1] if i else None)
        assert row["before"] == sorted(before)
        assert row["model_boundary"] == (i > 1 and dates[i - 2][:4] != dates[i - 1][:4])
        sell, buffer, backlog = None, 0, 0
        if scheduled:
            values = groups[dates[i - 1]]
            ordered = sorted(values, key=lambda s: (-values[s], s))
            rank = {s: j + 1 for j, s in enumerate(ordered)}
            exits = sorted((s for s in held if rank.get(s, float("inf")) > 16),
                           key=lambda s: (-rank.get(s, float("inf")), s))
            buffer = sum(8 < rank.get(s, float("inf")) <= 16 for s in held)
            backlog = max(0, len(exits) - 1)
            if exits:
                sell = exits[0]
                held.remove(sell)
            # First decision initializes; all later decisions can add at most one identity.
            remaining_budget = min(8 - len(held), 8 if i == 1 else 1)
            for s in ordered[:8]:
                if s not in held and remaining_budget:
                    held.add(s)
                    remaining_budget -= 1
        assert (row["buffer_retained"], row["exit_backlog"], row["target_exit"]) == (buffer, backlog, sell)
        assert row["after"] == sorted(held) and row["slots"] == len(held)
        assert row["empty_slots"] == 8 - len(held)
        assert row["entries"] == sorted(held - before) and row["exits"] == sorted(before - held)
        assert row["churn_fixed_slots"] == (len(held - before) + len(before - held)) / 16
        for s in before - held:
            begin = start.pop(s)
            expected_spells.append(dict(instrument=s, start=dates[begin], end_exclusive=date,
                                        sessions=i - begin, right_censored=False))
        for s in held - before:
            start[s] = i
    for s, begin in sorted(start.items()):
        expected_spells.append(dict(instrument=s, start=dates[begin], end_exclusive=None,
                                    sessions=len(dates) - begin, right_censored=True))
    def key(s):
        return s["start"], s["instrument"]
    assert sorted(spells, key=key) == sorted(expected_spells, key=key)
    closed = [s["sessions"] for s in spells if not s["right_censored"]]
    decisions = [r for r in rows if r["scheduled"]]
    noninitial = [r for r in rows if r["signal_date"] and not r["first_decision"]]
    assert summary["scheduled"] == len(decisions)
    assert summary["target_closed_spells"] == len(closed)
    assert summary["right_censored_spells"] == len(spells) - len(closed)
    assert summary["target_closed_spell_mean"] == (statistics.mean(closed) if closed else None)
    assert summary["target_closed_spell_median"] == (statistics.median(closed) if closed else None)
    assert summary["target_daily_churn_ex_initial"] == statistics.mean(r["churn_fixed_slots"] for r in noninitial)
    den = sum(len(r["before"]) for r in decisions)
    assert summary["buffer_retained_fraction"] == (sum(r["buffer_retained"] for r in decisions) / den if den else None)
    assert summary["cap_backlog_decisions"] == sum(r["exit_backlog"] > 0 for r in decisions)
    assert summary["minimum_target_slots_after_initial"] == min(r["slots"] for r in rows[1:])
    run, longest = 0, 0
    for r in rows[1:]:
        run = run + 1 if r["slots"] < 8 else 0
        longest = max(run, longest)
    assert summary["longest_target_underfilled_sessions"] == longest
    assert summary["model_boundaries"] == sum(r["model_boundary"] for r in rows)
    for annual in summary["annual"]:
        subset = [r for r in rows if r["date"].startswith(str(annual["year"]))]
        assert annual == dict(year=annual["year"], scheduled=sum(r["scheduled"] for r in subset),
                              target_exits=sum(len(r["exits"]) for r in subset),
                              target_entries=sum(len(r["entries"]) for r in subset),
                              cap_backlog_decisions=sum(r["exit_backlog"] > 0 for r in subset))
    for name, value in summary.items():
        if name.startswith("actual_"):
            assert value is None
    return dict(target_sessions=len(rows), target_spells=len(spells), independently_reranked=True)


def main():
    def deny(*args, **kwargs):
        raise RuntimeError("independent E3 verification offline")
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    def get(name):
        return json.loads((OUT / name).read_text(encoding="utf-8"))
    for name, digest in get("receipt.json").items():
        assert Path(name).name == name and sha(OUT / name) == digest
    binding = get("binding.json")
    assert binding["freeze_sha256"] == sha(REPORT / "freeze.json") == (REPORT / "freeze.sha256").read_text().strip()
    for name, digest in binding["code_sha256_lf"].items():
        assert hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest
    audit = []
    reader = BoundedScores(audit=audit)
    data = reader.load()
    result = verify_targets(data, reader.calendar, get("target_days.json"), get("target_spells.json"), get("target_summary.json"))
    probe = get("actual_dependency_probe.json")
    first = data[data.datetime.eq(reader.calendar[0])]
    scores = dict(zip(first.instrument, first.score))
    assert probe["original_top8"] == sorted(scores, key=lambda s: (-scores[s], s))[:8]
    assert probe["actual_sessions"] == 0 and all(probe[f"actual_R{i}"] is None for i in (1, 2, 3))
    assert not binding["actual_path_passed"] and not binding["outcomes"]
    source_files = 0
    for record in get("access.json"):
        if "sha256" in record:
            assert sha(ROOT / record["path"]) == record["sha256"]
            source_files += 1
        if record.get("role") == "E3_first_entry":
            assert record["start"] >= probe["signal"] and record["end"] <= probe["session"]
            assert set(record["columns"]) <= {"date", "instrument", "asset_id", "execution_code_reference", "board", "quote_status", "code", "tradestatus", "isST"}
    result.update(status="PASS_TARGET_ONLY_ACTUAL_PENDING", source_files=source_files,
                  freeze_sha256=sha(REPORT / "freeze.json"), receipt_sha256=sha(OUT / "receipt.json"),
                  actual_R1=None, actual_R2=None, actual_R3=None)
    with (OUT / "independent_verification.json").open("x", encoding="utf-8") as f:
        f.write(json_text(result))
    print(json_text(result))


if __name__ == "__main__":
    main()

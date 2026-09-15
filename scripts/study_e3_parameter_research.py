# ruff: noqa: E402
"""Offline 30-candidate target screen; economic execution remains fail-closed."""
import hashlib
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model_research.economic_prediction_structure import BoundedScores, sha, json_text, require
from model_research.economic_e3_parameter_structure import candidates, ranked_calendar, project, summarize
from scripts.audit_e3_parameter_inputs import audit_first

CONTRACT = ROOT / "reports/economic_translation_mvp/e3_parameter_research_v1/search.json"
OUT = ROOT / "outputs/economic_translation_mvp/e3_parameter_research_v2"
SEARCH_SHA = "08e281cfa4986350aa8bddc4791c5e32ff83d793aae746ceb0104cd55201545a"
CODE = ["model_research/economic_e3_parameter_structure.py", "model_research/economic_prediction_structure.py",
        "scripts/study_e3_parameter_research.py", "scripts/verify_e3_parameter_research.py",
        "scripts/audit_e3_parameter_inputs.py", "scripts/preflight_e3_structure.py",
        "qlib_integration/economic_strategy_membership.py", "qlib_integration/economic_mvp_scope.py",
        "qlib_integration/economic_core_inputs.py", "qlib_integration/economic_historical_inputs.py",
        "qlib_integration/execution_readiness.py"]


def offline():
    def deny(*args, **kwargs):
        raise RuntimeError("parameter target study forbids network")
    socket.socket.connect = deny
    socket.socket.connect_ex = deny


def main():
    offline()
    require(sha(CONTRACT) == SEARCH_SHA, "search space changed")
    search = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(search["candidates"] == candidates(), "undeclared candidate")
    for path, expected in search["sources"].items():
        require(sha(Path(path)) == expected, "research source changed: " + path)
    OUT.mkdir(exist_ok=False)
    access = []

    def put(name, value):
        with (OUT / name).open("x", encoding="utf-8", newline="\n") as f:
            f.write(json_text(value))
    try:
        put("started.json", dict(search_sha256=SEARCH_SHA, role="structural_only", economic_outcomes=False))
        reader = BoundedScores(audit=access)
        data = reader.load()
        days, rankings = ranked_calendar(data, reader.calendar)
        summaries = []
        for spec in search["candidates"]:
            rows, spells, episodes = project(days, rankings, spec)
            put(spec["id"] + ".json", dict(rows=rows, spells=spells, episodes=episodes))
            summaries.append(summarize(rows, spells, episodes, spec))
            print(spec["id"] + ": target complete", flush=True)
        put("summary.json", summaries)
        put("actual_input_audit.json", audit_first(rankings[0][:10], access))
        put("access.json", access)
        put("receipt.json", dict(search_sha256=SEARCH_SHA,
            code_lf={name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for name in CODE},
            files={p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
            status="E3 PARAMETER RESEARCH / ACTUAL PATH BLOCKED", selected_strategy=None,
            development_tuning_complete=False, actual_metrics=None))
    except Exception as exc:
        put("failure.json", dict(error=type(exc).__name__, message=str(exc), access=access))
        raise


if __name__ == "__main__":
    main()

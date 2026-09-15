# ruff: noqa: E402
"""One-off search-space freeze; deliberately no score reader or CLI parameters."""
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model_research.economic_prediction_structure import sha, json_text
from model_research.economic_e3_parameter_structure import candidates, adjacency


def main():
    out = ROOT / "reports/economic_translation_mvp/e3_parameter_research_v1"
    out.mkdir(exist_ok=False)
    sources = [ROOT / "docs/ECONOMIC_E3_PARAMETER_RESEARCH.md",
               ROOT / "reports/economic_translation_mvp/e3_freeze_v1/freeze.json",
               ROOT / "reports/economic_translation_mvp/e1_inputs.json",
               Path("D:/Download/给 Codex：E3 Portfolio Parameter Research 与 Strategy V2 冻结.md")]
    obj = dict(kind="SEARCH_SPACE_NOT_STRATEGY_V2_FREEZE", base_commit="7202dea",
        created_utc=datetime.now(timezone.utc).isoformat(), start="2015-01-05", end="2023-12-29",
        sources={str(p): sha(p) for p in sources}, candidates=candidates(), adjacency=adjacency(candidates()),
        outcome_authorization="development_only_after_actual_path_validation",
        economic_candidates="all_30_mechanically_valid_candidates_including_v1_control",
        screening="arithmetic_failures_stop; cap_backlog_at_least_80_percent_flag_only",
        inherited_rules="all_v1_rules_except_explicit_k_hold_interval_cap_and_generalized_batch_attempts",
        long_execution="user_run", selected_strategy=None)
    with (out / "search.json").open("x", encoding="utf-8", newline="\n") as f:
        f.write(json_text(obj))
    with (out / "search.sha256").open("x", encoding="ascii", newline="\n") as f:
        f.write(sha(out / "search.json") + "\n")
    print(sha(out / "search.json"))


if __name__ == "__main__":
    main()

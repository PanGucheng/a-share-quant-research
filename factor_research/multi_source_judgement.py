from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.report import markdown_table


IC_COLUMNS = [
    "alphalens_mean_ic_10d",
    "alphalens_mean_ic_20d",
    "jqfactor_mean_ic_10d",
    "jqfactor_mean_ic_20d",
]
QLIB_IR_COLUMNS = [
    "qlib_information_ratio_10d",
    "qlib_information_ratio_20d",
]
ANN_ALPHA_COLUMNS = [
    "alphalens_ann_alpha_10d",
    "alphalens_ann_alpha_20d",
]
REQUIRED_COLUMNS = [
    "pool_name",
    "factor",
    "source_family",
    "screening_gate",
    "role",
    "coverage",
    "missing_rate",
    "alphalens_status",
    "jqfactor_status",
    "qlib_status",
]


@dataclass(frozen=True)
class MultiSourceJudgementRules:
    min_probe_coverage: float = 0.90
    max_probe_missing_rate: float = 0.10
    min_metric_value_count: int = 8
    weak_abs_ic: float = 0.015
    consistent_abs_ic: float = 0.03
    strong_abs_ic: float = 0.05
    consistent_abs_qlib_ir: float = 3.0
    strong_abs_qlib_ir: float = 4.0
    min_direction_agreement_ratio: float = 0.67
    strong_direction_agreement_ratio: float = 0.83
    min_new_source_probes: int = 5


@dataclass(frozen=True)
class MultiSourceJudgementConfig:
    screening_input: Path
    output_dir: Path
    pool_name: str
    rules: MultiSourceJudgementRules


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def numeric(row: pd.Series, column: str) -> float:
    if column not in row:
        return np.nan
    value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else np.nan


def numeric_values(row: pd.Series, columns: list[str]) -> list[float]:
    values = []
    for column in columns:
        value = numeric(row, column)
        if pd.notna(value):
            values.append(value)
    return values


def sign(value: float, tolerance: float = 1e-12) -> int:
    if pd.isna(value) or abs(value) <= tolerance:
        return 0
    return 1 if value > 0 else -1


def sign_text(value: int) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def max_abs(values: list[float]) -> float:
    if not values:
        return np.nan
    return float(np.nanmax(np.abs(values)))


def first_numeric(row: pd.Series, columns: list[str]) -> float:
    for column in columns:
        value = numeric(row, column)
        if pd.notna(value):
            return value
    return np.nan


def direction_metrics(row: pd.Series) -> dict[str, object]:
    ic_values = numeric_values(row, IC_COLUMNS)
    ir_values = numeric_values(row, QLIB_IR_COLUMNS)
    alpha_values = numeric_values(row, ANN_ALPHA_COLUMNS)
    direction_values = ic_values + ir_values
    if not direction_values:
        return {
            "primary_mean_ic": np.nan,
            "max_abs_mean_ic": np.nan,
            "max_abs_qlib_ir": np.nan,
            "max_abs_ann_alpha": np.nan,
            "consensus_direction": "neutral",
            "consensus_direction_sign": 0,
            "direction_agreement_count": 0,
            "direction_observation_count": 0,
            "direction_agreement_ratio": np.nan,
        }
    seed = float(np.nanmedian(direction_values))
    consensus_sign = sign(seed)
    if consensus_sign == 0:
        strongest = direction_values[int(np.nanargmax(np.abs(direction_values)))]
        consensus_sign = sign(strongest)
    signs = [sign(value) for value in direction_values if sign(value) != 0]
    agreement_count = sum(1 for item in signs if item == consensus_sign)
    observation_count = len(signs)
    agreement_ratio = agreement_count / observation_count if observation_count else np.nan
    return {
        "primary_mean_ic": first_numeric(
            row,
            [
                "alphalens_mean_ic_20d",
                "jqfactor_mean_ic_20d",
                "alphalens_mean_ic_10d",
                "jqfactor_mean_ic_10d",
            ],
        ),
        "max_abs_mean_ic": max_abs(ic_values),
        "max_abs_qlib_ir": max_abs(ir_values),
        "max_abs_ann_alpha": max_abs(alpha_values),
        "consensus_direction": sign_text(consensus_sign),
        "consensus_direction_sign": consensus_sign,
        "direction_agreement_count": agreement_count,
        "direction_observation_count": observation_count,
        "direction_agreement_ratio": agreement_ratio,
    }


def issue_text(items: list[str]) -> str:
    return ",".join(dict.fromkeys(item for item in items if item))


def classify_alpha158(row: pd.Series) -> dict[str, object]:
    upstream_role = str(row.get("role", "monitor"))
    return {
        "judgement_role": upstream_role,
        "research_included": upstream_role == "alpha_candidate",
        "downstream_default_included": upstream_role == "alpha_candidate",
        "judgement_label": row.get("upstream_judgement_label", upstream_role),
        "judgement_reason": row.get("pool_reason", "preserve_alpha158_candidate_pool"),
        "source_policy": "preserve_alpha158_candidate_pool",
        "judgement_issue_tags": str(row.get("issue_tags", "") if pd.notna(row.get("issue_tags", "")) else ""),
    }


def classify_new_source(row: pd.Series, rules: MultiSourceJudgementRules) -> dict[str, object]:
    if str(row.get("screening_gate", "")) == "holdout":
        return {
            "judgement_role": "holdout",
            "research_included": False,
            "downstream_default_included": False,
            "judgement_label": "holdout",
            "judgement_reason": row.get("promotion_reason", "source_holdout"),
            "source_policy": "new_source_research_probe_rules",
            "judgement_issue_tags": "holdout",
        }

    issues: list[str] = []
    metric_count = numeric(row, "metric_value_count")
    coverage = numeric(row, "coverage")
    missing_rate = numeric(row, "missing_rate")
    max_ic = numeric(row, "max_abs_mean_ic")
    max_ir = numeric(row, "max_abs_qlib_ir")
    agreement = numeric(row, "direction_agreement_ratio")

    if pd.isna(metric_count) or metric_count < rules.min_metric_value_count:
        issues.append("insufficient_metrics")
    if pd.isna(coverage) or coverage < rules.min_probe_coverage:
        issues.append("low_coverage")
    if pd.notna(missing_rate) and missing_rate > rules.max_probe_missing_rate:
        issues.append("high_missing_rate")

    if "insufficient_metrics" in issues:
        return {
            "judgement_role": "new_source_monitor",
            "research_included": False,
            "downstream_default_included": False,
            "judgement_label": "insufficient_metrics",
            "judgement_reason": "metric_value_count_below_threshold",
            "source_policy": "new_source_research_probe_rules",
            "judgement_issue_tags": issue_text(issues),
        }
    if "low_coverage" in issues or "high_missing_rate" in issues:
        return {
            "judgement_role": "new_source_data_watch",
            "research_included": False,
            "downstream_default_included": False,
            "judgement_label": "data_quality_watch",
            "judgement_reason": "coverage_or_missing_rate_outside_probe_threshold",
            "source_policy": "new_source_research_probe_rules",
            "judgement_issue_tags": issue_text(issues),
        }
    if pd.isna(max_ic) or max_ic < rules.weak_abs_ic:
        return {
            "judgement_role": "new_source_monitor",
            "research_included": False,
            "downstream_default_included": False,
            "judgement_label": "weak_signal",
            "judgement_reason": "mean_ic_below_weak_threshold",
            "source_policy": "new_source_research_probe_rules",
            "judgement_issue_tags": "weak_signal",
        }
    if pd.isna(agreement) or agreement < rules.min_direction_agreement_ratio:
        return {
            "judgement_role": "new_source_mixed_signal",
            "research_included": False,
            "downstream_default_included": False,
            "judgement_label": "mixed_direction",
            "judgement_reason": "open_source_metric_direction_agreement_below_threshold",
            "source_policy": "new_source_research_probe_rules",
            "judgement_issue_tags": "mixed_direction",
        }

    strong = (
        max_ic >= rules.strong_abs_ic
        and pd.notna(max_ir)
        and max_ir >= rules.strong_abs_qlib_ir
        and agreement >= rules.strong_direction_agreement_ratio
    )
    if strong:
        return {
            "judgement_role": "new_source_alpha_probe",
            "research_included": True,
            "downstream_default_included": False,
            "judgement_label": "strong_signal_probe",
            "judgement_reason": "passes_strong_ic_qlib_ir_direction_rules",
            "source_policy": "new_source_research_probe_rules",
            "judgement_issue_tags": "",
        }

    consistent = (
        max_ic >= rules.consistent_abs_ic
        and pd.notna(max_ir)
        and max_ir >= rules.consistent_abs_qlib_ir
        and agreement >= rules.min_direction_agreement_ratio
    )
    if consistent:
        return {
            "judgement_role": "new_source_alpha_probe",
            "research_included": True,
            "downstream_default_included": False,
            "judgement_label": "consistent_signal_probe",
            "judgement_reason": "passes_consistent_ic_qlib_ir_direction_rules",
            "source_policy": "new_source_research_probe_rules",
            "judgement_issue_tags": "",
        }

    return {
        "judgement_role": "new_source_monitor",
        "research_included": False,
        "downstream_default_included": False,
        "judgement_label": "monitor",
        "judgement_reason": "signal_strength_below_probe_threshold",
        "source_policy": "new_source_research_probe_rules",
        "judgement_issue_tags": "",
    }


def validate_input(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"multi-source screening input missing required columns: {missing}")
    if frame["factor"].duplicated().any():
        duplicates = frame.loc[frame["factor"].duplicated(), "factor"].tolist()
        raise ValueError(f"multi-source screening input has duplicated factors: {duplicates[:10]}")


def build_judgement_board(config: MultiSourceJudgementConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = read_csv_or_empty(config.screening_input)
    if source.empty:
        raise FileNotFoundError(f"Missing or empty screening input: {config.screening_input}")
    validate_input(source)

    board = source.copy()
    board["upstream_role"] = board["role"]
    board["upstream_pool_reason"] = board["pool_reason"] if "pool_reason" in board.columns else ""
    if "judgement_label" in board.columns:
        board["upstream_judgement_label"] = board["judgement_label"]
        board = board.drop(columns=["judgement_label"])
    else:
        board["upstream_judgement_label"] = ""
    if "consensus_direction" in board.columns:
        board["upstream_consensus_direction"] = board["consensus_direction"]
        board = board.drop(columns=["consensus_direction"])
    else:
        board["upstream_consensus_direction"] = ""
    metric_rows = [direction_metrics(row) for _, row in board.iterrows()]
    board = pd.concat([board.reset_index(drop=True), pd.DataFrame(metric_rows)], axis=1)
    alpha158_mask = board["source_family"].eq("alpha158") & board["upstream_consensus_direction"].astype(str).ne("")
    board.loc[alpha158_mask, "consensus_direction"] = board.loc[alpha158_mask, "upstream_consensus_direction"]
    decision_rows = []
    for _, row in board.iterrows():
        if str(row.get("source_family", "")) == "alpha158":
            decision_rows.append(classify_alpha158(row))
        else:
            decision_rows.append(classify_new_source(row, config.rules))
    board = pd.concat([board.reset_index(drop=True), pd.DataFrame(decision_rows)], axis=1)
    board["pool_name"] = config.pool_name
    board["research_included"] = board["research_included"].map(as_bool)
    board["downstream_default_included"] = board["downstream_default_included"].map(as_bool)
    board["judgement_issue_tags"] = board["judgement_issue_tags"].fillna("")

    output_columns = [
        "pool_name",
        "factor",
        "source_family",
        "source_project",
        "category",
        "screening_gate",
        "promotion_decision",
        "promotion_reason",
        "upstream_role",
        "judgement_role",
        "research_included",
        "downstream_default_included",
        "judgement_label",
        "judgement_reason",
        "source_policy",
        "expected_direction",
        "consensus_direction",
        "consensus_direction_sign",
        "direction_agreement_count",
        "direction_observation_count",
        "direction_agreement_ratio",
        "primary_mean_ic",
        "max_abs_mean_ic",
        "max_abs_qlib_ir",
        "max_abs_ann_alpha",
        "coverage",
        "missing_rate",
        "valid_rows",
        "total_rows",
        "metric_value_count",
        "alphalens_status",
        "jqfactor_status",
        "qlib_status",
        "alphalens_mean_ic_10d",
        "alphalens_mean_ic_20d",
        "jqfactor_mean_ic_10d",
        "jqfactor_mean_ic_20d",
        "qlib_information_ratio_10d",
        "qlib_information_ratio_20d",
        "alphalens_ann_alpha_10d",
        "alphalens_ann_alpha_20d",
        "judgement_issue_tags",
        "license",
        "compute_adapter",
    ]
    for column in output_columns:
        if column not in board.columns:
            board[column] = pd.NA
    role_order = {
        "alpha_candidate": 0,
        "new_source_alpha_probe": 1,
        "monitor": 2,
        "new_source_monitor": 3,
        "new_source_mixed_signal": 4,
        "new_source_data_watch": 5,
        "excluded_high_turnover": 6,
        "excluded_unstable_context": 7,
        "excluded_redundant": 8,
        "holdout": 9,
    }
    board["_role_order"] = board["judgement_role"].map(role_order).fillna(99)
    board["_source_order"] = board["source_family"].map({"alpha158": 0, "ta": 1, "alpha101": 2}).fillna(9)
    board["max_abs_mean_ic"] = pd.to_numeric(board["max_abs_mean_ic"], errors="coerce")
    board["max_abs_qlib_ir"] = pd.to_numeric(board["max_abs_qlib_ir"], errors="coerce")
    board = board.sort_values(
        ["_role_order", "_source_order", "max_abs_mean_ic", "max_abs_qlib_ir", "factor"],
        ascending=[True, True, False, False, True],
    )
    board = board[output_columns].reset_index(drop=True)
    contract = build_contract_status(source, board, config.rules)
    return board, contract


def build_contract_status(
    source: pd.DataFrame,
    board: pd.DataFrame,
    rules: MultiSourceJudgementRules,
) -> pd.DataFrame:
    new_source = board[~board["source_family"].eq("alpha158")]
    new_source_strict = new_source[new_source["screening_gate"].eq("strict_screening_input")]
    probes = new_source[new_source["judgement_role"].eq("new_source_alpha_probe")]
    research = board[board["research_included"].eq(True)]
    alpha158_source_alpha = int(source[source["role"].eq("alpha_candidate")]["factor"].nunique())
    alpha158_board_alpha = int(board[board["judgement_role"].eq("alpha_candidate")]["factor"].nunique())
    checks = [
        {
            "check_id": "row_alignment",
            "status": "pass" if len(source) == len(board) and set(source["factor"]) == set(board["factor"]) else "blocked",
            "detail": f"source={len(source)}, board={len(board)}",
        },
        {
            "check_id": "alpha158_role_preserved",
            "status": "pass" if alpha158_source_alpha == alpha158_board_alpha else "blocked",
            "detail": f"source_alpha={alpha158_source_alpha}, board_alpha={alpha158_board_alpha}",
        },
        {
            "check_id": "new_source_probe_count",
            "status": "pass" if len(probes) >= rules.min_new_source_probes else "partial",
            "detail": f"new_source_alpha_probe={len(probes)}",
        },
        {
            "check_id": "holdout_not_research_included",
            "status": "pass" if research["screening_gate"].ne("holdout").all() else "blocked",
            "detail": f"research_included={len(research)}",
        },
        {
            "check_id": "new_source_not_downstream_default",
            "status": "pass" if not new_source["downstream_default_included"].any() else "blocked",
            "detail": f"new_source_downstream_default={int(new_source['downstream_default_included'].sum())}",
        },
        {
            "check_id": "strict_new_source_metrics",
            "status": "pass"
            if new_source_strict["metric_value_count"].notna().all() and not new_source_strict.empty
            else "partial",
            "detail": f"strict_new_source_rows={len(new_source_strict)}",
        },
    ]
    return pd.DataFrame(checks)


def write_outputs(
    output_dir: Path,
    board: pd.DataFrame,
    contract: pd.DataFrame,
    config: MultiSourceJudgementConfig,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    research = board[board["research_included"].eq(True)].copy()
    probes = board[board["judgement_role"].eq("new_source_alpha_probe")].copy()
    holdouts = board[board["judgement_role"].eq("holdout")].copy()
    monitor = board[~board["research_included"].eq(True) & ~board["judgement_role"].eq("holdout")].copy()

    board.to_csv(output_dir / "multi_source_judgement_board.csv", index=False, encoding="utf-8-sig")
    research.to_csv(output_dir / "multi_source_research_candidates.csv", index=False, encoding="utf-8-sig")
    probes.to_csv(output_dir / "multi_source_new_source_alpha_probes.csv", index=False, encoding="utf-8-sig")
    monitor.to_csv(output_dir / "multi_source_judgement_monitor.csv", index=False, encoding="utf-8-sig")
    holdouts.to_csv(output_dir / "multi_source_judgement_holdouts.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output_dir / "multi_source_judgement_contract_status.csv", index=False, encoding="utf-8-sig")

    payload = {
        "pool_name": config.pool_name,
        "rules": asdict(config.rules),
        "role_counts": board.groupby("judgement_role").size().to_dict() if not board.empty else {},
        "source_role_counts": {
            f"{source_family}:{role}": int(count)
            for (source_family, role), count in board.groupby(["source_family", "judgement_role"]).size().items()
        },
        "records": board.where(pd.notna(board), None).to_dict(orient="records"),
    }
    (output_dir / "multi_source_judgement_pool.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    write_report(output_dir, board, research, probes, holdouts, contract, config)


def write_report(
    output_dir: Path,
    board: pd.DataFrame,
    research: pd.DataFrame,
    probes: pd.DataFrame,
    holdouts: pd.DataFrame,
    contract: pd.DataFrame,
    config: MultiSourceJudgementConfig,
) -> None:
    role_counts = board.groupby(["source_family", "judgement_role"]).size().reset_index(name="count")
    label_counts = board.groupby(["source_family", "judgement_label"]).size().reset_index(name="count")
    probe_view = probes[
        [
            "factor",
            "source_family",
            "judgement_label",
            "consensus_direction",
            "primary_mean_ic",
            "max_abs_mean_ic",
            "max_abs_qlib_ir",
            "coverage",
        ]
    ].head(80)
    research_view = research[
        [
            "factor",
            "source_family",
            "judgement_role",
            "judgement_label",
            "consensus_direction",
            "max_abs_mean_ic",
            "max_abs_qlib_ir",
        ]
    ].head(80)
    lines = [
        "# Multi-Source Judgement V1",
        "",
        f"- Pool name: `{config.pool_name}`",
        "- Scope: research judgement only; no model training, no strategy optimization, no evaluator redefinition.",
        "- Alpha158 roles are preserved from the existing Alpha158 candidate pool.",
        "- TA and Alpha101 promoted factors can become `new_source_alpha_probe`, but are not downstream defaults.",
        "",
        "## Rule Snapshot",
        "",
        markdown_table(pd.DataFrame([asdict(config.rules)])),
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Role Counts",
        "",
        markdown_table(role_counts),
        "",
        "## Label Counts",
        "",
        markdown_table(label_counts),
        "",
        "## Research Candidates",
        "",
        markdown_table(research_view),
        "",
        "## New Source Alpha Probes",
        "",
        markdown_table(probe_view),
        "",
        "## Holdouts",
        "",
        markdown_table(
            holdouts[["factor", "source_family", "promotion_reason", "alphalens_status", "jqfactor_status", "qlib_status"]].head(80)
            if not holdouts.empty
            else pd.DataFrame()
        ),
        "",
        "## Output Files",
        "",
        "- `multi_source_judgement_board.csv`",
        "- `multi_source_research_candidates.csv`",
        "- `multi_source_new_source_alpha_probes.csv`",
        "- `multi_source_judgement_monitor.csv`",
        "- `multi_source_judgement_holdouts.csv`",
        "- `multi_source_judgement_contract_status.csv`",
        "- `multi_source_judgement_pool.json`",
        "",
        "## Notes",
        "",
        "- This layer only reads already generated evaluator metrics from Alphalens Reloaded, jqfactor_analyzer, and Qlib eval.",
        "- `new_source_alpha_probe` is a research queue, not a trading signal and not an automatic model input.",
        "- Coverage and missing-rate gates are intentionally stricter than source promotion so weak data does not look like alpha.",
    ]
    (output_dir / "multi_source_judgement_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_multi_source_judgement(config: MultiSourceJudgementConfig) -> dict[str, pd.DataFrame]:
    board, contract = build_judgement_board(config)
    write_outputs(config.output_dir, board, contract, config)
    return {
        "board": board,
        "contract": contract,
        "research_candidates": board[board["research_included"].eq(True)].copy(),
        "new_source_alpha_probes": board[board["judgement_role"].eq("new_source_alpha_probe")].copy(),
    }

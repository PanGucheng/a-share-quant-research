from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/tradability_exposure_attribution_v1.yaml")
PROXY_COLUMNS = {
    "liquidity_value": "mean_spearman_liquidity_value",
    "liquidity_bucket": "mean_spearman_liquidity_bucket",
    "tradability_score": "mean_spearman_tradability_score",
}


@dataclass(frozen=True)
class ExposureAttributionRules:
    min_watchlist_rows: int
    strong_abs_exposure: float
    material_abs_exposure: float
    moderate_abs_exposure: float
    strong_bucket_z_gap: float


@dataclass(frozen=True)
class ExposureAttributionConfig:
    probe_review_board: Path
    tradability_exposure_watchlist: Path
    diagnostic_exposure: Path
    output_dir: Path
    rules: ExposureAttributionRules


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing or empty required input: {path}")
    return pd.read_csv(path)


def load_config(path: Path) -> ExposureAttributionConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    rules = payload.get("rules", {})
    return ExposureAttributionConfig(
        probe_review_board=resolve_path(payload["probe_review_board"]),
        tradability_exposure_watchlist=resolve_path(payload["tradability_exposure_watchlist"]),
        diagnostic_exposure=resolve_path(payload["diagnostic_exposure"]),
        output_dir=resolve_path(payload.get("output_dir", "outputs/tradability_exposure_attribution_v1/current")),
        rules=ExposureAttributionRules(
            min_watchlist_rows=int(rules.get("min_watchlist_rows", 19)),
            strong_abs_exposure=float(rules.get("strong_abs_exposure", 0.65)),
            material_abs_exposure=float(rules.get("material_abs_exposure", 0.45)),
            moderate_abs_exposure=float(rules.get("moderate_abs_exposure", 0.30)),
            strong_bucket_z_gap=float(rules.get("strong_bucket_z_gap", 0.80)),
        ),
    )


def numeric(value: object) -> float:
    result = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(result) if pd.notna(result) else float("nan")


def truthy_series(values: pd.Series) -> pd.Series:
    return values.astype(str).str.lower().isin({"true", "1", "yes"})


def primary_proxy(row: pd.Series) -> tuple[str, float, float]:
    scored = []
    for proxy, column in PROXY_COLUMNS.items():
        value = numeric(row.get(column))
        if pd.notna(value):
            scored.append((abs(value), proxy, value))
    if not scored:
        return "", float("nan"), float("nan")
    abs_value, proxy, signed_value = sorted(scored, reverse=True)[0]
    return proxy, signed_value, abs_value


def exposure_strength(abs_exposure: float, rules: ExposureAttributionRules) -> str:
    if pd.isna(abs_exposure):
        return "missing"
    if abs_exposure >= rules.strong_abs_exposure:
        return "strong"
    if abs_exposure >= rules.material_abs_exposure:
        return "material"
    if abs_exposure >= rules.moderate_abs_exposure:
        return "moderate"
    return "low"


def attribution_label(row: pd.Series, rules: ExposureAttributionRules) -> str:
    strength = str(row["exposure_strength"])
    proxy = str(row["primary_exposure_proxy"])
    z_gap = abs(numeric(row.get("high_minus_low_liquidity_z")))
    if strength == "strong" and proxy in {"liquidity_value", "liquidity_bucket"} and z_gap >= rules.strong_bucket_z_gap:
        return "strong_liquidity_proxy"
    if strength in {"strong", "material"} and proxy in {"liquidity_value", "liquidity_bucket"}:
        return "material_liquidity_proxy"
    if strength in {"strong", "material"} and proxy == "tradability_score":
        return "material_tradability_score_proxy"
    if strength == "moderate":
        return "moderate_tradability_review"
    return "low_or_missing_review"


def recommended_action(row: pd.Series) -> str:
    label = str(row["attribution_label"])
    redundant = bool(row.get("redundancy_compounded", False))
    if label == "strong_liquidity_proxy":
        return "holdout_before_residualization"
    if label == "material_liquidity_proxy" and redundant:
        return "holdout_redundant_liquidity_proxy"
    if label.startswith("material_"):
        return "residualization_candidate_review"
    if label == "moderate_tradability_review":
        return "manual_review_before_training"
    return "monitor_only"


def build_attribution_board(
    review: pd.DataFrame,
    exposure: pd.DataFrame,
    rules: ExposureAttributionRules,
) -> pd.DataFrame:
    watch = review[review["review_action"].eq("tradability_exposure_review")].copy()
    exposure_cols = [
        "factor",
        "mean_spearman_liquidity_value",
        "liquidity_value_date_count",
        "mean_spearman_liquidity_bucket",
        "liquidity_bucket_date_count",
        "mean_spearman_tradability_score",
        "tradability_score_date_count",
        "high_liquidity_z_mean",
        "low_liquidity_z_mean",
        "high_minus_low_liquidity_z",
        "max_abs_tradability_exposure",
    ]
    exposure_cols = [column for column in exposure_cols if column in exposure.columns]
    merged = watch.drop(columns=[column for column in exposure_cols if column != "factor" and column in watch.columns], errors="ignore")
    merged = merged.merge(exposure[exposure_cols].drop_duplicates("factor"), on="factor", how="left")
    proxy_values = merged.apply(primary_proxy, axis=1, result_type="expand")
    proxy_values.columns = ["primary_exposure_proxy", "primary_exposure_value", "primary_abs_exposure"]
    merged = pd.concat([merged, proxy_values], axis=1)
    merged["exposure_direction"] = merged["primary_exposure_value"].apply(
        lambda value: "positive" if value > 0 else ("negative" if value < 0 else "missing")
    )
    merged["exposure_strength"] = merged["primary_abs_exposure"].apply(lambda value: exposure_strength(value, rules))
    merged["redundancy_compounded"] = truthy_series(
        merged.get("high_redundancy_watch", pd.Series(False, index=merged.index))
    )
    merged["attribution_label"] = merged.apply(lambda row: attribution_label(row, rules), axis=1)
    merged["recommended_action"] = merged.apply(recommended_action, axis=1)
    columns = [
        "factor",
        "source_family",
        "source_project",
        "category",
        "judgement_label",
        "max_abs_mean_ic",
        "max_abs_qlib_ir",
        "primary_exposure_proxy",
        "primary_exposure_value",
        "primary_abs_exposure",
        "exposure_direction",
        "exposure_strength",
        "mean_spearman_liquidity_value",
        "mean_spearman_liquidity_bucket",
        "mean_spearman_tradability_score",
        "high_liquidity_z_mean",
        "low_liquidity_z_mean",
        "high_minus_low_liquidity_z",
        "redundancy_compounded",
        "redundancy_representative",
        "attribution_label",
        "recommended_action",
    ]
    columns = [column for column in columns if column in merged.columns]
    return merged.sort_values(["primary_abs_exposure", "factor"], ascending=[False, True])[columns].reset_index(drop=True)


def build_contract_status(
    board: pd.DataFrame,
    review: pd.DataFrame,
    exposure: pd.DataFrame,
    rules: ExposureAttributionRules,
) -> pd.DataFrame:
    watch_count = int(review["review_action"].eq("tradability_exposure_review").sum())
    source_count = int(board["source_family"].nunique()) if "source_family" in board.columns else 0
    missing_proxy = int(board["primary_exposure_proxy"].eq("").sum()) if "primary_exposure_proxy" in board.columns else len(board)
    downstream_defaults = (
        int(truthy_series(review.get("downstream_default_included", pd.Series(False, index=review.index))).sum())
        if not review.empty
        else 0
    )
    rows = [
        {
            "check_id": "watchlist_rows",
            "status": "pass" if watch_count >= rules.min_watchlist_rows else "blocked",
            "detail": f"watchlist_rows={watch_count}",
        },
        {
            "check_id": "attribution_rows",
            "status": "pass" if len(board) >= rules.min_watchlist_rows else "blocked",
            "detail": f"attribution_rows={len(board)}",
        },
        {
            "check_id": "source_family_coverage",
            "status": "pass" if source_count >= 2 else "partial",
            "detail": f"source_families={source_count}",
        },
        {
            "check_id": "primary_proxy_present",
            "status": "pass" if missing_proxy == 0 else "blocked",
            "detail": f"missing_proxy={missing_proxy}",
        },
        {
            "check_id": "diagnostic_exposure_available",
            "status": "pass" if len(exposure) >= rules.min_watchlist_rows else "blocked",
            "detail": f"diagnostic_exposure_rows={len(exposure)}",
        },
        {
            "check_id": "no_downstream_default",
            "status": "pass" if downstream_defaults == 0 else "blocked",
            "detail": f"downstream_default={downstream_defaults}",
        },
    ]
    return pd.DataFrame(rows)


def write_report(
    config: ExposureAttributionConfig,
    board: pd.DataFrame,
    source_summary: pd.DataFrame,
    action_summary: pd.DataFrame,
    contract: pd.DataFrame,
) -> None:
    lines = [
        "# Tradability Exposure Attribution V1",
        "",
        "- Scope: attribution for probes already marked `tradability_exposure_review`.",
        "- Boundary: no model training, no strategy optimization, no evaluator definition changes.",
        f"- Review board: `{portable_path(config.probe_review_board)}`",
        f"- Diagnostic exposure: `{portable_path(config.diagnostic_exposure)}`",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Source Summary",
        "",
        markdown_table(source_summary),
        "",
        "## Action Summary",
        "",
        markdown_table(action_summary),
        "",
        "## Attribution Board",
        "",
        markdown_table(board),
        "",
        "## Notes",
        "",
        "- High tradability exposure does not prove a factor is invalid, but it blocks direct training admission.",
        "- `holdout_before_residualization` means the next useful experiment is neutralized/residualized evaluation, not raw-factor training.",
    ]
    (config.output_dir / "tradability_exposure_attribution_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_attribution(config: ExposureAttributionConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    review = read_csv_required(config.probe_review_board)
    exposure = read_csv_required(config.diagnostic_exposure)
    read_csv_required(config.tradability_exposure_watchlist)
    board = build_attribution_board(review, exposure, config.rules)
    source_summary = (
        board.groupby(["source_family", "exposure_direction", "exposure_strength", "attribution_label"])
        .size()
        .reset_index(name="factor_count")
        .sort_values(["source_family", "factor_count"], ascending=[True, False])
    )
    action_summary = (
        board.groupby(["recommended_action", "exposure_strength"])
        .size()
        .reset_index(name="factor_count")
        .sort_values(["recommended_action", "exposure_strength"])
    )
    contract = build_contract_status(board, review, exposure, config.rules)

    board.to_csv(config.output_dir / "tradability_exposure_attribution_board.csv", index=False, encoding="utf-8-sig")
    source_summary.to_csv(config.output_dir / "tradability_exposure_source_summary.csv", index=False, encoding="utf-8-sig")
    action_summary.to_csv(config.output_dir / "tradability_exposure_action_summary.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(config.output_dir / "tradability_exposure_contract_status.csv", index=False, encoding="utf-8-sig")
    write_report(config, board, source_summary, action_summary, contract)
    return {
        "attribution_board": board,
        "source_summary": source_summary,
        "action_summary": action_summary,
        "contract_status": contract,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit tradability exposure attribution V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    config = load_config(build_parser().parse_args().config)
    outputs = run_attribution(config)
    blocked = outputs["contract_status"][outputs["contract_status"]["status"].eq("blocked")]
    print(f"Tradability exposure attribution written to {config.output_dir}", flush=True)
    print(f"Attribution rows: {len(outputs['attribution_board'])}", flush=True)
    print(f"Action rows: {len(outputs['action_summary'])}", flush=True)
    if not blocked.empty:
        raise SystemExit(f"Tradability exposure attribution blocked: {blocked.to_dict(orient='records')}")


if __name__ == "__main__":
    main()

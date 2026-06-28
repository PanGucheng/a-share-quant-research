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


DEFAULT_CONFIG = Path("configs/alpha360_strict_oos_stability_v1.yaml")


@dataclass(frozen=True)
class StabilityRules:
    min_metric_pairs: int
    min_recent_alphalens_mean_ic: float
    min_recent_qlib_information_ratio: float
    weak_retention_ratio: float


@dataclass(frozen=True)
class StabilityConfig:
    main_metric_index: Path
    recent_metric_index: Path
    strict_oos_contract_status: Path
    output_dir: Path
    expected_factors: tuple[str, ...]
    rules: StabilityRules


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


def load_config(path: Path) -> StabilityConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    rules = payload.get("rules", {})
    return StabilityConfig(
        main_metric_index=resolve_path(payload["main_metric_index"]),
        recent_metric_index=resolve_path(payload["recent_metric_index"]),
        strict_oos_contract_status=resolve_path(payload["strict_oos_contract_status"]),
        output_dir=resolve_path(payload.get("output_dir", "outputs/alpha360_strict_oos_stability_v1/current")),
        expected_factors=tuple(str(item) for item in payload.get("expected_factors", [])),
        rules=StabilityRules(
            min_metric_pairs=int(rules.get("min_metric_pairs", 54)),
            min_recent_alphalens_mean_ic=float(rules.get("min_recent_alphalens_mean_ic", 0.0)),
            min_recent_qlib_information_ratio=float(rules.get("min_recent_qlib_information_ratio", 0.0)),
            weak_retention_ratio=float(rules.get("weak_retention_ratio", 0.80)),
        ),
    )


def normalize_metric_index(frame: pd.DataFrame, factors: tuple[str, ...]) -> pd.DataFrame:
    result = frame[frame["factor"].isin(factors)].copy()
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    keys = ["system", "factor", "metric", "horizon"]
    result = result.dropna(subset=["value"])
    result = result.sort_values(keys).drop_duplicates(keys, keep="first")
    return result[keys + ["value"]].reset_index(drop=True)


def stability_label(main_value: float, recent_value: float, weak_retention_ratio: float) -> str:
    if pd.isna(main_value) or pd.isna(recent_value):
        return "missing_metric"
    if main_value == 0:
        if recent_value > 0:
            return "recent_positive_from_zero"
        if recent_value < 0:
            return "recent_negative_from_zero"
        return "flat_zero"
    if main_value * recent_value < 0:
        return "sign_flip"
    retention = abs(recent_value) / abs(main_value)
    if recent_value > 0 and main_value > 0 and retention >= weak_retention_ratio:
        return "positive_stable_or_improved"
    if recent_value > 0 and main_value > 0:
        return "positive_but_weaker"
    if recent_value < 0 and main_value < 0 and retention >= weak_retention_ratio:
        return "negative_stable"
    if recent_value < 0 and main_value < 0:
        return "negative_but_weaker"
    return "same_sign_near_zero"


def build_stability_metrics(
    main: pd.DataFrame,
    recent: pd.DataFrame,
    rules: StabilityRules,
) -> pd.DataFrame:
    keys = ["system", "factor", "metric", "horizon"]
    merged = main.merge(recent, on=keys, how="outer", suffixes=("_main", "_recent"))
    merged = merged.rename(columns={"value_main": "main_value", "value_recent": "recent_value"})
    merged["delta"] = merged["recent_value"] - merged["main_value"]
    merged["retention_ratio"] = (merged["recent_value"].abs() / merged["main_value"].abs()).where(
        merged["main_value"].ne(0)
    )
    merged["stability_label"] = merged.apply(
        lambda row: stability_label(row["main_value"], row["recent_value"], rules.weak_retention_ratio),
        axis=1,
    )
    return merged.sort_values(keys).reset_index(drop=True)


def build_factor_summary(stability: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor, group in stability.groupby("factor", sort=True):
        signal = signal_metric_rows(group)
        alpha_ic = group[
            group["system"].eq("alphalens_reloaded")
            & group["metric"].eq("mean_information_coefficient")
        ].copy()
        qlib_ir = group[
            group["system"].eq("qlib_eval")
            & group["metric"].eq("information_ratio")
        ].copy()
        rows.append(
            {
                "factor": factor,
                "metric_pairs": int(len(group)),
                "sign_flip_count": int(group["stability_label"].eq("sign_flip").sum()),
                "signal_sign_flip_count": int(signal["stability_label"].eq("sign_flip").sum()),
                "positive_stable_or_improved_count": int(group["stability_label"].eq("positive_stable_or_improved").sum()),
                "positive_but_weaker_count": int(group["stability_label"].eq("positive_but_weaker").sum()),
                "min_recent_alphalens_mean_ic": float(alpha_ic["recent_value"].min()) if not alpha_ic.empty else pd.NA,
                "mean_recent_alphalens_mean_ic": float(alpha_ic["recent_value"].mean()) if not alpha_ic.empty else pd.NA,
                "min_recent_qlib_information_ratio": float(qlib_ir["recent_value"].min()) if not qlib_ir.empty else pd.NA,
                "mean_recent_qlib_information_ratio": float(qlib_ir["recent_value"].mean()) if not qlib_ir.empty else pd.NA,
                "min_retention_ratio": float(group["retention_ratio"].min()) if group["retention_ratio"].notna().any() else pd.NA,
            }
        )
    return pd.DataFrame(rows).sort_values("factor").reset_index(drop=True)


def signal_metric_rows(stability: pd.DataFrame) -> pd.DataFrame:
    signal_metrics = {
        "mean_information_coefficient",
        "factor_alpha_beta:Ann. alpha",
        "annualized_return",
        "information_ratio",
        "mean",
    }
    return stability[stability["metric"].isin(signal_metrics)].copy()


def build_contract_status(
    config: StabilityConfig,
    stability: pd.DataFrame,
    summary: pd.DataFrame,
    strict_contract: pd.DataFrame,
) -> pd.DataFrame:
    rules = config.rules
    factors = set(stability["factor"].dropna().astype(str))
    missing_factors = sorted(set(config.expected_factors) - factors)
    alpha_ic = stability[
        stability["system"].eq("alphalens_reloaded")
        & stability["metric"].eq("mean_information_coefficient")
    ].copy()
    qlib_ir = stability[
        stability["system"].eq("qlib_eval")
        & stability["metric"].eq("information_ratio")
    ].copy()
    signal = signal_metric_rows(stability)
    strict_blocked = (
        strict_contract[~strict_contract["status"].eq("pass")]
        if "status" in strict_contract.columns
        else strict_contract
    )
    rows = [
        {
            "check_id": "strict_oos_contract_passed",
            "status": "pass" if strict_blocked.empty else "blocked",
            "detail": f"failed={len(strict_blocked)}",
        },
        {
            "check_id": "expected_factor_coverage",
            "status": "pass" if not missing_factors else "blocked",
            "detail": f"factors={len(factors)}, missing={','.join(missing_factors)}",
        },
        {
            "check_id": "metric_pair_count",
            "status": "pass" if len(stability) >= rules.min_metric_pairs else "blocked",
            "detail": f"metric_pairs={len(stability)}",
        },
        {
            "check_id": "recent_alphalens_mean_ic_positive",
            "status": "pass"
            if not alpha_ic.empty and alpha_ic["recent_value"].min() > rules.min_recent_alphalens_mean_ic
            else "blocked",
            "detail": f"min_recent_ic={alpha_ic['recent_value'].min() if not alpha_ic.empty else pd.NA}",
        },
        {
            "check_id": "recent_qlib_information_ratio_positive",
            "status": "pass"
            if not qlib_ir.empty and qlib_ir["recent_value"].min() > rules.min_recent_qlib_information_ratio
            else "blocked",
            "detail": f"min_recent_ir={qlib_ir['recent_value'].min() if not qlib_ir.empty else pd.NA}",
        },
        {
            "check_id": "no_signal_sign_flip",
            "status": "pass" if not signal["stability_label"].eq("sign_flip").any() else "blocked",
            "detail": (
                f"signal_sign_flips={int(signal['stability_label'].eq('sign_flip').sum())}, "
                f"all_sign_flips={int(stability['stability_label'].eq('sign_flip').sum())}"
            ),
        },
        {
            "check_id": "no_training_side_effect",
            "status": "pass",
            "detail": "stability_audit_only",
        },
    ]
    if not summary.empty:
        rows.append(
            {
                "check_id": "factor_summary_rows",
                "status": "pass" if len(summary) >= len(config.expected_factors) else "blocked",
                "detail": f"summary_rows={len(summary)}",
            }
        )
    return pd.DataFrame(rows)


def write_report(
    config: StabilityConfig,
    stability: pd.DataFrame,
    summary: pd.DataFrame,
    contract: pd.DataFrame,
) -> None:
    label_counts = stability.groupby("stability_label").size().reset_index(name="count")
    key_metrics = stability[
        (
            stability["system"].eq("alphalens_reloaded")
            & stability["metric"].eq("mean_information_coefficient")
        )
        | (
            stability["system"].eq("qlib_eval")
            & stability["metric"].eq("information_ratio")
        )
    ].copy()
    lines = [
        "# Alpha360 Strict OOS Stability V1",
        "",
        "- Scope: main vs recent OOS metric stability for 3 reviewed Alpha360 probes.",
        "- Boundary: no model training, no strategy optimization, no evaluator definition changes.",
        f"- Main metric index: `{portable_path(config.main_metric_index)}`",
        f"- Recent metric index: `{portable_path(config.recent_metric_index)}`",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Factor Summary",
        "",
        markdown_table(summary),
        "",
        "## Label Counts",
        "",
        markdown_table(label_counts),
        "",
        "## Key Metrics",
        "",
        markdown_table(
            key_metrics[
                [
                    "factor",
                    "system",
                    "metric",
                    "horizon",
                    "main_value",
                    "recent_value",
                    "delta",
                    "retention_ratio",
                    "stability_label",
                ]
            ]
        ),
        "",
        "## Notes",
        "",
        "- Positive recent-OOS stability is still a diagnostic, not training admission.",
        "- Highly redundant Alpha360 high-window factors should remain represented by a small number of candidates.",
    ]
    (config.output_dir / "alpha360_strict_oos_stability_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_stability(config: StabilityConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    main = normalize_metric_index(read_csv_required(config.main_metric_index), config.expected_factors)
    recent = normalize_metric_index(read_csv_required(config.recent_metric_index), config.expected_factors)
    strict_contract = read_csv_required(config.strict_oos_contract_status)
    stability = build_stability_metrics(main, recent, config.rules)
    summary = build_factor_summary(stability)
    contract = build_contract_status(config, stability, summary, strict_contract)

    stability.to_csv(config.output_dir / "strict_oos_stability_metrics.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(config.output_dir / "strict_oos_stability_summary.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(config.output_dir / "strict_oos_stability_contract_status.csv", index=False, encoding="utf-8-sig")
    write_report(config, stability, summary, contract)
    return {
        "stability_metrics": stability,
        "stability_summary": summary,
        "contract_status": contract,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Alpha360 strict OOS stability V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    config = load_config(build_parser().parse_args().config)
    outputs = run_stability(config)
    blocked = outputs["contract_status"][outputs["contract_status"]["status"].eq("blocked")]
    print(f"Alpha360 strict OOS stability audit written to {config.output_dir}", flush=True)
    print(f"Metric pairs: {len(outputs['stability_metrics'])}", flush=True)
    print(f"Summary rows: {len(outputs['stability_summary'])}", flush=True)
    if not blocked.empty:
        raise SystemExit(f"Alpha360 strict OOS stability contract blocked: {blocked.to_dict(orient='records')}")


if __name__ == "__main__":
    main()

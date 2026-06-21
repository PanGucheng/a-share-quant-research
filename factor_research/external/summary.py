from __future__ import annotations

from pathlib import Path

import pandas as pd


def _read_indexed(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, index_col=0)


def _append_indexed_metrics(
    rows: list[dict],
    system: str,
    factor: str,
    metric: str,
    path: Path,
) -> None:
    frame = _read_indexed(path)
    if frame.empty:
        return
    for row_name, values in frame.iterrows():
        for column, value in values.items():
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(numeric):
                continue
            horizon = str(row_name) if len(frame.columns) == 1 else str(column)
            submetric = metric if len(frame.columns) == 1 else f"{metric}:{row_name}"
            rows.append(
                {
                    "system": system,
                    "factor": factor,
                    "metric": submetric,
                    "horizon": horizon,
                    "value": float(numeric),
                    "source_file": path.as_posix(),
                }
            )


def build_open_source_metric_index(output_dir: Path, factors: list[str]) -> pd.DataFrame:
    """Build a long metric index without creating a combined score."""

    rows: list[dict] = []
    for factor in factors:
        alpha_dir = output_dir / "alphalens_reloaded" / factor
        _append_indexed_metrics(
            rows,
            "alphalens_reloaded",
            factor,
            "mean_information_coefficient",
            alpha_dir / "mean_information_coefficient.csv",
        )
        _append_indexed_metrics(
            rows,
            "alphalens_reloaded",
            factor,
            "factor_alpha_beta",
            alpha_dir / "factor_alpha_beta.csv",
        )

        jq_dir = output_dir / "jqfactor_analyzer" / factor
        _append_indexed_metrics(
            rows,
            "jqfactor_analyzer",
            factor,
            "mean_information_coefficient",
            jq_dir / "mean_information_coefficient.csv",
        )

        qlib_dir = output_dir / "qlib_eval" / factor
        for path in sorted(qlib_dir.glob("*_risk_analysis.csv")):
            label = path.name.removesuffix("_risk_analysis.csv")
            frame = _read_indexed(path)
            if frame.empty:
                continue
            for metric_name, values in frame.iterrows():
                value = pd.to_numeric(values.iloc[0], errors="coerce")
                if pd.isna(value):
                    continue
                rows.append(
                    {
                        "system": "qlib_eval",
                        "factor": factor,
                        "metric": str(metric_name),
                        "horizon": label,
                        "value": float(value),
                        "source_file": path.as_posix(),
                    }
                )

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=["system", "factor", "metric", "horizon", "value", "source_file"])
    return result.sort_values(["system", "factor", "metric", "horizon"]).reset_index(drop=True)


def build_context_metric_index(
    output_dir: Path,
    factors: list[str],
    systems: list[str],
) -> pd.DataFrame:
    """Index grouped source metrics without combining or ranking them."""

    rows: list[dict] = []
    context_root = output_dir / "context"
    for system in systems:
        if system not in {"alphalens_reloaded", "jqfactor_analyzer"}:
            continue
        for factor in factors:
            factor_root = context_root / system / factor
            if not factor_root.exists():
                continue
            for path in factor_root.rglob("mean_information_coefficient_by_group.csv"):
                relative = path.relative_to(factor_root)
                return_mode, group_dimension = relative.parts[:2]
                frame = pd.read_csv(path)
                for _, row in frame.iterrows():
                    group = row["group"]
                    for horizon, value in row.drop(labels=["group"]).items():
                        numeric = pd.to_numeric(value, errors="coerce")
                        if pd.isna(numeric):
                            continue
                        rows.append(
                            {
                                "system": system,
                                "factor": factor,
                                "return_mode": return_mode,
                                "group_dimension": group_dimension,
                                "metric": "mean_information_coefficient_by_group",
                                "group": str(group),
                                "quantile": pd.NA,
                                "horizon": str(horizon),
                                "value": float(numeric),
                                "source_file": path.as_posix(),
                            }
                        )
            for path in factor_root.rglob("mean_return_by_quantile_by_group.csv"):
                relative = path.relative_to(factor_root)
                return_mode, group_dimension = relative.parts[:2]
                frame = pd.read_csv(path)
                for _, row in frame.iterrows():
                    quantile = row["factor_quantile"]
                    group = row["group"]
                    for horizon, value in row.drop(labels=["factor_quantile", "group"]).items():
                        numeric = pd.to_numeric(value, errors="coerce")
                        if pd.isna(numeric):
                            continue
                        rows.append(
                            {
                                "system": system,
                                "factor": factor,
                                "return_mode": return_mode,
                                "group_dimension": group_dimension,
                                "metric": "mean_return_by_quantile_by_group",
                                "group": str(group),
                                "quantile": int(quantile),
                                "horizon": str(horizon),
                                "value": float(numeric),
                                "source_file": path.as_posix(),
                            }
                        )
    columns = [
        "system",
        "factor",
        "return_mode",
        "group_dimension",
        "metric",
        "group",
        "quantile",
        "horizon",
        "value",
        "source_file",
    ]
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    return result.sort_values(columns[:-2]).reset_index(drop=True)


def build_evaluator_status(
    output_dir: Path,
    factors: list[str],
    systems: list[str],
    failures: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for system in systems:
        for factor in factors:
            if system == "project_current":
                factor_dir = output_dir / system
                files = sorted(path for path in factor_dir.glob("*.csv") if path.is_file())
            else:
                factor_dir = output_dir / system / factor
                files = sorted(path for path in factor_dir.glob("*.csv") if path.is_file())
            if failures.empty:
                factor_failures = pd.DataFrame()
                import_failures = pd.DataFrame()
            else:
                factor_failures = failures[(failures["system"] == system) & (failures["factor"] == factor)]
                import_failures = failures[(failures["system"] == system) & (failures["factor"] == "*")]
            failure_count = len(factor_failures) + len(import_failures)
            if files and failure_count == 0:
                status = "pass"
            elif files:
                status = "partial_pass"
            elif failure_count:
                status = "failed"
            else:
                status = "not_run"
            rows.append(
                {
                    "system": system,
                    "factor": factor,
                    "status": status,
                    "output_file_count": len(files),
                    "failure_count": failure_count,
                    "output_dir": factor_dir.as_posix(),
                }
            )
    return pd.DataFrame(rows)

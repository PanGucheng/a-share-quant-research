from __future__ import annotations

import argparse
import importlib.util
import importlib.metadata
import sys
import traceback
import types
import shutil
from multiprocessing import freeze_support
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.dataset import to_factor_data
from factor_research.alpha158_registry import load_external_factor_specs
from factor_research.context.evaluation import (
    attach_benchmark_relative_returns,
    attach_context,
    build_context_keys,
    context_coverage,
    load_benchmark_context,
)
from factor_research.external.adapters import (
    to_alphalens_factor_data,
    to_jqfactor_inputs,
    to_qlib_score_frame,
    write_adapter_report,
)
from factor_research.external.summary import (
    build_context_metric_index,
    build_evaluator_status,
    build_open_source_metric_index,
)
from factor_research.report import markdown_table
from factor_research.registry import enabled_specs
from scripts.run_factor_research_v3 import (
    DEFAULT_MARKET,
    DEFAULT_PROVIDER_URI,
    DEFAULT_WINDOWS,
    ResearchWindow,
    load_window_frame,
    parse_csv,
    parse_labels,
    resolve_path,
)


DEFAULT_FACTORS = "rev_5,rev_20_exclude_5,std_20,amount_mean_20,downside_std_20"
DEFAULT_LABELS = "label_10d_t1,label_20d_t1"
DEFAULT_OUTPUT_DIR = Path("outputs/factor_evaluation_v4/liquid2000_open_source_eval")
DEFAULT_SYSTEMS = ["alphalens_reloaded", "jqfactor_analyzer", "qlib_eval", "project_current"]


def write_csv(frame: pd.DataFrame | pd.Series, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(frame, pd.Series):
        frame.to_frame().to_csv(path, encoding="utf-8-sig")
    else:
        frame.to_csv(path, encoding="utf-8-sig")


def record_failure(rows: list[dict], system: str, factor: str, step: str, error: BaseException) -> None:
    rows.append(
        {
            "system": system,
            "factor": factor,
            "step": step,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback_tail": "\n".join(traceback.format_exception_only(type(error), error)).strip(),
        }
    )


def load_package_module_without_init(
    package_name: str,
    package_dir: Path,
    module_name: str,
    preload_modules: list[str],
):
    """Load a package submodule without executing the package's __init__.py.

    Some reference projects import plotting, data APIs, or UI helpers at package
    import time.  For V3.6 we only want the metric module, so this loader keeps
    the original metric source file intact while avoiding unrelated package
    side effects.
    """

    for key in list(sys.modules):
        if key == package_name or key.startswith(f"{package_name}."):
            del sys.modules[key]

    package = types.ModuleType(package_name)
    package.__path__ = [str(package_dir)]
    sys.modules[package_name] = package

    def load_submodule(name: str):
        full_name = f"{package_name}.{name}"
        file_path = package_dir / f"{name}.py"
        spec = importlib.util.spec_from_file_location(full_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load {full_name} from {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
        setattr(package, name, module)
        return module

    for preload in preload_modules:
        load_submodule(preload)
    return load_submodule(module_name), None


def jqfactor_label_period_map(labels: list[str]) -> dict[str, str]:
    mapping = {}
    for label in labels:
        if label.startswith("label_") and "d" in label:
            token = label.removeprefix("label_").split("_", maxsplit=1)[0]
            if token.endswith("d") and token[:-1].isdigit():
                mapping[label] = f"period_{token[:-1]}"
                continue
        mapping[label] = label
    return mapping


def dependency_status() -> pd.DataFrame:
    rows = []
    packages = {
        "empyrical": "alphalens_reloaded",
        "fastcache": "jqfactor_analyzer",
        "statsmodels": "alphalens_reloaded,jqfactor_analyzer",
        "cached_property": "jqfactor_analyzer",
    }
    for package, required_by in packages.items():
        try:
            version = importlib.metadata.version(package)
            status = "available"
            detail = ""
        except importlib.metadata.PackageNotFoundError as exc:
            version = ""
            status = "missing"
            detail = str(exc)
        rows.append(
            {
                "kind": "python_package",
                "name": package,
                "required_by": required_by,
                "status": status,
                "version_or_path": version,
                "detail": detail,
            }
        )

    sources = {
        "alphalens_reloaded": PROJECT_ROOT / "tmp" / "reference_repos" / "alphalens-reloaded" / "src" / "alphalens" / "performance.py",
        "jqfactor_analyzer": PROJECT_ROOT / "tmp" / "reference_repos" / "jqfactor_analyzer" / "jqfactor_analyzer" / "performance.py",
        "qlib_evaluate": Path("E:/qlib_prj/qlib_clone/qlib/contrib/evaluate.py"),
    }
    for name, path in sources.items():
        rows.append(
            {
                "kind": "source_file",
                "name": name,
                "required_by": name,
                "status": "available" if path.exists() else "missing",
                "version_or_path": path.as_posix(),
                "detail": "",
            }
        )
    return pd.DataFrame(rows)


def apply_yaml_config(args: argparse.Namespace) -> argparse.Namespace:
    if args.config is None:
        return args
    config_path = resolve_path(args.config)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    qlib_config = data.get("qlib", {})
    evaluation = data.get("evaluation", {})
    window = data.get("window", {})
    tradable_filter = data.get("tradable_filter", {})
    cache = data.get("cache", {})
    current_project = data.get("current_project", {})
    context = data.get("context", {})
    external_factor_frame = data.get("external_factor_frame", {})

    args.provider_uri = qlib_config.get("provider_uri", args.provider_uri)
    args.market = qlib_config.get("market", args.market)
    args.output_dir = Path(evaluation.get("output_dir", args.output_dir))
    args.labels = parse_labels(",".join(evaluation.get("labels", args.labels)))
    args.factors = list(evaluation.get("factors", args.factors))
    args.systems = list(evaluation.get("systems", args.systems))
    args.quantiles = int(evaluation.get("quantiles", args.quantiles))
    args.min_count = int(evaluation.get("min_count", args.min_count))
    args.sample_rows = int(evaluation.get("sample_rows", args.sample_rows))
    args.min_liquidity_bucket = int(tradable_filter.get("min_liquidity_bucket", args.min_liquidity_bucket))
    args.min_tradability_score = float(tradable_filter.get("min_tradability_score", args.min_tradability_score))
    args.feature_cache_dir = Path(cache.get("feature_cache_dir", args.feature_cache_dir))
    args.factor_cache_dir = Path(cache.get("factor_cache_dir", args.factor_cache_dir))
    args.refresh_feature_cache = bool(cache.get("refresh_feature_cache", args.refresh_feature_cache))
    args.refresh_factor_cache = bool(cache.get("refresh_factor_cache", args.refresh_factor_cache))
    args.current_project_input_dir = Path(current_project.get("input_dir", args.current_project_input_dir))
    args.context_config = context
    args.external_factor_frame_config = external_factor_frame
    if window:
        args.window = ResearchWindow(
            window["name"],
            str(window["start"]),
            str(window["end"]),
            Path(window["tradability_dir"]),
            Path(window["data_quality_dir"]),
        )
    return args


def load_external_factor_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing external factor frame: {path}")
    if path.suffix.lower() in {".pkl", ".pickle"}:
        frame = pd.read_pickle(path)
    else:
        frame = pd.read_csv(path, parse_dates=["datetime"])
    required = {"datetime", "instrument"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"External factor frame missing required columns: {sorted(missing)}")
    frame = frame.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    duplicated = frame.duplicated(["datetime", "instrument"], keep=False)
    if duplicated.any():
        raise ValueError(f"External factor frame contains duplicate keys: {int(duplicated.sum())}")
    return frame


def attach_external_factor_frame(
    frame: pd.DataFrame,
    config: dict,
    requested_factors: list[str],
    output_dir: Path,
) -> pd.DataFrame:
    if not bool(config.get("enabled", False)):
        return frame
    path = resolve_path(Path(config["path"]))
    external = load_external_factor_frame(path)
    factor_columns = [column for column in external.columns if column not in {"datetime", "instrument"}]
    configured_columns = config.get("factor_columns") or factor_columns
    configured = set(configured_columns)
    requested_external = [factor for factor in requested_factors if factor in configured and factor in factor_columns]
    if not requested_external:
        return frame
    missing = sorted(set(requested_external) - set(external.columns))
    if missing:
        raise ValueError(f"External factor frame missing requested columns: {missing}")
    base = frame.copy()
    base["instrument"] = base["instrument"].astype(str).str.upper()
    before_rows = len(base)
    result = base.merge(external[["datetime", "instrument", *requested_external]], on=["datetime", "instrument"], how="left")
    rows = []
    for factor in requested_external:
        valid = pd.to_numeric(result[factor], errors="coerce").notna()
        rows.append(
            {
                "factor": factor,
                "valid_rows": int(valid.sum()),
                "total_rows": int(len(result)),
                "coverage": float(valid.sum() / len(result)) if len(result) else 0.0,
            }
        )
    summary = pd.DataFrame(rows)
    target = output_dir / "external_factor_frame"
    target.mkdir(parents=True, exist_ok=True)
    summary.to_csv(target / "external_factor_frame_summary.csv", index=False, encoding="utf-8-sig")
    external.head(200).to_csv(target / "external_factor_frame_sample.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {
                "path": path.as_posix(),
                "base_rows": int(before_rows),
                "merged_rows": int(len(result)),
                "external_rows": int(len(external)),
                "factor_count": int(len(requested_external)),
            }
        ]
    ).to_csv(target / "external_factor_frame_manifest.csv", index=False, encoding="utf-8-sig")
    if summary["valid_rows"].eq(0).any():
        empty = summary.loc[summary["valid_rows"].eq(0), "factor"].tolist()
        raise ValueError(f"External factor frame produced empty factors after merge: {empty}")
    return result


def load_requested_specs(args: argparse.Namespace, factors: list[str], labels: list[str]) -> list:
    specs = [spec for spec in enabled_specs(labels) if spec.name in set(factors)]
    external_config = args.external_factor_frame_config or {}
    if bool(external_config.get("enabled", False)):
        known = {spec.name for spec in specs}
        configured_columns = external_config.get("factor_columns")
        if configured_columns:
            external_requested = [factor for factor in factors if factor in set(configured_columns)]
        else:
            external_requested = [factor for factor in factors if factor not in known]
        external_specs = load_external_factor_specs(
            resolve_path(Path(external_config["catalog_path"])),
            external_requested,
            labels,
            require_runnable=bool(external_config.get("require_runnable", True)),
            require_enabled=bool(external_config.get("require_enabled", True)),
        ) if external_requested else []
        specs.extend(spec for spec in external_specs if spec.name not in known)
    return specs


def run_alphalens(
    perf,
    factor_data: pd.DataFrame,
    factor: str,
    output_dir: Path,
    failures: list[dict],
) -> None:
    target = output_dir / "alphalens_reloaded" / factor
    target.mkdir(parents=True, exist_ok=True)
    steps: list[tuple[str, Callable[[], object]]] = [
        ("information_coefficient", lambda: perf.factor_information_coefficient(factor_data)),
        ("mean_information_coefficient", lambda: perf.mean_information_coefficient(factor_data)),
        ("mean_return_by_quantile", lambda: perf.mean_return_by_quantile(factor_data, demeaned=False)),
        ("factor_returns", lambda: perf.factor_returns(factor_data)),
        ("factor_alpha_beta", lambda: perf.factor_alpha_beta(factor_data)),
        (
            "rank_autocorrelation",
            lambda: pd.DataFrame(
                {
                    "1D": perf.factor_rank_autocorrelation(factor_data, period=1),
                    "5D": perf.factor_rank_autocorrelation(factor_data, period=5),
                    "10D": perf.factor_rank_autocorrelation(factor_data, period=10),
                }
            ),
        ),
    ]
    if "factor_quantile" in factor_data.columns:
        max_quantile = int(pd.to_numeric(factor_data["factor_quantile"], errors="coerce").max())
        steps.append(
            (
                "quantile_turnover",
                lambda: pd.concat(
                    {
                        "top_1D": perf.quantile_turnover(factor_data["factor_quantile"], max_quantile, period=1),
                        "top_5D": perf.quantile_turnover(factor_data["factor_quantile"], max_quantile, period=5),
                    },
                    axis=1,
                ),
            )
        )

    for step, func in steps:
        try:
            value = func()
            primary = value[0] if isinstance(value, tuple) else value
            if isinstance(primary, (pd.DataFrame, pd.Series)):
                numeric = (
                    primary.apply(pd.to_numeric, errors="coerce")
                    if isinstance(primary, pd.DataFrame)
                    else pd.to_numeric(primary, errors="coerce")
                )
                numeric_count = (
                    int(numeric.notna().sum().sum())
                    if isinstance(numeric, pd.DataFrame)
                    else int(numeric.notna().sum())
                )
                if numeric_count == 0:
                    raise ValueError(f"{step} produced no numeric values")
                if step == "mean_return_by_quantile" and isinstance(numeric, pd.DataFrame) and numeric.isna().any().any():
                    raise ValueError(f"{step} produced incomplete numeric output")
            if isinstance(value, tuple):
                write_csv(value[0], target / f"{step}.csv")
                write_csv(value[1], target / f"{step}_std_error.csv")
            elif isinstance(value, (pd.DataFrame, pd.Series)):
                write_csv(value, target / f"{step}.csv")
            else:
                pd.DataFrame({"value": [str(value)]}).to_csv(target / f"{step}.csv", index=False, encoding="utf-8-sig")
        except BaseException as exc:
            record_failure(failures, "alphalens_reloaded", factor, step, exc)


def run_jqfactor(
    perf,
    factor_data: pd.DataFrame,
    factor: str,
    output_dir: Path,
    failures: list[dict],
) -> None:
    target = output_dir / "jqfactor_analyzer" / factor
    target.mkdir(parents=True, exist_ok=True)
    steps: list[tuple[str, Callable[[], object]]] = [
        ("information_coefficient", lambda: perf.factor_information_coefficient(factor_data)),
        ("mean_information_coefficient", lambda: perf.mean_information_coefficient(factor_data)),
        ("mean_return_by_quantile", lambda: perf.mean_return_by_quantile(factor_data, demeaned=False)),
        ("factor_returns", lambda: perf.factor_returns(factor_data)),
        ("factor_alpha_beta", lambda: perf.factor_alpha_beta(factor_data)),
    ]
    if "factor_quantile" in factor_data.columns:
        max_quantile = int(pd.to_numeric(factor_data["factor_quantile"], errors="coerce").max())
        steps.append(
            (
                "quantile_turnover",
                lambda: pd.concat(
                    {
                        "top_1": perf.quantile_turnover(factor_data["factor_quantile"], max_quantile, period=1),
                        "top_5": perf.quantile_turnover(factor_data["factor_quantile"], max_quantile, period=5),
                    },
                    axis=1,
                ),
            )
        )

    for step, func in steps:
        try:
            value = func()
            primary = value[0] if isinstance(value, tuple) else value
            if isinstance(primary, (pd.DataFrame, pd.Series)):
                numeric = (
                    primary.apply(pd.to_numeric, errors="coerce")
                    if isinstance(primary, pd.DataFrame)
                    else pd.to_numeric(primary, errors="coerce")
                )
                numeric_count = (
                    int(numeric.notna().sum().sum())
                    if isinstance(numeric, pd.DataFrame)
                    else int(numeric.notna().sum())
                )
                if numeric_count == 0:
                    raise ValueError(f"{step} produced no numeric values")
                if step == "mean_return_by_quantile" and isinstance(numeric, pd.DataFrame) and numeric.isna().any().any():
                    raise ValueError(f"{step} produced incomplete numeric output")
            if isinstance(value, tuple):
                write_csv(value[0], target / f"{step}.csv")
                write_csv(value[1], target / f"{step}_std_error.csv")
            elif isinstance(value, (pd.DataFrame, pd.Series)):
                write_csv(value, target / f"{step}.csv")
            else:
                pd.DataFrame({"value": [str(value)]}).to_csv(target / f"{step}.csv", index=False, encoding="utf-8-sig")
        except BaseException as exc:
            record_failure(failures, "jqfactor_analyzer", factor, step, exc)


def run_grouped_context_evaluator(
    system: str,
    perf,
    factor_data: pd.DataFrame,
    factor: str,
    group_column: str,
    return_mode: str,
    output_dir: Path,
    failures: list[dict],
    status_rows: list[dict],
) -> None:
    target = output_dir / "context" / system / factor / return_mode / group_column
    target.mkdir(parents=True, exist_ok=True)
    try:
        if system == "alphalens_reloaded":
            grouped, report = to_alphalens_factor_data(factor_data, factor, group_column=group_column)
        elif system == "jqfactor_analyzer":
            inputs, report = to_jqfactor_inputs(
                factor_data,
                factor,
                label_period_map=jqfactor_label_period_map(sorted(factor_data["label"].dropna().unique())),
                group_column=group_column,
            )
            grouped = inputs["factor_data"]
        else:
            raise ValueError(f"Unsupported grouped context evaluator: {system}")
        write_adapter_report(report, target / "adapter_report.md")
    except BaseException as exc:
        step = f"context/{return_mode}/{group_column}/adapter"
        record_failure(failures, system, factor, step, exc)
        status_rows.append(
            {
                "system": system,
                "factor": factor,
                "return_mode": return_mode,
                "group_dimension": group_column,
                "step": "adapter",
                "status": "failed",
                "detail": str(exc),
            }
        )
        return

    if not isinstance(grouped, pd.DataFrame) or grouped.empty:
        status_rows.append(
            {
                "system": system,
                "factor": factor,
                "return_mode": return_mode,
                "group_dimension": group_column,
                "step": "adapter",
                "status": "empty",
                "detail": "adapter produced no rows",
            }
        )
        return

    steps: list[tuple[str, Callable[[], object]]] = [
        ("information_coefficient_by_group", lambda: perf.factor_information_coefficient(grouped, by_group=True)),
        ("mean_information_coefficient_by_group", lambda: perf.mean_information_coefficient(grouped, by_group=True)),
        (
            "mean_return_by_quantile_by_group",
            lambda: perf.mean_return_by_quantile(grouped, by_group=True, demeaned=False),
        ),
    ]
    for step, func in steps:
        try:
            value = func()
            primary = value[0] if isinstance(value, tuple) else value
            if isinstance(primary, (pd.DataFrame, pd.Series)):
                numeric = (
                    primary.apply(pd.to_numeric, errors="coerce")
                    if isinstance(primary, pd.DataFrame)
                    else pd.to_numeric(primary, errors="coerce")
                )
                numeric_count = (
                    int(numeric.notna().sum().sum())
                    if isinstance(numeric, pd.DataFrame)
                    else int(numeric.notna().sum())
                )
                if numeric_count == 0:
                    raise ValueError(f"{step} produced no numeric values")
                if (
                    step == "mean_return_by_quantile_by_group"
                    and isinstance(numeric, pd.DataFrame)
                    and numeric.isna().any().any()
                ):
                    raise ValueError(f"{step} produced incomplete numeric output")
            if isinstance(value, tuple):
                write_csv(value[0], target / f"{step}.csv")
                write_csv(value[1], target / f"{step}_std_error.csv")
            else:
                write_csv(value, target / f"{step}.csv")
            status = "pass"
            detail = ""
        except BaseException as exc:
            record_failure(failures, system, factor, f"context/{return_mode}/{group_column}/{step}", exc)
            status = "failed"
            detail = str(exc)
        status_rows.append(
            {
                "system": system,
                "factor": factor,
                "return_mode": return_mode,
                "group_dimension": group_column,
                "step": step,
                "status": status,
                "detail": detail,
            }
        )


def run_qlib_eval(score_frame: pd.DataFrame, factor: str, label: str, output_dir: Path, failures: list[dict]) -> None:
    target = output_dir / "qlib_eval" / factor
    target.mkdir(parents=True, exist_ok=True)
    try:
        from qlib.contrib.evaluate import risk_analysis

        daily = score_frame.groupby("datetime")[["score", "label"]].apply(
            lambda x: x["score"].corr(x["label"], method="spearman")
        )
        daily = daily.dropna()
        risk = risk_analysis(daily, freq="day")
        write_csv(daily.rename("daily_rank_ic"), target / f"{label}_daily_rank_ic.csv")
        write_csv(risk, target / f"{label}_risk_analysis.csv")
    except BaseException as exc:
        record_failure(failures, "qlib_eval", factor, f"{label}_risk_analysis", exc)


def write_current_project_summary(input_dir: Path, factors: list[str], output_dir: Path) -> None:
    target = output_dir / "project_current"
    target.mkdir(parents=True, exist_ok=True)
    summary_path = input_dir / "factor_neutralized_summary.csv"
    group_path = input_dir / "factor_neutralized_group_return_summary.csv"
    corr_path = input_dir / "factor_neutralized_correlation.csv"
    exposure_path = input_dir / "factor_exposure_correlation.csv"

    factor_set = {f"{factor}__raw" for factor in factors}
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        summary[summary["factor"].isin(factor_set)].to_csv(target / "factor_neutralized_summary.csv", index=False, encoding="utf-8-sig")
    if group_path.exists():
        group = pd.read_csv(group_path)
        group[group["factor"].isin(factor_set)].to_csv(
            target / "factor_neutralized_group_return_summary.csv", index=False, encoding="utf-8-sig"
        )
    if corr_path.exists():
        corr = pd.read_csv(corr_path)
        corr[
            corr["factor_a"].isin(factor_set) | corr["factor_b"].isin(factor_set)
        ].to_csv(target / "factor_neutralized_correlation.csv", index=False, encoding="utf-8-sig")
    if exposure_path.exists():
        exposure = pd.read_csv(exposure_path)
        exposure[exposure["factor"].isin(factors)].to_csv(target / "factor_exposure_correlation.csv", index=False, encoding="utf-8-sig")


def write_report(
    output_dir: Path,
    failures: pd.DataFrame,
    factors: list[str],
    evaluator_status: pd.DataFrame,
    dependencies: pd.DataFrame,
    context_status: pd.DataFrame,
) -> None:
    lines = [
        "# Factor Evaluation V4 Smoke Test Report",
        "",
        "This run validates whether open-source evaluation systems can consume the same tradability-filtered factor data.",
        "",
        f"- Factors: `{','.join(factors)}`",
        "- External evaluator results are stored side by side; no project-defined combined score is produced.",
        "- Failures are expected during dependency discovery and are recorded instead of stopping the batch.",
        "",
        "## Status",
        "",
        markdown_table(evaluator_status),
        "",
        "## Dependency Status",
        "",
        markdown_table(dependencies),
        "",
        "## Point-In-Time Context",
        "",
    ]
    if context_status.empty:
        lines.append("Context evaluation was not enabled.")
    else:
        context_summary = context_status.groupby(["system", "return_mode", "group_dimension", "status"]).size().reset_index(name="step_count")
        lines.append(markdown_table(context_summary))
    lines.extend(
        [
        "",
        "## Failures",
        "",
        ]
    )
    if failures.empty:
        lines.append("No failures were recorded.")
    else:
        status = failures.groupby(["system", "step"]).size().reset_index(name="failure_count")
        lines.append(markdown_table(status))
    lines.extend(
        [
            "",
            "## Output Layout",
            "",
            "- `factor_failure_reasons.csv`",
            "- `dependency_status.csv`",
            "- `evaluator_status.csv`",
            "- `open_source_metric_index.csv`",
            "- `adapter_reports/`",
            "- `input_samples/`",
            "- `alphalens_reloaded/<factor>/`",
            "- `jqfactor_analyzer/<factor>/`",
            "- `qlib_eval/<factor>/`",
            "- `project_current/`",
            "- `context/context_coverage.csv`",
            "- `context/context_evaluator_status.csv`",
            "- `context/context_metric_index.csv`",
            "- `context/<system>/<factor>/<return_mode>/<group_dimension>/`",
        ]
    )
    (output_dir / "factor_evaluation_v4_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dependencies = dependency_status()
    dependencies.to_csv(output_dir / "dependency_status.csv", index=False, encoding="utf-8-sig")
    factors = args.factors
    labels = args.labels
    specs = load_requested_specs(args, factors, labels)
    if not specs:
        raise ValueError(f"No enabled specs match requested factors: {factors}")

    window = args.window
    frame = load_window_frame(args, window, output_dir)
    frame = attach_external_factor_frame(frame, args.external_factor_frame_config or {}, factors, output_dir)
    factor_data = to_factor_data(frame, specs, labels, args.quantiles)
    input_sample_dir = output_dir / "input_samples"
    input_sample_dir.mkdir(parents=True, exist_ok=True)
    factor_data.head(args.sample_rows).to_csv(
        input_sample_dir / "internal_factor_data_sample.csv",
        index=False,
        encoding="utf-8-sig",
    )

    context_config = args.context_config or {}
    context_enabled = bool(context_config.get("enabled", False))
    context_keys = pd.DataFrame()
    benchmark_context = pd.DataFrame()
    membership_columns: dict[str, str] = {}
    if context_enabled:
        context_dir = output_dir / "context"
        quantile_scope = str(context_config.get("quantile_scope", "global_market"))
        if quantile_scope != "global_market":
            raise ValueError(f"Unsupported context quantile_scope: {quantile_scope}")
        if context_dir.exists():
            shutil.rmtree(context_dir)
        context_dir.mkdir(parents=True, exist_ok=True)
        provider_uri = context_config.get("provider_uri", args.provider_uri)
        context_keys, membership_columns = build_context_keys(
            frame,
            provider_uri,
            {str(name): str(source) for name, source in context_config["universes"].items()},
            str(context_config["listing_source"]),
            [str(value) for value in context_config["segment_priority"]],
        )
        coverage = context_coverage(context_keys, membership_columns)
        coverage.to_csv(context_dir / "context_coverage.csv", index=False, encoding="utf-8-sig")
        context_keys.head(args.sample_rows).to_csv(
            context_dir / "context_keys_sample.csv", index=False, encoding="utf-8-sig"
        )
        benchmark_context = load_benchmark_context(resolve_path(Path(context_config["benchmark_returns_path"])))
        (context_dir / "context_config.yaml").write_text(
            yaml.safe_dump(context_config, sort_keys=False, allow_unicode=False), encoding="utf-8"
        )

    failures: list[dict] = []
    alphalens_perf, alphalens_error = None, None
    if "alphalens_reloaded" in args.systems:
        try:
            alphalens_perf, alphalens_error = load_package_module_without_init(
                "alphalens",
                PROJECT_ROOT / "tmp" / "reference_repos" / "alphalens-reloaded" / "src" / "alphalens",
                "performance",
                ["utils"],
            )
        except BaseException as exc:
            alphalens_perf, alphalens_error = None, exc

    jq_perf, jq_error = None, None
    if "jqfactor_analyzer" in args.systems:
        try:
            jq_perf, jq_error = load_package_module_without_init(
                "jqfactor_analyzer",
                PROJECT_ROOT / "tmp" / "reference_repos" / "jqfactor_analyzer" / "jqfactor_analyzer",
                "performance",
                ["compat", "utils", "prepare"],
            )
        except BaseException as exc:
            jq_perf, jq_error = None, exc

    if alphalens_error is not None:
        record_failure(failures, "alphalens_reloaded", "*", "import", alphalens_error)
    if jq_error is not None:
        record_failure(failures, "jqfactor_analyzer", "*", "import", jq_error)

    context_status_rows: list[dict] = []
    for factor in factors:
        print(f"Evaluating external systems for {factor}", flush=True)
        factor_input = factor_data[factor_data["factor"].eq(factor)].copy()
        if context_enabled:
            factor_input = attach_context(factor_input, context_keys)
        if "alphalens_reloaded" in args.systems:
            alpha_data, alpha_report = to_alphalens_factor_data(factor_input, factor)
            write_adapter_report(alpha_report, output_dir / "adapter_reports" / f"{factor}_alphalens.md")
            if not alpha_data.empty:
                write_csv(alpha_data.head(args.sample_rows), output_dir / "input_samples" / f"{factor}_alphalens_sample.csv")
            if alphalens_perf is not None and not alpha_data.empty:
                run_alphalens(alphalens_perf, alpha_data, factor, output_dir, failures)

        if "jqfactor_analyzer" in args.systems:
            jq_map = jqfactor_label_period_map(labels)
            jq_inputs, jq_report = to_jqfactor_inputs(factor_input, factor, label_period_map=jq_map)
            write_adapter_report(jq_report, output_dir / "adapter_reports" / f"{factor}_jqfactor.md")
            jq_factor_data = jq_inputs["factor_data"]
            if isinstance(jq_factor_data, pd.DataFrame) and not jq_factor_data.empty:
                write_csv(jq_factor_data.head(args.sample_rows), output_dir / "input_samples" / f"{factor}_jqfactor_sample.csv")
            if jq_perf is not None and isinstance(jq_factor_data, pd.DataFrame) and not jq_factor_data.empty:
                run_jqfactor(jq_perf, jq_factor_data, factor, output_dir, failures)

        if "qlib_eval" in args.systems:
            for label in labels:
                qlib_frame, qlib_report = to_qlib_score_frame(factor_input, factor, label)
                write_adapter_report(qlib_report, output_dir / "adapter_reports" / f"{factor}_{label}_qlib.md")
                if not qlib_frame.empty:
                    write_csv(qlib_frame.head(args.sample_rows), output_dir / "input_samples" / f"{factor}_{label}_qlib_sample.csv")
                    run_qlib_eval(qlib_frame, factor, label, output_dir, failures)

        if context_enabled:
            group_dimensions = [str(value) for value in context_config.get("group_dimensions", [])]
            for system, perf in [
                ("alphalens_reloaded", alphalens_perf),
                ("jqfactor_analyzer", jq_perf),
            ]:
                if system not in args.systems or perf is None:
                    continue
                for group_column in group_dimensions:
                    if factor_input[group_column].nunique(dropna=True) < 2:
                        context_status_rows.append(
                            {
                                "system": system,
                                "factor": factor,
                                "return_mode": "raw_return",
                                "group_dimension": group_column,
                                "step": "dimension_check",
                                "status": "skipped_non_informative",
                                "detail": "fewer than two populated groups",
                            }
                        )
                        continue
                    run_grouped_context_evaluator(
                        system,
                        perf,
                        factor_input,
                        factor,
                        group_column,
                        "raw_return",
                        output_dir,
                        failures,
                        context_status_rows,
                    )

            relative = attach_benchmark_relative_returns(
                factor_input,
                benchmark_context,
                {str(name): str(benchmark) for name, benchmark in context_config["benchmark_by_segment"].items()},
                {str(label): str(column) for label, column in context_config["label_return_columns"].items()},
            )
            relative = relative[relative["excess_forward_return"].notna()].copy()
            relative["forward_return"] = relative["excess_forward_return"]
            for system, perf in [
                ("alphalens_reloaded", alphalens_perf),
                ("jqfactor_analyzer", jq_perf),
            ]:
                if system not in args.systems or perf is None:
                    continue
                for group_column in group_dimensions:
                    if relative[group_column].nunique(dropna=True) < 2:
                        context_status_rows.append(
                            {
                                "system": system,
                                "factor": factor,
                                "return_mode": "benchmark_excess_return",
                                "group_dimension": group_column,
                                "step": "dimension_check",
                                "status": "skipped_non_informative",
                                "detail": "fewer than two populated groups",
                            }
                        )
                        continue
                    run_grouped_context_evaluator(
                        system,
                        perf,
                        relative,
                        factor,
                        group_column,
                        "benchmark_excess_return",
                        output_dir,
                        failures,
                        context_status_rows,
                    )

    if "project_current" in args.systems:
        write_current_project_summary(resolve_path(args.current_project_input_dir), factors, output_dir)
    failure_frame = pd.DataFrame(failures)
    failure_frame.to_csv(output_dir / "factor_failure_reasons.csv", index=False, encoding="utf-8-sig")
    status = build_evaluator_status(output_dir, factors, args.systems, failure_frame)
    status.to_csv(output_dir / "evaluator_status.csv", index=False, encoding="utf-8-sig")
    metric_index = build_open_source_metric_index(output_dir, factors)
    metric_index.to_csv(output_dir / "open_source_metric_index.csv", index=False, encoding="utf-8-sig")
    context_status = pd.DataFrame(context_status_rows)
    if context_enabled:
        context_status.to_csv(
            output_dir / "context" / "context_evaluator_status.csv", index=False, encoding="utf-8-sig"
        )
        context_metric_index = build_context_metric_index(output_dir, factors, args.systems)
        context_metric_index.to_csv(
            output_dir / "context" / "context_metric_index.csv", index=False, encoding="utf-8-sig"
        )
    write_report(output_dir, failure_frame, factors, status, dependencies, context_status)
    print(f"Factor evaluation V4 outputs written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run V4 open-source factor evaluation smoke tests.")
    parser.add_argument("--config", type=Path, help="Optional YAML config. Values in the file override CLI defaults.")
    parser.add_argument("--provider-uri", default=DEFAULT_PROVIDER_URI)
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--labels", type=parse_labels, default=parse_labels(DEFAULT_LABELS))
    parser.add_argument("--factors", type=parse_csv, default=parse_csv(DEFAULT_FACTORS))
    parser.add_argument("--systems", type=parse_csv, default=DEFAULT_SYSTEMS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--quantiles", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=50)
    parser.add_argument("--min-liquidity-bucket", type=int, default=3)
    parser.add_argument("--min-tradability-score", type=float, default=75.0)
    parser.add_argument("--sample-rows", type=int, default=200)
    parser.add_argument("--feature-cache-dir", type=Path, default=Path("tmp/factor_feature_cache"))
    parser.add_argument("--factor-cache-dir", type=Path, default=Path("tmp/factor_frame_cache"))
    parser.add_argument("--no-feature-cache", action="store_true")
    parser.add_argument("--refresh-feature-cache", action="store_true")
    parser.add_argument("--no-factor-cache", action="store_true")
    parser.add_argument("--refresh-factor-cache", action="store_true")
    parser.add_argument("--current-project-input-dir", type=Path, default=Path("outputs/factor_research_v3/liquid2000_expanded"))
    parser.set_defaults(context_config={})
    parser.set_defaults(external_factor_frame_config={})
    parser.add_argument("--write-detail", action="store_true", help=argparse.SUPPRESS)
    parser.set_defaults(window=DEFAULT_WINDOWS[0])
    return parser


def main() -> None:
    freeze_support()
    args = apply_yaml_config(build_parser().parse_args())
    run(args)


if __name__ == "__main__":
    main()

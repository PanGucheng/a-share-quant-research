from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
import traceback
import types
from multiprocessing import freeze_support
from pathlib import Path
from typing import Callable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.dataset import to_factor_data
from factor_research.external.adapters import (
    to_alphalens_factor_data,
    to_jqfactor_inputs,
    to_qlib_score_frame,
    write_adapter_report,
)
from factor_research.report import markdown_table
from factor_research.registry import enabled_specs
from scripts.run_factor_research_v3 import (
    DEFAULT_MARKET,
    DEFAULT_PROVIDER_URI,
    DEFAULT_WINDOWS,
    load_window_frame,
    parse_csv,
    parse_labels,
    resolve_path,
)


DEFAULT_FACTORS = "rev_5,rev_20_exclude_5,std_20,amount_mean_20,downside_std_20"
DEFAULT_LABELS = "label_10d_t1,label_20d_t1"
DEFAULT_OUTPUT_DIR = Path("outputs/factor_evaluation_v4/liquid2000_open_source_eval")


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


def try_import(module_name: str, path: Path | None = None):
    if path is not None:
        sys.path.insert(0, str(path))
    try:
        return importlib.import_module(module_name), None
    except BaseException as exc:
        return None, exc


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


def summarize_series_frame(frame: pd.DataFrame | pd.Series) -> pd.DataFrame:
    if isinstance(frame, pd.Series):
        return frame.to_frame("value").T
    if frame.empty:
        return pd.DataFrame()
    numeric = frame.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame()
    return numeric.agg(["mean", "std", "min", "max", "count"])


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
            if isinstance(value, tuple):
                write_csv(value[0], target / f"{step}.csv")
                write_csv(value[1], target / f"{step}_std_error.csv")
            elif isinstance(value, (pd.DataFrame, pd.Series)):
                write_csv(value, target / f"{step}.csv")
            else:
                pd.DataFrame({"value": [str(value)]}).to_csv(target / f"{step}.csv", index=False, encoding="utf-8-sig")
        except BaseException as exc:
            record_failure(failures, "jqfactor_analyzer", factor, step, exc)


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


def write_report(output_dir: Path, failures: pd.DataFrame, factors: list[str]) -> None:
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
    ]
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
            "- `adapter_reports/`",
            "- `input_samples/`",
            "- `alphalens_reloaded/<factor>/`",
            "- `jqfactor_analyzer/<factor>/`",
            "- `qlib_eval/<factor>/`",
            "- `project_current/`",
        ]
    )
    (output_dir / "factor_evaluation_v4_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    factors = args.factors
    labels = args.labels
    specs = [spec for spec in enabled_specs(labels) if spec.name in set(factors)]
    if not specs:
        raise ValueError(f"No enabled specs match requested factors: {factors}")

    window = args.window
    frame = load_window_frame(args, window, output_dir)
    factor_data = to_factor_data(frame, specs, labels, args.quantiles)
    input_sample_dir = output_dir / "input_samples"
    input_sample_dir.mkdir(parents=True, exist_ok=True)
    factor_data.head(args.sample_rows).to_csv(
        input_sample_dir / "internal_factor_data_sample.csv",
        index=False,
        encoding="utf-8-sig",
    )

    failures: list[dict] = []
    try:
        alphalens_perf, alphalens_error = load_package_module_without_init(
            "alphalens",
            PROJECT_ROOT / "tmp" / "reference_repos" / "alphalens-reloaded" / "src" / "alphalens",
            "performance",
            ["utils"],
        )
    except BaseException as exc:
        alphalens_perf, alphalens_error = None, exc

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

    for factor in factors:
        print(f"Evaluating external systems for {factor}", flush=True)
        alpha_data, alpha_report = to_alphalens_factor_data(factor_data, factor)
        write_adapter_report(alpha_report, output_dir / "adapter_reports" / f"{factor}_alphalens.md")
        if not alpha_data.empty:
            write_csv(alpha_data.head(args.sample_rows), output_dir / "input_samples" / f"{factor}_alphalens_sample.csv")
        if alphalens_perf is not None and not alpha_data.empty:
            run_alphalens(alphalens_perf, alpha_data, factor, output_dir, failures)

        jq_map = jqfactor_label_period_map(labels)
        jq_inputs, jq_report = to_jqfactor_inputs(factor_data, factor, label_period_map=jq_map)
        write_adapter_report(jq_report, output_dir / "adapter_reports" / f"{factor}_jqfactor.md")
        jq_factor_data = jq_inputs["factor_data"]
        if isinstance(jq_factor_data, pd.DataFrame) and not jq_factor_data.empty:
            write_csv(jq_factor_data.head(args.sample_rows), output_dir / "input_samples" / f"{factor}_jqfactor_sample.csv")
        if jq_perf is not None and isinstance(jq_factor_data, pd.DataFrame) and not jq_factor_data.empty:
            run_jqfactor(jq_perf, jq_factor_data, factor, output_dir, failures)

        for label in labels:
            qlib_frame, qlib_report = to_qlib_score_frame(factor_data, factor, label)
            write_adapter_report(qlib_report, output_dir / "adapter_reports" / f"{factor}_{label}_qlib.md")
            if not qlib_frame.empty:
                write_csv(qlib_frame.head(args.sample_rows), output_dir / "input_samples" / f"{factor}_{label}_qlib_sample.csv")
                run_qlib_eval(qlib_frame, factor, label, output_dir, failures)

    write_current_project_summary(resolve_path(args.current_project_input_dir), factors, output_dir)
    failure_frame = pd.DataFrame(failures)
    failure_frame.to_csv(output_dir / "factor_failure_reasons.csv", index=False, encoding="utf-8-sig")
    write_report(output_dir, failure_frame, factors)
    print(f"Factor evaluation V4 outputs written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run V4 open-source factor evaluation smoke tests.")
    parser.add_argument("--provider-uri", default=DEFAULT_PROVIDER_URI)
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--labels", type=parse_labels, default=parse_labels(DEFAULT_LABELS))
    parser.add_argument("--factors", type=parse_csv, default=parse_csv(DEFAULT_FACTORS))
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
    parser.add_argument("--write-detail", action="store_true", help=argparse.SUPPRESS)
    parser.set_defaults(window=DEFAULT_WINDOWS[0])
    return parser


def main() -> None:
    freeze_support()
    args = build_parser().parse_args()
    run(args)


if __name__ == "__main__":
    main()

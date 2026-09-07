"""Run the initial contract audit and native interface smoke, never full selection."""

# ruff: noqa: E402 -- set thread limits and repository import path before NumPy.
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

import numpy as np
import pandas as pd
import psutil
import yaml

from factor_research.long_history_screening import (
    KEYS,
    LABEL,
    common_samples,
    development_calendar,
    exact_primary_labels,
    frame_hash,
    jqfactor_returns_compat,
    label_map,
    native_primary_smoke,
    normalize_keys,
    preflight,
    read_factor,
    sha256_file,
)
from qlib_baseline.settings import load_settings


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )


def native_modules() -> tuple[dict, dict]:
    from scripts.run_factor_evaluation_v4 import load_package_module_without_init

    modules, provenance = {}, {}
    for key, package, relative, preload in (
        ("alphalens", "alphalens", "alphalens-reloaded/src/alphalens", ["utils"]),
        (
            "jqfactor",
            "jqfactor_analyzer",
            "jqfactor_analyzer/jqfactor_analyzer",
            ["compat", "utils", "prepare"],
        ),
    ):
        location = ROOT / "tmp/reference_repos" / relative
        modules[key], _ = load_package_module_without_init(
            package, location, "performance", preload
        )
        provenance[key] = {
            name: sha256_file(location / f"{name}.py") for name in [*preload, "performance"]
        }
    modules["qlib"] = importlib.import_module("qlib.contrib.eva.alpha")
    modules["jqfactor_returns"], provenance["jqfactor_compatibility"] = jqfactor_returns_compat(
        modules["jqfactor"]
    )
    provenance["qlib"] = {
        "file": modules["qlib"].__file__,
        "sha256": sha256_file(Path(modules["qlib"].__file__)),
    }
    provenance["dependencies"] = {
        name: importlib.import_module(name).__version__
        for name in ("pandas", "numpy", "scipy", "qlib")
    }
    return modules, provenance


def run(
    config: dict, out: Path, *, smoke: bool, extended: bool = False, long_smoke: bool = False
) -> dict:
    # Exclusive new run directories preserve prior evidence, including failures.
    out.mkdir(parents=True, exist_ok=False)
    phase0 = out / "phase0"
    phase0.mkdir()
    status = {
        "primary_mvp_status": "in_progress",
        "phase0_status": "in_progress",
        "phase1_status": "not_started",
        "enrichment_status": "not_started",
        "held_aside_recent_diagnostic_accessed": False,
    }
    access, receipts, quality = [], [], []
    started = time.perf_counter()
    try:
        settings = load_settings(project_root=ROOT)
        if settings.qlib_provider is None:
            raise ValueError("configure qlib_provider in project.local.yaml")
        if settings.qlib_source:
            sys.path.insert(0, str(settings.qlib_source))
        calendar_path = settings.qlib_provider / "calendars/day.txt"
        calendar = development_calendar(calendar_path)
        inventory, partitions, identity = preflight(ROOT, config)
        identity.update(
            {
                "git_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "implementation_hashes": {
                    name: sha256_file(ROOT / name)
                    for name in (
                        "factor_research/long_history_screening.py",
                        "scripts/run_long_history_multi_evaluator_screening_v1.py",
                        "research_validation/labels.py",
                        "research_validation/canonical_dataset.py",
                    )
                },
                "calendar_sha256": sha256_file(calendar_path),
                "provider": str(settings.qlib_provider),
                "price_contract": "provider $close; adjusted price ratio; T+1 close to T+21 close; no fill",
            }
        )
        write_json(phase0 / "resolved_config.json", config)
        write_json(phase0 / "input_identity.json", identity)
        inventory.to_csv(phase0 / "factor_inventory.csv", index=False)
        label_map(calendar).to_parquet(phase0 / "label_date_map.parquet", index=False)
        jobs = [
            {
                "factor": factor,
                "backend": backend,
                "label": LABEL,
                "stage": "phase2a_required",
                "status": "not_started",
            }
            for factor in inventory.loc[inventory.research_usable, "factor"]
            for backend in ("alphalens", "jqfactor", "qlib")
        ]
        pd.DataFrame(jobs).to_csv(phase0 / "job_inventory.csv", index=False)
        write_json(
            phase0 / "universe_contract.json",
            {
                "universe": config["universe"],
                "authority": "canonical dated keys",
                "limitations": "Inherited practical PIT/lifecycle certification; not re-certified from raw events",
                "min_count": config["min_count"],
                "quantile_method": "qcut duplicates=drop; require five bins; independent IC mask",
            },
        )
        write_json(
            phase0 / "metric_definitions.json",
            {
                "profile_status": "proposed_until_extended_smoke",
                "rank_ic": "Native daily Spearman on identical finite factor/mature label samples",
                "pearson_ic": "Qlib calc_ic first result",
                "alphalens_quantile": "Native mean_return_by_quantile by_date=True demeaned=False",
                "jqfactor_returns": "Native factor_returns demeaned=True group_adjust=False",
                "qlib_long_short": "Native (top20pct mean - bottom20pct mean)/2; overlapping 20D labels, not strategy NAV",
                "optional_not_run": [
                    "10D",
                    "alpha_beta",
                    "turnover",
                    "autocorrelation",
                    "secondary_universe",
                ],
            },
        )
        # Metadata audit is not the complete Phase 0 feature/PIT audit.
        status["phase0_status"] = "metadata_pass_sample_audit_pending"
        if not smoke:
            return status
        smoke_dir = out / "smoke"
        smoke_dir.mkdir()
        modules, provenance = native_modules()
        write_json(smoke_dir / "native_provenance.json", provenance)
        signal_dates = calendar[calendar >= pd.Timestamp(config["smoke"]["start"])][
            : config["smoke"]["trading_days"]
        ]
        if len(signal_dates) != config["smoke"]["trading_days"]:
            raise ValueError("insufficient smoke trading dates")
        mapping = label_map(calendar).set_index("datetime").loc[signal_dates]
        if mapping.exit_date.isna().any():
            raise ValueError("smoke requests immature labels")
        import qlib
        from qlib.config import C, REG_CN
        from qlib.data import D

        qlib.init(provider_uri=str(settings.qlib_provider), region=REG_CN)
        C.kernels = 1
        C.joblib_backend = "sequential"
        status["phase1_status"] = "minimal_smoke_running"
        smoke_jobs = [
            ("minimal", factor, signal_dates) for factor in config["smoke"]["minimal_factors"]
        ]
        if extended:
            smoke_jobs = [
                (
                    era,
                    factor,
                    calendar[
                        (calendar >= pd.Timestamp(bounds[0]))
                        & (calendar <= pd.Timestamp(bounds[1]))
                    ][:60],
                )
                for era, bounds in config["signal_eras"].items()
                for factor in config["smoke"]["representative_factors"]
            ]
        if long_smoke:
            # Native primary metrics are daily; yearly chunks bound memory and
            # retain the label tail across year boundaries within development.
            mature_calendar = calendar[:-21]
            smoke_jobs = [
                (f"long_{year}", factor, mature_calendar[mature_calendar.year == year])
                for factor in config["smoke"]["minimal_factors"]
                for year in range(2010, 2024)
            ]
        pd.DataFrame(
            [
                {"period": period, "factor": factor, "start": dates[0], "end": dates[-1]}
                for period, factor, dates in smoke_jobs
            ]
        ).to_csv(smoke_dir / "smoke_factor_inventory.csv", index=False)
        for period, factor, signal_dates in smoke_jobs:
            mapping = label_map(calendar).set_index("datetime").loc[signal_dates]
            tick = time.perf_counter()
            print(f"Smoke {period}/{factor}: reading bounded canonical input", flush=True)
            values = read_factor(
                partitions, factor, signal_dates[0], signal_dates[-1], access=access
            )
            prices = normalize_keys(
                D.features(
                    sorted(values.instrument.unique()),
                    ["$close"],
                    start_time=mapping.entry_date.min(),
                    end_time=mapping.exit_date.max(),
                    freq="day",
                ).reset_index()
            )
            if (
                prices.empty
                or not prices.datetime.between(
                    mapping.entry_date.min(), mapping.exit_date.max()
                ).all()
            ):
                raise ValueError("price provider violated bounded request or returned no data")
            access.append(
                {
                    "kind": "price",
                    "factor": factor,
                    "path": str(settings.qlib_provider),
                    "requested_start": str(mapping.entry_date.min().date()),
                    "requested_end": str(mapping.exit_date.max().date()),
                    "rows": len(prices),
                    "slice_hash": frame_hash(prices),
                }
            )
            labels = exact_primary_labels(values[KEYS], prices, calendar)
            merged = values.merge(labels[[*KEYS, LABEL]], on=KEYS, validate="one_to_one")
            ic, quantile, masks = common_samples(merged, factor, min_count=config["min_count"])
            folder = smoke_dir / period / factor
            folder.mkdir(parents=True)
            masks.to_csv(folder / "daily_sample_status.csv", index=False)
            labels.head(50).to_csv(folder / "label_handcheck_sample.csv", index=False)
            finite = np.isfinite(values[factor])
            quality.append(
                {
                    "factor": factor,
                    "scope": f"smoke_{period}_only",
                    "rows": len(values),
                    "finite_count": int(finite.sum()),
                    "coverage": float(finite.mean()),
                    "signal_start": signal_dates[0],
                    "signal_end": signal_dates[-1],
                }
            )
            if ic.empty:
                receipt = {
                    "factor": factor,
                    "period": period,
                    "parity_status": "unavailable",
                    "native_status": {},
                    "reason": "no_definable_daily_samples",
                    "candidate_status": "not_evaluated",
                }
                write_json(folder / "receipt.json", receipt)
                receipts.append(receipt)
                continue
            results, receipt = native_primary_smoke(
                ic, quantile, modules, atol=config["parity_atol"]
            )
            # Deterministic sequential replay uses the same inputs, independent native calls.
            repeat, repeated_receipt = native_primary_smoke(
                ic, quantile, modules, atol=config["parity_atol"]
            )
            for name, result in results.items():
                if isinstance(result, pd.Series):
                    pd.testing.assert_series_equal(result, repeat[name], check_exact=True)
                    result = result.to_frame(name=name)
                else:
                    pd.testing.assert_frame_equal(result, repeat[name], check_exact=True)
                result.to_parquet(folder / f"{name}.parquet")
            if receipt != repeated_receipt:
                raise ValueError("non-deterministic native receipt")
            receipt.update(
                {
                    "factor": factor,
                    "period": period,
                    "sequential_replay": "pass",
                    "wall_seconds": time.perf_counter() - tick,
                    "rss_bytes": psutil.Process().memory_info().rss,
                    "peak_working_set_bytes": getattr(
                        psutil.Process().memory_info(), "peak_wset", None
                    ),
                }
            )
            write_json(folder / "receipt.json", receipt)
            receipts.append(receipt)
            print(f"Smoke {factor}: {receipt['native_status']}", flush=True)
        status["phase0_status"] = "metadata_and_label_sample_pass_full_feature_audit_pending"
        native_failed = any(
            any(v.startswith("failed:") for v in r["native_status"].values()) for r in receipts
        )
        if not any(r["parity_status"] == "pass" for r in receipts):
            raise ValueError("smoke produced no native parity evidence")
        status["phase1_status"] = (
            "minimal_smoke_native_blocked"
            if native_failed
            else "minimal_smoke_pass_extended_pending"
        )
        if extended:
            status["phase1_status"] = (
                "extended_short_windows_native_blocked"
                if native_failed
                else "extended_short_windows_pass_long_smoke_pending"
            )
        if long_smoke:
            status["phase1_status"] = (
                "long_smoke_native_blocked"
                if native_failed
                else "long_smoke_pass_profile_review_pending"
            )
        write_json(smoke_dir / "summary.json", {"receipts": receipts})
        status["phase2a_status"] = "not_started"
        status["required_next"] = (
            "Complete feature/PIT boundary audit, resolve native failures, extended 24-factor/era smoke and resource/profile freeze before full"
        )
        return status
    except Exception as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"
        status["execution_status"] = "failed"
        raise
    finally:
        status["elapsed_seconds"] = time.perf_counter() - started
        pd.DataFrame(access).to_csv(phase0 / "access_audit.csv", index=False)
        pd.DataFrame(quality).to_csv(phase0 / "feature_quality.csv", index=False)
        write_json(out / "status.json", status)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/long_history_multi_evaluator_screening_v1.yaml",
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--smoke", action="store_true", help="Also run minimum real native smoke; no full run"
    )
    parser.add_argument(
        "--extended-smoke",
        action="store_true",
        help="Run fixed 24 factors across four 60-date eras",
    )
    parser.add_argument(
        "--long-smoke",
        action="store_true",
        help="Six fixed factors across full mature development in year chunks",
    )
    args = parser.parse_args()
    if not args.run_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for c in args.run_id
    ):
        parser.error("run-id must contain only letters, digits, underscore or hyphen")
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    result = run(
        config,
        ROOT / "outputs/long_history_multi_evaluator_screening_v1" / args.run_id,
        smoke=args.smoke or args.extended_smoke or args.long_smoke,
        extended=args.extended_smoke,
        long_smoke=args.long_smoke,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if "blocked" in result.get("phase1_status", "") else 0


if __name__ == "__main__":
    raise SystemExit(main())

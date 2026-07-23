from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.factor_dependency import (  # noqa: E402
    classify_python_method,
    filter_only_reuse_allowed,
    qlib_expression_lookback,
    validate_dependency_inventory,
)
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    content_reference_id,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "canary_cases.csv",
    "contract_status.csv",
    "dependency_report.md",
    "dependency_summary.csv",
    "factor_dependency_inventory.csv",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def expression_map(path: Path) -> dict[str, str]:
    frame = pd.read_csv(path)
    return dict(zip(frame["catalog_name"].astype(str), frame["expression"].astype(str)))


def build_inventory(config: dict[str, object]) -> pd.DataFrame:
    inventory = pd.read_csv(resolve(config["factor_inventory"]))
    alpha158 = expression_map(resolve(config["alpha158_inventory"]))
    alpha360 = expression_map(resolve(config["alpha360_inventory"]))
    alpha101_source = resolve(config["alpha101_reference_source"]).read_text(encoding="utf-8")
    illegal_keys = pd.read_csv(resolve(config["illegal_key_resolution"]))
    affected_dates = int(pd.to_datetime(illegal_keys["datetime"]).nunique())
    policies = config["source_policies"]
    rows: list[dict[str, object]] = []

    for item in inventory.itertuples(index=False):
        source = str(item.source)
        policy = policies[source]
        fallback_sensitive = bool(policy.get("fallback_sensitive", False))
        classification_proven = True
        if source in {"alpha158", "alpha360"}:
            expression = (alpha158 if source == "alpha158" else alpha360).get(str(item.name))
            if expression is None:
                dependency_class = "unknown"
                cross = False
                lookback = None
                evidence = "formula_inventory_entry_missing"
                classification_proven = False
            else:
                dependency_class = "pure_time_series"
                cross = False
                lookback = qlib_expression_lookback(expression)
                evidence = (
                    f"{policy['execution_scope']};expression={expression};"
                    "Qlib Rank is rolling Rank(value,window), not cross-sectional rank"
                )
        elif source in {"ta", "project_basic"}:
            dependency_class = "pure_time_series"
            cross = False
            lookback = int(policy["conservative_max_lookback_trading_days"])
            evidence = (
                f"{policy['execution_scope']};adapter computes each instrument "
                "independently before concatenation"
            )
        elif source == "alpha101":
            result = classify_python_method(alpha101_source, str(item.registry_name))
            dependency_class = result.dependency_class
            cross = result.cross_sectional_operator_present
            lookback = result.max_lookback_trading_days
            evidence = (
                f"{policy['execution_scope']};{result.evidence};"
                f"adapter_fallback={policy['fallback_reason']}"
            )
            classification_proven = dependency_class != "unknown"
        else:
            dependency_class = "unknown"
            cross = False
            lookback = None
            evidence = "source_policy_missing"
            classification_proven = False

        reuse = filter_only_reuse_allowed(
            dependency_class,
            classification_proven=classification_proven,
            fallback_sensitive=fallback_sensitive,
        )
        rows.append(
            {
                "factor": item.name,
                "source_family": source,
                "batch_id": item.batch_id,
                "dependency_class": dependency_class,
                "cross_sectional_operator_present": cross,
                "max_lookback_trading_days": lookback,
                "state_propagation_rule": (
                    "same_date_universe_and_instrument_history"
                    if dependency_class == "mixed"
                    else "same_date_universe"
                    if dependency_class == "cross_sectional"
                    else "instrument_local_history_only"
                    if dependency_class == "pure_time_series"
                    else "unresolved_fail_closed"
                ),
                "classification_evidence": evidence,
                "classifier_version": config["classifier_version"],
                "affected_date_count": (
                    affected_dates
                    if dependency_class in {"cross_sectional", "mixed", "unknown"}
                    else 0
                ),
                "fallback_sensitive": fallback_sensitive,
                "filter_only_reuse_allowed": reuse,
                "recompute_policy": (
                    "filter_only_common_keys_bit_identical_candidate"
                    if reuse
                    else "mandatory_recompute_audit"
                ),
                "review_status": "proven" if classification_proven else "blocked_unknown",
            }
        )
    return pd.DataFrame(rows).sort_values(["source_family", "factor"]).reset_index(drop=True)


def build_canaries(frame: pd.DataFrame) -> pd.DataFrame:
    def choose(label: str, query: str, expected: str) -> dict[str, object]:
        matches = frame.query(query)
        if matches.empty:
            return {
                "case": label,
                "factor": "",
                "expected_dependency_class": expected,
                "status": "fail",
                "detail": "no_matching_catalog_factor",
            }
        row = matches.iloc[0]
        return {
            "case": label,
            "factor": row["factor"],
            "expected_dependency_class": expected,
            "status": "pass" if row["dependency_class"] == expected else "fail",
            "detail": row["classification_evidence"],
        }

    rows = [
        choose(
            "proven_pure_time_series",
            "source_family == 'alpha158' and dependency_class == 'pure_time_series'",
            "pure_time_series",
        ),
        choose(
            "proven_cross_sectional",
            "source_family == 'alpha101' and dependency_class == 'cross_sectional'",
            "cross_sectional",
        ),
        choose(
            "mixed_complex",
            "source_family == 'alpha101' and dependency_class == 'mixed'",
            "mixed",
        ),
        choose(
            "alpha101_fallback_sensitive",
            "source_family == 'alpha101' and fallback_sensitive == True",
            "mixed",
        ),
    ]
    rows.append(
        {
            "case": "unknown_fail_closed_fixture",
            "factor": "__unknown_fixture__",
            "expected_dependency_class": "unknown",
            "status": (
                "pass"
                if not filter_only_reuse_allowed(
                    "unknown",
                    classification_proven=False,
                    fallback_sensitive=False,
                )
                else "fail"
            ),
            "detail": "unknown must never permit filter-only reuse",
        }
    )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit 669-factor dependency semantics.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_dependency_v1.yaml"))
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    resolved = {
        **config,
        "config_file_sha256": file_sha256(config_path),
        "factor_inventory_sha256": file_sha256(resolve(config["factor_inventory"])),
        "alpha101_reference_source_sha256": file_sha256(resolve(config["alpha101_reference_source"])),
        "alpha101_adapter_source_sha256": file_sha256(resolve(config["alpha101_adapter_source"])),
    }
    frame = build_inventory(config)
    canaries = build_canaries(frame)
    errors = validate_dependency_inventory(
        frame, pd.read_csv(resolve(config["factor_inventory"]))["name"]
    )
    checks = [
        ("factor_count_669", len(frame) == 669, f"actual={len(frame)}"),
        ("factor_set_exact", not any(value.startswith("factor_set_mismatch") for value in errors), ";".join(errors)),
        ("factor_unique", not frame["factor"].duplicated().any(), ""),
        ("dependency_class_valid", not any(value.startswith("invalid_dependency") for value in errors), ";".join(errors)),
        ("unknown_fail_closed", "unknown_filter_only_reuse" not in errors, ";".join(errors)),
        ("non_time_series_recompute", "non_time_series_filter_only_reuse" not in errors, ";".join(errors)),
        ("canary_coverage", canaries["status"].eq("pass").all(), f"passed={canaries['status'].eq('pass').sum()}/{len(canaries)}"),
        ("all_source_families_present", frame["source_family"].nunique() == 5, f"actual={frame['source_family'].nunique()}"),
    ]
    contract = pd.DataFrame(
        [
            {
                "check": name,
                "status": "pass" if passed else "fail",
                "severity": "critical",
                "detail": detail,
            }
            for name, passed, detail in checks
        ]
    )
    summary = (
        frame.groupby(["source_family", "dependency_class", "recompute_policy"], dropna=False)
        .size()
        .rename("factor_count")
        .reset_index()
    )
    ready = contract["status"].eq("pass").all()
    output = resolve(config["output_dir"])
    with StageOutputPublisher(output, CONTROLLED) as publisher:
        frame.to_csv(publisher.path("factor_dependency_inventory.csv"), index=False, encoding="utf-8-sig")
        canaries.to_csv(publisher.path("canary_cases.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        summary.to_csv(publisher.path("dependency_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("dependency_report.md").write_text(
            "\n".join(
                [
                    "# Factor Dependency Audit V1",
                    "",
                    f"- Factors audited: `{len(frame)}`",
                    f"- Classifier: `{config['classifier_version']}`",
                    f"- Contract ready: `{str(ready).lower()}`",
                    "- `unknown` and every universe-sensitive/fallback-sensitive factor are fail-closed to mandatory recomputation.",
                    "",
                    summary.to_markdown(index=False),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files = [
            publisher.path(name)
            for name in CONTROLLED
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="factor_dependency_v1",
            config=resolved,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[
                resolve(config["factor_catalog_manifest"]),
                resolve(config["universe_v2_manifest"]),
            ],
            factor_catalog_id=content_reference_id(
                "factor-catalog-669",
                [resolve(config["factor_inventory"])],
            ),
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_dependency_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())

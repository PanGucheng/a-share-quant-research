from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/exposure_data_capability_audit_v1.yaml")


@dataclass(frozen=True)
class ExposureCapabilityConfig:
    provider_uri: str
    market: str
    start: str
    end: str
    max_instruments: int
    output_dir: Path
    reference_repos: dict[str, Path]
    existing_outputs: dict[str, Path]
    field_probe: dict[str, tuple[str, ...]]


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_config(path: Path) -> ExposureCapabilityConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    return ExposureCapabilityConfig(
        provider_uri=str(payload["provider_uri"]),
        market=str(payload["market"]),
        start=str(payload["start"]),
        end=str(payload["end"]),
        max_instruments=int(payload.get("max_instruments", 5)),
        output_dir=resolve_path(payload.get("output_dir", "outputs/exposure_data_capability_audit_v1/current")),
        reference_repos={str(key): resolve_path(value) for key, value in payload.get("reference_repos", {}).items()},
        existing_outputs={str(key): resolve_path(value) for key, value in payload.get("existing_outputs", {}).items()},
        field_probe={
            str(key): tuple(str(item) for item in values)
            for key, values in payload.get("field_probe", {}).items()
        },
    )


def scan_reference_capabilities(reference_repos: dict[str, Path]) -> pd.DataFrame:
    targets = [
        ("factortest", "sw_industry", ["getSWIndustryData", "addSWIndustry", "getZXIndustryData", "addXZXind"]),
        ("factortest", "market_cap", ["getCMV", "addXSize", "RegbySize", "calcNeuSize"]),
        ("factortest", "industry_size_neutralization", ["Regbysize", "calcNeuIndsize"]),
        ("factortest", "barra", ["getBarraData", "addXBarra", "RegbyBarra", "calcNeuBarra"]),
        ("qlib_factor_platform", "neutralization_helper", ["neutralize_factor"]),
    ]
    rows: list[dict[str, Any]] = []
    for repo_key, capability, tokens in targets:
        repo = reference_repos.get(repo_key, Path(""))
        text = ""
        files = []
        if repo.exists():
            for path in repo.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".py", ".md"}:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    text += "\n" + content
                    files.append(path)
        matched = [token for token in tokens if token in text]
        rows.append(
            {
                "reference_project": repo_key,
                "capability": capability,
                "status": "present" if matched else "missing",
                "matched_tokens": ",".join(matched),
                "repo_path": portable_path(repo) if repo else "",
                "scanned_file_count": len(files),
            }
        )
    return pd.DataFrame(rows)


def probe_provider_fields(config: ExposureCapabilityConfig) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=config.provider_uri, region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    universe = D.instruments(config.market)
    instruments = D.list_instruments(
        universe,
        start_time=config.start,
        end_time=config.end,
        as_list=True,
    )
    instruments = sorted(str(item).upper() for item in instruments)[: config.max_instruments]
    rows: list[dict[str, Any]] = []
    for group, fields in config.field_probe.items():
        for field in fields:
            status = "missing"
            valid_rows = 0
            total_rows = 0
            error = ""
            try:
                frame = D.features(
                    instruments,
                    [field],
                    start_time=config.start,
                    end_time=config.end,
                    freq="day",
                )
                total_rows = int(len(frame))
                values = pd.to_numeric(frame.iloc[:, 0], errors="coerce") if not frame.empty else pd.Series(dtype=float)
                valid_rows = int(values.notna().sum())
                status = "available" if valid_rows > 0 else "empty"
            except Exception as exc:  # noqa: BLE001 - audit should record provider errors.
                error = f"{type(exc).__name__}: {exc}"
            rows.append(
                {
                    "field_group": group,
                    "field": field,
                    "status": status,
                    "valid_rows": valid_rows,
                    "total_rows": total_rows,
                    "sample_instruments": ",".join(instruments),
                    "error": error,
                }
            )
    return pd.DataFrame(rows)


def audit_existing_outputs(existing_outputs: dict[str, Path]) -> pd.DataFrame:
    expected_files = {
        "factor_context": ["benchmark_returns.csv", "universe_membership_counts.csv", "universe_membership_asof.csv"],
        "tradability": ["tradability_labels.csv"],
        "data_quality_tradability": ["data_quality_report.md"],
        "tradability_exposure_attribution": [
            "tradability_exposure_attribution_board.csv",
            "tradability_exposure_contract_status.csv",
        ],
    }
    rows = []
    for name, path in existing_outputs.items():
        files = expected_files.get(name, [])
        present = [item for item in files if (path / item).exists() and (path / item).stat().st_size > 0]
        rows.append(
            {
                "capability": name,
                "path": portable_path(path),
                "status": "available" if len(present) == len(files) and files else "partial" if present else "missing",
                "expected_files": ",".join(files),
                "present_files": ",".join(present),
            }
        )
    return pd.DataFrame(rows)


def build_capability_board(
    reference: pd.DataFrame,
    provider_fields: pd.DataFrame,
    project_outputs: pd.DataFrame,
) -> pd.DataFrame:
    field_summary = (
        provider_fields.groupby("field_group")
        .agg(
            available_fields=("status", lambda values: int((values == "available").sum())),
            probed_fields=("field", "count"),
        )
        .reset_index()
    )
    rows = [
        {
            "capability": "reference_industry_size_barra_design",
            "status": "available" if reference["status"].eq("present").all() else "partial",
            "detail": f"present={int(reference['status'].eq('present').sum())}/{len(reference)}",
            "next_action": "Use reference designs as module boundaries; do not copy data vendor assumptions.",
        },
        {
            "capability": "project_context_benchmark_universe",
            "status": "available"
            if project_outputs[project_outputs["capability"].eq("factor_context")]["status"].eq("available").any()
            else "missing",
            "detail": "factor_context_v1 benchmark/universe/listing context",
            "next_action": "Keep as current context baseline.",
        },
        {
            "capability": "tradability_and_data_quality_prefilters",
            "status": "available"
            if project_outputs[project_outputs["capability"].isin(["tradability", "data_quality_tradability"])]["status"].isin(["available", "partial"]).all()
            else "missing",
            "detail": "tradability labels and data quality outputs",
            "next_action": "Keep mandatory before exposure evaluation.",
        },
    ]
    for group in ["size", "industry", "barra"]:
        item = field_summary[field_summary["field_group"].eq(group)]
        available = int(item["available_fields"].iloc[0]) if not item.empty else 0
        probed = int(item["probed_fields"].iloc[0]) if not item.empty else 0
        if group == "size":
            next_action = "Use available size field for residualized smoke." if available else "Find or derive market-cap data before size neutralization."
        elif group == "industry":
            next_action = "Use industry field for grouped and neutralized evaluation." if available else "Add external SW/CITICS industry mapping before industry neutralization."
        else:
            next_action = "Use available Barra fields for neutralization smoke." if available else "Do not run Barra neutralization until Barra/style exposures are sourced."
        rows.append(
            {
                "capability": f"provider_{group}_fields",
                "status": "available" if available else "missing",
                "detail": f"available={available}/{probed}",
                "next_action": next_action,
            }
        )
    return pd.DataFrame(rows)


def build_contract_status(
    reference: pd.DataFrame,
    provider_fields: pd.DataFrame,
    project_outputs: pd.DataFrame,
    capability: pd.DataFrame,
) -> pd.DataFrame:
    rows = [
        {
            "check_id": "reference_capabilities_scanned",
            "status": "pass" if not reference.empty and reference["status"].eq("present").any() else "blocked",
            "detail": f"present={int(reference['status'].eq('present').sum())}/{len(reference)}",
        },
        {
            "check_id": "provider_fields_probed",
            "status": "pass" if not provider_fields.empty else "blocked",
            "detail": f"probed_fields={len(provider_fields)}",
        },
        {
            "check_id": "project_context_available",
            "status": "pass"
            if project_outputs[project_outputs["capability"].eq("factor_context")]["status"].eq("available").any()
            else "partial",
            "detail": "factor_context_v1",
        },
        {
            "check_id": "prefilter_outputs_available",
            "status": "pass"
            if project_outputs[project_outputs["capability"].isin(["tradability", "data_quality_tradability"])]["status"].isin(["available", "partial"]).all()
            else "blocked",
            "detail": "tradability,data_quality_tradability",
        },
        {
            "check_id": "exposure_capability_board_written",
            "status": "pass" if len(capability) >= 6 else "blocked",
            "detail": f"capabilities={len(capability)}",
        },
        {
            "check_id": "no_training_side_effect",
            "status": "pass",
            "detail": "data_capability_audit_only",
        },
    ]
    return pd.DataFrame(rows)


def write_report(
    config: ExposureCapabilityConfig,
    reference: pd.DataFrame,
    provider_fields: pd.DataFrame,
    project_outputs: pd.DataFrame,
    capability: pd.DataFrame,
    contract: pd.DataFrame,
) -> None:
    field_status = provider_fields.groupby(["field_group", "status"]).size().reset_index(name="field_count")
    lines = [
        "# Exposure Data Capability Audit V1",
        "",
        "- Scope: data capability audit for industry, size, and Barra-style exposure diagnostics.",
        "- Boundary: no model training, no neutralization run, no strategy optimization.",
        f"- Provider: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Capability Board",
        "",
        markdown_table(capability),
        "",
        "## Provider Field Status",
        "",
        markdown_table(field_status),
        "",
        "## Provider Field Probe",
        "",
        markdown_table(provider_fields),
        "",
        "## Project Outputs",
        "",
        markdown_table(project_outputs),
        "",
        "## Reference Capabilities",
        "",
        markdown_table(reference),
        "",
        "## Notes",
        "",
        "- Missing provider industry or Barra fields should be treated as data gaps, not implementation failures.",
        "- Residualized evaluation should start with any available size field; industry/Barra neutralization requires explicit data sourcing.",
    ]
    (config.output_dir / "exposure_data_capability_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_audit(config: ExposureCapabilityConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    reference = scan_reference_capabilities(config.reference_repos)
    provider_fields = probe_provider_fields(config)
    project_outputs = audit_existing_outputs(config.existing_outputs)
    capability = build_capability_board(reference, provider_fields, project_outputs)
    contract = build_contract_status(reference, provider_fields, project_outputs, capability)

    reference.to_csv(config.output_dir / "reference_capabilities.csv", index=False, encoding="utf-8-sig")
    provider_fields.to_csv(config.output_dir / "provider_field_probe.csv", index=False, encoding="utf-8-sig")
    project_outputs.to_csv(config.output_dir / "project_data_capabilities.csv", index=False, encoding="utf-8-sig")
    capability.to_csv(config.output_dir / "exposure_data_capability_board.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(config.output_dir / "exposure_data_capability_contract_status.csv", index=False, encoding="utf-8-sig")
    write_report(config, reference, provider_fields, project_outputs, capability, contract)
    return {
        "reference_capabilities": reference,
        "provider_field_probe": provider_fields,
        "project_data_capabilities": project_outputs,
        "capability_board": capability,
        "contract_status": contract,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit exposure data capability V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    config = load_config(build_parser().parse_args().config)
    outputs = run_audit(config)
    blocked = outputs["contract_status"][outputs["contract_status"]["status"].eq("blocked")]
    print(f"Exposure data capability audit written to {config.output_dir}", flush=True)
    print(f"Capabilities: {len(outputs['capability_board'])}", flush=True)
    print(f"Provider field probes: {len(outputs['provider_field_probe'])}", flush=True)
    if not blocked.empty:
        raise SystemExit(f"Exposure data capability audit blocked: {blocked.to_dict(orient='records')}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import re
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.factor_clustering import hierarchical_clusters  # noqa: E402
from factor_research.factor_similarity import combined_distance, daily_exposure_similarity, performance_similarity  # noqa: E402
from factor_research.representative_selection import select_representatives  # noqa: E402
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED_OUTPUTS = (
    "exposure_correlation_matrix.csv", "performance_correlation_matrix.csv", "factor_distance_matrix.csv",
    "factor_clusters.csv", "cluster_representatives.csv", "excluded_redundant_factors.csv",
    "cluster_stability.csv", "contract_status.csv", "clustering_report.md", "artifact_manifest.json",
)


def _write_blocked(publisher: StageOutputPublisher, config: dict, code_state, stability: pd.DataFrame) -> None:
    pd.DataFrame(columns=["factor"]).to_csv(publisher.path("exposure_correlation_matrix.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["factor"]).to_csv(publisher.path("performance_correlation_matrix.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["factor"]).to_csv(publisher.path("factor_distance_matrix.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["factor", "cluster_id"]).to_csv(publisher.path("factor_clusters.csv"), index=False, encoding="utf-8-sig")
    representative_columns = ["cluster_id", *stability.columns.tolist(), "representative_score", "is_representative"]
    pd.DataFrame(columns=list(dict.fromkeys(representative_columns))).to_csv(publisher.path("cluster_representatives.csv"), index=False, encoding="utf-8-sig")
    excluded_columns = ["factor", "cluster_id", *stability.columns.tolist(), "representative_score", "exclusion_reason"]
    pd.DataFrame(columns=list(dict.fromkeys(excluded_columns))).to_csv(publisher.path("excluded_redundant_factors.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["cluster_id", "member_count"]).to_csv(publisher.path("cluster_stability.csv"), index=False, encoding="utf-8-sig")
    contract = pd.DataFrame([
        {"check_name": "eligible_factor_count", "status": "blocked", "observed_value": 0, "required_value": ">0", "severity": "critical", "reason": "blocked_no_eligible_factors"},
        {"check_name": "clustering_status", "status": "blocked", "observed_value": "blocked_no_eligible_factors", "required_value": "pass", "severity": "critical", "reason": "No factor passes hardened stability eligibility."},
    ])
    contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
    publisher.path("clustering_report.md").write_text("# Factor Clustering V1\n\n- Status: `blocked_no_eligible_factors`\n- Eligible factors: `0`\n", encoding="utf-8")
    output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="factor_clustering_v1", config=config,
        output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
        input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
        missing_lineage_fields=["universe_artifact_id"], lineage_status="reference_only",
        artifact_status="blocked", blocked_reason="blocked_no_eligible_factors",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Cluster stable factors and choose representatives.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_clustering_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    full_stability = pd.read_csv(PROJECT_ROOT / config["stability_board"])
    stability = full_stability.loc[
        full_stability["stability_role"].isin(config["eligible_roles"])
        & full_stability["eligible_window_count"].gt(0)
    ].copy()
    output = PROJECT_ROOT / config["output_dir"]
    with StageOutputPublisher(output, CONTROLLED_OUTPUTS) as publisher:
        if stability.empty:
            _write_blocked(publisher, config, code_state, full_stability)
            publisher.publish()
            print("factor clustering blocked: no eligible factors")
            return 2

        factor_map = {factor: factor.split("|")[0] for factor in stability["factor"]}
        frame = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
        exposure = daily_exposure_similarity(frame, factor_map, int(config["max_exposure_dates"]))
        series_map = {}
        for path in PROJECT_ROOT.glob(config["daily_ic_glob"]):
            match = re.search(r"label_(\d+d_t\d+)_", path.name)
            key = f"{path.parent.name}|{match.group(1)}"
            if key in factor_map:
                data = pd.read_csv(path, parse_dates=["datetime"])
                series_map[key] = data.set_index("datetime")["daily_rank_ic"]
        performance = performance_similarity(series_map)
        distance = combined_distance(exposure, performance, float(config["exposure_weight"]))
        clusters = hierarchical_clusters(distance, float(config["cluster_distance_threshold"]), config["linkage_method"])
        representatives, excluded = select_representatives(clusters, stability)
        cluster_stability = clusters.groupby("cluster_id").size().reset_index(name="member_count")
        contract = pd.DataFrame([
            {"check_name": "eligible_factor_count", "status": "pass", "observed_value": len(stability), "required_value": ">0", "severity": "critical", "reason": "Current eligible stability inputs."},
            {"check_name": "every_selected_factor_has_cluster", "status": "pass" if len(clusters) == len(stability) else "fail", "observed_value": len(clusters), "required_value": len(stability), "severity": "critical", "reason": "Every eligible factor requires a cluster."},
            {"check_name": "every_cluster_has_representative", "status": "pass" if representatives.cluster_id.nunique() == clusters.cluster_id.nunique() else "fail", "observed_value": representatives.cluster_id.nunique(), "required_value": clusters.cluster_id.nunique(), "severity": "critical", "reason": "Every cluster requires one representative."},
            {"check_name": "default_combination_duplicate_cluster_votes", "status": "pass" if not representatives.cluster_id.duplicated().any() else "fail", "observed_value": int(representatives.cluster_id.duplicated().sum()), "required_value": 0, "severity": "critical", "reason": "One default vote per cluster."},
        ])
        exposure.to_csv(publisher.path("exposure_correlation_matrix.csv"), encoding="utf-8-sig")
        performance.to_csv(publisher.path("performance_correlation_matrix.csv"), encoding="utf-8-sig")
        distance.to_csv(publisher.path("factor_distance_matrix.csv"), encoding="utf-8-sig")
        clusters.to_csv(publisher.path("factor_clusters.csv"), index=False, encoding="utf-8-sig")
        representatives.to_csv(publisher.path("cluster_representatives.csv"), index=False, encoding="utf-8-sig")
        excluded.to_csv(publisher.path("excluded_redundant_factors.csv"), index=False, encoding="utf-8-sig")
        cluster_stability.to_csv(publisher.path("cluster_stability.csv"), index=False, encoding="utf-8-sig")
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("clustering_report.md").write_text(f"# Factor Clustering V1\n\n- Eligible factors: `{len(stability)}`\n- Clusters: `{clusters.cluster_id.nunique()}`\n- Representatives: `{len(representatives)}`\n", encoding="utf-8")
        output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="factor_clustering_v1", config=config,
            output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
            input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
            start_date=frame.datetime.min(), end_date=frame.datetime.max(), missing_lineage_fields=["universe_artifact_id"],
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())

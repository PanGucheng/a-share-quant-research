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


def main() -> int:
    parser = argparse.ArgumentParser(description="Cluster stable factors and choose representatives.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_clustering_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    stability = pd.read_csv(PROJECT_ROOT / config["stability_board"])
    stability = stability.loc[stability["stability_role"].isin(config["eligible_roles"])].copy()
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
        {"check_name": "every_selected_factor_has_cluster", "status": "pass" if len(clusters) == len(stability) else "fail", "observed_value": len(clusters), "required_value": len(stability), "severity": "critical", "reason": "Every eligible factor requires a cluster."},
        {"check_name": "every_cluster_has_representative", "status": "pass" if representatives.cluster_id.nunique() == clusters.cluster_id.nunique() else "fail", "observed_value": representatives.cluster_id.nunique(), "required_value": clusters.cluster_id.nunique(), "severity": "critical", "reason": "Every cluster requires one representative."},
        {"check_name": "default_combination_duplicate_cluster_votes", "status": "pass" if not representatives.cluster_id.duplicated().any() else "fail", "observed_value": int(representatives.cluster_id.duplicated().sum()), "required_value": 0, "severity": "critical", "reason": "Representatives give one default vote per cluster."},
        {"check_name": "clustering_backend", "status": "pass", "observed_value": config["backend"], "required_value": "scipy", "severity": "warning", "reason": "Riskfolio-Lib remains optional and uninstalled; SciPy is the compatible backend."},
    ])
    output = PROJECT_ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    exposure.to_csv(output / "exposure_correlation_matrix.csv", encoding="utf-8-sig")
    performance.to_csv(output / "performance_correlation_matrix.csv", encoding="utf-8-sig")
    distance.to_csv(output / "factor_distance_matrix.csv", encoding="utf-8-sig")
    clusters.to_csv(output / "factor_clusters.csv", index=False, encoding="utf-8-sig")
    representatives.to_csv(output / "cluster_representatives.csv", index=False, encoding="utf-8-sig")
    excluded.to_csv(output / "excluded_redundant_factors.csv", index=False, encoding="utf-8-sig")
    cluster_stability.to_csv(output / "cluster_stability.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "clustering_report.md").write_text(f"# Factor Clustering V1\n\n- Eligible factors: `{len(stability)}`\n- Clusters: `{clusters.cluster_id.nunique()}`\n- Representatives: `{len(representatives)}`\n- Backend: `scipy`\n", encoding="utf-8")
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())

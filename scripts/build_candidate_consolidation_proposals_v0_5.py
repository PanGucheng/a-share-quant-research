"""Interpret sealed similarities; write every member and stop for human review."""

# ruff: noqa: E402
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.summarize_candidate_consolidation_v0_5 import verify_daily
from scripts.run_candidate_consolidation_v0_5 import completed_chunk, run_lock
from factor_research.candidate_consolidation import cluster_distance, verify_primary
from factor_research.candidate_consolidation_summary import view_masks, stable_annotations
from factor_research.candidate_consolidation_proposals import (
    POLICY,
    semantic_review,
    propose_groups,
)
from factor_research.long_history_screening import sha256_file
from qlib_baseline.io import atomic_write_json, atomic_write_text
from research_validation.canonical_dataset import canonical_hash
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform


def full_exact_groups(names, folders):
    signatures = {f: [] for f in names}
    for folder in folders:
        parent = {f: f for f in names}

        def find(f):
            while parent[f] != f:
                f = parent[f]
            return f

        for pair in json.loads((folder / "aliases.json").read_text())["relations"]:
            a, b = find(pair["factor_a"]), find(pair["factor_b"])
            parent[max(a, b)] = min(a, b)
        for f in names:
            signatures[f].append(find(f))
    groups = {}
    for f in names:
        groups.setdefault(tuple(signatures[f]), []).append(f)
    return [g for g in groups.values() if len(g) > 1]


def run(out):
    destination = out / "proposal_v1"
    report = ROOT / "reports/candidate_consolidation_v0_5"
    with run_lock(destination / "run.lock"):
        policy_path = report / "REPRESENTATIVE_POLICY.json"
        if not policy_path.exists() or json.loads(policy_path.read_text()) != POLICY:
            raise ValueError("representative policy must be recorded before interpreting outputs")
        contract, dates, folders, receipts, arrays = verify_daily(out)
        summary = out / "summary_v1"
        if json.loads((summary / "status.json").read_text())["status"] != "complete":
            raise ValueError("summary incomplete")
        summary_binding = json.loads((summary / "contract.json").read_text())
        if summary_binding["daily_contract_hash"] != canonical_hash(contract):
            raise ValueError("summary/daily contract mismatch")
        tables = []
        for folder in sorted((summary / "blocks").iterdir()):
            completed_chunk(folder, canonical_hash(summary_binding))
            tables.append(pd.read_parquet(folder / "pairs.parquet"))
        combined = pd.concat(tables, ignore_index=True)
        names = contract["factor_axis"]
        size = len(names)
        i, j = np.triu_indices(size, 1)
        views = {}
        for view, frame in combined.groupby("view", sort=False):
            frame = frame.sort_values("pair_id").reset_index(drop=True)
            if frame.pair_id.tolist() != list(range(len(i))):
                raise ValueError("summary pair coverage/order mismatch")
            views[view] = frame
        if set(views) != set(view_masks(dates)):
            raise ValueError("summary view coverage mismatch")

        def matrix(values, diagonal=0):
            x = np.full((size, size), np.nan)
            x[i, j] = values
            x[j, i] = values
            np.fill_diagonal(x, diagonal)
            return pd.DataFrame(x, index=names, columns=names)

        distances = {
            v: matrix(np.where(t.comparable, 1 - t.median_abs_rho, np.nan))
            for v, t in views.items()
        }
        stable_similarity = np.min(np.stack([views[v].median_abs_rho for v in "ABCD"]), axis=0)
        stable_known = np.logical_and.reduce([views[v].comparable for v in "ABCD"])
        distances["Stable"] = matrix(np.where(stable_known, 1 - stable_similarity, np.nan))
        all_members, counts, stability, representatives = [], [], [], []
        memberships = {}
        for view, distance in distances.items():
            distance.to_parquet(destination / f"distance_{view}.parquet")
            np.save(
                destination / f"complete_linkage_{view}.npy",
                linkage(squareform(distance.fillna(2).to_numpy()), method="complete"),
                allow_pickle=False,
            )
            for level in POLICY["levels"]:
                cut = round(1 - level, 8)
                members = cluster_distance(distance, cut, view=view)
                memberships[(view, level)] = members
                all_members.append(members.assign(level=level))
                sizes = members.groupby("cluster_id").size()
                counts.append(
                    {
                        "view": view,
                        "level": level,
                        "clusters": len(sizes),
                        "singletons": int((sizes == 1).sum()),
                        "largest_cluster": int(sizes.max()),
                    }
                )
        finite = np.concatenate([a["finite_count"] for a in arrays])
        infinite = np.concatenate([a["infinite_count"] for a in arrays])
        universe = np.concatenate([a["universe_count"] for a in arrays])
        masks = view_masks(dates)
        quality = pd.DataFrame(
            {
                "factor": names,
                "full_coverage": finite.sum(axis=0) / universe.sum(),
                "infinite_fraction": infinite.sum(axis=0) / universe.sum(),
            }
        )
        for era in "ABCD":
            mask = masks[era]
            quality["coverage_" + era] = finite[mask].sum(axis=0) / universe[mask].sum()
        quality["worst_era_coverage"] = quality[["coverage_" + e for e in "ABCD"]].min(axis=1)
        semantics = semantic_review(pd.read_csv(out / "inventory_semantic_audit.csv"))
        active_semantics = semantics.loc[semantics.factor.isin(names)]
        full_signed = matrix(views["Full"].median_signed_rho.to_numpy(), diagonal=1)
        exact = full_exact_groups(names, folders)
        aliases = []
        for group in exact:
            ranked = quality.loc[quality.factor.isin(group)].merge(
                active_semantics[["factor", "formula_token_count"]], on="factor"
            )
            ranked = ranked.sort_values(
                [
                    "worst_era_coverage",
                    "full_coverage",
                    "infinite_fraction",
                    "formula_token_count",
                    "factor",
                ],
                ascending=[False, False, True, True, True],
            )
            rep = ranked.factor.iloc[0]
            aliases.extend(
                {
                    "factor": f,
                    "canonical_representation_proposal": rep,
                    "relation_type": "exact_duplicate",
                    "evidence_status": "empirically_verified_all_months",
                    "month_count": len(folders),
                    "mask_equal": True,
                    "definition_scope": "2010-01-29..2023-12-29 canonical key axis; not universal formula proof",
                }
                for f in group
            )
        for level in POLICY["levels"]:
            members = memberships[("Full", level)]
            proposals = propose_groups(
                members[["factor", "cluster_id"]], active_semantics, quality, distances["Full"]
            )
            representatives.append(proposals.assign(level=level))
            proposals["representation_sign"] = [
                float(np.sign(full_signed.loc[r.factor, r.proposed_representative]))
                if pd.notna(r.proposed_representative) else np.nan
                for r in proposals.itertuples(index=False)
            ]
            representatives[-1] = proposals.assign(level=level)
            # Average is strictly a local contrast in fully known complete clusters.
            for _, group in members.groupby("cluster_id"):
                local = distances["Full"].loc[list(group.factor), list(group.factor)]
                average = cluster_distance(
                    local, round(1 - level, 8), method="average", view="Full_local"
                )
                all_members.append(average.assign(level=level))
            for view in [v for v in views if v != "Full"]:
                other = memberships[(view, level)].set_index("factor").cluster_id
                for cluster, group in members.groupby("cluster_id"):
                    g = list(group.factor)
                    known = distances[view].loc[g, g].notna().to_numpy()
                    left, right = np.triu_indices(len(g), 1)
                    comparable = known[left, right]
                    retained = other.loc[g].to_numpy()[left] == other.loc[g].to_numpy()[right]
                    # Jaccard is restricted to a disclosed comparison universe:
                    # factors comparable to every member of this Full cluster.
                    eligible = distances[view].loc[:, g].notna().all(axis=1)
                    eligible_names = set(eligible.index[eligible])
                    ref = set(g) & eligible_names
                    best = 0.0 if ref else np.nan
                    for candidate_id in set(other.loc[list(ref)]):
                        cand = set(other.index[other.eq(candidate_id)]) & eligible_names
                        if ref and cand:
                            best = max(best, len(ref & cand) / len(ref | cand))
                    stability.append(
                        {
                            "level": level,
                            "cluster_id": cluster,
                            "comparison_view": view,
                            "members": len(g),
                            "comparable_pairs": int(comparable.sum()),
                            "all_pairs": len(left),
                            "co_membership_retention": float(retained[comparable].mean())
                            if comparable.any()
                            else np.nan,
                            "eligible_reference_members": len(ref),
                            "eligible_universe_members": len(eligible_names),
                            "best_eligible_member_jaccard": best,
                            "full_max_within_cluster_distance": float(
                                distances["Full"].loc[g, g].max().max()
                            ),
                        }
                    )
        board = pd.DataFrame({"factor": names})
        long = pd.concat(representatives, ignore_index=True)
        for level, group in long.groupby("level"):
            suffix = str(level).replace(".", "_")
            projection = group[["factor", "cluster_id", "proposal_role", "proposed_representative", "representation_sign"]]
            board = board.merge(
                projection.rename(
                    columns={c: c + "_" + suffix for c in projection if c != "factor"}
                ),
                on="factor",
                validate="one_to_one",
            )
        board["user_decision"] = "pending"
        board["replacement_authority"] = "none_proposal_only"
        alias_table = pd.DataFrame(
            aliases,
            columns=[
                "factor",
                "canonical_representation_proposal",
                "relation_type",
                "evidence_status",
                "month_count",
                "mask_equal",
                "definition_scope",
            ],
        )
        board = board.merge(
            alias_table[["factor", "canonical_representation_proposal"]],
            on="factor",
            how="left",
            validate="one_to_one",
        )
        exposure = []
        for control in contract["config"]["controls"]:
            c = names.index(control)
            selected = (i == c) | (j == c)
            for view in ("Full", "A", "B", "C", "D"):
                frame = views[view].loc[selected].copy()
                positions = np.where(i[selected] == c, j[selected], i[selected])
                frame["factor"] = [names[p] for p in positions]
                frame["control"] = control
                frame["self_comparison"] = False
                frame["interpretation"] = "marginal_exposure_annotation_only"
                exposure.append(frame)
        risk = pd.concat(exposure, ignore_index=True)
        families = active_semantics.set_index("factor").proposed_family
        for control in contract["config"]["controls"]:
            selected = risk.control.eq(control)
            if "market_cap" in control:
                intended = {"Size"}
            elif "volatility" in control:
                intended = {"VolatilityRisk", "RiskLottery"}
            else:
                intended = {"Liquidity"}
            same_family = risk.loc[selected, "factor"].map(families).isin(intended)
            high = risk.loc[selected, "median_abs_rho"].ge(0.85) & risk.loc[selected, "comparable"]
            risk.loc[selected, "exposure_role"] = np.where(
                same_family,
                "intended_family_consistent",
                np.where(high, "possibly_unintended_review", "unresolved_or_not_dominant"),
            )
        # Self comparisons are definition annotations, excluded from risk findings.
        for control in contract["config"]["controls"]:
            risk = pd.concat(
                [
                    risk,
                    pd.DataFrame(
                        [
                            {
                                "factor": control,
                                "control": control,
                                "view": v,
                                "self_comparison": True,
                                "interpretation": "identity_only_not_a_risk_finding",
                            }
                            for v in ("Full", "A", "B", "C", "D")
                        ]
                    ),
                ],
                ignore_index=True,
            )
        all_clusters = pd.concat(all_members, ignore_index=True)
        economic = all_clusters.loc[all_clusters.view.eq("Full")].merge(
            active_semantics, on="factor"
        )
        cluster_economic = (
            economic.groupby(["level", "cluster_id"])
            .agg(
                members=("factor", "size"),
                mechanisms=("mechanism", lambda x: json.dumps(sorted(set(x)))),
                horizons=("horizon", lambda x: json.dumps(sorted(set(x)))),
                unresolved_members=("representative_eligible", lambda x: int((~x).sum())),
            )
            .reset_index()
        )
        cluster_risk = all_clusters.loc[all_clusters.view.eq("Full")].merge(
            risk.loc[risk.view.eq("Full") & ~risk.self_comparison][
                ["factor", "control", "median_signed_rho", "median_abs_rho", "comparable"]
            ],
            on="factor",
        )
        cluster_risk = (
            cluster_risk.groupby(["level", "cluster_id", "control"])
            .agg(
                signed_min=("median_signed_rho", "min"),
                signed_max=("median_signed_rho", "max"),
                member_median_abs=("median_abs_rho", "median"),
                comparable_members=("comparable", "sum"),
            )
            .reset_index()
        )
        cluster_risk["comparable_members"] = cluster_risk.comparable_members.astype(int)
        relation_counts = []
        for level in POLICY["levels"]:
            states = stable_annotations(views, level)
            era_pass = np.stack(
                [
                    (
                        views[v].median_abs_rho.ge(level)
                        & views[v].q10_abs_rho.ge(level)
                        & views[v].sign_consistency.ge(0.95)
                    ).to_numpy()
                    for v in "ABCD"
                ]
            )
            era_sign = np.stack([views[v].dominant_sign for v in "ABCD"])
            changed = (era_pass != era_pass[0]).any(axis=0) | (era_sign != era_sign[0]).any(axis=0)
            states = np.where(
                (states == "no_stable_redundancy") & changed, "regime_dependent", states
            )
            pd.DataFrame(
                {
                    "factor_a": np.asarray(names)[i],
                    "factor_b": np.asarray(names)[j],
                    "relation": states,
                }
            ).to_parquet(destination / f"pair_relations_{level}.parquet", index=False)
            relation_counts.append({"level": level, **pd.Series(states).value_counts().to_dict()})
        products = {
            "economic_semantic_review.csv": semantics,
            "feature_quality.csv": quality,
            "exact_alias_map.csv": alias_table,
            "representative_proposal_board.csv": board,
            "cluster_counts.csv": pd.DataFrame(counts),
            "cluster_stability.csv": pd.DataFrame(stability),
            "cluster_economic_summary.csv": cluster_economic,
            "stable_pair_counts.csv": pd.DataFrame(relation_counts),
        }
        for name, frame in products.items():
            frame.to_csv(report / name, index=False)
        all_clusters.to_parquet(destination / "cluster_membership.parquet", index=False)
        long.to_parquet(destination / "representative_policy_details.parquet", index=False)
        risk.to_parquet(destination / "risk_exposure_annotations.parquet", index=False)
        cluster_risk.to_parquet(destination / "cluster_risk_exposure.parquet", index=False)
        risk.loc[risk.view.eq("Full")].to_csv(report / "risk_exposure_full.csv", index=False)
        limits = {
            "price_level": "unavailable_units_not_verified_for_this_provider",
            "industry": "unavailable_for_development",
            "scope": "feature_only_not_independent_alpha",
            "semantic_review": "rule_assisted_reconciliation_not_expert_signoff",
        }
        verify_primary(ROOT)
        result = {
            "status": "representative_proposal_stop_for_human_review",
            "daily_contract_hash": canonical_hash(contract),
            "summary_contract_hash": canonical_hash(summary_binding),
            "policy_hash": canonical_hash(POLICY),
            "active": len(board),
            "semantic_rows": len(semantics),
            "exact_groups": len(exact),
            "exact_group_members": len(alias_table),
            "limits": limits,
            "code_hashes": {
                p: sha256_file(ROOT / p)
                for p in (
                    "factor_research/candidate_consolidation_proposals.py",
                    "scripts/build_candidate_consolidation_proposals_v0_5.py",
                )
            },
            "report_hashes": {n: sha256_file(report / n) for n in products},
        }
        counts_table = (
            "| Level | Clusters | Singletons | Largest |\n|---|---:|---:|---:|\n"
            + "\n".join(
                f"| {r['level']} | {r['clusters']} | {r['singletons']} | {r['largest_cluster']} |"
                for r in counts
                if r["view"] == "Full"
            )
        )
        atomic_write_text(
            report / "REPORT.md",
            "# Candidate Consolidation V0.5 代表提案\n\n"
            + "状态：STOP FOR HUMAN REVIEW。保留全部494成员、765语义记录；无最终Core、删除或模型。\n\n"
            + f"全期逐月精确相等证据：{len(exact)}组，共{len(alias_table)}个成员。\n\n"
            + counts_table
            + "\n\n四个层级并列诊断，不选择某个层级作为入池规则。簇内继续按机制/窗口分层，保留窗口变体；代表只按覆盖、异常、公式复杂度和距离排序。\n\n"
            + "市值、换手、交易活动、非流动性和波动暴露已计算。价格单位的provider-specific provenance未验证，价格暴露暂缺；行业无开发期数据。单因子边际相关不证明独立Alpha。\n\n"
            + "[代表提案](representative_proposal_board.csv)、[精确重复](exact_alias_map.csv)、[语义审阅](economic_semantic_review.csv)、[聚类稳定性](cluster_stability.csv)、[风险暴露](risk_exposure_full.csv)。详细日证据、矩阵及各时期暴露保留在runtime。\n",
        )
        result["report_hashes"].update({name: sha256_file(report / name) for name in
            ("REPORT.md", "risk_exposure_full.csv", "REPRESENTATIVE_POLICY.json")})
        result["runtime_hashes"] = {p.name: sha256_file(p) for p in destination.iterdir()
            if p.suffix in {".parquet", ".npy"}}
        atomic_write_json(report / "PROPOSAL_RECEIPT.json", result)
        atomic_write_json(destination / "status.json", result)
        atomic_write_json(out / "status.json", {
            "status": result["status"], "daily_evidence": "complete", "summary": "complete",
            "proposal": "complete_with_disclosed_limits", "limits": limits,
            "held_aside_recent_diagnostic_accessed": False,
        })
        print(
            json.dumps(
                {k: v for k, v in result.items() if k not in {"report_hashes", "code_hashes", "runtime_hashes"}},
                indent=2,
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_id):
        parser.error("invalid run-id")
    run(ROOT / "outputs/candidate_consolidation_v0_5" / args.run_id)

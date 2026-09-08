"""Build a separate V0.5.1 representative proposal from sealed V0.5 evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from factor_research.candidate_consolidation import verify_primary
from factor_research.candidate_consolidation_revision import (
    POLICY, LOW_COVERAGE_REVIEW, ta_definitions, revised_semantics, propose_revision,
)
from factor_research.candidate_consolidation_summary import stable_annotations
from factor_research.long_history_screening import sha256_file
from qlib_baseline.io import atomic_write_json, atomic_write_text
from research_validation.canonical_dataset import canonical_hash
from scripts.run_candidate_consolidation_v0_5 import completed_chunk, run_lock


def verify_sealed(root, out):
    report = root / "reports/candidate_consolidation_v0_5"
    receipt = json.loads((report / "PROPOSAL_RECEIPT.json").read_text())
    for key, base in [("report_hashes", report), ("runtime_hashes", out / "proposal_v1"), ("code_hashes", root)]:
        for name, expected in receipt[key].items():
            if sha256_file(base / name) != expected:
                raise ValueError(f"sealed source changed: {key}/{name}")
    verify_primary(root)
    contract = json.loads((out / "contract.json").read_text())
    if canonical_hash(contract) != receipt["daily_contract_hash"]:
        raise ValueError("daily contract mismatch")
    return report, receipt, contract


def load_views(out, receipt, names):
    summary = out / "summary_v1"
    binding = json.loads((summary / "contract.json").read_text())
    if canonical_hash(binding) != receipt["summary_contract_hash"]:
        raise ValueError("sealed summary binding mismatch")
    tables, hashes = [], {}
    for folder in sorted((summary / "blocks").iterdir()):
        if completed_chunk(folder, canonical_hash(binding)) is None:
            raise ValueError("incomplete summary block")
        path = folder / "pairs.parquet"
        hashes[str(path.relative_to(out))] = sha256_file(path)
        tables.append(pd.read_parquet(path, filters=[("view", "in", ["Full", "A", "B", "C", "D"])]))
    joined = pd.concat(tables, ignore_index=True)
    views = {v: g.sort_values("pair_id").reset_index(drop=True) for v, g in joined.groupby("view")}
    expected = list(range(len(names) * (len(names) - 1) // 2))
    if set(views) != {"Full", "A", "B", "C", "D"} or any(v.pair_id.tolist() != expected for v in views.values()):
        raise ValueError("Full/Era pair axis incomplete")
    return views, hashes


def pair_table(names, views, relation, level):
    i, j = np.triu_indices(len(names), 1)
    result = pd.DataFrame({"factor_a": np.asarray(names)[i], "factor_b": np.asarray(names)[j]})
    if not result.equals(relation[["factor_a", "factor_b"]]):
        raise ValueError("relation pair axis mismatch")
    result["relation"] = relation.relation.to_numpy()
    result["strict_stable"] = stable_annotations(views, level) == "stable_redundancy"
    if not np.array_equal(result.strict_stable, result.relation.eq("stable_redundancy")):
        raise ValueError("sealed relation disagrees with recomputed strict rule")
    result["all_views_comparable"] = np.logical_and.reduce([v.comparable for v in views.values()])
    for view, data in views.items():
        for column in ["comparable", "valid_dates", "valid_date_fraction", "q10_n_common", "q10_common_coverage",
                       "median_abs_rho", "q10_abs_rho", "median_signed_rho", "dominant_sign", "sign_consistency"]:
            result[view + "_" + column] = data[column].to_numpy()
    return result


def source_audit(root):
    source = root / "tmp/reference_repos/ta"
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if commit != "a890410710a6e483c9ba08da7f3dd5089e4b9dff":
        raise ValueError("unexpected TA reference commit")
    if subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--", "ta"], text=True).strip():
        raise ValueError("TA source has local modifications")
    paths = [*sorted((source / "ta").glob("*.py"))]
    paths += [root / p for p in [
        "factor_research/factor_library.py", "factor_universe_v2/mature_factors.py",
        "factor_universe_v2/historical_data.py", "research_validation/overlap_lineage.py",
        "scripts/run_full_research_feature_matrix_v1.py",
        "scripts/run_historical_data_engineering_extension_v1.py",
        "scripts/run_canonical_historical_dataset_assembly_v1.py",
        "outputs/canonical_historical_dataset_assembly_v1/current/factor_lineage.csv",
        "outputs/canonical_historical_dataset_assembly_v1/current/partition_manifest.csv",
    ]]
    return source, {"ta_commit": commit, "hashes": {str(p.relative_to(root)): sha256_file(p) for p in paths}}


def recursive_gap_diagnostic(source):
    """Synthetic causal gap experiment, with the same pinned classes and parameters.

    Does not replace canonical data or claim the experiment quantifies every real gap.
    """
    sys.path.insert(0, str(source))
    from ta.trend import ADXIndicator
    from ta.volatility import AverageTrueRange
    from ta.trend import EMAIndicator
    base = pd.Series(100 + np.arange(160) * .1 + np.sin(np.arange(160)))
    rows = []
    for variant in ["complete", "single_internal_gap", "leading_gap"]:
        close, high, low = base.copy(), base + 2, base - 2
        if variant != "complete":
            gap = 60 if variant == "single_internal_gap" else 0
            close.iloc[gap] = high.iloc[gap] = low.iloc[gap] = np.nan
        adx = ADXIndicator(high, low, close, window=14, fillna=False)
        series = {"ta_volatility_atr": AverageTrueRange(high, low, close, window=10, fillna=False).average_true_range(),
                  "ta_trend_adx_pos": adx.adx_pos(), "ta_trend_adx_neg": adx.adx_neg(),
                  "ta_trend_ema_fast": EMAIndicator(close, window=12, fillna=False).ema_indicator()}
        for factor, values in series.items():
            rows.append({"factor": factor, "case": variant, "tail_start_index": 100,
                         "tail_rows": 60, "tail_finite": int(np.isfinite(values.iloc[100:]).sum())})
    return pd.DataFrame(rows)


def real_gap_diagnostic(root, source):
    """Bounded 2013 attribution: two alphabetic all-missing names plus one finite control.

    Reconstruct only these three indicators for three stocks using the historical
    300-session bootstrap and PIT mask. Missingness selects diagnostic examples,
    never working-set membership or a replacement threshold.
    """
    from factor_research.candidate_consolidation import read_panel
    from factor_research.long_history_screening import DATASET_ID, frame_hash
    from research_validation.canonical_dataset import canonical_dataset_identity
    from research_validation.feature_matrix import build_pit_key_grid
    from factor_research.alpha101_source import mask_raw_to_pit_membership
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D
    sys.path.insert(0, str(source))
    from ta.trend import ADXIndicator
    from ta.volatility import AverageTrueRange
    base = root / "outputs/canonical_historical_dataset_assembly_v1/current"
    partitions, lineage = pd.read_csv(base / "partition_manifest.csv"), pd.read_csv(base / "factor_lineage.csv")
    if canonical_dataset_identity(partitions, lineage) != DATASET_ID:
        raise ValueError("diagnostic canonical identity mismatch")
    access, factors = [], sorted(LOW_COVERAGE_REVIEW)
    panel = read_panel(partitions, factors, "2013-01-01", "2013-12-31", access=access)
    counts = panel.groupby("instrument").ta_volatility_atr.count()
    symbols = sorted(set(list(counts[counts.eq(0)].index[:2]) + list(counts[counts.gt(200)].index[:1])))
    if len(symbols) != 3:
        raise ValueError("missing bounded diagnostic examples")
    provider = root.parent / "qlib_data/cn_data_community_20260609_derived"
    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels, C.joblib_backend = 1, "sequential"
    calendar = pd.DatetimeIndex(D.calendar(start_time="2010-01-01", end_time="2013-12-31"))
    start = calendar[calendar.searchsorted(pd.Timestamp("2013-01-01")) - 300]
    raw = D.features(symbols, ["$high", "$low", "$close"], start_time=start, end_time="2013-12-31").reset_index()
    raw.instrument = raw.instrument.str.upper()
    if not raw.datetime.between(pd.Timestamp("2010-01-29"), pd.Timestamp("2013-12-31")).all():
        raise ValueError("raw diagnostic date boundary")
    path = root / "outputs/historical_data_engineering_extension_v1/universe/universe_intervals.csv"
    intervals = pd.read_csv(path)
    keys = build_pit_key_grid(intervals[intervals.instrument.isin(symbols)], calendar[calendar >= start])
    masked = mask_raw_to_pit_membership(raw, keys, membership_start=pd.to_datetime(intervals.start_date).min())
    rows = []
    for symbol, group in masked.groupby("instrument"):
        group = group.sort_values("datetime")
        high, low, close = [group[f] for f in ["$high", "$low", "$close"]]
        adx = ADXIndicator(high, low, close, window=14, fillna=False)
        computed = {"ta_volatility_atr": AverageTrueRange(high, low, close, window=10, fillna=False).average_true_range(),
                    "ta_trend_adx_pos": adx.adx_pos(), "ta_trend_adx_neg": adx.adx_neg()}
        gaps = group[["$high", "$low", "$close"]].isna().any(axis=1)
        raw_gaps = raw.loc[raw.instrument.eq(symbol), ["$high", "$low", "$close"]].isna().any(axis=1)
        for factor, values in computed.items():
            compared = pd.DataFrame({"datetime": group.datetime, "recomputed": values}).merge(
                panel.loc[panel.instrument.eq(symbol), ["datetime", factor]], on="datetime", validate="one_to_one")
            x, y = compared.recomputed.to_numpy(), compared[factor].to_numpy()
            equal = np.isclose(x, y, rtol=1e-7, atol=1e-8, equal_nan=True)
            rows.append({"instrument": symbol, "factor": factor, "start": "2013-01-01", "end": "2013-12-31",
                         "warmup_start": str(start.date()), "rows": len(compared), "raw_gap_rows": int(raw_gaps.sum()),
                         "masked_gap_rows": int(gaps.sum()), "gap_dates": json.dumps(group.loc[gaps, "datetime"].dt.strftime("%Y-%m-%d").tolist()),
                         "canonical_finite": int(np.isfinite(y).sum()), "recomputed_finite": int(np.isfinite(x).sum()),
                         "mismatches": int((~equal).sum()), "interpretation": "bounded_recursion_and_mask_replay_not_global_attribution"})
    evidence = {"selection": "2013 alphabetic first two ATR all-missing stocks and first ATR >200 finite-row control",
                "canonical_slices": access, "raw_fields": ["$high", "$low", "$close"], "symbols": symbols,
                "raw_start": str(start.date()), "raw_end": "2013-12-31", "raw_slice_hash": frame_hash(raw),
                "masked_slice_hash": frame_hash(masked), "intervals_sha256": sha256_file(path)}
    return pd.DataFrame(rows), evidence


def run(root, out, revision):
    original, receipt, contract = verify_sealed(root, out)
    report = original / revision
    destination = out / ("proposal_" + revision)
    with run_lock(out / "revision.lock"):
        if report.exists() or destination.exists():
            raise ValueError("revision already exists; preserve it and use a new revision-id")
        source, provenance = source_audit(root)
        # Record policy before interpreting the revision's numerical results.
        report.mkdir(parents=True)
        destination.mkdir(parents=True)
        atomic_write_json(report / "REPRESENTATIVE_POLICY.json", POLICY)
        names = contract["factor_axis"]
        if names != sorted(names) or len(names) != 494:
            raise ValueError("expected sealed sorted 494 axis")
        inventory = pd.read_csv(out / "inventory_semantic_audit.csv")
        # The runtime inventory must match the sealed report's original semantic projection.
        old_semantics = pd.read_csv(original / "economic_semantic_review.csv")
        from factor_research.candidate_consolidation_proposals import semantic_review
        pd.testing.assert_frame_equal(semantic_review(inventory).reset_index(drop=True), old_semantics, check_dtype=False)
        semantic = revised_semantics(inventory, ta_definitions(source))
        active = semantic.loc[semantic.factor.isin(names)]
        if len(semantic) != 765 or len(active) != 494:
            raise ValueError("semantic membership changed")
        quality = pd.read_csv(original / "feature_quality.csv")
        distance = pd.read_parquet(out / "proposal_v1/distance_Full.parquet")
        memberships = pd.read_parquet(out / "proposal_v1/cluster_membership.parquet")
        old = pd.read_parquet(out / "proposal_v1/representative_policy_details.parquet")
        exact = pd.read_csv(original / "exact_alias_map.csv")
        exact["registration_status"] = "registered_development_sample_equality_identity_preserved"
        views, summary_hashes = load_views(out, receipt, names)
        outputs, changes, support = [], [], []
        sem = semantic.set_index("factor")
        for level in POLICY["levels"]:
            relations = pd.read_parquet(out / f"proposal_v1/pair_relations_{level}.parquet")
            pairs = pair_table(names, views, relations, level)
            members = memberships.loc[memberships.view.eq("Full") & memberships.level.eq(level), ["factor", "cluster_id"]]
            proposed = propose_revision(members, active, quality, distance, pairs)
            proposed["level"] = level
            proposed = proposed.merge(exact[["factor", "canonical_representation_proposal"]], on="factor", how="left", validate="one_to_one")
            proposed["replacement_authority"] = "none_proposal_only"
            outputs.append(proposed)
            lookup = pairs.set_index(["factor_a", "factor_b"])
            newer = proposed.set_index("factor")
            selected_pairs = set()
            for row in proposed.itertuples():
                if pd.notna(row.considered_representative) and row.factor != row.considered_representative:
                    selected_pairs.add(tuple(sorted([row.factor, row.considered_representative])))
            for row in old.loc[old.level.eq(level)].itertuples():
                new = newer.loc[row.factor]
                flags = []
                if row.proposal_role == "conditional_alias_proposal":
                    f, g = row.factor, row.proposed_representative
                    pair = tuple(sorted([f, g])); selected_pairs.add(pair)
                    if lookup.loc[pair, "relation"] != "stable_redundancy":
                        flags.append(lookup.loc[pair, "relation"])
                    for c in ["mechanism", "horizon", "formula_units"]:
                        if sem.loc[f, c] != sem.loc[g, c]:
                            flags.append("different_" + c)
                    flags += [str(sem.loc[n, "replacement_hold_reason"]) for n in [f, g] if sem.loc[n, "replacement_hold_reason"]]
                changed = row.proposal_role != new.proposal_role or str(row.proposed_representative) != str(new.proposed_representative)
                changes.append({"level": level, "factor": row.factor, "old_role": row.proposal_role,
                                "old_representative": row.proposed_representative, "new_role": new.proposal_role,
                                "new_representative": new.proposed_representative, "changed": changed,
                                "old_alias_review_reasons": json.dumps(sorted(set(flags))), "reason": new.reason,
                                "user_decision": "pending"})
            support.append(lookup.loc[sorted(selected_pairs)].reset_index().assign(level=level) if selected_pairs else pairs.iloc[:0].assign(level=level))
        long = pd.concat(outputs, ignore_index=True)
        changes = pd.DataFrame(changes)
        board = pd.DataFrame({"factor": names})
        for level, group in long.groupby("level"):
            columns = ["factor", "proposal_role", "proposed_representative", "representation_sign", "reason", "all_views_comparable_peers", "unknown_pair_count"]
            board = board.merge(group[columns].rename(columns={c: c + "_" + str(level).replace(".", "_") for c in columns if c != "factor"}), on="factor", validate="one_to_one")
        board = board.merge(active[["factor", "mechanism", "horizon", "formula_units", "replacement_hold_reason"]], on="factor", validate="one_to_one")
        board = board.merge(exact[["factor", "canonical_representation_proposal", "registration_status"]], on="factor", how="left", validate="one_to_one")
        board["user_decision"], board["replacement_authority"] = "pending", "none_proposal_only"
        diagnostic = recursive_gap_diagnostic(source)
        real_diagnostic, diagnostic_access = real_gap_diagnostic(root, source)
        coverage = quality.loc[quality.factor.isin(LOW_COVERAGE_REVIEW)].copy()
        coverage["diagnosis"] = "pinned_recursion_propagates_internal_NaN_synthetic_confirmed; bounded_2013_replay_disclosed_separately"
        coverage["action"] = "defer_representation_keep_canonical_and_primary_immutable"
        products = {"economic_semantic_review.csv": semantic, "representative_proposal_board.csv": board,
                    "proposal_changes.csv": changes, "exact_alias_registration.csv": exact,
                    "member_representative_evidence.csv": pd.concat(support, ignore_index=True),
                    "recursive_gap_diagnostic.csv": diagnostic, "low_coverage_review.csv": coverage,
                    "real_gap_diagnostic.csv": real_diagnostic,
                    "proposal_counts.csv": long.groupby(["level", "proposal_role"]).size().rename("members").reset_index()}
        for name, frame in products.items():
            frame.to_csv(report / name, index=False)
        long.to_parquet(destination / "representative_policy_details.parquet", index=False)
        atomic_write_json(report / "SOURCE_AUDIT.json", provenance)
        atomic_write_json(report / "DIAGNOSTIC_ACCESS.json", diagnostic_access)
        atomic_write_json(report / "PRICE_SCALE_AUDIT.json", {
            "status": "unresolved_replacement_deferred",
            "verified": ["TA receives provider OHLC without cross-sectional demeaning or nominal-price reconstruction in ta_batch",
                         "EMA/SMA/channel levels retain provider price units; widths and event outputs are separate methods",
                         "KAMA uses canonical causal implementation and anchored state"],
            "not_verified": ["provider-specific original-price to stored-price scale chain",
                             "whether scale factors are comparable across stocks on the same date"],
            "decision": "do_not_construct_nominal_price_control_from_unverified_close; defer provider-price replacement",
            "next_required_evidence": "provider source/adjustment receipt or development-date raw-price reconciliation including stock-specific scaling",
            "new_price_control_computed": False,
        })
        verify_sealed(root, out)
        aliases = long.loc[long.proposal_role.eq("conditional_alias_proposal")]
        validation = {"semantic_rows": len(semantic), "active": len(board), "level_rows": len(long),
                      "old_alias_rows_reviewed": int(changes.old_role.eq("conditional_alias_proposal").sum()),
                      "new_conditional_alias_rows": len(aliases),
                      "active_semantics_resolved": int(active.semantic_resolved.sum()),
                      "active_unresolved_semantics": int((~active.semantic_resolved).sum()),
                      "exact_groups_registered": exact.canonical_representation_proposal.nunique(),
                      "real_diagnostic_comparisons": len(real_diagnostic),
                      "real_diagnostic_mismatches": int(real_diagnostic.mismatches.sum()),
                      "primary_files_unchanged": len(verify_primary(root)),
                      "original_proposal_hashes_unchanged": True, "held_aside_recent_diagnostic_accessed": False}
        assert len(long) == 494 * 4 and validation["old_alias_rows_reviewed"] == 104
        assert aliases.empty or aliases.pair_strict_stable.all()
        atomic_write_json(report / "VALIDATION.json", validation)
        text = "# Candidate Consolidation V0.5.1 修订提案\n\n"
        text += "状态：修订版已生成，停止供人工审阅；没有Core、删除或自动替换。\n\n"
        text += f"保留494成员和765语义记录；active中{validation['active_semantics_resolved']}项恢复了明确语义、窗口和量纲。旧版104条条件替代逐条复核，新版共有{len(aliases)}条跨层级条件替代提案；数量是规则结果，不是压缩目标。\n\n"
        text += "新规则将不同指标方法、窗口、会计口径分开；语义未知、价格尺度未确认及状态/递归缺失问题暂缓替代。排序移除运行说明构造的公式复杂度。任何近似替代都必须通过已有Full和四Era的可比、q10及符号标准。单例展示可比与未知pair数量，不称为独立信息。\n\n"
        text += "五组精确重复单独登记为开发期等值关系，保留全部身份和原Primary方向；未把某个聚类cut或簇数当成最终池大小。\n\n"
        text += "[494行新版提案](representative_proposal_board.csv)、[全部变更及原因](proposal_changes.csv)、[实际pair证据](member_representative_evidence.csv)、[语义表](economic_semantic_review.csv)、[五组关系登记](exact_alias_registration.csv)、[低覆盖审阅](low_coverage_review.csv)、[递归缺失实验](recursive_gap_diagnostic.csv)、[真实样本核对](real_gap_diagnostic.csv)、[有界读取记录](DIAGNOSTIC_ACCESS.json)、[来源核验](SOURCE_AUDIT.json)、[验收](VALIDATION.json)。\n\n"
        text += "ATR和ADX +/- 的固定源码递归会传播内部缺失；合成实验用于解释这种行为，不冒充对全部真实缺失的归因。canonical值和Primary不修写。价格单位和完整provider处理链尚未核定，价格相关提案保持暂缓；行业仍无开发期覆盖。32项active Alpha101的实现语义继续待逐项复核。\n\n"
        text += f"真实核对共{len(real_diagnostic)}个股票—指标组合，累计{int(real_diagnostic.mismatches.sum())}个值/mask差异（rtol=1e-7、atol=1e-8）。原始输入本身存在缺失，PIT mask后进入递归；该证据解释所选样本，不代表全市场缺失均有相同来源。[价格尺度审计](PRICE_SCALE_AUDIT.json)保留已知与未知边界。\n\n"
        text += "本次复用2010–2023汇总，另对2013年三只股票的三个指标作有界核对，原始输入从2011-10-13开始以复现300交易日warmup。未重跑日Spearman或收益评估。原版receipt绑定文件逐hash不变；修订版独立发布，外部全量命令无需重跑。\n"
        atomic_write_text(report / "REPORT.md", text)
        result = {"status": "complete_stop_for_human_review", "revision": revision, **validation,
                  "source_proposal_receipt_sha256": sha256_file(original / "PROPOSAL_RECEIPT.json"),
                  "summary_hashes": summary_hashes,
                  "policy": POLICY,
                  "code_hashes": {p: sha256_file(root / p) for p in ["factor_research/candidate_consolidation_revision.py", "scripts/revise_candidate_consolidation_v0_5_1.py"]},
                  "report_hashes": {p.name: sha256_file(p) for p in report.iterdir() if p.is_file()},
                  "runtime_hashes": {"representative_policy_details.parquet": sha256_file(destination / "representative_policy_details.parquet")}}
        atomic_write_json(report / "RECEIPT.json", result)
        atomic_write_json(destination / "status.json", result)
        print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="consolidation_20260908_v2")
    parser.add_argument("--revision-id", default="v0_5_1")
    args = parser.parse_args()
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value) for value in [args.run_id, args.revision_id]):
        parser.error("invalid run/revision id")
    run(ROOT, ROOT / "outputs/candidate_consolidation_v0_5" / args.run_id, args.revision_id)

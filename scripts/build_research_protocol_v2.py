from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.research_protocol_v2 import (  # noqa: E402
    ProtocolV2Config,
    TrainingHistoryCandidate,
    build_research_protocol_v2,
    load_calendar,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frame_sha256(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    ).hexdigest()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8")


def build_config(payload: dict[str, object]) -> ProtocolV2Config:
    label = payload["label"]
    development = payload["development"]
    diagnostic = payload["historical_diagnostic"]
    candidates = tuple(
        TrainingHistoryCandidate(
            candidate_id=item["id"],
            mode=item["mode"],
            safe_training_dates=item.get("safe_training_dates"),
        )
        for item in payload["training_history_candidates"]
    )
    return ProtocolV2Config(
        matrix_start=pd.Timestamp(payload["matrix_start"]),
        matrix_end=pd.Timestamp(payload["matrix_end"]),
        execution_lag=int(label["execution_lag"]),
        holding_days=int(label["holding_days"]),
        first_validation_start=pd.Timestamp(development["first_validation_start"]),
        validation_months=int(development["validation_months"]),
        development_step_months=int(development["step_months"]),
        development_environment_count=int(development["environment_count"]),
        minimum_train_dates=int(development["minimum_train_dates"]),
        minimum_validation_dates=int(development["minimum_validation_dates"]),
        selection_freeze_boundary=pd.Timestamp(development["selection_freeze_boundary"]),
        first_diagnostic_start=pd.Timestamp(diagnostic["first_test_start"]),
        diagnostic_months=int(diagnostic["test_months"]),
        diagnostic_step_months=int(diagnostic["step_months"]),
        diagnostic_environment_count=int(diagnostic["environment_count"]),
        minimum_test_dates=int(diagnostic["minimum_test_dates"]),
        candidates=candidates,
    )


def v1_v2_comparison(payload: dict[str, object], outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    legacy = outputs["legacy_v1_windows"]
    development = outputs["development_environments"]
    diagnostic = outputs["diagnostic_environments"]
    tasks = outputs["development_tasks"]
    rows: list[dict[str, object]] = []
    for row in legacy.itertuples(index=False):
        rows.append(
            {
                "protocol": "V1",
                "unit_id": row.split_id,
                "training_history": "expanding",
                "usable_train_dates": row.train_dates,
                "usable_validation_dates": row.validation_dates,
                "diagnostic_dates": row.test_dates,
                "purged_dates": row.purged_dates,
                "embargoed_dates": row.embargoed_dates,
                "selection_environment_count": 1,
                "diagnostic_environment_count": 1,
                "evidence_role": "legacy_historical_diagnostic_anchor",
            }
        )
    for row in tasks.itertuples(index=False):
        rows.append(
            {
                "protocol": "V2",
                "unit_id": row.task_id,
                "training_history": row.training_history_id,
                "usable_train_dates": row.train_dates,
                "usable_validation_dates": row.validation_dates,
                "diagnostic_dates": 0,
                "purged_dates": row.purged_dates,
                "embargoed_dates": row.embargoed_dates,
                "selection_environment_count": development["environment_id"].nunique(),
                "diagnostic_environment_count": diagnostic["environment_id"].nunique(),
                "evidence_role": "development_selection_authority",
            }
        )
    return pd.DataFrame(rows)


def purge_embargo_audit(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    legacy = outputs["legacy_v1_windows"]
    rows = []
    for row in legacy.itertuples(index=False):
        nominal_validation = (
            int(row.validation_dates) + int(row.purged_dates) // 2 + int(row.embargoed_dates) // 2
        )
        rows.append(
            {
                "protocol": "V1",
                "unit_id": row.split_id,
                "nominal_validation_dates": nominal_validation,
                "usable_validation_dates": int(row.validation_dates),
                "validation_label_overlap_purge_dates": int(row.purged_dates) // 2,
                "validation_extra_embargo_dates": int(row.embargoed_dates) // 2,
                "required_label_gap_trading_dates": int(row.label_horizon) + int(row.execution_lag),
                "actual_pre_boundary_feature_gap": int(row.label_horizon)
                + int(row.execution_lag)
                + int(row.embargoed_dates) // 2,
                "semantic_finding": "exact purge followed by same-side fixed embargo; duplicate conservatism",
            }
        )
    for row in outputs["development_environments"].itertuples(index=False):
        rows.append(
            {
                "protocol": "V2",
                "unit_id": row.environment_id,
                "nominal_validation_dates": row.nominal_trading_dates,
                "usable_validation_dates": row.validation_dates,
                "validation_label_overlap_purge_dates": row.maturity_boundary_exclusions,
                "validation_extra_embargo_dates": 0,
                "required_label_gap_trading_dates": 21,
                "actual_pre_boundary_feature_gap": 21,
                "semantic_finding": "exact interval purge only; maturity exclusions isolate adjacent evidence windows",
            }
        )
    return pd.DataFrame(rows)


def report_text(
    payload: dict[str, object],
    outputs: dict[str, pd.DataFrame],
    comparison: pd.DataFrame,
    qlib_commit: str,
) -> str:
    development = outputs["development_environments"]
    diagnostic = outputs["diagnostic_environments"]
    tasks = outputs["development_tasks"]
    v1 = comparison.loc[comparison["protocol"].eq("V1")]
    expanding = tasks.loc[tasks["training_history_id"].eq("expanding")]
    v1_nominal_validation = int(
        (v1["usable_validation_dates"] + v1["purged_dates"] / 2 + v1["embargoed_dates"] / 2).sum()
    )
    v2_nominal_validation = int(development["nominal_trading_dates"].sum())
    audit_pass = outputs["validation_audit"]["status"].eq("pass").all()
    return f"""# Research Protocol V2 / Purged Rolling Split V2

> 状态：`FROZEN DESIGN`；本阶段只设计、生成并验证研究协议，没有训练模型、读取候选结果或修改 Strategy V1 / Forward Track。

## 结论

Research Protocol V2 已具备开始后续 Structured ML V1 **开发研究**的时间边界基础（本阶段未启动该研究）。它把模型选择固定在 `{development["environment_id"].nunique()}` 个 development 时间环境，把 `{diagnostic["environment_id"].nunique()}` 个更细历史环境及旧三个 test 全部隔离为 `post_observation_research / historical_diagnostic_only`。所有 `{len(outputs["validation_audit"])}` 个关键验证项状态为 `{"pass" if audit_pass else "blocked"}`。

V2 的主要变化不是放松保护，而是删除 V1 在 exact interval purge 之后重复执行的同侧 20 日 embargo。标签仍为 `t+1` 入场、`t+21` 退出，因此训练样本必须满足 `label_end < evaluation_start`，边界前真正需要排除 21 个 feature dates。

## V1 审计

V1 最初为早期因子筛选、LightGBM baseline 和少量 historical holdout 设计。它的优点是简单、保守、按真实交易日保存精确 assignments，并阻止 train/validation 标签跨入后续 period。其三个 outer split 的 train/validation/test 日期分别为：

{chr(10).join(f"- `{r.split_id}`: {r.train_dates}/{r.validation_dates}/{r.test_dates}" for r in outputs["legacy_v1_windows"].itertuples(index=False))}

名义 6 个月 validation 在真实日历中约有 `{int((v1["usable_validation_dates"] + v1["purged_dates"] / 2 + v1["embargoed_dates"] / 2).min())}`–`{int((v1["usable_validation_dates"] + v1["purged_dates"] / 2 + v1["embargoed_dates"] / 2).max())}` 个交易日。每段先删除 21 个与 test interval 重叠的 validation feature dates，再删除 20 个 validation tail dates，所以只剩 `{int(v1["usable_validation_dates"].min())}`–`{int(v1["usable_validation_dates"].max())}` 日。train 边界也执行相同的 21+20 删除。

purge 的真实作用是删除标签区间与下一段相交的样本；embargo 在 V1 实现中又从已经安全的 train/validation 尾部各删 20 日。它没有隔离 evaluation 之后进入未来训练的样本，也没有单独声明序列依赖机制，因此语义上是对相同边界的第二层 buffer，而非不同风险。V1 仍无 interval overlap；问题是信息损失和语义重复，不是保护不足。

## V2 时间结构

### Development evidence

固定 `{development["environment_id"].nunique()}` 个两个月 validation 环境、每三个月推进一次：

{chr(10).join(f"- `{r.environment_id}`: {r.validation_start:%Y-%m-%d}..{r.validation_end:%Y-%m-%d}, {r.validation_dates} dates, labels through {r.validation_label_end:%Y-%m-%d}" for r in development.itertuples(index=False))}

一月间隔用于让 20 日标签自然成熟；若节假日使 interval 仍跨入下一环境，生成器按实际 `label_end` 排除尾部日期，而不是使用看起来安全的固定数字。最后 development label 在 `{development["validation_label_end"].max():%Y-%m-%d}` 已成熟，早于 2024-08-01 diagnostic boundary。

两个且仅两个训练历史假设进入候选：

- `expanding`：旧数据仍有统计信息；每 fold 使用全部合法历史，train dates 为 `{int(expanding["train_dates"].min())}`–`{int(expanding["train_dates"].max())}`。
- `sliding_504`：A 股非平稳性可能使约两年以前的数据有害；每 fold 固定使用最后 504 个已经通过 interval purge 的训练日。

不扫描 1/2/2.5/3/4 年。两种窗口必须在同一五个环境上比较；旧历史 diagnostics 不能改变选择。

### Historical diagnostic evidence

V2 预定义 `{diagnostic["environment_id"].nunique()}` 个两个月、三个月步长的历史诊断环境，从 `{diagnostic["test_start"].min():%Y-%m-%d}` 到 `{diagnostic["test_end"].max():%Y-%m-%d}`。它们增加 regime、decay 和 failure analysis 的分辨率，但全部是已经观察过的历史，不是 fresh OOS。旧 `split_001`–`split_003` 保留原日期与 artifact identity，仅作为与旧实验对照的 legacy anchors。

只有 development 中冻结的单一 candidate 才能 replay diagnostics；模板当前全部 `execution_authorized=false`。diagnostic performance、feature importance 或失败不能回流改模型、representation、窗口、调仓或超参数。

### Forward evidence

现有 Strategy V1 Forward Track 原样保留。V2 不把历史重新切片包装成 prospective evidence。任何 Model/Strategy V2 的真实确认仍须在候选冻结后由自然到来的新数据提供。

## 模型选择与 trial governance

后续 LightGBM、DoubleEnsemble 和 raw/economic/sleeve/hybrid representation 使用完全相同的五个 folds。主指标是各 fold `mean_daily_rank_ic` 的等权平均，同时强制报告 paired delta、worst fold、fold dispersion、negative-fold count、coverage 和 failure count。

challenger 只有在 paired mean 与 median delta 都为正、至少赢 3/5 folds、且无 fold 失败时才可替代较简单 incumbent；否则记录 tie/inconclusive。每个注册实验只允许改变一个轴，最多 8 个 candidate。architecture、representation、training window 和 hyperparameter 试验分别登记，candidate manifest 必须在 fit 前冻结，实际尝试数（含失败）不可删除。

## Label horizon 与决策频率

20 日标签描述从次日到第 21 个交易日的中期横截面收益，不要求 portfolio 只能每 20 日调仓。5 日 rebalance 是执行层的持仓更新选择，但会重复使用高度相关的中期信号，可能放大 turnover。后续模型报告必须提供 score autocorrelation/decay、5 日更新下的持仓重叠与 turnover；本阶段不 sweep 5d/10d/20d/40d 标签。是否研究多 horizon 保留为独立、预注册的后续问题。

## Qlib 评估

固定 Qlib commit 为 `{qlib_commit}`，无需升级。当前 `RollingGen` 支持 expanding/sliding segment 平移、固定 trading-step 与粗粒度 `trunc_days`，适合在项目边界确定后物化普通 Qlib task；它不能表达逐样本 exact label interval、evidence authority、split-local feature eligibility 或 diagnostic isolation。因此 V2 采用项目生成器作为 authority，暂不调用 RollingGen。

Recorder 可记录模型 artifact，Collector 可汇总 recorder，TaskManager 则引入独立 task backend；当前项目已有 hash manifest、prediction lineage 和 CSV 任务表。现在接入会增加 MLflow/MongoDB/task glue，未证明减少复杂度，所以全部暂缓。Structured ML 首次规模扩张后再用实际重复成本复评。

## V1 与 V2 的信息效率

- V1：3 个 outer validations，共 `{int(v1["usable_validation_dates"].sum())}` / `{v1_nominal_validation}` 个按 split 计的 usable/nominal validation dates（`{int(v1["usable_validation_dates"].sum()) / v1_nominal_validation:.1%}`）；3 个 historical test windows；每 split 42 purge + 40 embargo dates。
- V2：每个训练历史 candidate 看到 5 个统一 validation environments，共 `{int(expanding["validation_dates"].sum())}` / `{v2_nominal_validation}` 个 usable/nominal validation dates（`{int(expanding["validation_dates"].sum()) / v2_nominal_validation:.1%}`）；7 个细粒度 diagnostic environments；每 task 只做 exact 21-date train-side interval purge，额外 embargo 为 0。
- V2 的价值是更多 selection regimes、统一 candidate comparison 和明确证据权限，不是把更多历史窗口称作 OOS。保护等价或更强：训练标签仍严格结束于 evaluation 前，且最后 development label 也严格早于 diagnostic boundary。

## 独立验证与边界

验证覆盖 train/evaluation label overlap、chronology、duplicate/cross-fold assignments、calendar/matrix-date scope、相邻环境 label isolation、development/diagnostic authority、legacy test isolation、determinism、embargo=0 和 task execution hard-stop。Factor Universe V2、Matrix、Economic Multi-Factor Research V1、Model/Strategy V1、frozen predictions、historical releases 与 Forward outputs 均未修改。

## 对阶段问题的简答

1. V1 为早期少量 holdout 和严格防泄漏而设计；优点是简单保守、exact assignments 可审计。
2. 不适合 Structured ML 的核心是单一 regime 选参、outer windows 少、以及 purge 后重复 embargo。
3. V2 使用 5 个 development 环境、两个有经济假设的训练历史方案、7 个 diagnostic 环境和不变的 forward evidence 层。
4. expanding/sliding 都保留为 development hypothesis；diagnostics 不参与选择。
5. 旧三个 test 是 legacy diagnostic anchors；Forward Track 角色不变。
6. 20 日 label 与 5 日 decision 可以共存，但必须审计 decay/turnover；多 horizon 需另立研究。
7. Qlib RollingGen 当前不采用为 authority，也无需升级；Recorder/Task/Collector 暂缓。
8. V2 保持 exact interval protection，提高 regime coverage并减少无解释的数据损失。
9. Model V2 下一阶段只能先注册 candidate、只跑 development、冻结 winner/无 winner 结论，再解锁 historical replay。
10. 当前已具备开始 Structured ML V1 protocol-governed development 的基础，但本阶段没有开始训练或比较。

## Remaining uncertainties

- 五个 development 环境仍来自有限的 2023–2024 历史，不能消除 regime uncertainty。
- 504 日 sliding 是一个机制假设，不是已知最优窗口；若结论 inconclusive，应保留 expanding incumbent，而不是增加窗口搜索。
- diagnostic replay 的成本和 Qlib experiment tracking 需求只有在真实 Structured ML 任务规模出现后才能可靠评估。
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and audit Research Protocol V2 without model training."
    )
    parser.add_argument("--config", type=Path, default=Path("configs/research_protocol_v2.yaml"))
    args = parser.parse_args()
    config_path = resolve(args.config)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = build_config(payload)
    calendar_path = resolve(payload["calendar_path"])
    calendar = load_calendar(calendar_path, config.matrix_start, config.matrix_end)
    legacy_manifest_path = resolve(payload["legacy_v1"]["split_manifest"])
    legacy_assignments_path = resolve(payload["legacy_v1"]["date_assignments"])
    legacy_manifest = pd.read_csv(
        legacy_manifest_path,
        parse_dates=[
            "train_start",
            "train_end",
            "validation_start",
            "validation_end",
            "test_start",
            "test_end",
        ],
    )
    legacy_assignments = pd.read_csv(legacy_assignments_path, parse_dates=["datetime"])
    outputs = build_research_protocol_v2(calendar, config, legacy_manifest, legacy_assignments)
    repeated = build_research_protocol_v2(
        calendar[::-1], config, legacy_manifest, legacy_assignments
    )

    upstream_payloads = {
        name: json.loads(resolve(path).read_text(encoding="utf-8"))
        for name, path in payload["upstream_authority"].items()
    }
    matrix = upstream_payloads["matrix_manifest"]
    labels = upstream_payloads["labels_manifest"]
    universe = upstream_payloads["universe_manifest"]
    feature_policy = payload["feature_eligibility"]
    deterministic = all(
        frame_sha256(outputs[name]) == frame_sha256(repeated[name])
        for name in (
            "development_environments",
            "development_tasks",
            "development_date_assignments",
            "diagnostic_environments",
            "diagnostic_task_templates",
            "diagnostic_date_assignments",
        )
    )
    authority_checks = [
        (
            "matrix_authority_status",
            matrix["artifact_status"],
            "research_ready_with_blocked_factors",
        ),
        ("matrix_stage_closed", matrix["stage_lifecycle"], "CLOSED"),
        ("matrix_calendar_start", matrix["start_date"], str(config.matrix_start.date())),
        ("matrix_calendar_end", matrix["end_date"], str(config.matrix_end.date())),
        ("matrix_calendar_date_count", int(matrix["date_count"]), len(calendar)),
        ("labels_authority_status", labels["artifact_status"], "pass"),
        ("universe_authority_status", universe["artifact_status"], "pass"),
        (
            "labels_universe_alignment",
            labels["universe_artifact_id"],
            universe["universe_artifact_id"],
        ),
        ("split_local_feature_eligibility_required", feature_policy["split_local_required"], True),
        ("feature_eligibility_fit_scope", feature_policy["fit_scope"], "task_train_dates_only"),
        (
            "validation_test_feature_eligibility_reads_forbidden",
            feature_policy["validation_or_test_eligibility_reads_forbidden"],
            True,
        ),
        ("task_generation_deterministic", deterministic, True),
    ]
    authority_audit = pd.DataFrame(
        [
            {
                "check_name": name,
                "status": "pass" if observed == required else "fail",
                "observed_value": observed,
                "required_value": required,
                "severity": "critical",
                "reason": "Research Protocol V2 upstream, feature-scope, and determinism contract.",
            }
            for name, observed, required in authority_checks
        ]
    )
    outputs["validation_audit"] = pd.concat(
        [outputs["validation_audit"], authority_audit], ignore_index=True
    )
    if outputs["validation_audit"]["status"].eq("fail").any():
        raise ValueError("Research Protocol V2 validation failed")

    output_dir = resolve(payload["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_names = (
        "development_environments",
        "development_tasks",
        "development_date_assignments",
        "development_purged_dates",
        "window_excluded_dates",
        "diagnostic_environments",
        "diagnostic_task_templates",
        "diagnostic_date_assignments",
        "diagnostic_purged_dates",
        "legacy_v1_windows",
        "validation_audit",
    )
    for name in frame_names:
        write_csv(outputs[name], output_dir / f"{name}.csv")
    write_csv(authority_audit, output_dir / "authority_audit.csv")

    comparison = v1_v2_comparison(payload, outputs)
    purge_audit = purge_embargo_audit(outputs)
    write_csv(comparison, output_dir / "v1_v2_comparison.csv")
    write_csv(purge_audit, output_dir / "purge_embargo_audit.csv")
    (output_dir / "resolved_config.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    qlib_repo = resolve(payload["qlib_integration"]["repository"])
    qlib_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=qlib_repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    if qlib_commit != payload["qlib_integration"]["pinned_commit"]:
        raise ValueError("Qlib checkout no longer matches the registered commit")
    qlib_audit = {
        "pinned_commit": qlib_commit,
        "upgrade_required": False,
        "rolling_gen_available": True,
        "supports_expanding": True,
        "supports_sliding": True,
        "supports_fixed_trading_step": True,
        "supports_coarse_trunc_days": True,
        "supports_exact_per_sample_label_intervals": False,
        "supports_project_evidence_authority": False,
        "adopted_as_split_authority": False,
        "decision": "retain project generator; allow optional downstream materialization only",
        "recorder_task_collector_adopted": False,
        "task_management_decision": "defer until measured Structured ML experiment volume justifies glue",
    }
    (output_dir / "qlib_capability_audit.json").write_text(
        json.dumps(qlib_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    trial_governance = {
        "one_axis_per_registered_experiment": True,
        "maximum_registered_candidates_per_experiment": 8,
        "candidate_manifest_frozen_before_fit": True,
        "failed_trials_count_toward_budget": True,
        "development_environments_required": 5,
        "historical_diagnostic_feedback_forbidden": True,
        "formal_model_competition_started": False,
    }
    (output_dir / "trial_governance.json").write_text(
        json.dumps(trial_governance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    source_paths = {
        "config": config_path,
        "generator": PROJECT_ROOT / "research_validation/research_protocol_v2.py",
        "runner": PROJECT_ROOT / "scripts/build_research_protocol_v2.py",
        "calendar": calendar_path,
        "legacy_split_manifest": legacy_manifest_path,
        "legacy_date_assignments": legacy_assignments_path,
        "legacy_purged_dates": resolve(payload["legacy_v1"]["purged_dates"]),
        "legacy_embargoed_dates": resolve(payload["legacy_v1"]["embargoed_dates"]),
        "matrix_manifest": resolve(payload["upstream_authority"]["matrix_manifest"]),
        "labels_manifest": resolve(payload["upstream_authority"]["labels_manifest"]),
        "universe_manifest": resolve(payload["upstream_authority"]["universe_manifest"]),
    }
    receipts = pd.DataFrame(
        [
            {
                "source_id": name,
                "path": path.relative_to(PROJECT_ROOT).as_posix()
                if path.is_relative_to(PROJECT_ROOT)
                else str(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for name, path in source_paths.items()
        ]
    )
    write_csv(receipts, output_dir / "source_receipts.csv")
    (output_dir / "REPORT.md").write_text(
        report_text(payload, outputs, comparison, qlib_commit), encoding="utf-8"
    )

    files = sorted(
        path for path in output_dir.iterdir() if path.is_file() and path.name != "manifest.json"
    )
    manifest = {
        "schema_version": 2,
        "stage_id": "research_protocol_v2",
        "protocol_identity": "purged_rolling_split_v2",
        "artifact_status": "frozen_design_ready",
        "design_frozen_before_model_outcomes": True,
        "formal_model_competition_started": False,
        "development_evidence_role": "selection_authority",
        "historical_diagnostic_evidence_role": "historical_diagnostic_only",
        "forward_evidence_role": "prospective_evidence_only",
        "legacy_v1_preserved": True,
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "matrix_changed": False,
        "leakage_validation_passed": True,
        "development_environment_count": int(
            outputs["development_environments"]["environment_id"].nunique()
        ),
        "diagnostic_environment_count": int(
            outputs["diagnostic_environments"]["environment_id"].nunique()
        ),
        "training_history_candidate_count": len(config.candidates),
        "qlib_commit": qlib_commit,
        "output_file_hashes": {path.name: sha256(path) for path in files},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(outputs["validation_audit"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

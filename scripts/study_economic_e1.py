"""User-run E1 structural study; no price, label or portfolio execution entry."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import pyarrow
import scipy
from model_research import economic_prediction_structure as e1

OUT = ROOT / "outputs/economic_translation_mvp/e1_b494_v1"
DELIVERY = ROOT / "reports/economic_translation_mvp/DELIVERY_VERIFICATION.json"
CODE = [
    "model_research/economic_prediction_structure.py",
    "scripts/study_economic_e1.py",
    "scripts/study_economic_e1.ps1",
    "tests/test_economic_prediction_structure.py",
    "reports/economic_translation_mvp/e1_inputs.json",
]


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(e1.json_text(value))


def binding():
    return dict(
        code_hashes_lf={
            p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p in CODE
        },
        runtime=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            pandas=pd.__version__,
            scipy=scipy.__version__,
            pyarrow=pyarrow.__version__,
        ),
        canonical=e1.BoundedScores().inventory["canonical_dataset_id"],
        lags=list(e1.LAGS),
        percentiles=list(e1.PCTS),
        buffer=[10, 20],
        role="E1_B_scores_keys_only",
        outcome_access=False,
        e3_authorized=False,
        e4_authorized=False,
    )


def check_delivery_binding():
    delivered = json.loads(DELIVERY.read_text(encoding="utf-8"))
    e1.require(
        delivered["e1_execution_binding"] == binding(),
        "E1 delivered code/runtime/input binding differs; stop before score access",
    )


def verify():
    receipt = json.loads((OUT / "receipt.json").read_text(encoding="utf-8"))
    e1.require(receipt["binding"] == binding(), "E1 binding changed; preserve evidence")
    for name, expected in receipt["files"].items():
        e1.require(
            Path(name).name == name and e1.sha(OUT / name) == expected, "E1 output hash mismatch"
        )
    audit = []
    reader = e1.BoundedScores(audit=audit)
    data = reader.load()
    tables = {
        name: pd.read_parquet(OUT / f"{name}.parquet")
        for name in ("daily", "rank_lags", "membership", "migration", "turnover", "ages", "spells")
    }
    result = e1.independent_verify(data, reader.calendar, tables)
    path = OUT / "independent_replay.json"
    replay = dict(
        result=result,
        input_sha256=e1.sha(e1.INPUTS),
        receipt_sha256=e1.sha(OUT / "receipt.json"),
        access=audit,
    )
    if path.exists():
        e1.require(
            json.loads(path.read_text(encoding="utf-8")) == replay, "existing replay changed"
        )
    else:
        write_json(path, replay)
    print(e1.json_text(result))


def run():
    if (OUT / "receipt.json").exists():
        receipt = json.loads((OUT / "receipt.json").read_text(encoding="utf-8"))
        e1.require(receipt["binding"] == binding(), "E1 binding changed; preserve evidence")
        for name, expected in receipt["files"].items():
            e1.require(
                Path(name).name == name and e1.sha(OUT / name) == expected,
                "existing output hash mismatch",
            )
        print("Existing E1 seal verified; --verify performs independent replay")
        return
    OUT.mkdir(parents=True, exist_ok=False)
    write_json(
        OUT / "started.json",
        dict(
            started=datetime.now(timezone.utc).isoformat(),
            binding=binding(),
            git_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
        ),
    )
    audit = []
    try:
        reader = e1.BoundedScores(audit=audit)
        data = reader.load()
        print(
            f"B494 scores/keys verified: {len(data)} rows; {len(reader.calendar)} dates", flush=True
        )
        tables = e1.study(data, reader.calendar)
        for name, frame in tables.items():
            frame.to_parquet(OUT / f"{name}.parquet", index=False)
        e1.summarize(tables).to_csv(OUT / "summary.csv", index=False, lineterminator="\n")
        # Evidence, not an automated E3 decision. No post-hoc numerical cutoff.
        turn = tables["turnover"].query("not cold_start").groupby("series").membership_churn.mean()
        spells = tables["spells"].query("series == 'buffer10_20'")
        closed = spells.loc[~spells.right_censored]
        diagnostic = dict(
            status="E1 STRUCTURE COMPUTED / INDEPENDENT REPLAY REQUIRED",
            recommendation="inconclusive_pending_human_structural_review",
            candidate="single_pre_specified_10_20",
            dates=len(reader.calendar),
            rows=len(data),
            daily_candidate_min=int(tables["daily"].candidates.min()),
            daily_candidate_max=int(tables["daily"].candidates.max()),
            mean_membership_churn=turn.to_dict(),
            buffer_spells=len(spells),
            buffer_right_censored=int(spells.right_censored.sum()),
            buffer_closed_median_duration=float(closed.duration.median()) if len(closed) else None,
            buffer_closed_one_day_fraction=float(closed.duration.eq(1).mean())
            if len(closed)
            else None,
            pathology_thresholds="No numerical optimization/acceptance threshold; human review of fixed descriptive evidence",
            e3_frozen=False,
            no_prices_labels_costs_nav=True,
        )
        write_json(OUT / "structural_review.json", diagnostic)
        rank = (
            tables["rank_lags"]
            .groupby("lag")
            .agg(
                mean_spearman=("spearman", "mean"),
                scoreable=("scoreable", "sum"),
                possible=("scoreable", "size"),
            )
        )
        lines = [
            "# E1 B494 prediction structure",
            "",
            "结构计算已封存；独立重放状态以同目录 independent_replay.json 为准。",
            "",
            f"日期 {len(reader.calendar)}；行数 {len(data)}；候选数 {diagnostic['daily_candidate_min']}–{diagnostic['daily_candidate_max']}。",
            "",
            "| Trading-day lag | Mean Spearman | Scoreable / possible |",
            "|---|---|---|",
        ]
        lines += [
            f"| {lag} | {r.mean_spearman:.8f} | {int(r.scoreable)} / {int(r.possible)} |"
            for lag, r in rank.iterrows()
        ]
        lines += [
            "",
            "全池percentile Pearson与交集内Spearman分开保存；模型年界单列，不压缩缺日。",
            "",
            f"日均membership churn：Top10 rebuild={turn.get('top10', float('nan')):.6f}；10/20 buffer={turn.get('buffer10_20', float('nan')):.6f}。",
            "",
            f"Buffer spells={len(spells)}；右删失={int(spells.right_censored.sum())}；已退出spell中位长度={diagnostic['buffer_closed_median_duration']}。",
            "",
            "这些是成员结构，未使用价格、标签、成交成本或真实收益。Cold start单独报告，observed duration不是alpha半衰期。",
            "",
            "Top10为primary structural set，Top5/20仅背景。年度与三段描述见summary.csv；迁移含absent状态。",
            "",
            "建议状态：inconclusive，等待人工检查固定证据是否过短、近似全重建、过黏或异常；未设结果驱动阈值。",
            "未运行其他buffer，不选择最优参数；E3/E4未授权。",
            "",
        ]
        (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
        write_json(OUT / "access.json", audit)
        files = {p.name: e1.sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}
        write_json(OUT / "receipt.json", dict(status="complete", binding=binding(), files=files))
        print("E1 structure sealed; now run --verify for independent replay", flush=True)
    except Exception as exc:
        write_json(OUT / "failure.json", dict(error=repr(exc), access=audit))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    check_delivery_binding()
    verify() if args.verify else run()

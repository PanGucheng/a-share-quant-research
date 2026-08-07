from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml

from model_research.forward_pipeline import load_trading_calendar
from model_research.forward_prediction_contract import validate_prediction_freeze_receipt
from qlib_integration.market_semantics import infer_board, load_yaml, resolve_lot_rule
from research_validation.feature_matrix import file_sha256


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "strategy_v1_paper_portfolio_v1"


def _run_qlib_execution(
    signal: pd.DataFrame, market: pd.DataFrame, config: dict[str, object]
) -> dict[str, pd.DataFrame]:
    from qlib_integration.runner import run_qlib_execution

    return run_qlib_execution(signal, market, config)


def _resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def load_paper_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(_resolve(path).read_text(encoding="utf-8"))
    if config.get("stage_id") != STAGE_ID:
        raise ValueError("paper portfolio stage id is invalid")

    historical = _read_json(_resolve(config["historical_config"]))
    selected = _read_json(_resolve(config["selected_portfolio_rule"]))
    frozen = {
        "portfolio_id": "P01",
        "top_k": 50,
        "rebalance_interval": 5,
        "weighting": "equal_weight",
        "initial_cash": 10_000_000.0,
        "risk_degree": 0.95,
        "lot_size": 100,
        "dynamic_lot_rules": True,
        "buy_commission_rate": 0.0003,
        "sell_commission_rate": 0.0003,
        "sell_tax_rate": 0.001,
        "minimum_commission": 5.0,
        "slippage_bps": 10.0,
        "max_participation_rate": 0.05,
        "signal_lag_trading_days": 1,
        "strict_t_plus_one": True,
    }
    if selected.get("selected_portfolio_id") != "P01":
        raise ValueError("historical selected portfolio is not P01")
    for field, expected in frozen.items():
        observed = (
            selected.get("selected_portfolio_id")
            if field == "portfolio_id"
            else selected.get(field, historical.get(field))
        )
        if observed != expected:
            raise ValueError(f"historical P01 field differs: {field}")
        if config.get(field) != expected:
            raise ValueError(f"paper P01 field differs: {field}")
    return config


def _initial_state(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "strategy_id": "strategy_v1",
        "portfolio_id": "P01",
        "top_k": int(config["top_k"]),
        "rebalance_interval": int(config["rebalance_interval"]),
        "first_execution_date": None,
        "last_decision_date": None,
        "last_rebalance_decision_date": None,
        "decision_dates": [],
        "rebalance_decision_dates": [],
        "pending_execution_dates": [],
        "executed_through": None,
        "paper_decision_count": 0,
        "label_read_count": 0,
        "status": "waiting_for_prediction",
        "production_model_selected": False,
        "live_trading_ready": False,
    }


def create_paper_decision(
    config: Mapping[str, Any],
    *,
    decision_date: str,
    calendar_path: str | Path,
    repository_root: str | Path = PROJECT_ROOT,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    output_root = _resolve(config["output_root"])
    decision_dir = output_root / "decisions" / decision_date
    decision_path = decision_dir / "decision.json"
    if decision_path.exists():
        raise FileExistsError(f"paper decision already exists: {decision_date}")

    prediction_dir = _resolve(config["prediction_root"]) / decision_date
    prediction_path = prediction_dir / "prediction.csv"
    receipt_path = prediction_dir / "prediction_receipt.json"
    if not prediction_path.is_file() or not receipt_path.is_file():
        raise FileNotFoundError(f"official prediction is missing: {decision_date}")
    receipt = _read_json(receipt_path)
    if receipt.get("status") != "pending_label" or receipt.get("evidence_eligible") is not True:
        raise ValueError("prediction is not an official prospective prediction")

    calendar = load_trading_calendar(calendar_path)
    freeze = _read_json(_resolve(config["candidate_freeze"]))
    validated = validate_prediction_freeze_receipt(
        receipt,
        candidate_freeze_effective_time=freeze["candidate_freeze_effective_time_utc"],
        trading_calendar=calendar,
        repository=repository_root,
    )
    if validated["decision_date"] != decision_date:
        raise ValueError("prediction receipt decision date differs")
    execution_date = validated["label_start_date"]
    now = created_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("paper decision timestamp must be timezone-aware")
    cutoff = datetime.fromisoformat(str(validated["label_start_cutoff"]))
    if now >= cutoff:
        raise PermissionError("paper decision was created after execution cutoff")

    prediction = pd.read_csv(prediction_path)
    required = {"datetime", "instrument", "score"}
    if not required.issubset(prediction.columns):
        raise ValueError("prediction schema is incomplete")
    prediction["datetime"] = pd.to_datetime(prediction["datetime"], errors="raise").dt.date
    prediction["instrument"] = prediction["instrument"].astype(str).str.upper()
    prediction["score"] = pd.to_numeric(prediction["score"], errors="coerce")
    if (
        prediction.empty
        or not prediction["datetime"].astype(str).eq(decision_date).all()
        or prediction["instrument"].duplicated().any()
        or not np.isfinite(prediction["score"]).all()
    ):
        raise ValueError("prediction rows are invalid for paper selection")

    state_path = output_root / "status.json"
    state = _read_json(state_path) if state_path.is_file() else _initial_state(config)
    if decision_date in state["decision_dates"]:
        raise FileExistsError(f"paper decision already recorded: {decision_date}")
    if state["last_decision_date"] is not None:
        previous_position = calendar.index(
            pd.Timestamp(state["last_decision_date"]).date()
        )
        current_position = calendar.index(pd.Timestamp(decision_date).date())
        if current_position != previous_position + 1:
            raise ValueError("paper decisions must cover consecutive trading days")
    execution = pd.Timestamp(execution_date)
    if state["first_execution_date"] is None:
        rebalance = True
        state["first_execution_date"] = execution_date
    else:
        start = pd.Timestamp(state["first_execution_date"]).date()
        execution_position = calendar.index(execution.date())
        start_position = calendar.index(start)
        rebalance = (execution_position - start_position) % int(config["rebalance_interval"]) == 0

    if rebalance:
        from qlib_integration.strategy_adapter import equal_weight_targets

        scores = prediction.sort_values("instrument", kind="stable").set_index("instrument")["score"]
        targets = equal_weight_targets(scores, int(config["top_k"]))
        selected_scores = scores.loc[list(targets)]
        target = pd.DataFrame(
            {
                "decision_date": decision_date,
                "execution_date": execution_date,
                "instrument": list(targets),
                "rank": range(1, len(targets) + 1),
                "score": selected_scores.to_numpy(),
                "target_weight": list(targets.values()),
                "target_stock_weight": [float(config["risk_degree"]) * value for value in targets.values()],
            }
        )
        state["last_rebalance_decision_date"] = decision_date
        state["rebalance_decision_dates"].append(decision_date)
        target_source_date = decision_date
    else:
        target_source_date = str(state["last_rebalance_decision_date"])
        source = output_root / "decisions" / target_source_date / "target_weights.csv"
        target = pd.read_csv(source)
        target["decision_date"] = decision_date
        target["execution_date"] = execution_date

    target = target.sort_values("rank", kind="stable").reset_index(drop=True)
    _atomic_csv(decision_dir / "target_weights.csv", target)
    decision = {
        "schema_version": 1,
        "strategy_id": "strategy_v1",
        "portfolio_id": "P01",
        "decision_date": decision_date,
        "execution_date": execution_date,
        "execution_cutoff": validated["label_start_cutoff"],
        "decision_created_at": now.isoformat(),
        "action": "rebalance" if rebalance else "hold",
        "target_source_decision_date": target_source_date,
        "selected_count": len(target),
        "target_weight_sum": float(target["target_weight"].sum()),
        "target_stock_weight_sum": float(target["target_stock_weight"].sum()),
        "prediction_row_count": len(prediction),
        "prediction_sha256": file_sha256(prediction_path),
        "prediction_commit_sha": receipt["prediction_commit_sha"],
        "label_read_count": 0,
        "status": "pending_execution",
    }
    _atomic_json(decision_path, decision)

    state["decision_dates"].append(decision_date)
    state["decision_dates"] = sorted(state["decision_dates"])
    state["pending_execution_dates"].append(execution_date)
    state["pending_execution_dates"] = sorted(set(state["pending_execution_dates"]))
    state["last_decision_date"] = decision_date
    state["paper_decision_count"] = len(state["decision_dates"])
    state["status"] = "pending_execution"
    _atomic_json(state_path, state)
    return decision


def refresh_paper_execution(config: Mapping[str, Any]) -> dict[str, Any]:
    """Replay the existing Qlib execution path once execution-day data exists."""

    output_root = _resolve(config["output_root"])
    state_path = output_root / "status.json"
    state = _read_json(state_path)
    decisions = [
        _read_json(output_root / "decisions" / value / "decision.json")
        for value in state["decision_dates"]
    ]
    daily_root = _resolve(config["daily_update_root"])
    available = []
    for decision in decisions:
        execution_dir = daily_root / decision["execution_date"]
        if not (execution_dir / "summary.json").is_file():
            break
        available.append(decision)
    if not available:
        return {"status": "pending_execution", "pending_execution_dates": state["pending_execution_dates"]}

    dates = sorted({value for row in available for value in (row["decision_date"], row["execution_date"])})
    daily_frames = []
    for value in dates:
        target = daily_root / value
        summary = _read_json(target / "summary.json")
        if summary.get("status") != "ready":
            raise ValueError(f"daily update is not ready: {value}")
        source = str(summary.get("source"))
        daily_path = target / f"{source}_qlib_daily.csv"
        daily = pd.read_csv(daily_path)
        daily["datetime"] = pd.to_datetime(daily["date"], errors="raise").dt.normalize()
        daily["instrument"] = daily["symbol"].astype(str).str.upper()
        daily_frames.append(daily)
    daily = pd.concat(daily_frames, ignore_index=True)

    prediction_frames = []
    for decision in available:
        prediction = pd.read_csv(_resolve(config["prediction_root"]) / decision["decision_date"] / "prediction.csv")
        prediction_frames.append(prediction[["datetime", "instrument", "score"]])
    signal = pd.concat(prediction_frames, ignore_index=True)
    signal["method"] = "strategy_v1_lightgbm"
    signal["signal_artifact_id"] = "official_forward_prediction"
    signal["profile_name"] = "strategy_v1"
    signal["profile_type"] = "prospective_paper"
    signal["research_run_family_id"] = "strategy_v1_forward"

    instruments = sorted(signal["instrument"].astype(str).str.upper().unique())
    calendar = pd.DatetimeIndex(dates)
    index = pd.MultiIndex.from_product([instruments, calendar], names=["instrument", "datetime"])
    daily = daily.set_index(["instrument", "datetime"]).reindex(index).sort_index()
    for column in ("raw_open", "raw_close", "raw_volume", "raw_amount", "factor"):
        daily[column] = pd.to_numeric(daily[column], errors="coerce")
    previous_close = daily.groupby(level="instrument")["raw_close"].shift(1)
    daily["change"] = daily["raw_close"] / previous_close - 1.0
    first_date = daily.index.get_level_values("datetime") == calendar[0]
    daily.loc[first_date, "change"] = 0.0
    valid = (
        daily["raw_open"].gt(0)
        & daily["raw_close"].gt(0)
        & daily["raw_volume"].gt(0)
        & daily["factor"].gt(0)
    )
    daily["open"] = daily["raw_open"]
    daily["close"] = daily.groupby(level="instrument")["raw_close"].ffill()
    daily["volume"] = daily["raw_volume"].fillna(0.0)
    daily["amount"] = daily["raw_amount"].fillna(0.0)
    daily["factor"] = daily.groupby(level="instrument")["factor"].ffill()
    daily["suspended"] = ~valid
    daily["limit_up"] = valid & daily["change"].ge(float(config["limit_threshold_approximation"]))
    daily["limit_down"] = valid & daily["change"].le(-float(config["limit_threshold_approximation"]))
    daily["can_buy"] = valid & ~daily["limit_up"]
    daily["can_sell"] = valid & ~daily["limit_down"]
    daily["execution_price"] = daily["raw_open"]
    market = daily.reset_index()
    trading_rules = load_yaml(_resolve(config["trading_rules"]))
    boards = market["instrument"].map(infer_board)
    if boards.eq("unknown").any():
        raise ValueError("paper execution encountered an unsupported A-share board")
    for side in ("buy", "sell"):
        resolved = boards.map(
            lambda board: resolve_lot_rule(trading_rules, board=board, side=side)
        )
        if side == "buy":
            market["lot_minimum_buy"] = resolved.map(lambda row: row["minimum_shares"])
            market["lot_increment_buy"] = resolved.map(lambda row: row["increment_shares"])
        else:
            market["lot_increment_sell"] = resolved.map(lambda row: row["increment_shares"])

    run_config = {
        field: config[field]
        for field in (
            "initial_cash", "top_k", "rebalance_interval", "risk_degree", "lot_size",
            "dynamic_lot_rules", "buy_commission_rate", "sell_commission_rate",
            "sell_tax_rate", "minimum_commission", "slippage_bps", "max_participation_rate",
        )
    }
    result = _run_qlib_execution(signal, market, run_config)
    _atomic_csv(output_root / "trades.csv", result["fills"])
    _atomic_csv(output_root / "rejected_orders.csv", result["rejected_orders"])
    _atomic_csv(output_root / "positions.csv", result["positions"])
    _atomic_csv(output_root / "daily_nav.csv", result["daily_accounting"])
    executed_through = available[-1]["execution_date"]
    for decision in available:
        decision_path = output_root / "decisions" / decision["decision_date"] / "decision.json"
        decision["status"] = "executed"
        decision["execution_recorded_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_json(decision_path, decision)
    state["executed_through"] = executed_through
    state["pending_execution_dates"] = [
        value for value in state["pending_execution_dates"] if value > executed_through
    ]
    state["status"] = "active" if not state["pending_execution_dates"] else "pending_execution"
    _atomic_json(state_path, state)
    return {
        "status": state["status"],
        "executed_through": executed_through,
        "trade_count": len(result["fills"]),
        "position_rows": len(result["positions"]),
        "nav_rows": len(result["daily_accounting"]),
    }

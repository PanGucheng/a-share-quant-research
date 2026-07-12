from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.model_comparison import prerequisite_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate model comparison on all required research contracts.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_model_comparison_v1.yaml"))
    args = parser.parse_args(); path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    contracts = {name: pd.read_csv(PROJECT_ROOT / contract_path) for name, contract_path in config["prerequisites"].items()}
    status = prerequisite_status(contracts); ready = bool((status.status == "pass").all())
    output = PROJECT_ROOT / config["output_dir"]; output.mkdir(parents=True, exist_ok=True); status.to_csv(output / "prerequisite_status.csv", index=False, encoding="utf-8-sig")
    contract = pd.DataFrame([{"check_name": "model_comparison_prerequisites", "status": "pass" if ready else "blocked", "observed_value": int((status.status == "pass").sum()), "required_value": len(status), "severity": "critical", "reason": "Model training must not start until every prerequisite contract passes."}, {"check_name": "model_training_started", "status": "pass", "observed_value": False, "required_value": False, "severity": "critical", "reason": "No model is trained while prerequisites are blocked."}])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "model_comparison_report.md").write_text(f"# Factor Model Comparison V1\n\n- Prerequisites ready: `{ready}`\n- Training started: `false`\n- Planned order: `{', '.join(config['models'])}`\n", encoding="utf-8")
    print(contract.to_string(index=False))
    if not ready: return 2
    raise NotImplementedError("Prerequisites passed; model training implementation requires a separate approved run.")


if __name__ == "__main__": raise SystemExit(main())

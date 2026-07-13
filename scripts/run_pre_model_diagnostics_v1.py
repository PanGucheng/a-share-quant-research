from __future__ import annotations

from multiprocessing import freeze_support
from pathlib import Path

from run_final_portfolio_diagnostics_v1 import main


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main(Path("configs/pre_model_diagnostics_v1.yaml")))

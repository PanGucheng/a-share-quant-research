import argparse
import logging
from pathlib import Path

from tradability.builder import apply_overrides, load_config, output_dir, run


def parse_args():
    parser = argparse.ArgumentParser(description="Build A-share tradability labels.")
    parser.add_argument("--config", default="tradability/config.yaml")
    parser.add_argument("--provider-uri")
    parser.add_argument("--market")
    parser.add_argument("--start-time")
    parser.add_argument("--end-time")
    parser.add_argument("--data-quality-dir")
    parser.add_argument("--output-dir")
    return parser.parse_args()


def configure_logging(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger("tradability")


def main():
    args = parse_args()
    config = apply_overrides(load_config(Path(args.config)), args)
    out = output_dir(config)
    logger = configure_logging(out / "run.log")
    try:
        result = run(config, logger)
    except Exception:
        logger.exception("Tradability label generation failed.")
        raise
    print(f"Tradability labels completed: {result}")


if __name__ == "__main__":
    main()

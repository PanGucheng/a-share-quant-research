if __name__ == "__main__":
    import subprocess
    import sys
    from pathlib import Path

    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "qlib_baseline.cli.forward_predict", *sys.argv[1:]],
            cwd=Path(__file__).resolve().parents[1],
        )
    )

from qlib_baseline.cli.forward_predict import main

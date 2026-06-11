import os
import sys
import tempfile
from multiprocessing import freeze_support
from pathlib import Path

from qlib.cli.run import run


def main():
    project_root = Path(__file__).resolve().parents[1]
    temp_root = project_root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)

    os.environ["TMP"] = str(temp_root)
    os.environ["TEMP"] = str(temp_root)
    os.environ["TMPDIR"] = str(temp_root)
    tempfile.tempdir = str(temp_root)

    run()


if __name__ == "__main__":
    freeze_support()
    main()

import os
import tempfile
from multiprocessing import freeze_support
from pathlib import Path

from qlib.cli.run import run


def enable_sandbox_compat(temp_root: Path):
    import subprocess
    import sys
    import uuid

    from qlib.workflow.recorder import MLflowRecorder

    def mkdir_temp_dir(suffix=None, prefix=None, dir=None):
        root = Path(dir or tempfile.tempdir or temp_root)
        name_prefix = prefix or "qlib_tmp_"
        name_suffix = suffix or ""
        for _ in range(100):
            path = root / f"{name_prefix}{uuid.uuid4().hex}{name_suffix}"
            try:
                path.mkdir(parents=True, exist_ok=False)
                return str(path)
            except FileExistsError:
                continue
        raise FileExistsError(f"Unable to create a unique temp directory under {root}")

    tempfile.mkdtemp = mkdir_temp_dir

    original_temporary_directory = tempfile.TemporaryDirectory

    def temporary_directory_ignore_cleanup_errors(*args, **kwargs):
        kwargs.setdefault("ignore_cleanup_errors", True)
        return original_temporary_directory(*args, **kwargs)

    tempfile.TemporaryDirectory = temporary_directory_ignore_cleanup_errors

    def log_uncommitted_code_best_effort(self):
        for cmd, fname in [
            ("git diff", "code_diff.txt"),
            ("git status", "code_status.txt"),
            ("git diff --cached", "code_cached.txt"),
        ]:
            try:
                out = subprocess.check_output(cmd, shell=True)
                self.client.log_text(self.id, out.decode(), fname)
            except Exception as exc:
                print(f"skip_uncommitted_code_log {fname}: {exc}", file=sys.stderr)

    MLflowRecorder._log_uncommitted_code = log_uncommitted_code_best_effort


def main():
    project_root = Path(__file__).resolve().parents[1]
    temp_root = Path(os.environ.get("TMP") or os.environ.get("TEMP") or project_root / "tmp")
    temp_root.mkdir(parents=True, exist_ok=True)

    os.environ["TMP"] = str(temp_root)
    os.environ["TEMP"] = str(temp_root)
    os.environ["TMPDIR"] = str(temp_root)
    tempfile.tempdir = str(temp_root)

    if os.environ.get("QLIB_BASELINE_SAFE_MODE") == "1":
        enable_sandbox_compat(temp_root)

    run()


if __name__ == "__main__":
    freeze_support()
    main()

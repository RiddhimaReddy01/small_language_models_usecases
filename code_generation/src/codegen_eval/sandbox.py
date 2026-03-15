from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import psutil


PASS_MARKER = "__CODEGEN_EVAL_PASS__"


def build_execution_script(dataset: str, generated_code: str, test_code: str, entry_point: str) -> str:
    if dataset == "HumanEval":
        runner = f"{test_code.rstrip()}\n\ncheck({entry_point})\nprint('{PASS_MARKER}')\n"
    else:
        runner = f"{test_code.rstrip()}\nprint('{PASS_MARKER}')\n"

    return (
        generated_code.rstrip()
        + "\n\n"
        + textwrap.dedent(
            f"""
            if __name__ == "__main__":
                {textwrap.indent(runner.rstrip(), "    ")}
            """
        ).strip()
        + "\n"
    )


def _peak_memory_gb(process: subprocess.Popen[str]) -> float:
    peak_bytes = 0
    try:
        ps_process = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                peak_bytes = max(peak_bytes, ps_process.memory_info().rss)
            except psutil.Error:
                break
            time.sleep(0.05)
        if process.poll() is not None:
            try:
                peak_bytes = max(peak_bytes, ps_process.memory_info().rss)
            except psutil.Error:
                pass
    except psutil.Error:
        return 0.0
    return peak_bytes / (1024**3)


def execute_code(script: str, timeout_seconds: int) -> dict[str, str | float | int]:
    with tempfile.TemporaryDirectory(prefix="codegen_eval_") as temp_dir:
        script_path = Path(temp_dir) / "run_eval.py"
        script_path.write_text(script, encoding="utf-8")

        start = time.perf_counter()
        process = subprocess.Popen(
            [sys.executable, "-I", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        peak_ram_gb = _peak_memory_gb(process)
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            timeout = False
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            timeout = True
        elapsed = time.perf_counter() - start

    return {
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_seconds": elapsed,
        "peak_ram_gb": peak_ram_gb,
        "timeout": timeout,
    }

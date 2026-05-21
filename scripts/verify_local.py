from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    output = ROOT / "output" / "local_verify_release_check.json"
    return run([sys.executable, "render.py", "release-check", "-o", str(output)])


def run(command: list[str]) -> int:
    print(f"> {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode
    print(f"Local verification passed. Report: {ROOT / 'output' / 'local_verify_release_check.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the official lexical baseline across all LongEval-Sci snapshots."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import run_baseline
from longeval_sci.config import load_config


if __name__ == "__main__":
    run_baseline(load_config("configs/official_pyterrier.yaml"))

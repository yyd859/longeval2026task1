"""Compatibility wrapper: run the lexical baseline and persist its index if configured."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import main_run_pipeline


if __name__ == "__main__":
    main_run_pipeline()

"""Random seed helpers."""

from __future__ import annotations

import random

import numpy as np


def set_seed(seed: int) -> None:
    """Set deterministic seeds where possible."""
    random.seed(seed)
    np.random.seed(seed)

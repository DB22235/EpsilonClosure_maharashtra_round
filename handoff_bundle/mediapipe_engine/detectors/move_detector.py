"""
Geometric Whole-Hand Move Detector for MediaPipe Palm Trajectory.
"""

from __future__ import annotations
import math


def is_valid_move(
    palm_history: list[list[float]],
    min_displacement: float = 100.0,
    min_points: int = 8,
) -> bool:
    """
    Detects whole-hand movement by tracking palm center or wrist coordinates.
    """
    if not palm_history:
        return False

    valid = [p for p in palm_history if len(p) >= 2 and (p[0] != 0 or p[1] != 0)]
    if len(valid) < min_points:
        return False

    # Check scale (pixel vs normalized 0..1)
    max_val = max(max(p[0], p[1]) for p in valid)
    effective_min_disp = min_displacement if max_val > 1.0 else (min_displacement / 960.0)

    dx = valid[-1][0] - valid[0][0]
    dy = valid[-1][1] - valid[0][1]
    total_displacement = math.sqrt(dx * dx + dy * dy)

    if total_displacement < effective_min_disp:
        return False

    # Step distances
    step_distances = [
        math.sqrt((valid[i][0] - valid[i - 1][0]) ** 2 + (valid[i][1] - valid[i - 1][1]) ** 2)
        for i in range(1, len(valid))
    ]
    avg_step = sum(step_distances) / len(step_distances)

    min_avg_step = 3.0 if max_val > 1.0 else (3.0 / 960.0)
    if avg_step < min_avg_step:
        return False

    return True

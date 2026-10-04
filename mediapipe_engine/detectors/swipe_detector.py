"""
Geometric Swipe Detector for MediaPipe Trajectory.
"""

from __future__ import annotations


def is_valid_swipe(
    point_history: list[list[float]],
    min_displacement: float = 280.0,
    min_points: int = 6,
    max_vertical_ratio: float = 0.6,
) -> bool:
    """
    Detects a fast, deliberate horizontal swipe gesture.
    """
    if not point_history:
        return False

    # Filter out [0, 0] padding points
    valid_points = [p for p in point_history if len(p) >= 2 and (p[0] != 0 or p[1] != 0)]
    if len(valid_points) < min_points:
        return False

    x_coords = [p[0] for p in valid_points]
    y_coords = [p[1] for p in valid_points]

    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    x_span = x_max - x_min
    y_span = y_max - y_min

    # Adjust threshold if coordinates are normalized (0.0 to 1.0)
    effective_min_disp = min_displacement if min_displacement > 1.0 and x_max > 1.0 else (min_displacement / 960.0)

    # 1. Horizontal span check
    if x_span < effective_min_disp:
        return False

    # 2. Vertical vs Horizontal ratio check (horizontal motion)
    if y_span / (x_span + 1e-6) > max_vertical_ratio:
        return False

    # 3. Direction consistency check (straight progression)
    dx = valid_points[-1][0] - valid_points[0][0]
    if abs(dx) / (x_span + 1e-6) < 0.8:
        return False

    return True

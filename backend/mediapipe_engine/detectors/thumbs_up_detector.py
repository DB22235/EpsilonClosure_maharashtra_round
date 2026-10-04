"""
Geometric Thumbs Up Detector for MediaPipe 21 Hand Landmarks.
"""

from __future__ import annotations
import math


def is_thumbs_up(landmark_list: list[list[float]]) -> bool:
    """
    Detects if the 21 hand landmarks form a valid 'THUMBS UP' gesture:
    - 4 fingers (Index, Middle, Ring, Pinky) are folded in.
    - Thumb tip (landmark 4) is extended UPWARDS above IP (3) and MCP (2).
    """
    if not landmark_list or len(landmark_list) < 21:
        return False

    wrist = landmark_list[0]

    def dist(p1: list[float], p2: list[float]) -> float:
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    # 1. Folded state for 4 fingers (Index: 8 vs 6, Middle: 12 vs 10, Ring: 16 vs 14, Pinky: 20 vs 18)
    finger_pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
    for tip_idx, pip_idx in finger_pairs:
        dist_tip_wrist = dist(landmark_list[tip_idx], wrist)
        dist_pip_wrist = dist(landmark_list[pip_idx], wrist)
        if dist_tip_wrist > dist_pip_wrist * 1.15:
            return False

    # 2. Check Thumb is extended UPWARDS
    thumb_tip = landmark_list[4]
    thumb_ip = landmark_list[3]
    thumb_mcp = landmark_list[2]

    # In image coordinates, Y decreases towards top of screen.
    # Thumb tip must be higher up in the frame than IP joint and MCP joint.
    thumb_pointing_up = (thumb_tip[1] < thumb_ip[1]) and (thumb_ip[1] < thumb_mcp[1] or thumb_tip[1] < thumb_mcp[1])

    # Thumb must be extended relative to wrist
    dist_thumb_wrist = dist(thumb_tip, wrist)
    dist_mcp_wrist = dist(thumb_mcp, wrist)
    thumb_extended = dist_thumb_wrist > dist_mcp_wrist * 1.2

    return thumb_pointing_up and thumb_extended

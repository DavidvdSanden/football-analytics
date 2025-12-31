import math
import numpy as np


def euclidean(a, b):
    """Calculate Euclidean distance between points a and b."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def shot_angle(shot, left_post, right_post):
    """
    Calculate the open goal angle from the shot position to the goalposts.

    Parameters:
        shot: (x, y) coordinates of the shot location
        left_post: (x, y) coordinates of the left goalpost
        right_post: (x, y) coordinates of the right goalpost

    Returns:
        angle in radians
    """
    a = euclidean(shot, left_post)
    b = euclidean(shot, right_post)
    c = euclidean(left_post, right_post)

    try:
        angle = math.acos((a**2 + b**2 - c**2) / (2 * a * b))
    except Exception:
        angle = 0.0  # If calculation fails, return 0
    return angle


def point_in_triangle(p, a, b, c):
    """
    Check if point p is inside triangle ABC using barycentric coordinates.
    p, a, b, c = [x, y]
    """
    # Convert to vectors
    v0 = [c[0] - a[0], c[1] - a[1]]
    v1 = [b[0] - a[0], b[1] - a[1]]
    v2 = [p[0] - a[0], p[1] - a[1]]

    # Dot products
    dot00 = v0[0] * v0[0] + v0[1] * v0[1]
    dot01 = v0[0] * v1[0] + v0[1] * v1[1]
    dot02 = v0[0] * v2[0] + v0[1] * v2[1]
    dot11 = v1[0] * v1[0] + v1[1] * v1[1]
    dot12 = v1[0] * v2[0] + v1[1] * v2[1]

    # Barycentric coordinates
    denom = dot00 * dot11 - dot01 * dot01
    if denom == 0:
        return False  # Degenerate triangle

    inv_denom = 1 / denom
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom

    # Inside triangle when u >= 0, v >= 0, u+v <= 1
    return (u >= 0) and (v >= 0) and (u + v <= 1)


def count_opponents_in_shot_triangle(shot_loc, left_post, right_post, freeze_frame):
    """
    Counts how many *opposition* players (non-teammates, non-GK) are inside
    the shot triangle.
    """

    count = 0

    for p in freeze_frame:
        if p.get("teammate"):
            continue  # ignore teammates

        # exclude goalkeeper
        if p.get("position", {}).get("name", "") == "Goalkeeper":
            continue

        loc = p["location"]

        if point_in_triangle(loc, shot_loc, left_post, right_post):
            count += 1

    return count


def _angle(a, b):
    """angle from point a -> point b in radians (range -pi..pi)"""
    return math.atan2(b[1] - a[1], b[0] - a[0])


def _normalize_ang(a):
    """Normalize angle to [-pi, pi)"""
    a = (a + math.pi) % (2 * math.pi) - math.pi
    return a


def _angle_diff(a, b):
    """Smallest signed difference b-a in radians"""
    d = _normalize_ang(b - a)
    return d


def _intervals_union(intervals):
    """Union list of intervals on circle-like line but we assume no wrap-around here (angles in increasing order).
    Intervals are (start, end) with start <= end. Returns merged list.
    """
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def blocked_goal_fraction(
    shot_loc,
    left_post,
    right_post,
    defenders,
    keeper=None,
    player_radius=0.25,
    keeper_radius=0.75,
):
    """
    Compute fraction of goal angular span blocked by opponents (and optionally keeper).
    Inputs:
      shot_loc: (x,y) of shot
      left_post, right_post: (x,y) coordinates of posts (goal line at x=120 for StatsBomb coords)
      defenders: list of dicts or list of (x,y) positions for opposition players EXCLUDING keeper
                 each element can be a dict with 'location' or a 2-tuple (x,y)
      keeper: optional (x,y) location of keeper (can be None)
      player_radius: radius (m) used to represent a defender's blocking width (default 0.5 m)
      keeper_radius: effective blocking radius for keeper (default 1.5 m)
    Returns:
      uncovered_fraction (float between 0 and 1), blocked_angle, total_goal_angle (radians)
    """
    # goal angular span
    ang_L = _angle(shot_loc, left_post)
    ang_R = _angle(shot_loc, right_post)

    # ensure goal span is the smaller angular interval from L->R in correct orientation
    # we will make goal_start < goal_end in numeric sense by mapping to continuous range
    # pick start = min angle, end = max angle after unwrapping via reference
    # unwrap angles so that ang_R is reached from ang_L by moving positive or negative?
    # simpler: compute both and take absolute difference
    # We'll map all angles to an interval centered on the goal mid-angle to avoid wrapping issues.
    goal_mid = _normalize_ang((ang_L + ang_R) / 2.0)

    def _rel(a):
        return _normalize_ang(a - goal_mid)

    rel_L = _rel(ang_L)
    rel_R = _rel(ang_R)
    # ensure rel_L < rel_R
    if rel_L > rel_R:
        rel_L, rel_R = rel_R, rel_L
    goal_span = rel_R - rel_L
    if goal_span <= 0:
        return 0.0, 0.0, 0.0

    # helper to compute occlusion interval for a circle of radius r at point p
    def occlusion_interval(p, r):
        dx = p[0] - shot_loc[0]
        dy = p[1] - shot_loc[1]
        dist = math.hypot(dx, dy)
        if dist <= 1e-6:
            # player at shooter location -> blocks entire goal (degenerate)
            return (rel_L, rel_R)
        # if player circle covers shot point (dist < r), treat as blocking everything
        if dist <= r:
            return (rel_L, rel_R)
        # half-angle subtended by the defender circle
        half_ang = math.asin(min(1.0, r / dist))
        center_ang = _rel(math.atan2(dy, dx))
        start = center_ang - half_ang
        end = center_ang + half_ang
        # intersect with goal span
        # if interval completely outside goal span, return None
        # but keep as (start,end) for later clipping
        return (start, end)

    intervals = []

    # defenders input flexibility
    def extract_xy(obj):
        if isinstance(obj, (list, tuple, np.ndarray)) and len(obj) >= 2:
            return (float(obj[0]), float(obj[1]))
        if isinstance(obj, dict) and "location" in obj:
            loc = obj["location"]
            return (float(loc[0]), float(loc[1]))
        raise ValueError("defender format not recognized")

    for d in defenders:
        px, py = extract_xy(d)
        start, end = occlusion_interval((px, py), player_radius)
        # clip interval to goal span
        # if interval outside, skip; else append clipped piece
        # interval coordinates are relative to goal_mid; goal span is [rel_L, rel_R]
        # If start > rel_R or end < rel_L => no overlap
        if end < rel_L or start > rel_R:
            continue
        s_clipped = max(start, rel_L)
        e_clipped = min(end, rel_R)
        if e_clipped > s_clipped + 1e-9:
            intervals.append((s_clipped, e_clipped))

    # keeper
    if keeper is not None:
        kx, ky = extract_xy(keeper)
        start, end = occlusion_interval((kx, ky), keeper_radius)
        if not (end < rel_L or start > rel_R):
            intervals.append((max(start, rel_L), min(end, rel_R)))

    # unify intervals
    merged = _intervals_union(intervals)
    blocked_angle = sum(e - s for s, e in merged)
    uncovered_fraction = max(0.0, 1.0 - blocked_angle / goal_span)
    return uncovered_fraction, blocked_angle, goal_span


def keeper_in_shot_triangle(shot_loc, left_post, right_post, freeze_frame):
    """
    Return True if the opposing goalkeeper (if present) is located inside the
    triangle defined by the shot location and the two goal posts.

    Parameters
    ----------
    shot_loc : (x,y)
    left_post, right_post : (x,y)
    freeze_frame : list of player dicts (each with 'teammate', 'position', 'location')

    Returns
    -------
    bool
    """
    if not freeze_frame:
        return False

    # find opponent goalkeeper
    keeper_loc = None
    for p in freeze_frame:
        if p.get("teammate"):
            continue
        pos_name = p.get("position", {}).get("name", "") or ""
        if pos_name.lower() == "goalkeeper":
            keeper_loc = p.get("location")
            break

    if not keeper_loc:
        return False

    try:
        return bool(point_in_triangle(keeper_loc, shot_loc, left_post, right_post))
    except Exception:
        return False

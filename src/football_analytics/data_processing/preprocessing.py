import json
from datetime import datetime, date, time
import numpy as np
import football_analytics.utils.helper as helper


def _parse_int(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError:
            try:
                return datetime.fromisoformat(value).date().isoformat()
            except ValueError:
                return value
    return value


def _parse_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.time().isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, str):
        for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).time().isoformat()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value).time().isoformat()
        except ValueError:
            return value
    return value


def _parse_timestamp(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, time.min).isoformat()
    if isinstance(value, str):
        cleaned = value.rstrip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1]
        try:
            return datetime.fromisoformat(cleaned).isoformat()
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(cleaned, fmt).isoformat()
                except ValueError:
                    continue
            return value
    return value


def extract_shot_features(event, match_id=None):
    # -----------------------------
    # CONSTANTEN
    # -----------------------------
    GOAL_CENTER = [120, 40]
    LEFT_POST = [120, 36]
    RIGHT_POST = [120, 44]

    # PLAYER / TEAM
    attacking_team = event["possession_team"]
    defending_team = event["possession_team"]
    shot_taker = event["player"]

    # -----------------------------
    # EXTRACT FEATURES
    # -----------------------------
    play_pattern = event["play_pattern"]["name"]
    shot = event.get("shot") or {}
    shot_loc = event["location"]

    # Freeze frame
    freeze_frame = shot.get("freeze_frame")

    if freeze_frame:
        # Keeper
        keeper_list = [
            p["location"]
            for p in shot["freeze_frame"]
            if not p["teammate"]
            and p.get("position", {}).get("name", "") == "Goalkeeper"
        ]
        keeper_loc = keeper_list[0] if keeper_list else GOAL_CENTER

        # Defenders & teammates
        defenders = [
            p["location"]
            for p in shot["freeze_frame"]
            if not p["teammate"]
            and p.get("position", {}).get("name", "") != "Goalkeeper"
        ]
        teammates = [p["location"] for p in shot["freeze_frame"] if p["teammate"]]

        keeper_distance = helper.euclidean(shot_loc, keeper_loc)
        num_def_in_shot_triangle = helper.count_opponents_in_shot_triangle(
            shot_loc, LEFT_POST, RIGHT_POST, shot["freeze_frame"]
        )
        num_teammates_in_box = sum(
            [1 for t in teammates if t[0] > 100 and 36 <= t[1] <= 44]
        )
        frac_goal_uncovered, blocked_ang, total_ang = helper.blocked_goal_fraction(
            shot_loc, LEFT_POST, RIGHT_POST, defenders, keeper=keeper_loc
        )
        keeper_is_in_shot_triangle = helper.keeper_in_shot_triangle(
            shot_loc, LEFT_POST, RIGHT_POST, shot["freeze_frame"]
        )
    else:
        defenders = None
        teammates = None
        keeper_distance = None
        num_def_in_shot_triangle = None
        num_teammates_in_box = None
        frac_goal_uncovered = None
        keeper_is_in_shot_triangle = None

    # Categorical / context features
    shot_type = shot.get("type", {}).get("name")
    body_part = shot.get("body_part", {}).get("name")

    # Outcome
    outcome = shot.get("outcome", {}).get("name")

    # Basic features
    distance_to_goal = helper.euclidean(shot_loc, GOAL_CENTER)
    angle_to_goal = helper.shot_angle(shot_loc, LEFT_POST, RIGHT_POST)
    min_defender_distance = (
        min([helper.euclidean(shot_loc, d) for d in defenders]) if defenders else None
    )
    avg_defender_distance = (
        sum([helper.euclidean(shot_loc, d) for d in defenders]) / len(defenders)
        if defenders
        else None
    )

    shot_type_id = shot.get("type", {}).get("id")
    is_penalty = shot_type == "Penalty" or shot_type_id == 88
    if is_penalty:
        if keeper_distance is None:
            keeper_distance = distance_to_goal
        if num_def_in_shot_triangle is None:
            num_def_in_shot_triangle = 0
        if num_teammates_in_box is None:
            num_teammates_in_box = 0
        if frac_goal_uncovered is None:
            frac_goal_uncovered, _, _ = helper.blocked_goal_fraction(
                shot_loc, LEFT_POST, RIGHT_POST, [], keeper=GOAL_CENTER
            )
        penalty_area_x = 102
        min_penalty_def_dist = max(0.0, shot_loc[0] - penalty_area_x)
        if min_defender_distance is None:
            min_defender_distance = min_penalty_def_dist
        if avg_defender_distance is None:
            avg_defender_distance = min_penalty_def_dist
        keeper_is_in_shot_triangle = True

    # Dynamic ratio features
    shot_to_min_def_ratio = (
        distance_to_goal / (min_defender_distance + 0.01)
        if min_defender_distance is not None
        else None
    )

    # Parse `under_pressure` carefully (float('nan') should be treated as False)
    _up = event.get("under_pressure", False)
    if isinstance(_up, float) and np.isnan(_up):
        under_pressure = False
    elif isinstance(_up, str):
        under_pressure = _up.strip().lower() in ("true", "1", "yes", "y")
    else:
        under_pressure = bool(_up)

    # Combine all extracted features into a single dict
    full_json = event.to_json() if hasattr(event, "to_json") else json.dumps(event)
    shot_data_row = {
        "statsbomb_event_id": event["id"],
        "match_id": match_id,
        "play_pattern": play_pattern,
        "attacking_team": attacking_team,
        "shot_taker": shot_taker,
        "x1": shot_loc[0],
        "y1": shot_loc[1],
        "distance_to_goal": distance_to_goal,
        "angle_to_goal_deg": angle_to_goal * 180 / np.pi,
        "keeper_distance": keeper_distance,
        "min_defender_distance": min_defender_distance,
        "avg_defender_distance": avg_defender_distance,
        "num_def_in_shot_triangle": num_def_in_shot_triangle,
        "frac_goal_uncovered": frac_goal_uncovered,
        "num_teammates_in_box": num_teammates_in_box,
        "shot_to_min_def_ratio": shot_to_min_def_ratio,
        "shot_type": shot_type,
        "body_part": body_part,
        "outcome": outcome,
        "full_json": full_json,
        "statsbomb_xg": shot.get("statsbomb_xg", None),
        "attacking_team_id": attacking_team.get("id"),
        "shot_taker_id": shot_taker.get("id"),
        "keeper_is_in_shot_triangle": keeper_is_in_shot_triangle,
        "under_pressure": under_pressure,
        "timestamp": _parse_time(event.get("timestamp", None)),
        "period": event.get("period", None),
        "minute": event.get("minute", None),
        "second": event.get("second", None),
    }

    return shot_data_row


def extract_team_row(team):
    """
    Normalize a team object from a StatsBomb match entry into a flat dict.
    """
    if not team:
        return None

    team_id = (
        team.get("home_team_id") or team.get("away_team_id") or team.get("team_id")
    )
    team_name = (
        team.get("home_team_name")
        or team.get("away_team_name")
        or team.get("team_name")
    )
    team_gender = (
        team.get("home_team_gender")
        or team.get("away_team_gender")
        or team.get("team_gender")
    )
    team_group = (
        team.get("home_team_group")
        or team.get("away_team_group")
        or team.get("team_group")
    )

    country = team.get("country") or {}

    managers = team.get("managers") or []
    manager = managers[0] if managers else {}
    manager_country = manager.get("country") or {}

    return {
        "team_id": team_id,
        "team_name": team_name,
        "team_gender": team_gender,
        "team_group": team_group,
        "country_id": country.get("id"),
        "country_name": country.get("name"),
        "manager_id": manager.get("id"),
        "manager_name": manager.get("name"),
        "manager_nickname": manager.get("nickname"),
        "manager_dob": manager.get("dob"),
        "manager_country_id": manager_country.get("id"),
        "manager_country_name": manager_country.get("name"),
    }


def extract_player_row(event):
    """
    Normalize player information from a StatsBomb event into a flat dict.
    """
    if not event:
        return None

    player = event.get("player") or {}
    if not player:
        return None

    position = event.get("position") or {}
    team = event.get("team") or {}
    jersey_number = event.get("jersey_number")

    return {
        "statsbomb_player_id": player.get("id"),
        "player_name": player.get("name"),
        "position_id": position.get("id"),
        "position_name": position.get("name"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "jersey_number": jersey_number,
    }


def extract_match_row(match):
    """
    Normalize a StatsBomb match entry into a flat dict for database ingestion.
    """
    if not match:
        return None

    competition = match.get("competition") or {}
    season = match.get("season") or {}
    home_team = match.get("home_team") or {}
    away_team = match.get("away_team") or {}
    competition_stage = match.get("competition_stage") or {}
    stadium = match.get("stadium") or {}
    referee = match.get("referee") or {}

    return {
        "match_id": _parse_int(match.get("match_id")),
        "match_date": _parse_date(match.get("match_date")),
        "kick_off": _parse_time(match.get("kick_off")),
        "competition_id": _parse_int(competition.get("competition_id")),
        "season_id": _parse_int(season.get("season_id")),
        "home_team_id": _parse_int(home_team.get("home_team_id")),
        "away_team_id": _parse_int(away_team.get("away_team_id")),
        "home_score": _parse_int(match.get("home_score")),
        "away_score": _parse_int(match.get("away_score")),
        "match_status": match.get("match_status"),
        "match_status_360": match.get("match_status_360"),
        "last_updated": _parse_timestamp(match.get("last_updated")),
        "last_updated_360": _parse_timestamp(match.get("last_updated_360")),
        "match_week": _parse_int(match.get("match_week")),
        "competition_stage_id": _parse_int(competition_stage.get("id")),
        "stadium_id": _parse_int(stadium.get("id")),
        "referee_id": _parse_int(referee.get("id")),
    }

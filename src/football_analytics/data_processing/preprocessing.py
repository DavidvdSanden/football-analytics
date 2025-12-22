import numpy as np
import football_analytics.utils.helper as helper


def extract_shot_features(event, match_id=None):
    # -----------------------------
    # CONSTANTEN
    # -----------------------------
    GOAL_CENTER = [120, 40]
    LEFT_POST = [120, 36]
    RIGHT_POST = [120, 44]

    # PLAYER / TEAM
    attacking_team = event['possession_team']
    defending_team = event['possession_team']
    shot_taker = event['player']

    # -----------------------------
    # EXTRACT FEATURES
    # -----------------------------
    play_pattern = event['play_pattern']['name']
    shot = event.get('shot') or {}
    shot_loc = event['location']

    # Freeze frame
    freeze_frame = shot.get('freeze_frame')

    if freeze_frame:
        # Keeper
        keeper_list = [p['location'] for p in shot['freeze_frame'] if not p['teammate'] and p.get('position', {}).get('name','')=='Goalkeeper']
        keeper_loc = keeper_list[0] if keeper_list else GOAL_CENTER

        # Defenders & teammates
        defenders = [p['location'] for p in shot['freeze_frame'] if not p['teammate'] and p.get('position', {}).get('name','') != 'Goalkeeper']
        teammates = [p['location'] for p in shot['freeze_frame'] if p['teammate']]

        keeper_distance = helper.euclidean(shot_loc, keeper_loc)
        num_def_in_shot_triangle = helper.count_opponents_in_shot_triangle(
            shot_loc,
            LEFT_POST,
            RIGHT_POST,
            shot['freeze_frame']
        )
        num_teammates_in_box = sum([1 for t in teammates if t[0] > 100 and 36 <= t[1] <= 44])
        frac_goal_uncovered, blocked_ang, total_ang = helper.blocked_goal_fraction(
            shot_loc, LEFT_POST, RIGHT_POST, defenders, keeper=keeper_loc
        )
    else:
        defenders = None
        teammates = None
        keeper_distance = None
        num_def_in_shot_triangle = None
        num_teammates_in_box = None
        frac_goal_uncovered = None



    # Categorical / context features
    shot_type = shot.get('type', {}).get('name')
    body_part = shot.get('body_part', {}).get('name')

    # Outcome
    outcome = shot.get('outcome', {}).get('name')

    # Basis features
    distance_to_goal = helper.euclidean(shot_loc, GOAL_CENTER)
    angle_to_goal = helper.shot_angle(shot_loc, LEFT_POST, RIGHT_POST)
    min_defender_distance = min([helper.euclidean(shot_loc, d) for d in defenders]) if defenders else None
    avg_defender_distance = sum([helper.euclidean(shot_loc, d) for d in defenders])/len(defenders) if defenders else None

    shot_type_id = shot.get('type', {}).get('id')
    is_penalty = shot_type == 'Penalty' or shot_type_id == 88
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

    # Dynamische ratio features
    shot_to_min_def_ratio = distance_to_goal / (min_defender_distance + 0.01) if min_defender_distance is not None else None

    # Combineer alles in 1 rij
    shot_data_row = {
        'statsbomb_event_id': event['id'],
        'match_id': match_id,
        'play_pattern': play_pattern,
        'attacking_team': attacking_team,
        'shot_taker': shot_taker,
        'x1': shot_loc[0],
        'y1': shot_loc[1],
        'distance_to_goal': distance_to_goal,
        'angle_to_goal_deg': angle_to_goal * 180 / np.pi,
        'keeper_distance': keeper_distance,
        'min_defender_distance': min_defender_distance,
        'avg_defender_distance': avg_defender_distance,
        'num_def_in_shot_triangle': num_def_in_shot_triangle,
        'frac_goal_uncovered': frac_goal_uncovered,
        'num_teammates_in_box': num_teammates_in_box,
        'shot_to_min_def_ratio': shot_to_min_def_ratio,
        'shot_type': shot_type,
        'body_part': body_part,
        'outcome': outcome,
        'full_json': event.to_json(),
        'statsbomb_xg': shot.get('statsbomb_xg', None),
        'attacking_team_id': attacking_team.get('id'),
        'shot_taker_id': shot_taker.get('id'),
    }

    return shot_data_row


def extract_team_row(team):
    """
    Normalize a team object from a StatsBomb match entry into a flat dict.
    """
    if not team:
        return None

    team_id = team.get('home_team_id') or team.get('away_team_id') or team.get('team_id')
    team_name = team.get('home_team_name') or team.get('away_team_name') or team.get('team_name')
    team_gender = team.get('home_team_gender') or team.get('away_team_gender') or team.get('team_gender')
    team_group = team.get('home_team_group') or team.get('away_team_group') or team.get('team_group')

    country = team.get('country') or {}

    managers = team.get('managers') or []
    manager = managers[0] if managers else {}
    manager_country = manager.get('country') or {}

    return {
        'team_id': team_id,
        'team_name': team_name,
        'team_gender': team_gender,
        'team_group': team_group,
        'country_id': country.get('id'),
        'country_name': country.get('name'),
        'manager_id': manager.get('id'),
        'manager_name': manager.get('name'),
        'manager_nickname': manager.get('nickname'),
        'manager_dob': manager.get('dob'),
        'manager_country_id': manager_country.get('id'),
        'manager_country_name': manager_country.get('name'),
    }


def extract_player_row(event):
    """
    Normalize player information from a StatsBomb event into a flat dict.
    """
    if not event:
        return None

    player = event.get('player') or {}
    if not player:
        return None

    position = event.get('position') or {}
    team = event.get('team') or {}
    jersey_number = event.get('jersey_number')

    return {
        'statsbomb_player_id': player.get('id'),
        'player_name': player.get('name'),
        'position_id': position.get('id'),
        'position_name': position.get('name'),
        'team_id': team.get('id'),
        'team_name': team.get('name'),
        'jersey_number': jersey_number,
    }

import plotly.graph_objects as go
import numpy as np
import pandas as pd

def create_pitch():
    """
    Returns a Plotly figure object with a football pitch drawn.
    """
    pitch_length = 120
    pitch_width = 80
    center_y = pitch_width / 2
    pen_box_width = 44
    pen_box_depth = 18
    gk_box_width = 20
    gk_box_depth = 6
    goal_width = 8
    goal_depth = 0.1
    penalty_spot = 12
    arc_radius = 10

    fig = go.Figure()

    # ----------------------------- Pitch background -----------------------------
    fig.add_shape(type="rect",
                  x0=0, y0=0, x1=pitch_length, y1=pitch_width,
                  line=dict(color="black"), fillcolor="#6BBF59", layer="below")

    # Pitch boundary & center line
    fig.add_shape(type="rect", x0=0, y0=0, x1=pitch_length, y1=pitch_width,
                  line=dict(color="white", width=2), layer="below")
    fig.add_shape(type="line", x0=pitch_length / 2, y0=0,
                  x1=pitch_length / 2, y1=pitch_width,
                  line=dict(color="white", width=2), layer="below")

    # Center circle & spot
    fig.add_shape(type="circle",
                  x0=pitch_length / 2 - 10, y0=center_y - 10,
                  x1=pitch_length / 2 + 10, y1=center_y + 10,
                  line=dict(color="white", width=2), layer="below")
    fig.add_shape(type="circle",
                  x0=pitch_length / 2 - 0.3, y0=center_y - 0.3,
                  x1=pitch_length / 2 + 0.3, y1=center_y + 0.3,
                  line=dict(color="white", width=2), fillcolor="white", layer="below")

    # Penalty boxes
    fig.add_shape(type="rect",
                  x0=0, y0=center_y - pen_box_width / 2,
                  x1=pen_box_depth, y1=center_y + pen_box_width / 2,
                  line=dict(color="white", width=2), layer="below")
    fig.add_shape(type="rect",
                  x0=pitch_length - pen_box_depth, y0=center_y - pen_box_width / 2,
                  x1=pitch_length, y1=center_y + pen_box_width / 2,
                  line=dict(color="white", width=2), layer="below")

    # Goalkeeper boxes
    fig.add_shape(type="rect",
                  x0=0, y0=center_y - gk_box_width / 2,
                  x1=gk_box_depth, y1=center_y + gk_box_width / 2,
                  line=dict(color="white", width=2), layer="below")
    fig.add_shape(type="rect",
                  x0=pitch_length - gk_box_depth, y0=center_y - gk_box_width / 2,
                  x1=pitch_length, y1=center_y + gk_box_width / 2,
                  line=dict(color="white", width=2), layer="below")

    # Goals
    fig.add_shape(type="rect",
                  x0=-goal_depth, y0=center_y - goal_width / 2,
                  x1=0, y1=center_y + goal_width / 2,
                  line=dict(color="white", width=6), layer="below")
    fig.add_shape(type="rect",
                  x0=pitch_length, y0=center_y - goal_width / 2,
                  x1=pitch_length + goal_depth, y1=center_y + goal_width / 2,
                  line=dict(color="white", width=6), layer="below")

    # Penalty spots
    fig.add_shape(type="circle",
                  x0=penalty_spot - 0.3, y0=center_y - 0.3,
                  x1=penalty_spot + 0.3, y1=center_y + 0.3,
                  line=dict(color="white", width=2), fillcolor="white", layer="below")
    fig.add_shape(type="circle",
                  x0=pitch_length - penalty_spot - 0.3, y0=center_y - 0.3,
                  x1=pitch_length - penalty_spot + 0.3, y1=center_y + 0.3,
                  line=dict(color="white", width=2), fillcolor="white", layer="below")

    # Penalty arcs
    d = pen_box_depth - penalty_spot
    angle = np.arccos(d / arc_radius)
    theta_left = np.linspace(-angle, angle, 75)
    theta_right = np.linspace(np.pi - angle, np.pi + angle, 75)

    # Penalty arcs drawn as shapes (SVG paths) so they can be placed below/above traces reliably
    xs_left = (penalty_spot + arc_radius * np.cos(theta_left)).tolist()
    ys_left = (center_y + arc_radius * np.sin(theta_left)).tolist()
    path_left = "M " + " L ".join(f"{x},{y}" for x, y in zip(xs_left, ys_left))
    fig.add_shape(type="path", path=path_left, line=dict(color='white', width=2), layer='below')

    xs_right = (pitch_length - penalty_spot + arc_radius * np.cos(theta_right)).tolist()
    ys_right = (center_y + arc_radius * np.sin(theta_right)).tolist()
    path_right = "M " + " L ".join(f"{x},{y}" for x, y in zip(xs_right, ys_right))
    fig.add_shape(type="path", path=path_right, line=dict(color='white', width=2), layer='below')

    # Layout
    fig.update_layout(
        xaxis=dict(range=[-5, pitch_length + 5], showgrid=False, zeroline=False),
        yaxis=dict(range=[-5, pitch_width + 5], showgrid=False, zeroline=False, scaleanchor="x"),
        width=1100, height=700, plot_bgcolor="#6BBF59", showlegend=False
    )

    return fig

def plot_shot_overview(shots):
    """
    Overview of all shots on the pitch.
    Accepts DataFrame or list of dicts.
    """
    if isinstance(shots, list):
        shots = pd.DataFrame(shots)
    df = shots.copy()

    # Determine coordinates
    if {"x1", "y1"}.issubset(df.columns):
        xs, ys = df["x1"], df["y1"]
    elif {"x", "y"}.issubset(df.columns):
        xs, ys = df["x"], df["y"]
    else:
        raise ValueError("Input must contain (x, y) or (x1, y1) columns.")

    colors = df.get("xG", pd.Series(np.zeros(len(df))))
    hover_texts = df.apply(lambda row: "<br>".join([f"{col}: {row[col]}" for col in df.columns]), axis=1)

    fig = create_pitch()

    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers",
        marker=dict(size=10, color=colors, opacity=0.7, colorscale="Reds", cmin=0, cmax=1, line=dict(color="#3F4646", width=1), showscale=True),
        text=hover_texts, hoverinfo="text"
    ))

    fig.update_layout(title="Overview of Shots")
    fig.show()


def plot_shot_heatmap(shots, bins=(40, 30), weights_col=None, normalize=False,
                      scale='sqrt', zero_transparent=True, colorscale='YlOrRd'):
    """
    Plot a 2D heatmap of shot locations on the pitch.

    Parameters
    ----------
    shots : DataFrame or list of dicts
        Shot records containing x/y coordinates (either `x1`/`y1` or `x`/`y`).
    bins : tuple(int, int)
        Number of bins in x and y directions (default (30, 20)).
    weights_col : str or None
        Column name to weight each shot (e.g. 'xG'). If None, each shot counts equally.
    normalize : bool
        If True, normalize raw heat values to [0, 1] before scaling.
    scale : {'linear', 'sqrt', 'log'}
        Visualization scaling to emphasize low-intensity areas. Default 'sqrt'.
    zero_transparent : bool
        If True, bins with zero value will be transparent so the pitch shows through.
    colorscale : str or list
        Plotly colorscale for the heatmap.
    """
    if isinstance(shots, list):
        shots = pd.DataFrame(shots)
    df = shots.copy()

    if df.empty:
        raise ValueError("No shot data provided")

    # Determine coordinates
    if {"x1", "y1"}.issubset(df.columns):
        xs, ys = df["x1"].to_numpy(), df["y1"].to_numpy()
    elif {"x", "y"}.issubset(df.columns):
        xs, ys = df["x"].to_numpy(), df["y"].to_numpy()
    else:
        raise ValueError("Input must contain (x, y) or (x1, y1) columns.")

    # Weights
    if weights_col and weights_col in df.columns:
        weights = df[weights_col].to_numpy()
    else:
        weights = np.ones_like(xs, dtype=float)

    # Define bin edges matching pitch coordinates (0-120 x, 0-80 y)
    x_edges = np.linspace(0, 120, bins[0] + 1)
    y_edges = np.linspace(0, 80, bins[1] + 1)

    H, x_edges_out, y_edges_out = np.histogram2d(xs, ys, bins=[x_edges, y_edges], weights=weights)

    if normalize:
        maxv = H.max()
        H = H / (maxv if maxv > 0 else 1)

    # Prepare display values: apply scaling to emphasize low-intensity bins
    if scale == 'log':
        z_disp = np.log1p(H)
    elif scale == 'sqrt':
        z_disp = np.sqrt(H)
    else:
        z_disp = H.astype(float)

    # Make zero bins transparent if requested
    if zero_transparent:
        z_disp = np.where(H == 0, np.nan, z_disp)

    # Transpose so heatmap rows correspond to y axis
    z = z_disp.T

    x_centers = (x_edges_out[:-1] + x_edges_out[1:]) / 2
    y_centers = (y_edges_out[:-1] + y_edges_out[1:]) / 2

    fig = create_pitch()

    # Prepare colorbar ticks that show original counts while using scaled values for color mapping
    H_orig = H.copy()
    # z is already the transposed scaled display array
    z_for_plot = z

    # Build tick labels mapping: choose a handful of original-count tick positions
    H_max = float(H_orig.max())
    H_pos = H_orig[H_orig > 0]
    H_min_pos = float(H_pos.min()) if H_pos.size > 0 else 0.0
    n_ticks = 5
    original_ticks = np.linspace(H_min_pos, H_max, n_ticks)

    if scale == 'log':
        tickvals = np.log1p(original_ticks)
    elif scale == 'sqrt':
        tickvals = np.sqrt(original_ticks)
    else:
        tickvals = original_ticks

    # Format tick text nicely (integers if counts, else floats)
    def fmt(v):
        if float(v).is_integer():
            return str(int(v))
        return f"{v:.2f}"

    ticktext = [fmt(v) for v in original_ticks]

    # Build per-cell hover text (string) and use hoverinfo='text' for compatibility
    XX, YY = np.meshgrid(x_centers, y_centers)
    hover_texts = np.empty_like(H_orig.T, dtype=object)
    for i in range(hover_texts.shape[0]):
        for j in range(hover_texts.shape[1]):
            hover_texts[i, j] = f"Count: {fmt(H_orig.T[i, j])}<br>x: {XX[i, j]:.1f}<br>y: {YY[i, j]:.1f}"

    fig.add_trace(go.Heatmap(
        x=x_centers,
        y=y_centers,
        z=z_for_plot,
        text=hover_texts,
        hoverinfo='text',
        colorscale=colorscale,
        reversescale=False,
        opacity=0.85,
        zsmooth='best',
        colorbar=dict(title=(weights_col or 'Count'), tickmode='array', tickvals=tickvals, ticktext=ticktext),
    ))

    # Ensure heatmap traces render on top of pitch shapes/traces by reordering traces
    heatmaps = [t for t in fig.data if isinstance(t, go.Heatmap)]
    others = [t for t in fig.data if not isinstance(t, go.Heatmap)]
    fig.data = tuple(others + heatmaps)

    fig.update_layout(title="Shot Heatmap")
    fig.show()


def plot_shot_details(shot_data):
    """
    Plots player positions at the moment of a shot and highlights the shooter.

    Parameters:
    -----------
    shot : dict
        Shot dictionary containing:
        - 'end_location': [x, y, z]
        - 'freeze_frame': list of dicts with player positions
        - optionally 'statsbomb_xg', 'body_part', etc.
    """

    # ----------------------------------------------------------
    # Convert freeze_frame → DataFrame
    # ----------------------------------------------------------
    shot = shot_data.get('shot', [])
    ff = shot.get("freeze_frame", [])
    df = pd.DataFrame(ff)

    # Flatten nested columns
    df["x"] = df["location"].apply(lambda loc: loc[0])
    df["y"] = df["location"].apply(lambda loc: loc[1])
    df["player_name"] = df["player"].apply(lambda p: p["name"])
    df["position_name"] = df["position"].apply(lambda p: p["name"])
    df["team"] = df["teammate"].apply(lambda t: "Teammate" if t else "Opponent")

    # Hover text
    df["hover"] = df.apply(
        lambda row: f"Player: {row['player_name']}<br>"
                    f"Position: {row['position_name']}<br>"
                    f"Team: {row['team']}", axis=1
    )

    # Colors
    colors = df["teammate"].map({True: "blue", False: "red"})

    fig = create_pitch()

    # -----------------------------
    # Freeze frame players
    # -----------------------------
    fig.add_trace(go.Scatter(
        x=df["x"], y=df["y"],
        mode="markers+text",
        marker=dict(size=12, color=colors, line=dict(color="black", width=1)),
        # text=df["player_name"],
        textposition="top center",
        hovertext=df["hover"],
        hoverinfo="text",
        name="Players"
    ))

    # -----------------------------
    # Shooter marker
    # -----------------------------
    shooter_x, shooter_y = shot_data["location"][:2]
    shooter_name = shot_data.get('player', [])
    shooter_name = shooter_name.get("name", "")

    fig.add_trace(go.Scatter(
        x=[shooter_x], y=[shooter_y],
        mode="markers+text",
        marker=dict(size=16, color="gold", line=dict(color="black", width=3), symbol="star"),
        # text=["Shooter"],
        textposition="top center",
        hovertext=f"Shooter: {shooter_name}",
        hoverinfo="text",
        name="Shooter"
    ))

    # Layout
    fig.update_layout(
        title="Shot Detail with Freeze Frame"
    )

    fig.show()
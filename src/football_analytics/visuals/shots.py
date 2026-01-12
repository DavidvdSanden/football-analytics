import plotly.graph_objects as go
import numpy as np
import pandas as pd


def _get_pitch_theme_colors(pitch_theme):
    if pitch_theme == "dark":
        return "#1E1E1E", "#E6E6E6", False
    if pitch_theme == "green":
        return "#6BBF59", "white", False
    if pitch_theme == "transparent":
        return "rgba(0,0,0,0)", "#0B1C2D", True
    raise ValueError("pitch_theme must be one of: 'green', 'dark', 'transparent'")


def create_pitch(
    pitch_theme="green",
    show_axis_labels=True,
    x_range=None,
    y_range=None,
    lock_aspect=True,
    padding=5,
    layout_margin=None,
    fixed_size=True,
):
    """
    Returns a Plotly figure object with a football pitch drawn.

    Parameters
    ----------
    pitch_theme : {'green', 'dark', 'transparent'}
        Color theme for the pitch background.
    show_axis_labels : bool
        If False, hide axis tick labels and ticks.
    x_range, y_range : list[float] or None
        Custom axis ranges for zooming, e.g. [20, 100]. If None, defaults are used.
    lock_aspect : bool
        If True, lock the aspect ratio so 1 unit in x equals 1 unit in y.
    padding : float
        Padding (in pitch units) to add around the pitch when x_range/y_range are None.
    layout_margin : dict or None
        Plotly layout margin override. If None, defaults are used.
    fixed_size : bool
        If True, set an explicit width/height. If False, allow responsive sizing.
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

    pitch_color, line_color, is_transparent = _get_pitch_theme_colors(pitch_theme)

    # ----------------------------- Pitch background -----------------------------
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=pitch_length,
        y1=pitch_width,
        line=dict(color=line_color),
        fillcolor=pitch_color,
        layer="below",
    )

    # Pitch boundary & center line
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=pitch_length,
        y1=pitch_width,
        line=dict(color=line_color, width=2),
        layer="below",
    )
    fig.add_shape(
        type="line",
        x0=pitch_length / 2,
        y0=0,
        x1=pitch_length / 2,
        y1=pitch_width,
        line=dict(color=line_color, width=2),
        layer="below",
    )

    # Center circle & spot
    fig.add_shape(
        type="circle",
        x0=pitch_length / 2 - 10,
        y0=center_y - 10,
        x1=pitch_length / 2 + 10,
        y1=center_y + 10,
        line=dict(color=line_color, width=2),
        layer="below",
    )
    fig.add_shape(
        type="circle",
        x0=pitch_length / 2 - 0.3,
        y0=center_y - 0.3,
        x1=pitch_length / 2 + 0.3,
        y1=center_y + 0.3,
        line=dict(color=line_color, width=2),
        fillcolor=line_color,
        layer="below",
    )

    # Penalty boxes
    fig.add_shape(
        type="rect",
        x0=0,
        y0=center_y - pen_box_width / 2,
        x1=pen_box_depth,
        y1=center_y + pen_box_width / 2,
        line=dict(color=line_color, width=2),
        layer="below",
    )
    fig.add_shape(
        type="rect",
        x0=pitch_length - pen_box_depth,
        y0=center_y - pen_box_width / 2,
        x1=pitch_length,
        y1=center_y + pen_box_width / 2,
        line=dict(color=line_color, width=2),
        layer="below",
    )

    # Goalkeeper boxes
    fig.add_shape(
        type="rect",
        x0=0,
        y0=center_y - gk_box_width / 2,
        x1=gk_box_depth,
        y1=center_y + gk_box_width / 2,
        line=dict(color=line_color, width=2),
        layer="below",
    )
    fig.add_shape(
        type="rect",
        x0=pitch_length - gk_box_depth,
        y0=center_y - gk_box_width / 2,
        x1=pitch_length,
        y1=center_y + gk_box_width / 2,
        line=dict(color=line_color, width=2),
        layer="below",
    )

    # Goals
    fig.add_shape(
        type="rect",
        x0=-goal_depth,
        y0=center_y - goal_width / 2,
        x1=0,
        y1=center_y + goal_width / 2,
        line=dict(color=line_color, width=6),
        layer="below",
    )
    fig.add_shape(
        type="rect",
        x0=pitch_length,
        y0=center_y - goal_width / 2,
        x1=pitch_length + goal_depth,
        y1=center_y + goal_width / 2,
        line=dict(color=line_color, width=6),
        layer="below",
    )

    # Penalty spots
    fig.add_shape(
        type="circle",
        x0=penalty_spot - 0.3,
        y0=center_y - 0.3,
        x1=penalty_spot + 0.3,
        y1=center_y + 0.3,
        line=dict(color=line_color, width=2),
        fillcolor=line_color,
        layer="below",
    )
    fig.add_shape(
        type="circle",
        x0=pitch_length - penalty_spot - 0.3,
        y0=center_y - 0.3,
        x1=pitch_length - penalty_spot + 0.3,
        y1=center_y + 0.3,
        line=dict(color=line_color, width=2),
        fillcolor=line_color,
        layer="below",
    )

    # Penalty arcs
    d = pen_box_depth - penalty_spot
    angle = np.arccos(d / arc_radius)
    theta_left = np.linspace(-angle, angle, 75)
    theta_right = np.linspace(np.pi - angle, np.pi + angle, 75)

    # Penalty arcs drawn as shapes (SVG paths) so they can be placed below/above traces reliably
    xs_left = (penalty_spot + arc_radius * np.cos(theta_left)).tolist()
    ys_left = (center_y + arc_radius * np.sin(theta_left)).tolist()
    path_left = "M " + " L ".join(f"{x},{y}" for x, y in zip(xs_left, ys_left))
    fig.add_shape(
        type="path", path=path_left, line=dict(color=line_color, width=2), layer="below"
    )

    xs_right = (pitch_length - penalty_spot + arc_radius * np.cos(theta_right)).tolist()
    ys_right = (center_y + arc_radius * np.sin(theta_right)).tolist()
    path_right = "M " + " L ".join(f"{x},{y}" for x, y in zip(xs_right, ys_right))
    fig.add_shape(
        type="path",
        path=path_right,
        line=dict(color=line_color, width=2),
        layer="below",
    )

    # Layout
    default_x_range = [-padding, pitch_length + padding]
    default_y_range = [-padding, pitch_width + padding]
    xaxis_cfg = dict(
        range=x_range or default_x_range,
        showgrid=False,
        zeroline=False,
        showticklabels=show_axis_labels,
        ticks="outside" if show_axis_labels else "",
        fixedrange=False,
    )
    yaxis_cfg = dict(
        range=y_range or default_y_range,
        showgrid=False,
        zeroline=False,
        showticklabels=show_axis_labels,
        ticks="outside" if show_axis_labels else "",
        fixedrange=False,
    )
    if lock_aspect:
        yaxis_cfg["scaleanchor"] = "x"
        xaxis_cfg["constrain"] = "range"
        yaxis_cfg["constrain"] = "range"

    layout_kwargs = dict(
        xaxis=xaxis_cfg,
        yaxis=yaxis_cfg,
        plot_bgcolor=pitch_color,
        paper_bgcolor="rgba(0,0,0,0)" if is_transparent else pitch_color,
        showlegend=False,
        margin=layout_margin or dict(l=5, r=5, t=5, b=5),
    )
    if fixed_size:
        layout_kwargs.update(width=600, height=400)
    else:
        layout_kwargs.update(autosize=True)

    fig.update_layout(**layout_kwargs)

    return fig


def plot_shot_overview(
    shots,
    xg_column="xg",
    show=True,
    away_on_left=False,
    pitch_theme="green",
    show_axis_labels=True,
    home_team_id=None,
    away_team_id=None,
    team_id_column="attacking_team_id",
    pitch_padding=5,
    layout_margin=None,
    fixed_size=False,
    height_figure=300,
):
    """
    Overview of all shots on the pitch.
    Accepts DataFrame or list of dicts.
    If away_on_left is True, away team shots are mirrored to the left half.
    pitch_theme controls the pitch background color.
    """
    if isinstance(shots, list):
        shots = pd.DataFrame(shots)
    df = shots.copy()

    # Determine coordinates (prefer x1/y1 unless they are empty)
    if {"x1", "y1"}.issubset(df.columns):
        x_col, y_col = "x1", "y1"
        if df[x_col].isna().all() or df[y_col].isna().all():
            if {"x", "y"}.issubset(df.columns):
                x_col, y_col = "x", "y"
            else:
                raise ValueError(
                    "Input must contain non-empty (x1, y1) or (x, y) columns."
                )
    elif {"x", "y"}.issubset(df.columns):
        x_col, y_col = "x", "y"
    else:
        raise ValueError("Input must contain (x, y) or (x1, y1) columns.")

    xs, ys = df[x_col].copy(), df[y_col].copy()

    if away_on_left:
        if home_team_id is None or away_team_id is None:
            raise ValueError(
                "home_team_id and away_team_id are required when away_on_left=True."
            )
        if team_id_column not in df.columns:
            raise ValueError(
                f"Input must contain '{team_id_column}' when away_on_left=True."
            )
        pitch_length = 120
        away_mask = df[team_id_column] == away_team_id
        xs.loc[away_mask] = pitch_length - xs.loc[away_mask]

    colors = df.get(xg_column, pd.Series(np.zeros(len(df))))
    hover_texts = df.apply(
        lambda row: "<br>".join([f"{col}: {row[col]}" for col in df.columns]), axis=1
    )

    fig = create_pitch(
        pitch_theme=pitch_theme,
        show_axis_labels=show_axis_labels,
        padding=pitch_padding,
        layout_margin=layout_margin,
        fixed_size=fixed_size,
    )

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            marker=dict(
                size=10,
                color=colors,
                opacity=0.7,
                colorscale="Reds",
                cmin=0,
                cmax=1,
                showscale=True,
                line=dict(color="#3F4646", width=1),
                colorbar=dict(
                    title=dict(
                        text="Expected Goals (xG)",
                        font=dict(size=10),
                        side="bottom",
                    ),
                    orientation="h",
                    len=0.7,
                    thickness=12,
                    y=0.07,
                    yanchor="middle",
                    x=0.5,
                    xanchor="center",
                    bgcolor="rgba(0,0,0,0)",
                    outlinewidth=0,
                ),
            ),
            text=hover_texts,
            hoverinfo="text",
        )
    )

    if away_on_left:
        fig.add_annotation(
            text="\u2190 Away \u2003\u2003Home \u2192",
            xref="x",
            yref="y",
            x=60,
            y=76,
            showarrow=False,
            font=dict(size=12),
        )

    if show:
        fig.show()
        fig.update_layout(title="Overview of Shots")

    fig.update_layout(height=height_figure)

    return fig


def plot_shot_heatmap(
    shots,
    bins=(40, 30),
    weights_col=None,
    normalize=False,
    scale="sqrt",
    zero_transparent=True,
    colorscale="YlOrRd",
    pitch_theme="green",
    show_axis_labels=True,
):
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
    pitch_theme : {'green', 'dark', 'transparent'}
        Color theme for the pitch background.
    show_axis_labels : bool
        If False, hide axis tick labels and ticks.
    away_on_left : bool
        If True, mirror away-team shots to the left half of the pitch.
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

    H, x_edges_out, y_edges_out = np.histogram2d(
        xs, ys, bins=[x_edges, y_edges], weights=weights
    )

    if normalize:
        maxv = H.max()
        H = H / (maxv if maxv > 0 else 1)

    # Prepare display values: apply scaling to emphasize low-intensity bins
    if scale == "log":
        z_disp = np.log1p(H)
    elif scale == "sqrt":
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

    fig = create_pitch(pitch_theme=pitch_theme, show_axis_labels=show_axis_labels)

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

    if scale == "log":
        tickvals = np.log1p(original_ticks)
    elif scale == "sqrt":
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
            hover_texts[i, j] = (
                f"Count: {fmt(H_orig.T[i, j])}<br>x: {XX[i, j]:.1f}<br>y: {YY[i, j]:.1f}"
            )

    fig.add_trace(
        go.Heatmap(
            x=x_centers,
            y=y_centers,
            z=z_for_plot,
            text=hover_texts,
            hoverinfo="text",
            colorscale=colorscale,
            reversescale=False,
            opacity=0.85,
            zsmooth="best",
            colorbar=dict(
                title=(weights_col or "Count"),
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
            ),
        )
    )

    # Ensure heatmap traces render on top of pitch shapes/traces by reordering traces
    heatmaps = [t for t in fig.data if isinstance(t, go.Heatmap)]
    others = [t for t in fig.data if not isinstance(t, go.Heatmap)]
    fig.data = tuple(others + heatmaps)

    fig.update_layout(title="Shot Heatmap")
    fig.show()


def plot_shot_conversion_heatmap(
    shots,
    bins=(30, 20),
    goal_col=None,
    min_shots=5,
    zero_transparent=True,
    colorscale="YlOrRd",
    shrink=True,
    prior_shots=5.0,
    show_ci=True,
    ci_level=0.95,
    plot_3d=False,
    height="conversion",
    height_scale=0.5,
    pitch_theme="green",
    show_axis_labels=True,
):
    """
    Plot a heatmap showing the percentage of shots converted to goals per bin.

    Parameters
    ----------
    shots : DataFrame or list of dicts
        Shot records containing x/y coordinates (either `x1`/`y1` or `x`/`y`).
    bins : tuple(int, int)
        Number of bins in x and y directions.
    goal_col : str or None
        Column indicating goals. If None, function will try to auto-detect common columns
        like `is_goal` or `shot_outcome` (matching 'goal' case-insensitive).
    min_shots : int
        Minimum number of shots in a bin required to display a conversion value.
        Bins with fewer shots will be filtered out (shown as transparent). Default is 5.
    zero_transparent : bool
        If True, bins with no shots (or below `min_shots`) will be transparent.
    colorscale : str or list
        Plotly colorscale for the conversion heatmap.
    plot_3d : bool
        If True, render the conversion heatmap as a 3D surface with the pitch at z=0
        and bin values shown along the z-axis.
    height : {'conversion', 'shots'}
        Which value to use for the z-axis when `plot_3d` is True: 'conversion'
        (percent) or 'shots' (raw shot counts).
    height_scale : float
        Multiplier applied to the z values for better visual scaling in 3D.
    pitch_theme : {'green', 'dark', 'transparent'}
        Color theme for the pitch background.
    show_axis_labels : bool
        If False, hide axis tick labels and ticks.
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

    # Determine goal mask
    if goal_col and goal_col in df.columns:
        goals = df[goal_col]
    elif "is_goal" in df.columns:
        goals = df["is_goal"]
    elif "outcome" in df.columns:
        goals = df["outcome"].astype(str).str.lower().str.contains("goal")
    elif "result" in df.columns:
        goals = df["result"].astype(str).str.lower().str.contains("goal")
    else:
        raise ValueError("Could not detect goal column; pass `goal_col` explicitly.")

    goals_mask = goals.astype(bool).to_numpy().astype(float)

    # Define bin edges matching pitch coordinates (0-120 x, 0-80 y)
    x_edges = np.linspace(0, 120, bins[0] + 1)
    y_edges = np.linspace(0, 80, bins[1] + 1)

    shots_count, x_edges_out, y_edges_out = np.histogram2d(
        xs, ys, bins=[x_edges, y_edges]
    )
    goals_count, _, _ = np.histogram2d(
        xs, ys, bins=[x_edges, y_edges], weights=goals_mask
    )

    # Observed conversion rate (goals / shots) — compute safely to avoid divide warnings
    obs_conv = np.full_like(shots_count, np.nan, dtype=float)
    mask_shots = shots_count > 0
    if np.any(mask_shots):
        obs_conv[mask_shots] = goals_count[mask_shots] / shots_count[mask_shots]

    # Shrinkage (empirical Bayes / pseudocounts) to avoid extreme rates in tiny bins
    total_shots = shots_count.sum()
    total_goals = goals_count.sum()
    p0 = (total_goals / total_shots) if total_shots > 0 else 0.0
    if shrink:
        conv = (goals_count + prior_shots * p0) / (shots_count + prior_shots)
    else:
        conv = obs_conv

    # Mask bins with too few shots
    if min_shots > 1:
        conv = np.where(shots_count >= min_shots, conv, np.nan)

    # Prepare display: percentage 0-100
    conv_percent = conv * 100.0

    # Ensure bins with zero shots are always transparent
    conv_percent = np.where(shots_count == 0, np.nan, conv_percent)

    # Optionally keep other masked bins transparent
    if zero_transparent:
        conv_percent = np.where(np.isnan(conv_percent), np.nan, conv_percent)

    z = conv_percent.T

    # Compute Wilson CI for observed conversion (for hover) if requested
    if show_ci:
        try:
            from scipy.stats import norm

            zval = float(norm.ppf(1 - (1 - ci_level) / 2))
        except Exception:
            # Fallback z-values for common levels
            if abs(ci_level - 0.95) < 1e-6:
                zval = 1.96
            elif abs(ci_level - 0.90) < 1e-6:
                zval = 1.645
            else:
                zval = 1.96
        # compute phat safely (avoid dividing where shots_count == 0)
        phat = np.zeros_like(shots_count, dtype=float)
        mask = shots_count > 0
        if np.any(mask):
            phat[mask] = goals_count[mask] / shots_count[mask]
        n = shots_count
        # compute Wilson CI only where n > 0 to avoid invalid divides
        wilson_low = np.full_like(n, np.nan, dtype=float)
        wilson_high = np.full_like(n, np.nan, dtype=float)
        maskn = n > 0
        if np.any(maskn):
            den = 1 + (zval**2) / n[maskn]
            center = phat[maskn] + (zval**2) / (2 * n[maskn])
            adj = zval * np.sqrt(
                (phat[maskn] * (1 - phat[maskn]) + (zval**2) / (4 * n[maskn]))
                / n[maskn]
            )
            wilson_low[maskn] = (center - adj) / den
            wilson_high[maskn] = (center + adj) / den
    else:
        wilson_low = wilson_high = None

    x_centers = (x_edges_out[:-1] + x_edges_out[1:]) / 2
    y_centers = (y_edges_out[:-1] + y_edges_out[1:]) / 2

    # Build per-cell hover text (including shrunk conversion and CI if requested)
    XX, YY = np.meshgrid(x_centers, y_centers)
    hover_texts = np.empty_like(z, dtype=object)
    for i in range(hover_texts.shape[0]):
        for j in range(hover_texts.shape[1]):
            shots_n = int(shots_count.T[i, j])
            goals_n = int(goals_count.T[i, j])
            pct = z[i, j]
            # indicate filtered bins explicitly when shots < min_shots
            if shots_n < int(min_shots):
                pct_text = f"<{int(min_shots)} shots (filtered)"
                if show_ci:
                    ci_text = "N/A"
                hover_line = (
                    f"Shots: {shots_n}<br>Goals: {goals_n}<br>Conversion: {pct_text}"
                )
                if show_ci and wilson_low is not None:
                    hover_line += f"<br>{int(ci_level*100)}% CI: {ci_text}"
                hover_texts[i, j] = hover_line
                continue

            pct_text = "N/A" if np.isnan(pct) else f"{pct:.1f}%"
            if show_ci and wilson_low is not None:
                low = wilson_low.T[i, j] * 100.0
                high = wilson_high.T[i, j] * 100.0
                ci_text = "N/A" if np.isnan(low) else f"{low:.1f}%–{high:.1f}%"
                hover_texts[i, j] = (
                    f"Shots: {shots_n}<br>Goals: {goals_n}<br>Conversion: {pct_text}<br>{int(ci_level*100)}% CI: {ci_text}"
                )
            else:
                hover_texts[i, j] = (
                    f"Shots: {shots_n}<br>Goals: {goals_n}<br>Conversion: {pct_text}"
                )

    # If 3D requested, render as 3D surface(s)
    if plot_3d:
        pitch_color, line_color, is_transparent = _get_pitch_theme_colors(pitch_theme)
        # X, Y grids for surfaces
        X, Y = np.meshgrid(x_centers, y_centers)

        # Choose z-values for height
        if height == "shots":
            Z = shots_count.T.astype(float)
            z_title = "Shots"
        else:
            # use conversion percent (may contain nan for filtered bins)
            Z = z.copy()
            z_title = "Conversion (%)"

        # apply scaling
        Z_scaled = Z * float(height_scale)

        fig3d = go.Figure()

        # base pitch plane at z=0
        base_z = np.zeros_like(Z_scaled)
        fig3d.add_trace(
            go.Surface(
                x=X,
                y=Y,
                z=base_z,
                surfacecolor=np.zeros_like(base_z),
                colorscale=[[0, pitch_color], [1, pitch_color]],
                showscale=False,
                opacity=0.0 if is_transparent else 0.9,
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Add 3D line traces to replicate pitch markings (match create_pitch styling)
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

        z0 = 0.0

        # Utility to add a 3d line
        def add_line(xs, ys, width=4, name=None):
            fig3d.add_trace(
                go.Scatter3d(
                    x=xs,
                    y=ys,
                    z=[z0] * len(xs),
                    mode="lines",
                    line=dict(color=line_color, width=width),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        # Pitch boundary
        xb = [0, pitch_length, pitch_length, 0, 0]
        yb = [0, 0, pitch_width, pitch_width, 0]
        add_line(xb, yb, width=6)

        # Center line
        add_line([pitch_length / 2, pitch_length / 2], [0, pitch_width], width=4)

        # Center circle
        theta = np.linspace(0, 2 * np.pi, 120)
        xc = (pitch_length / 2) + 10 * np.cos(theta)
        yc = center_y + 10 * np.sin(theta)
        add_line(xc.tolist(), yc.tolist(), width=4)

        # Penalty boxes
        left_pen = [0, pen_box_depth, pen_box_depth, 0, 0]
        left_pen_y = [
            center_y - pen_box_width / 2,
            center_y - pen_box_width / 2,
            center_y + pen_box_width / 2,
            center_y + pen_box_width / 2,
            center_y - pen_box_width / 2,
        ]
        add_line(left_pen, left_pen_y, width=4)
        right_pen = [
            pitch_length,
            pitch_length - pen_box_depth,
            pitch_length - pen_box_depth,
            pitch_length,
            pitch_length,
        ]
        right_pen_y = left_pen_y
        add_line(right_pen, right_pen_y, width=4)

        # Goalkeeper boxes
        left_gk = [0, gk_box_depth, gk_box_depth, 0, 0]
        left_gk_y = [
            center_y - gk_box_width / 2,
            center_y - gk_box_width / 2,
            center_y + gk_box_width / 2,
            center_y + gk_box_width / 2,
            center_y - gk_box_width / 2,
        ]
        add_line(left_gk, left_gk_y, width=4)
        right_gk = [
            pitch_length,
            pitch_length - gk_box_depth,
            pitch_length - gk_box_depth,
            pitch_length,
            pitch_length,
        ]
        add_line(right_gk, left_gk_y, width=4)

        # Goals (thicker)
        add_line(
            [-goal_depth, 0],
            [center_y - goal_width / 2, center_y - goal_width / 2],
            width=8,
        )
        add_line(
            [-goal_depth, 0],
            [center_y + goal_width / 2, center_y + goal_width / 2],
            width=8,
        )
        add_line(
            [pitch_length, pitch_length + goal_depth],
            [center_y - goal_width / 2, center_y - goal_width / 2],
            width=8,
        )
        add_line(
            [pitch_length, pitch_length + goal_depth],
            [center_y + goal_width / 2, center_y + goal_width / 2],
            width=8,
        )

        # Penalty spots
        fig3d.add_trace(
            go.Scatter3d(
                x=[penalty_spot],
                y=[center_y],
                z=[z0],
                mode="markers",
                marker=dict(size=4, color=line_color),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig3d.add_trace(
            go.Scatter3d(
                x=[pitch_length - penalty_spot],
                y=[center_y],
                z=[z0],
                mode="markers",
                marker=dict(size=4, color=line_color),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Penalty arcs (left and right)
        d = pen_box_depth - penalty_spot
        angle = np.arccos(d / arc_radius)
        theta_left = np.linspace(-angle, angle, 75)
        theta_right = np.linspace(np.pi - angle, np.pi + angle, 75)
        xs_left = (penalty_spot + arc_radius * np.cos(theta_left)).tolist()
        ys_left = (center_y + arc_radius * np.sin(theta_left)).tolist()
        add_line(xs_left, ys_left, width=4)
        xs_right = (
            pitch_length - penalty_spot + arc_radius * np.cos(theta_right)
        ).tolist()
        ys_right = (center_y + arc_radius * np.sin(theta_right)).tolist()
        add_line(xs_right, ys_right, width=4)

        # conversion / shots surface (holes where NaN)
        fig3d.add_trace(
            go.Surface(
                x=X,
                y=Y,
                z=Z_scaled,
                surfacecolor=Z,  # color by original values (percent or counts)
                colorscale=colorscale,
                cmin=np.nanmin(Z) if np.isfinite(np.nanmin(Z)) else 0,
                cmax=np.nanmax(Z) if np.isfinite(np.nanmax(Z)) else 1,
                colorbar=dict(
                    title=z_title,
                    ticksuffix="%" if z_title.startswith("Conversion") else "",
                ),
                hovertemplate="%{x:.1f}, %{y:.1f}<br>"
                + z_title
                + ": %{customdata[0]:.2f}<br>Shots: %{customdata[1]:.0f}",
                customdata=np.dstack((np.nan_to_num(Z, nan=np.nan), shots_count.T)),
                showscale=True,
                opacity=0.9,
                showlegend=False,
            )
        )

        # camera & layout
        max_z = np.nanmax(Z_scaled)
        fig3d.update_layout(
            title="Shot Conversion Heatmap (3D)",
            scene=dict(
                xaxis=dict(title="X", range=[0, 120]),
                yaxis=dict(title="Y", range=[0, 80]),
                zaxis=dict(
                    title=z_title,
                    range=[0, float(max_z * 1.2) if np.isfinite(max_z) else 1],
                ),
                aspectmode="auto",
            ),
            width=1200,
            height=800,
        )

        return fig3d

    # 2D heatmap (existing behavior)
    fig = create_pitch(pitch_theme=pitch_theme, show_axis_labels=show_axis_labels)

    fig.add_trace(
        go.Heatmap(
            x=x_centers,
            y=y_centers,
            z=z,
            text=hover_texts,
            hoverinfo="text",
            colorscale=colorscale,
            reversescale=False,
            opacity=0.85,
            zsmooth="best",
            colorbar=dict(title="Conversion (%)", ticksuffix="%"),
        )
    )

    # Ensure heatmap traces render on top
    heatmaps = [t for t in fig.data if isinstance(t, go.Heatmap)]
    others = [t for t in fig.data if not isinstance(t, go.Heatmap)]
    fig.data = tuple(others + heatmaps)

    fig.update_layout(title="Shot Conversion Heatmap")
    return fig


def plot_shot_details(
    shot_data,
    show=True,
    pitch_theme="green",
    show_axis_labels=True,
    title=None,
    fixed_size=False,
    pitch_padding=5,
    away_on_left=False,
    home_team_id=None,
    away_team_id=None,
    height_figure=300,
):
    """
    Plots player positions at the moment of a shot and highlights the shooter.

    Parameters:
    -----------
    shot : dict
        Shot dictionary containing:
        - 'end_location': [x, y, z]
        - 'freeze_frame': list of dicts with player positions
        - optionally 'statsbomb_xg', 'body_part', etc.
    pitch_theme : {'green', 'dark', 'transparent'}
        Color theme for the pitch background.
    show_axis_labels : bool
        If False, hide axis tick labels and ticks.
    pitch_padding : float
        Padding (in pitch units) to add around the pitch.
    """

    # ----------------------------------------------------------
    # Convert freeze_frame → DataFrame
    # ----------------------------------------------------------
    shot = shot_data.get("shot", {})
    if isinstance(shot, list):
        shot = shot[0] if shot else {}
    if not isinstance(shot, dict):
        shot = {}
    ff = shot.get("freeze_frame", [])
    if not ff:
        fig = create_pitch(
            pitch_theme=pitch_theme,
            show_axis_labels=show_axis_labels,
            fixed_size=fixed_size,
            padding=pitch_padding,
        )
        if title:
            fig.update_layout(title)
        if show:
            fig.show()
        return fig
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
        f"Team: {row['team']}",
        axis=1,
    )

    # Colors
    colors = df["teammate"].map({True: "blue", False: "red"})

    # Identify goalkeeper(s) and give them a distinct shape/linewidth to stand out
    df["is_opposition_goalkeeper"] = df["position_name"].astype(
        str
    ).str.lower().str.contains("goal") & (~df["teammate"])
    # Marker properties per-point (Plotly accepts lists for per-point marker attributes)
    marker_colors = np.where(df["is_opposition_goalkeeper"], "red", colors).tolist()
    marker_symbols = np.where(
        df["is_opposition_goalkeeper"], "diamond", "circle"
    ).tolist()
    marker_sizes = np.where(df["is_opposition_goalkeeper"], 14, 12).tolist()
    marker_line_widths = np.where(df["is_opposition_goalkeeper"], 3, 1).tolist()

    shot_team_id = None
    if away_on_left:
        if home_team_id is None or away_team_id is None:
            raise ValueError(
                "home_team_id and away_team_id are required when away_on_left=True."
            )
        team = shot_data.get("team", {})
        shot_team_id = team.get("id") if isinstance(team, dict) else None
        if shot_team_id is None:
            shot_team_id = shot_data.get("team_id")
        if shot_team_id == away_team_id:
            pitch_length = 120
            df["x"] = pitch_length - df["x"]

    fig = create_pitch(
        pitch_theme=pitch_theme,
        show_axis_labels=show_axis_labels,
        fixed_size=fixed_size,
        padding=pitch_padding,
    )

    if away_on_left:
        fig.add_annotation(
            text="\u2190 Away \u2003\u2003Home \u2192",
            xref="x",
            yref="y",
            x=60,
            y=76,
            showarrow=False,
            font=dict(size=12),
        )

    # -----------------------------
    # Freeze frame players
    # -----------------------------
    fig.add_trace(
        go.Scatter(
            x=df["x"],
            y=df["y"],
            mode="markers+text",
            marker=dict(
                size=marker_sizes,
                color=marker_colors,
                symbol=marker_symbols,
                line=dict(color="black", width=marker_line_widths),
            ),
            # text=df["player_name"],
            textposition="top center",
            hovertext=df["hover"],
            hoverinfo="text",
            name="Players",
        )
    )

    # -----------------------------
    # Shooter marker
    # -----------------------------
    shooter_x, shooter_y = shot_data["location"][:2]
    if away_on_left and shot_team_id == away_team_id:
        pitch_length = 120
        shooter_x = pitch_length - shooter_x
    shooter_name = shot_data.get("player", [])
    shooter_name = shooter_name.get("name", "")

    fig.add_trace(
        go.Scatter(
            x=[shooter_x],
            y=[shooter_y],
            mode="markers+text",
            marker=dict(
                size=16, color="gold", line=dict(color="black", width=3), symbol="star"
            ),
            # text=["Shooter"],
            textposition="top center",
            hovertext=f"Shooter: {shooter_name}",
            hoverinfo="text",
            name="Shooter",
        )
    )

    # Layout
    if title:
        fig.update_layout(title)

    if show:
        fig.show()

    fig.update_layout(height=height_figure)
    return fig


def plot_xg_progression(
    shots: pd.DataFrame,
    home_team_id: int,
    away_team_id: int,
    home_team_name: str = "Home",
    away_team_name: str = "Away",
    xg_col: str = "statsbomb_xg",
    outcome_col: str = "outcome",
    goal_value: str = "Goal",
    show: bool = True,
    height_figure: int = 400,
):
    df = shots.copy()

    # 1. Continuous match time
    df["match_time"] = df["minute"] + df["second"] / 60

    # 2. Split teams
    home = df[df["attacking_team_id"] == home_team_id].copy()
    away = df[df["attacking_team_id"] == away_team_id].copy()

    # 3. Sort
    home = home.sort_values("match_time")
    away = away.sort_values("match_time")

    # 4. Cumulative xG
    home["cum_xg"] = home[xg_col].cumsum()
    away["cum_xg"] = away[xg_col].cumsum()

    # 5. Determine common end time
    last_shot_time = df["match_time"].max()
    end_time = max(90, last_shot_time)

    # 6. Extend for step plotting
    def extend_to_end(df_team):
        if df_team.empty:
            return pd.DataFrame({"match_time": [0, end_time], "cum_xg": [0, 0]})

        last_row = df_team.iloc[-1]
        return pd.concat(
            [
                pd.DataFrame({"match_time": [0], "cum_xg": [0]}),
                df_team[["match_time", "cum_xg"]],
                pd.DataFrame(
                    {
                        "match_time": [end_time],
                        "cum_xg": [last_row["cum_xg"]],
                    }
                ),
            ],
            ignore_index=True,
        )

    home_plot = extend_to_end(home)
    away_plot = extend_to_end(away)

    # 7. Plot step lines
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=home_plot["match_time"],
            y=home_plot["cum_xg"],
            mode="lines",
            name=home_team_name,
            line=dict(width=3, shape="hv"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=away_plot["match_time"],
            y=away_plot["cum_xg"],
            mode="lines",
            name=away_team_name,
            line=dict(width=3, shape="hv", dash="dash"),
        )
    )

    # 8. Add goal icons
    def add_goal_icons(df_team):
        goals = df_team[df_team[outcome_col] == goal_value]
        for _, row in goals.iterrows():
            fig.add_annotation(
                x=row["match_time"],
                y=row["cum_xg"],
                text="⚽",
                showarrow=False,
                yshift=8,
                font=dict(size=16),
            )

    add_goal_icons(home)
    add_goal_icons(away)

    # 9. Layout
    fig.update_layout(
        xaxis_title="Match time (minutes)",
        yaxis_title="Cumulative xG",
        hovermode="x unified",
        template="plotly_white",
        height=height_figure,
        margin=dict(l=5, r=5, t=5, b=5),
    )

    fig.add_vline(x=45, line_dash="dot", opacity=0.4)

    if show:
        fig.show()
    return fig

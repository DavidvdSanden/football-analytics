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

def plot_shot_overview(shots, xg_column="xg", show=True):
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

    colors = df.get(xg_column, pd.Series(np.zeros(len(df))))
    hover_texts = df.apply(lambda row: "<br>".join([f"{col}: {row[col]}" for col in df.columns]), axis=1)

    fig = create_pitch()

    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers",
        marker=dict(size=10, color=colors, opacity=0.7, colorscale="Reds", cmin=0, cmax=1, line=dict(color="#3F4646", width=1), showscale=True),
        text=hover_texts, hoverinfo="text"
    ))

    fig.update_layout(title="Overview of Shots")
    if show:
        fig.show()
    return fig


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


def plot_shot_conversion_heatmap(shots, bins=(30, 20), goal_col=None, min_shots=5,
                                 zero_transparent=True, colorscale='YlOrRd',
                                 shrink=True, prior_shots=5.0, show_ci=True, ci_level=0.95,
                                 plot_3d=False, height='conversion', height_scale=0.5):
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

    shots_count, x_edges_out, y_edges_out = np.histogram2d(xs, ys, bins=[x_edges, y_edges])
    goals_count, _, _ = np.histogram2d(xs, ys, bins=[x_edges, y_edges], weights=goals_mask)

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
            den = 1 + (zval ** 2) / n[maskn]
            center = phat[maskn] + (zval ** 2) / (2 * n[maskn])
            adj = zval * np.sqrt((phat[maskn] * (1 - phat[maskn]) + (zval ** 2) / (4 * n[maskn])) / n[maskn])
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
                hover_line = f"Shots: {shots_n}<br>Goals: {goals_n}<br>Conversion: {pct_text}"
                if show_ci and wilson_low is not None:
                    hover_line += f"<br>{int(ci_level*100)}% CI: {ci_text}"
                hover_texts[i, j] = hover_line
                continue

            pct_text = "N/A" if np.isnan(pct) else f"{pct:.1f}%"
            if show_ci and wilson_low is not None:
                low = wilson_low.T[i, j] * 100.0
                high = wilson_high.T[i, j] * 100.0
                ci_text = "N/A" if np.isnan(low) else f"{low:.1f}%–{high:.1f}%"
                hover_texts[i, j] = f"Shots: {shots_n}<br>Goals: {goals_n}<br>Conversion: {pct_text}<br>{int(ci_level*100)}% CI: {ci_text}"
            else:
                hover_texts[i, j] = f"Shots: {shots_n}<br>Goals: {goals_n}<br>Conversion: {pct_text}"

    # If 3D requested, render as 3D surface(s)
    if plot_3d:
        # X, Y grids for surfaces
        X, Y = np.meshgrid(x_centers, y_centers)

        # Choose z-values for height
        if height == 'shots':
            Z = shots_count.T.astype(float)
            z_title = 'Shots'
        else:
            # use conversion percent (may contain nan for filtered bins)
            Z = z.copy()
            z_title = 'Conversion (%)'

        # apply scaling
        Z_scaled = Z * float(height_scale)

        fig3d = go.Figure()

        # base pitch plane at z=0
        base_z = np.zeros_like(Z_scaled)
        fig3d.add_trace(go.Surface(
            x=X, y=Y, z=base_z,
            surfacecolor=np.zeros_like(base_z),
            colorscale=[[0, '#6BBF59'], [1, '#6BBF59']],
            showscale=False,
            opacity=0.9,
            hoverinfo='skip',
            showlegend=False
        ))

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
            fig3d.add_trace(go.Scatter3d(x=xs, y=ys, z=[z0] * len(xs), mode='lines',
                                        line=dict(color='white', width=width), hoverinfo='skip', showlegend=False))

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
        left_pen_y = [center_y - pen_box_width / 2, center_y - pen_box_width / 2,
                      center_y + pen_box_width / 2, center_y + pen_box_width / 2,
                      center_y - pen_box_width / 2]
        add_line(left_pen, left_pen_y, width=4)
        right_pen = [pitch_length, pitch_length - pen_box_depth, pitch_length - pen_box_depth, pitch_length, pitch_length]
        right_pen_y = left_pen_y
        add_line(right_pen, right_pen_y, width=4)

        # Goalkeeper boxes
        left_gk = [0, gk_box_depth, gk_box_depth, 0, 0]
        left_gk_y = [center_y - gk_box_width / 2, center_y - gk_box_width / 2,
                     center_y + gk_box_width / 2, center_y + gk_box_width / 2,
                     center_y - gk_box_width / 2]
        add_line(left_gk, left_gk_y, width=4)
        right_gk = [pitch_length, pitch_length - gk_box_depth, pitch_length - gk_box_depth, pitch_length, pitch_length]
        add_line(right_gk, left_gk_y, width=4)

        # Goals (thicker)
        add_line([-goal_depth, 0], [center_y - goal_width / 2, center_y - goal_width / 2], width=8)
        add_line([-goal_depth, 0], [center_y + goal_width / 2, center_y + goal_width / 2], width=8)
        add_line([pitch_length, pitch_length + goal_depth], [center_y - goal_width / 2, center_y - goal_width / 2], width=8)
        add_line([pitch_length, pitch_length + goal_depth], [center_y + goal_width / 2, center_y + goal_width / 2], width=8)

        # Penalty spots
        fig3d.add_trace(go.Scatter3d(x=[penalty_spot], y=[center_y], z=[z0], mode='markers',
                         marker=dict(size=4, color='white'), hoverinfo='skip', showlegend=False))
        fig3d.add_trace(go.Scatter3d(x=[pitch_length - penalty_spot], y=[center_y], z=[z0], mode='markers',
                         marker=dict(size=4, color='white'), hoverinfo='skip', showlegend=False))

        # Penalty arcs (left and right)
        d = pen_box_depth - penalty_spot
        angle = np.arccos(d / arc_radius)
        theta_left = np.linspace(-angle, angle, 75)
        theta_right = np.linspace(np.pi - angle, np.pi + angle, 75)
        xs_left = (penalty_spot + arc_radius * np.cos(theta_left)).tolist()
        ys_left = (center_y + arc_radius * np.sin(theta_left)).tolist()
        add_line(xs_left, ys_left, width=4)
        xs_right = (pitch_length - penalty_spot + arc_radius * np.cos(theta_right)).tolist()
        ys_right = (center_y + arc_radius * np.sin(theta_right)).tolist()
        add_line(xs_right, ys_right, width=4)

        # conversion / shots surface (holes where NaN)
        fig3d.add_trace(go.Surface(
            x=X, y=Y, z=Z_scaled,
            surfacecolor=Z,  # color by original values (percent or counts)
            colorscale=colorscale,
            cmin=np.nanmin(Z) if np.isfinite(np.nanmin(Z)) else 0,
            cmax=np.nanmax(Z) if np.isfinite(np.nanmax(Z)) else 1,
            colorbar=dict(title=z_title, ticksuffix='%' if z_title.startswith('Conversion') else ''),
            hovertemplate='%{x:.1f}, %{y:.1f}<br>' + z_title + ': %{customdata[0]:.2f}<br>Shots: %{customdata[1]:.0f}',
            customdata=np.dstack((np.nan_to_num(Z, nan=np.nan), shots_count.T)),
            showscale=True,
            opacity=0.9,
            showlegend=False
        ))

        # camera & layout
        max_z = np.nanmax(Z_scaled)
        fig3d.update_layout(
            title='Shot Conversion Heatmap (3D)',
            scene=dict(
                xaxis=dict(title='X', range=[0, 120]),
                yaxis=dict(title='Y', range=[0, 80]),
                zaxis=dict(title=z_title, range=[0, float(max_z * 1.2) if np.isfinite(max_z) else 1]),
                aspectmode='auto'
            ),
            width=1200, height=800
        )

        return fig3d

    # 2D heatmap (existing behavior)
    fig = create_pitch()

    fig.add_trace(go.Heatmap(
        x=x_centers,
        y=y_centers,
        z=z,
        text=hover_texts,
        hoverinfo='text',
        colorscale=colorscale,
        reversescale=False,
        opacity=0.85,
        zsmooth='best',
        colorbar=dict(title='Conversion (%)', ticksuffix='%')
    ))

    # Ensure heatmap traces render on top
    heatmaps = [t for t in fig.data if isinstance(t, go.Heatmap)]
    others = [t for t in fig.data if not isinstance(t, go.Heatmap)]
    fig.data = tuple(others + heatmaps)

    fig.update_layout(title="Shot Conversion Heatmap")
    return fig


def plot_shot_details(shot_data, show=True):
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
    shot = shot_data.get('shot', {})
    if isinstance(shot, list):
        shot = shot[0] if shot else {}
    if not isinstance(shot, dict):
        shot = {}
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

    # Identify goalkeeper(s) and give them a distinct shape/linewidth to stand out
    df["is_opposition_goalkeeper"] = df["position_name"].astype(str).str.lower().str.contains("goal") & (~df["teammate"])
    # Marker properties per-point (Plotly accepts lists for per-point marker attributes)
    marker_colors = np.where(df["is_opposition_goalkeeper"], "red", colors).tolist()
    marker_symbols = np.where(df["is_opposition_goalkeeper"], "diamond", "circle").tolist()
    marker_sizes = np.where(df["is_opposition_goalkeeper"], 14, 12).tolist()
    marker_line_widths = np.where(df["is_opposition_goalkeeper"], 3, 1).tolist()

    fig = create_pitch()

    # -----------------------------
    # Freeze frame players
    # -----------------------------
    fig.add_trace(go.Scatter(
        x=df["x"], y=df["y"],
        mode="markers+text",
        marker=dict(size=marker_sizes, color=marker_colors, symbol=marker_symbols,
                    line=dict(color="black", width=marker_line_widths)),
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

    if show:
        fig.show()
    return fig

from __future__ import annotations

from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import streamlit as st
import torch
import joblib

from football_analytics.data_processing.preprocessing import extract_shot_features


INHOUSE_FEATURE_COLUMNS = [
    "distance_to_goal",
    "angle_to_goal_deg",
    "keeper_distance",
    "min_defender_distance",
    "num_teammates_in_box",
    "is_penalty",
    "num_def_in_shot_triangle",
    "frac_goal_uncovered",
    "keeper_is_in_shot_triangle",
    "is_with_feet",
    "under_pressure",
]

_BOOL_FEATURE_COLUMNS = {
    "is_penalty",
    "keeper_is_in_shot_triangle",
    "is_with_feet",
    "under_pressure",
}


class XGModel(torch.nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 16),
            torch.nn.ReLU(),
            torch.nn.Linear(16, 8),
            torch.nn.ReLU(),
            torch.nn.Linear(8, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _default_model_dir() -> Path:
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "xg_model" / "nn_models"


def _safe_parse_json(payload):
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return None
    if isinstance(payload, float) and np.isnan(payload):
        return None
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
    return None


def _coerce_bool(series: pd.Series) -> pd.Series:
    if series is None:
        return pd.Series(dtype=int)
    if series.dtype == bool:
        return series.astype(int)
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).astype(int)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(("true", "1", "yes", "y"))
        .astype(int)
    )


def list_inhouse_models(model_dir: Path | None = None):
    model_dir = model_dir or _default_model_dir()
    if not model_dir.exists():
        return []

    pattern = re.compile(r"nn_xg_model_(\d{8}_\d{6})\.pth$")
    models = []

    for model_path in model_dir.glob("nn_xg_model_*.pth"):
        match = pattern.match(model_path.name)
        timestamp = match.group(1) if match else model_path.stem
        scaler_path = model_dir / f"scaler_{timestamp}.save"
        if not scaler_path.exists():
            continue
        label = f"NN {timestamp}"
        models.append(
            {
                "label": label,
                "timestamp": timestamp,
                "model_path": model_path,
                "scaler_path": scaler_path,
            }
        )

    return sorted(models, key=lambda m: m["timestamp"], reverse=True)


def _fill_missing_features_from_json(df: pd.DataFrame) -> pd.DataFrame:
    if "full_json" not in df.columns:
        return df

    missing_mask = df[INHOUSE_FEATURE_COLUMNS].isna().any(axis=1)
    if not missing_mask.any():
        return df

    for idx, row in df.loc[missing_mask].iterrows():
        event = _safe_parse_json(row.get("full_json"))
        if not event:
            continue
        try:
            features = extract_shot_features(event, match_id=row.get("match_id"))
        except Exception:
            continue

        for col in INHOUSE_FEATURE_COLUMNS:
            if col in features and pd.isna(df.at[idx, col]):
                df.at[idx, col] = features[col]

        for extra_col in ("body_part", "shot_type", "under_pressure"):
            if extra_col not in df.columns:
                df[extra_col] = np.nan
            if extra_col in features and pd.isna(df.at[idx, extra_col]):
                df.at[idx, extra_col] = features[extra_col]

    return df


def prepare_inhouse_features(shots_df: pd.DataFrame):
    df = shots_df.copy()
    warnings = []

    for col in INHOUSE_FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    df = _fill_missing_features_from_json(df)

    if "is_penalty" not in shots_df.columns or df["is_penalty"].isna().any():
        if "shot_type" in df.columns:
            df["is_penalty"] = df["shot_type"].fillna("").eq("Penalty").astype(int)
        else:
            df["is_penalty"] = 0

    if "is_with_feet" not in shots_df.columns or df["is_with_feet"].isna().any():
        if "body_part" in df.columns:
            df["is_with_feet"] = (
                df["body_part"]
                .fillna("")
                .isin(("Right Foot", "Left Foot"))
                .astype(int)
            )
        else:
            df["is_with_feet"] = 0

    for col in _BOOL_FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0
        df[col] = _coerce_bool(df[col])

    if df[INHOUSE_FEATURE_COLUMNS].isna().any().any():
        warnings.append("Missing in-house xG features were filled with 0.")
        df[INHOUSE_FEATURE_COLUMNS] = df[INHOUSE_FEATURE_COLUMNS].fillna(0)

    return df, warnings


@st.cache_resource(show_spinner=False)
def _load_model_and_scaler(model_path: str, scaler_path: str):
    model = XGModel(input_dim=len(INHOUSE_FEATURE_COLUMNS))
    state = torch.load(model_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    scaler = joblib.load(scaler_path)
    return model, scaler


def infer_inhouse_xg(shots_df: pd.DataFrame, model_path: Path, scaler_path: Path):
    if shots_df.empty:
        df = shots_df.copy()
        df["inhouse_xg"] = np.array([], dtype=float)
        return df, []

    df, warnings = prepare_inhouse_features(shots_df)
    model, scaler = _load_model_and_scaler(str(model_path), str(scaler_path))

    features = df[INHOUSE_FEATURE_COLUMNS].astype(float).to_numpy()
    scaled = scaler.transform(features)

    with torch.no_grad():
        logits = model(torch.tensor(scaled, dtype=torch.float32))
        probs = torch.sigmoid(logits).numpy().flatten()

    df = df.copy()
    df["inhouse_xg"] = probs
    return df, warnings


def apply_xg_model_selection(shots_df: pd.DataFrame, model_dir: Path | None = None):
    st.sidebar.subheader("xG Model")
    use_inhouse = st.sidebar.checkbox(
        "Use in-house xG model", value=st.session_state.get("use_inhouse_xg", False)
    )
    st.session_state["use_inhouse_xg"] = use_inhouse

    if not use_inhouse:
        return shots_df, "statsbomb_xg", "StatsBomb xG"

    models = list_inhouse_models(model_dir)
    if not models:
        st.warning("No in-house models found. Falling back to StatsBomb xG.")
        return shots_df, "statsbomb_xg", "StatsBomb xG"

    labels = [m["label"] for m in models]
    stored_label = st.session_state.get("selected_inhouse_xg_label")
    if stored_label in labels:
        label_index = labels.index(stored_label)
    else:
        label_index = 0
    selected_label = st.sidebar.selectbox(
        "In-house model", labels, index=label_index
    )
    st.session_state["selected_inhouse_xg_label"] = selected_label
    selected = models[labels.index(selected_label)]

    try:
        updated_df, warnings = infer_inhouse_xg(
            shots_df, selected["model_path"], selected["scaler_path"]
        )
    except Exception as exc:
        st.warning(f"In-house xG failed ({exc}). Falling back to StatsBomb xG.")
        return shots_df, "statsbomb_xg", "StatsBomb xG"

    for message in warnings:
        st.warning(message)

    return updated_df, "inhouse_xg", selected_label

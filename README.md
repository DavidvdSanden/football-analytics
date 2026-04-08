# Football Analytics

End-to-end football analytics workspace: data ingestion and processing, xG modeling,
and Streamlit dashboards for match and shot analysis.

![App Overview](app_overview.gif)

## Highlights

- Data processing utilities in `src/football_analytics/data_processing`
- xG model notebooks and saved neural model artifacts in `models/xg_model/`
- Streamlit dashboards for teams, players, and match-level shot analysis
- Shot visualization and geometry helpers in `src/football_analytics/visuals` and `src/football_analytics/utils/shot_geometry.py`

## Tech Stack

- Data and analysis: pandas, numpy, scikit-learn
- Modeling: PyTorch
- App and visuals: Streamlit, Plotly, Matplotlib, mplsoccer
- Data access: Supabase client and PostgreSQL (psycopg2)

## Quick start

Requirements:
- Python 3.10+

```powershell
git clone <repo>
cd <repo>
python bootstrap.py 
```

The bootstrap script creates `.venv`, installs dependencies from `requirements.txt`,
and installs the project in editable mode.

Activate the environment:

```powershell
.\.venv\Scripts\activate
```

```bash
source .venv/bin/activate
```

## Run the Streamlit app

```powershell
streamlit run apps\streamlit\Home.py
```

## What Works Today

- Home page with quick links to app sections
- Teams page for browsing unique clubs from the configured database table
- Players page with name search and competition/season/team filtering
- Match Details page with match selection, shot data exploration, and xG-related views

## Configuration

Set your database backend in `.env`:

```env
DB_BACKEND=supabase
```

Supported values:
- `supabase`
- `postgres`

If using Supabase in Streamlit Cloud, add credentials to
`.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
```

If using Supabase locally, add to `.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-or-anon-key
```

If using PostgreSQL, add to `.env`:

```env
DB_BACKEND=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=football_analysis
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
# Optional
POSTGRES_SSLMODE=require
```

## Data

Data lives under `data/`:
- `data/statsbomb/` for StatsBomb open data snapshots and processed files
- `data/wyscout/raw/` for Wyscout exports (events, matches, teams, players)

Current Streamlit pages are database-backed and expect populated tables (for example,
competitions, matches, teams, players, and shots) in the active backend.

## Repository layout

- `apps/streamlit/` Streamlit entrypoint and page definitions
- `src/football_analytics/` Core package code
- `models/xg_model/` xG model notebooks and saved model/scaler artifacts
- `models/xv_model/` xV model work and notebooks
- `models/injury_prediction/` Injury prediction modeling area
- `databricks_pipeline/` ETL and pipeline work

## Current Development Stage

This project is under active development, with ongoing work on model quality,
data pipelines, and dashboard experience.

## Roadmap

See `ROADMAP.md` for planned modeling and analysis milestones.

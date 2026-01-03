# Football Analytics

End-to-end football analytics workspace: data ingestion and processing, xG modeling,
and Streamlit dashboards for match and shot analysis.

## Highlights

- Data processing utilities in `src/football_analytics/data_processing`
- xG model notebooks and saved neural models in `xg_model/`
- Streamlit dashboards for matches, teams, players, and shot details
- Shot visualizations and geometry helpers in `src/football_analytics/visuals` and `utils`

## Quick start

Requirements:
- Python 3.10+

```powershell
git clone <repo>
cd <repo>
python bootstrap.py 
```

## Run the Streamlit app

```powershell
streamlit run apps\streamlit\Home.py
```

## Configuration

Streamlit uses Supabase credentials from Streamlit secrets. Create
`.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
```

Some utilities load Supabase credentials from `.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-or-anon-key
```

## Data

Data lives under `data/`:
- `data/statsbomb/` for StatsBomb open data snapshots and processed files
- `data/wyscout/raw/` for Wyscout exports (events, matches, teams, players)

## Repository layout

- `apps/streamlit/` Streamlit entrypoint and page definitions
- `src/football_analytics/` Core package code
- `xg_model/` Model notebooks and saved model/scaler artifacts
- `databricks_pipeline/` ETL and pipeline work

## Roadmap

See `ROADMAP.md` for planned modeling and analysis milestones.

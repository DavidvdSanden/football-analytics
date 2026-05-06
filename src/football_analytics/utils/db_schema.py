from __future__ import annotations

import os

from .database import get_db_backend, get_postgres_conn


def ensure_transfermarkt_tables() -> None:
    """Create/align Transfermarkt tables and indexes in configured schema."""
    backend = get_db_backend()
    if backend != "postgres":
        raise ValueError(
            f"Transfermarkt scraper currently supports postgres only. Active backend: {backend}"
        )

    schema = os.getenv("TRANSFERMARKT_DB_SCHEMA", "transfermarkt").strip()

    sql_statements = [
        f"CREATE SCHEMA IF NOT EXISTS {schema};",
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.clubs (
            tm_club_id BIGINT PRIMARY KEY,
            club_name TEXT NOT NULL,
            country TEXT,
            profile_url TEXT,
            scraped_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.players (
            tm_player_id BIGINT PRIMARY KEY,
            full_name TEXT NOT NULL,
            date_of_birth DATE,
            nationality TEXT,
            preferred_foot TEXT,
            main_position TEXT,
            current_tm_club_id TEXT,
            profile_url TEXT,
            scraped_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.player_market_values (
            tm_player_id BIGINT NOT NULL,
            valuation_date DATE NOT NULL,
            market_value_eur BIGINT,
            source_url TEXT,
            scraped_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS tm_club_id BIGINT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS club_name TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS country TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS profile_url TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ DEFAULT NOW();",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS tm_player_id BIGINT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS full_name TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS date_of_birth DATE;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS nationality TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS preferred_foot TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS main_position TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS current_tm_club_id TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS profile_url TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ DEFAULT NOW();",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS tm_player_id BIGINT;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS valuation_date DATE;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS market_value_eur BIGINT;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS source_url TEXT;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ DEFAULT NOW();",
        f"CREATE UNIQUE INDEX IF NOT EXISTS uq_transfermarkt_clubs_tm_club_id ON {schema}.clubs(tm_club_id);",
        f"CREATE UNIQUE INDEX IF NOT EXISTS uq_transfermarkt_players_tm_player_id ON {schema}.players(tm_player_id);",
        f"CREATE UNIQUE INDEX IF NOT EXISTS uq_transfermarkt_pmv_player_date ON {schema}.player_market_values(tm_player_id, valuation_date);",
        f"CREATE INDEX IF NOT EXISTS idx_transfermarkt_pmv_valuation_date ON {schema}.player_market_values(valuation_date);",
    ]

    conn = get_postgres_conn()
    try:
        with conn.cursor() as cur:
            for statement in sql_statements:
                cur.execute(statement)
        conn.commit()
    finally:
        conn.close()

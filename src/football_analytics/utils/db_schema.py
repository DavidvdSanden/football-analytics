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
            official_name TEXT,
            founded_on DATE,
            address_raw TEXT,
            city TEXT,
            crest_url TEXT,
            profile_url TEXT,
            profile_last_scraped_at TIMESTAMPTZ,
            scraped_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.players (
            tm_player_id BIGINT PRIMARY KEY,
            full_name TEXT NOT NULL,
            home_name TEXT,
            date_of_birth DATE,
            place_of_birth TEXT,
            height_cm INTEGER,
            nationality TEXT,
            citizenship_raw TEXT,
            preferred_foot TEXT,
            main_position TEXT,
            detailed_position TEXT,
            current_tm_club_id TEXT,
            joined_current_club_on DATE,
            contract_expires_on DATE,
            last_contract_extension_on DATE,
            player_image_url TEXT,
            profile_url TEXT,
            profile_last_scraped_at TIMESTAMPTZ,
            scraped_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.player_market_values (
            tm_player_id BIGINT NOT NULL,
            valuation_date DATE NOT NULL,
            market_value_eur BIGINT,
            market_value_raw TEXT,
            change_direction TEXT,
            source_url TEXT,
            scraped_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS tm_club_id BIGINT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS club_name TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS country TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS official_name TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS founded_on DATE;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS address_raw TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS city TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS crest_url TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS profile_url TEXT;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS profile_last_scraped_at TIMESTAMPTZ;",
        f"ALTER TABLE {schema}.clubs ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ DEFAULT NOW();",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS tm_player_id BIGINT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS full_name TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS home_name TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS date_of_birth DATE;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS place_of_birth TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS height_cm INTEGER;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS nationality TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS citizenship_raw TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS preferred_foot TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS main_position TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS detailed_position TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS current_tm_club_id TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS joined_current_club_on DATE;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS contract_expires_on DATE;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS last_contract_extension_on DATE;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS player_image_url TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS profile_url TEXT;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS profile_last_scraped_at TIMESTAMPTZ;",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ DEFAULT NOW();",
        f"ALTER TABLE {schema}.players ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS tm_player_id BIGINT;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS valuation_date DATE;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS market_value_eur BIGINT;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS market_value_raw TEXT;",
        f"ALTER TABLE {schema}.player_market_values ADD COLUMN IF NOT EXISTS change_direction TEXT;",
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

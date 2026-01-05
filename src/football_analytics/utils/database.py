import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Create and return Supabase client from .env."""
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    return create_client(supabase_url, supabase_key)


def get_db_backend() -> str:
    """Return the active DB backend name."""
    load_dotenv()
    return os.getenv("DB_BACKEND", "postgres").strip().lower()


def get_postgres_conn():
    """Create and return a Postgres connection from .env."""
    try:
        import psycopg2
    except ImportError as exc:
        raise ImportError(
            "psycopg2 is required for Postgres backend. Install with: pip install psycopg2-binary"
        ) from exc

    load_dotenv()
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    dbname = os.getenv("POSTGRES_DB", "football_analysis")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    sslmode = os.getenv("POSTGRES_SSLMODE")

    if not user or not password:
        raise ValueError("POSTGRES_USER and POSTGRES_PASSWORD must be set.")

    conn_kwargs = {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
    }
    if sslmode:
        conn_kwargs["sslmode"] = sslmode

    return psycopg2.connect(**conn_kwargs)


def fetch_all_rows_in_batches(
    table_name: str,
    key_column: str,
    columns: str = "*",
    batch_size: int = 5000,
    max_batches: int | None = None,
):
    """
    Fetch all rows from the active database in batches to avoid timeouts.

    Args:
        table_name: Name of the table to query
        key_column: String indicating the key indexing column on which table will be ordered
        columns: Comma-separated column names or "*" for all
        batch_size: Number of rows per batch
        max_batches: Optional limit (for testing or large tables)

    Returns:
        List of dicts containing all rows fetched.
    """
    all_rows = []
    offset = 0
    batch_count = 0
    last_key = None

    if get_db_backend() == "supabase":
        supabase = get_supabase_client()
        while True:
            try:
                query = (
                    supabase.table(table_name)
                    .select(columns)
                    .order(key_column, desc=False)
                    .limit(batch_size)
                )
                if last_key is not None:
                    query = query.gt(key_column, last_key)

                response = query.execute()
                data = response.data

                if not data:
                    break

                all_rows.extend(data)
                last_key = data[-1][key_column]  # last key fetched

                offset += batch_size
                batch_count += 1
                print(f"Fetched {len(data)} rows (total {len(all_rows)}).")

                # Optional: stop early if max_batches is set
                if max_batches and batch_count >= max_batches:
                    print(f"Reached max_batches ({max_batches}), stopping early.")
                    break

            except Exception as e:
                print(f"Error fetching batch starting at {offset}: {e}")
                time.sleep(2)
                break
        return all_rows

    try:
        import psycopg2.extras
    except ImportError as exc:
        raise ImportError(
            "psycopg2 is required for Postgres backend. Install with: pip install psycopg2-binary"
        ) from exc

    conn = get_postgres_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            while True:
                try:
                    if last_key is None:
                        query = (
                            f"SELECT {columns} FROM {table_name} "
                            f"ORDER BY {key_column} ASC LIMIT %s"
                        )
                        cur.execute(query, (batch_size,))
                    else:
                        query = (
                            f"SELECT {columns} FROM {table_name} "
                            f"WHERE {key_column} > %s ORDER BY {key_column} ASC LIMIT %s"
                        )
                        cur.execute(query, (last_key, batch_size))

                    data = cur.fetchall()
                    if not data:
                        break

                    all_rows.extend(data)
                    last_key = data[-1][key_column]  # last key fetched

                    offset += batch_size
                    batch_count += 1
                    print(f"Fetched {len(data)} rows (total {len(all_rows)}).")

                    if max_batches and batch_count >= max_batches:
                        print(f"Reached max_batches ({max_batches}), stopping early.")
                        break
                except Exception as e:
                    print(f"Error fetching batch starting at {offset}: {e}")
                    time.sleep(2)
                    break
    finally:
        conn.close()

    return all_rows


def fetch_rows(
    table_name: str,
    columns: str = "*",
    filters: dict | None = None,
    limit: int | None = None,
):
    """Fetch rows with optional equality filters and limit."""
    if get_db_backend() == "supabase":
        supabase = get_supabase_client()
        query = supabase.table(table_name).select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data or []

    try:
        import psycopg2.extras
    except ImportError as exc:
        raise ImportError(
            "psycopg2 is required for Postgres backend. Install with: pip install psycopg2-binary"
        ) from exc

    def _normalize_param(value):
        try:
            import numpy as np
        except ImportError:
            return value
        if isinstance(value, np.generic):
            return value.item()
        return value

    conn = get_postgres_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = f"SELECT {columns} FROM {table_name}"
            params = []
            if filters:
                where = " AND ".join([f"{col} = %s" for col in filters.keys()])
                sql += f" WHERE {where}"
                params.extend([_normalize_param(v) for v in filters.values()])
            if limit:
                sql += " LIMIT %s"
                params.append(_normalize_param(limit))
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def fetch_rows_by_column(
    table_name: str,
    column: str,
    value,
    columns: str = "*",
    limit: int | None = None,
):
    """Fetch rows matching a single equality filter."""
    return fetch_rows(
        table_name=table_name,
        columns=columns,
        filters={column: value},
        limit=limit,
    )


def upsert_rows(
    table_name: str,
    rows: list[dict],
    conflict_columns: str | list[str],
):
    """Upsert rows into the active database using conflict columns."""
    if not rows:
        return None

    if get_db_backend() == "supabase":
        supabase = get_supabase_client()
        conflict = (
            ", ".join(conflict_columns)
            if isinstance(conflict_columns, list)
            else conflict_columns
        )
        response = supabase.table(table_name).upsert(
            rows, on_conflict=conflict
        ).execute()
        return response.data

    try:
        import psycopg2.extras
    except ImportError as exc:
        raise ImportError(
            "psycopg2 is required for Postgres backend. Install with: pip install psycopg2-binary"
        ) from exc

    conflict_cols = (
        [c.strip() for c in conflict_columns.split(",")]
        if isinstance(conflict_columns, str)
        else list(conflict_columns)
    )
    columns = list(rows[0].keys())
    values = [[row.get(col) for col in columns] for row in rows]
    update_cols = [c for c in columns if c not in conflict_cols]
    column_list = ", ".join(columns)

    if update_cols:
        set_clause = ", ".join([f"{c}=EXCLUDED.{c}" for c in update_cols])
        insert_sql = (
            f"INSERT INTO {table_name} ({column_list}) VALUES %s "
            f"ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {set_clause}"
        )
    else:
        insert_sql = (
            f"INSERT INTO {table_name} ({column_list}) VALUES %s "
            f"ON CONFLICT ({', '.join(conflict_cols)}) DO NOTHING"
        )

    conn = get_postgres_conn()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, insert_sql, values)
        conn.commit()
    finally:
        conn.close()

    return None

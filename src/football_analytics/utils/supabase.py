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


def fetch_all_rows_in_batches(
    table_name: str,
    key_column: str,
    columns: str = "*",
    batch_size: int = 5000,
    max_batches: int | None = None,
):
    """
    Fetch all rows from a Supabase table in batches to avoid timeouts.

    Args:
        table_name: Name of the table to query
        key_column: String indicating the key indexing column on which table will be ordered
        columns: Comma-separated column names or "*" for all
        batch_size: Number of rows per batch
        max_batches: Optional limit (for testing or large tables)

    Returns:
        List of dicts containing all rows fetched.
    """
    supabase = get_supabase_client()
    all_rows = []
    offset = 0
    batch_count = 0
    last_key = None

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

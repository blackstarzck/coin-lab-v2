from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import default_env_file, load_settings


def _api_key() -> str | None:
    return (
        os.getenv("COIN_LAB_SUPABASE_SECRET_KEY")
        or os.getenv("COIN_LAB_SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("COIN_LAB_SUPABASE_ANON_KEY")
    )


def _check_rest_connection(supabase_url: str, api_key: str) -> tuple[bool, str]:
    url = f"{supabase_url.rstrip('/')}/rest/v1/strategies?select=id&limit=1"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
    }
    response = httpx.get(url, headers=headers, timeout=20.0)
    if response.status_code != 200:
        return False, f"REST check failed with status {response.status_code}: {response.text[:200]}"
    return True, f"REST check succeeded: {response.text[:200]}"


def _check_postgres_connection(database_url: str) -> tuple[bool, str]:
    import psycopg2

    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
    finally:
        conn.close()
    return row == (1,), f"Postgres check returned {row!r}"


def main() -> int:
    settings = load_settings()
    env_file = default_env_file()
    supabase_url = os.getenv("COIN_LAB_SUPABASE_URL")
    api_key = _api_key()

    print(f"env_file={env_file}")
    print(f"env_file_exists={env_file.exists()}")
    print(f"store_backend={settings.store_backend}")
    print(f"database_url_present={bool(settings.database_url)}")
    print(f"supabase_url_present={bool(supabase_url)}")
    print(f"supabase_api_key_present={bool(api_key)}")

    rest_ok = False
    if supabase_url and api_key:
        try:
            rest_ok, message = _check_rest_connection(supabase_url, api_key)
        except Exception as exc:
            rest_ok = False
            message = f"REST check raised {type(exc).__name__}: {exc}"
        print(f"supabase_rest_ok={rest_ok}")
        print(message)
    else:
        print("supabase_rest_ok=False")
        print("REST check skipped because COIN_LAB_SUPABASE_URL or an API key is missing.")

    postgres_ok = False
    if settings.store_backend == "postgres":
        if not settings.database_url:
            print("postgres_store_ok=False")
            print("Postgres check skipped because COIN_LAB_DATABASE_URL is missing.")
            return 1
        try:
            postgres_ok, message = _check_postgres_connection(settings.database_url)
        except Exception as exc:
            postgres_ok = False
            message = f"Postgres check raised {type(exc).__name__}: {exc}"
        print(f"postgres_store_ok={postgres_ok}")
        print(message)
        return 0 if postgres_ok else 1

    print("postgres_store_ok=False")
    print("Postgres store check skipped because COIN_LAB_STORE_BACKEND is not 'postgres'.")
    print("Current runtime can reach Supabase REST only; persistence is still using the in-memory store.")
    return 0 if rest_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

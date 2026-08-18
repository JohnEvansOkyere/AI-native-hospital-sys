"""Apply VeloxaCare's versioned PostgreSQL migrations.

Usage from the repository root:
    MIGRATION_DATABASE_URL='postgresql://...' python backend/migrate.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

if os.getenv("MIGRATION_DATABASE_URL", "").strip():
    os.environ["DATABASE_URL"] = os.environ["MIGRATION_DATABASE_URL"].strip()

from db import database_backend, init_db  # noqa: E402


async def main() -> None:
    if database_backend() != "postgres":
        raise SystemExit(
            "DATABASE_URL is not configured with a PostgreSQL connection string"
        )
    await init_db()
    print("Supabase PostgreSQL migrations are up to date.")


if __name__ == "__main__":
    asyncio.run(main())

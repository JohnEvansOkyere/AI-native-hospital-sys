"""Read-only verification of the configured production PostgreSQL database."""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db import connect, database_backend  # noqa: E402


APPLICATION_TABLES = {
    "patients", "staff_users", "messages", "adherence_logs", "checkin_logs",
    "conversation_state", "escalations", "staff_sessions", "inbound_events",
    "reminder_dispatches", "consent_events", "clinic_settings", "audit_events",
    "care_logs", "appointments", "schema_migrations",
}


async def main() -> None:
    if database_backend() != "postgres":
        raise SystemExit("DATABASE_URL is not configured for PostgreSQL")

    async with connect() as db:
        versions = [
            row[0] for row in await (
                await db.execute("SELECT version FROM schema_migrations ORDER BY version")
            ).fetchall()
        ]
        table_rows = await (
            await db.execute(
                """SELECT c.relname, c.relrowsecurity
                   FROM pg_class c
                   JOIN pg_namespace n ON n.oid=c.relnamespace
                   WHERE n.nspname='public' AND c.relkind='r'"""
            )
        ).fetchall()
        table_rls = {row[0]: bool(row[1]) for row in table_rows}
        missing = sorted(APPLICATION_TABLES - set(table_rls))
        rls_disabled = sorted(
            table for table in APPLICATION_TABLES if table in table_rls and not table_rls[table]
        )
        patient_count = (await (await db.execute("SELECT COUNT(*) FROM patients")).fetchone())[0]
        staff_count = (await (await db.execute("SELECT COUNT(*) FROM staff_users")).fetchone())[0]

    print("database_backend=postgres")
    print(f"migrations={','.join(versions)}")
    print(f"application_tables={len(APPLICATION_TABLES)}")
    print(f"missing_tables={','.join(missing) or 'none'}")
    print(f"rls_disabled={','.join(rls_disabled) or 'none'}")
    print(f"patient_count={patient_count}")
    print(f"staff_count={staff_count}")

    if not versions or missing or rls_disabled:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

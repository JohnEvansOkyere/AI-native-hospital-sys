"""Database-boundary checks that do not require live Supabase credentials."""

import os
import sys
import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import db  # noqa: E402
from config import missing_production_config  # noqa: E402
from services import auth  # noqa: E402


def test_postgres_placeholder_conversion_ignores_quoted_question_marks():
    sql = "SELECT '?' AS literal, value FROM things WHERE first=? AND second=?"
    assert db._postgres_placeholders(sql) == (
        "SELECT '?' AS literal, value FROM things WHERE first=$1 AND second=$2"
    )


def test_project_api_url_is_rejected_as_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "https://example.supabase.co")
    with pytest.raises(RuntimeError, match="PostgreSQL connection string"):
        db._postgres_url()


def test_production_requires_postgres_not_legacy_turso(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://legacy.example")
    missing = missing_production_config()
    assert "DATABASE_URL" in missing
    assert "TURSO_DATABASE_URL" not in missing


def test_postgres_never_creates_the_local_demo_admin(monkeypatch):
    class EmptyCursor:
        async def fetchone(self):
            return (0,)

    class EmptyDatabase:
        async def execute(self, _sql, _params=()):
            return EmptyCursor()

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql://configured")
    monkeypatch.delenv("BOOTSTRAP_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="hosted database"):
        asyncio.run(auth.ensure_bootstrap_admin(EmptyDatabase()))


def test_bootstrap_admin_insert_is_idempotent(monkeypatch):
    class EmptyCursor:
        async def fetchone(self):
            return (0,)

    class RecordingDatabase:
        def __init__(self):
            self.statements = []

        async def execute(self, sql, _params=()):
            self.statements.append(sql)
            return EmptyCursor()

        async def commit(self):
            return None

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://configured")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "LongEnoughPassword")
    database = RecordingDatabase()
    asyncio.run(auth.ensure_bootstrap_admin(database))
    assert any("ON CONFLICT(email) DO NOTHING" in sql for sql in database.statements)


def test_production_cookie_is_secure_except_on_localhost_http(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    assert auth.cookie_options("https", "care.example.com")["secure"] is True
    assert auth.cookie_options("http", "care.example.com")["secure"] is True
    assert auth.cookie_options("http", "localhost")["secure"] is False
    assert auth.cookie_options("http", "127.0.0.1")["secure"] is False


def test_postgres_migration_has_no_sqlite_only_ddl():
    migration = (BACKEND / "migrations" / "001_initial.sql").read_text()
    for sqlite_only in ("AUTOINCREMENT", "INSERT OR REPLACE", "PRAGMA"):
        assert sqlite_only not in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration


@pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_URL"), reason="POSTGRES_TEST_URL is not configured",
)
def test_postgres_round_trip_and_rls(monkeypatch):
    """Exercise the real adapter/schema against a disposable PostgreSQL DB."""
    monkeypatch.setenv("DATABASE_URL", os.environ["POSTGRES_TEST_URL"])
    monkeypatch.setenv("DEMO_SEED", "0")

    async def verify():
        await db.init_db()
        async with db.connect() as connection:
            patient_id = await db.insert_returning_id(
                connection,
                """INSERT INTO patients
                   (name, phone, age, condition, drug_name, drug_dosage, enrolled_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("Postgres Smoke", "+233240000099", 50, "hypertension",
                 "Amlodipine", "5mg", date.today().isoformat()),
            )
            await connection.execute(
                """INSERT INTO conversation_state (patient_id, current_flow, context)
                   VALUES (?, 'idle', '{}')
                   ON CONFLICT(patient_id) DO UPDATE SET current_flow=excluded.current_flow""",
                (patient_id,),
            )
            message_id = await db.insert_returning_id(
                connection,
                """INSERT INTO messages
                   (patient_id, direction, body, created_at) VALUES (?,?,?,?)""",
                (patient_id, "inbound", "YES", datetime.now().isoformat()),
            )
            await connection.commit()

            row = await (await connection.execute(
                """SELECT p.name, m.body FROM patients p
                   JOIN messages m ON m.patient_id=p.id WHERE p.id=? AND m.id=?""",
                (patient_id, message_id),
            )).fetchone()
            assert row == ("Postgres Smoke", "YES")
            cutoff = (datetime.now() - timedelta(days=1)).isoformat()
            assert (await (await connection.execute(
                "SELECT COUNT(*) FROM messages WHERE created_at>=?", (cutoff,),
            )).fetchone())[0] >= 1
            rls = await (await connection.execute(
                """SELECT relrowsecurity FROM pg_class
                   WHERE relname='patients' AND relnamespace='public'::regnamespace"""
            )).fetchone()
            assert rls == (True,)

    asyncio.run(verify())

"""Database-backed staff authentication for the clinic dashboard."""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from config import production_like


COOKIE_NAME = "veloxacare_session"
SESSION_HOURS = 12
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return "$".join([
        "scrypt", str(SCRYPT_N), str(SCRYPT_R), str(SCRYPT_P),
        base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode(),
    ])


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = encoded.split("$", 5)
        if scheme != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=base64.urlsafe_b64decode(salt.encode()),
            n=int(n), r=int(r), p=int(p),
        )
        return secrets.compare_digest(actual, base64.urlsafe_b64decode(expected.encode()))
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def ensure_bootstrap_admin(db) -> None:
    cursor = await db.execute("SELECT COUNT(*) FROM staff_users")
    if (await cursor.fetchone())[0] > 0:
        return
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Clinic Administrator").strip()
    if not email or not password:
        # A hosted PostgreSQL database is never a demo database, even if an
        # operator forgot APP_ENV. Refuse to create the well-known local account
        # in Supabase under every circumstance.
        if production_like() or os.getenv("DATABASE_URL", "").strip():
            raise RuntimeError(
                "No staff account exists. Set BOOTSTRAP_ADMIN_EMAIL and "
                "BOOTSTRAP_ADMIN_PASSWORD before starting a hosted database."
            )
        email, password, name = (
            "admin@veloxacare.local", "VeloxaCare-Local-Only", "Local Demo Administrator",
        )
    await db.execute(
        """INSERT INTO staff_users (email, name, role, password_hash, active, created_at)
           VALUES (?,?,?,?,1,?)
           ON CONFLICT(email) DO NOTHING""",
        (email, name, "admin", hash_password(password), utc_now().isoformat()),
    )
    await db.commit()


async def authenticate(db, email: str, password: str) -> dict | None:
    cursor = await db.execute(
        """SELECT id, email, name, role, password_hash, active,
                  failed_login_count, locked_until
           FROM staff_users WHERE email=?""",
        (email.strip().lower(),),
    )
    row = await cursor.fetchone()
    if not row or not row[5]:
        return None
    now = utc_now()
    if row[7]:
        try:
            if datetime.fromisoformat(row[7]) > now:
                return None
        except ValueError:
            pass
    if not verify_password(password, row[4]):
        failures = int(row[6] or 0) + 1
        locked_until = (now + timedelta(minutes=15)).isoformat() if failures >= 5 else None
        await db.execute(
            "UPDATE staff_users SET failed_login_count=?, locked_until=? WHERE id=?",
            (0 if locked_until else failures, locked_until, row[0]),
        )
        await db.commit()
        return None
    await db.execute(
        "UPDATE staff_users SET failed_login_count=0, locked_until=NULL, last_login_at=? WHERE id=?",
        (now.isoformat(), row[0]),
    )
    await db.commit()
    return {"id": row[0], "email": row[1], "name": row[2], "role": row[3]}


async def create_session(db, user_id: int, user_agent: str = "", ip_address: str = "") -> dict:
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    now, expires = utc_now(), utc_now() + timedelta(hours=SESSION_HOURS)
    await db.execute(
        """INSERT INTO staff_sessions
           (token_hash, user_id, csrf_token, created_at, expires_at, last_seen_at,
            user_agent, ip_address) VALUES (?,?,?,?,?,?,?,?)""",
        (token_digest(token), user_id, csrf, now.isoformat(), expires.isoformat(),
         now.isoformat(), user_agent[:300], ip_address[:100]),
    )
    await db.commit()
    return {"token": token, "csrf_token": csrf, "expires_at": expires.isoformat()}


async def get_session(db, token: str) -> dict | None:
    if not token:
        return None
    now, digest = utc_now().isoformat(), token_digest(token)
    cursor = await db.execute(
        """SELECT u.id, u.email, u.name, u.role, s.csrf_token, s.expires_at
           FROM staff_sessions s JOIN staff_users u ON u.id=s.user_id
           WHERE s.token_hash=? AND s.expires_at>? AND u.active=1""",
        (digest, now),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    await db.execute("UPDATE staff_sessions SET last_seen_at=? WHERE token_hash=?", (now, digest))
    await db.commit()
    return {
        "id": row[0], "email": row[1], "name": row[2], "role": row[3],
        "csrf_token": row[4], "expires_at": row[5],
    }


async def revoke_session(db, token: str) -> None:
    if token:
        await db.execute("DELETE FROM staff_sessions WHERE token_hash=?", (token_digest(token),))
        await db.commit()


def cookie_options(scheme: str = "", hostname: str = "") -> dict:
    local_http = scheme == "http" and hostname in {"localhost", "127.0.0.1", "::1"}
    return {
        "key": COOKIE_NAME, "httponly": True,
        "secure": production_like() and not local_http,
        "samesite": "strict", "max_age": SESSION_HOURS * 3600, "path": "/",
    }

"""Runtime policy for separating local demo behaviour from clinic deployments."""

import os


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def environment() -> str:
    return (os.getenv("APP_ENV") or os.getenv("VERCEL_ENV") or "development").strip().lower()


def production_like() -> bool:
    return environment() in {"production", "preview", "staging"}


def demo_tools_enabled() -> bool:
    return False if production_like() else _flag("ENABLE_DEMO_TOOLS", default=True)


def demo_seed_enabled() -> bool:
    return False if production_like() else _flag("DEMO_SEED", default=True)


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def missing_production_config() -> list[str]:
    """Return launch-blocking settings without exposing their values."""
    if not production_like():
        return []
    required = [
        "DATABASE_URL", "META_ACCESS_TOKEN",
        "META_PHONE_NUMBER_ID", "META_VERIFY_TOKEN", "META_APP_SECRET",
        "CRON_SECRET", "META_MEDICATION_REMINDER_TEMPLATE",
    ]
    return [name for name in required if not os.getenv(name, "").strip()]

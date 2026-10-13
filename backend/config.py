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


# Without these the care team cannot safely message a patient at all, so
# clinical writes are blocked until they are set.
MESSAGING_REQUIRED = [
    "DATABASE_URL", "META_ACCESS_TOKEN",
    "META_PHONE_NUMBER_ID", "META_VERIFY_TOKEN", "META_APP_SECRET",
    "CRON_SECRET",
]
# Missing these degrades one feature, not the workspace: scheduled reminders
# record a failed dispatch, while care-team messages still go out.
FEATURE_REQUIRED = ["META_MEDICATION_REMINDER_TEMPLATE"]


def _missing(names: list[str]) -> list[str]:
    if not production_like():
        return []
    return [name for name in names if not os.getenv(name, "").strip()]


def missing_messaging_config() -> list[str]:
    """Settings whose absence blocks clinical writes and patient messaging."""
    return _missing(MESSAGING_REQUIRED)


def missing_production_config() -> list[str]:
    """Every launch setting not yet configured (for /health), values never exposed."""
    return _missing(MESSAGING_REQUIRED + FEATURE_REQUIRED)

"""Server-side cache for Resume Review Day reads.

Payloads are stored under a version number. Writes bump that version, so
the next read misses without scanning keys. That works on both Redis and
the local-memory cache used in tests.
"""

from django.core.cache import cache

CACHE_TTL = 60 * 60
DATA_VERSION_KEY = "rrd:data-version"
SETTINGS_VERSION_KEY = "rrd:settings-version"


def _version(key: str) -> int:
    version = cache.get(key)
    if version is None:
        cache.add(key, 1, timeout=None)
        version = cache.get(key) or 1
    return int(version)


def _bump(key: str) -> None:
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=None)


def invalidate_resume_review_data() -> None:
    """Drop cached employer, timeslot, and roster payloads."""
    _bump(DATA_VERSION_KEY)


def invalidate_resume_review_settings() -> None:
    """Drop cached registration-page flags."""
    _bump(SETTINGS_VERSION_KEY)


def cache_versions() -> dict:
    """Versions the client compares so it refetches only after expiry or invalidation."""
    return {
        "data_version": _version(DATA_VERSION_KEY),
        "settings_version": _version(SETTINGS_VERSION_KEY),
    }


def cached_value(key_fn, builder):
    """Return a cached JSON-ready value, building it on a miss."""
    key = key_fn()
    value = cache.get(key)
    if value is not None:
        return value
    value = builder()
    cache.set(key_fn(), value, CACHE_TTL)
    return value


def employer_list_key() -> str:
    return f"rrd:v{_version(DATA_VERSION_KEY)}:employer_list"


def roster_key() -> str:
    return f"rrd:v{_version(DATA_VERSION_KEY)}:roster"


def timeslots_key(full_path: str) -> str:
    return f"rrd:v{_version(DATA_VERSION_KEY)}:timeslots:{full_path}"


def page_flags() -> dict:
    """Public registration flags. Cached until settings are saved."""

    def _key() -> str:
        return f"rrd:v{_version(SETTINGS_VERSION_KEY)}:settings"

    def _load() -> dict:
        from .models import ResumeReviewSettings

        settings = ResumeReviewSettings.current()
        return {
            "employer_page_open": settings.employer_page_open,
            "student_page_open": settings.student_page_open,
        }

    return cached_value(_key, _load)

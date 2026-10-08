"""Server-side cache for Resume Review Day reads."""

from django.core.cache import cache

CACHE_TTL = 60 * 60

EMPLOYERS = "rrd:employers"
ROSTER = "rrd:roster"
SETTINGS = "rrd:settings"
TIMESLOT_KEYS = "rrd:timeslot-keys"


def cached(key, build):
    """Return a cached value, building it on a miss."""
    value = cache.get(key)
    if value is not None:
        return value
    value = build()
    cache.set(key, value, CACHE_TTL)
    return value


def cached_timeslots(path, build):
    """Cache one timeslot query. The path is remembered so it can be deleted later."""
    key = f"rrd:timeslots:{path}"
    known = cache.get(TIMESLOT_KEYS) or []
    if key not in known:
        cache.set(TIMESLOT_KEYS, [*known, key], timeout=None)
    return cached(key, build)


def invalidate_resume_review_data() -> None:
    """Drop cached employer, timeslot, and roster payloads."""
    known = cache.get(TIMESLOT_KEYS) or []
    cache.delete_many([EMPLOYERS, ROSTER, TIMESLOT_KEYS, *known])


def invalidate_resume_review_settings() -> None:
    """Drop cached registration-page flags."""
    cache.delete(SETTINGS)


def page_flags() -> dict:
    """Public registration flags. Cached until settings are saved."""

    def load() -> dict:
        from .models import ResumeReviewSettings

        settings = ResumeReviewSettings.current()
        return {
            "employer_page_open": settings.employer_page_open,
            "student_page_open": settings.student_page_open,
        }

    return cached(SETTINGS, load)

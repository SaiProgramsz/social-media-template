from __future__ import annotations

import os

from django.conf import settings


def _default_words() -> set[str]:
    # Keep this list small and configurable; it's a starter, not a complete solution.
    return {
        "fuck",
        "shit",
        "bitch",
        "asshole",
        "bastard",
        "cunt",
        "dick",
        "pussy",
        "slut",
        "whore",
    }


def get_profanity_words() -> set[str]:
    words = getattr(settings, "PROFANITY_WORDS", None)
    if isinstance(words, (set, list, tuple)):
        return {str(w).strip().lower() for w in words if str(w).strip()}

    env_words = os.getenv("PROFANITY_WORDS", "").strip()
    if env_words:
        return {w.strip().lower() for w in env_words.split(",") if w.strip()}

    return _default_words()


def contains_profanity(text: str) -> bool:
    if not text:
        return False
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    tokens = {t for t in normalized.split() if t}
    bad = get_profanity_words()
    return any(t in bad for t in tokens)


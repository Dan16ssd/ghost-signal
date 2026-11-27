"""Settings read from the environment (and a local .env file, never committed)."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass


def _flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Answer writing
    # No key -> no AI: answers use plain source extracts, fixed messages fall back to English.
    use_llm: bool = _flag("GHOST_USE_LLM", True) and bool(os.getenv("ANTHROPIC_API_KEY"))
    model: str = os.getenv("GHOST_MODEL", "claude-opus-5-5")
    max_segments: int = int(os.getenv("GHOST_MAX_SEGMENTS", "3"))
    # Abuse / cost guard
    max_questions_per_hour: int = int(os.getenv("GHOST_MAX_PER_HOUR", "20"))
    # Daily cap on AI calls for everyone together; above it, answers fall back to plain extracts
    max_ai_calls_per_day: int = int(os.getenv("GHOST_MAX_AI_PER_DAY", "2000"))
    max_reminders: int = int(os.getenv("GHOST_MAX_REMINDERS", "5"))
    # Medicine calls (Twilio Voice). Off = SMS reminders only.
    voice_calls: bool = _flag("GHOST_VOICE_CALLS", True)
    max_calls_per_day: int = int(os.getenv("GHOST_MAX_CALLS_PER_DAY", "200"))
    # State (opt-outs, limits, reminders)
    db_path: str = os.getenv("GHOST_DB", "ghost_signal.db")
    # Twilio
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from_number: str = os.getenv("TWILIO_FROM_NUMBER", "")
    # Public URL Twilio calls (needed to check Twilio's signature behind a proxy)
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    # Outgoing HTTP
    http_timeout: float = float(os.getenv("GHOST_HTTP_TIMEOUT", "8"))
    # Wikipedia blocks clients without contact info: set this to the public repo URL or an email.
    contact: str = os.getenv("GHOST_CONTACT", "")

    @property
    def user_agent(self) -> str:
        return f"GhostSignal/0.1 ({self.contact})" if self.contact else "GhostSignal/0.1"

    @property
    def twilio_can_send(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)


settings = Settings()

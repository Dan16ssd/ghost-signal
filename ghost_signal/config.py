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
    use_llm: bool = _flag("GHOST_USE_LLM", True)
    model: str = os.getenv("GHOST_MODEL", "claude-opus-5-5")
    max_segments: int = int(os.getenv("GHOST_MAX_SEGMENTS", "3"))
    # Abuse / cost guard
    max_questions_per_hour: int = int(os.getenv("GHOST_MAX_PER_HOUR", "20"))
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

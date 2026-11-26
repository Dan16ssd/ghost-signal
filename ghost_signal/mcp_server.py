"""Ghost Signal as an MCP server, so Kiro (or any MCP client) can use the answer engine as tools.

We use it while building: Kiro's agent asks real questions in many languages and checks the
replies against the SMS rules without a phone. Configured in .kiro/settings/mcp.json.

Run:  python -m ghost_signal.mcp_server        (stdio)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import answer, countries, sms, sources
from . import lang as L

mcp = FastMCP("ghost-signal")


@mcp.tool()
def ask(text: str, country: str = "") -> dict:
    """Send one SMS to Ghost Signal as if from a country (ISO code like 'LA', 'EG', 'KE') and get the reply
    exactly as the phone would receive it, with its SMS part count and encoding."""
    c = countries.from_code(country)
    r = answer.handle(text, sender=f"mcp:{country or 'any'}", country=c)
    return {"reply": r.text, "kind": r.kind, "language": r.lang, "segments": r.segments, "encoding": r.encoding}


@mcp.tool()
def check_sms(text: str) -> dict:
    """How a text would travel as SMS: encoding (GSM-7 or UCS-2), parts, and whether it fits Ghost Signal's limit."""
    parts = sms.segments(text)
    return {"encoding": sms.encoding(text), "units": sms.units(text), "segments": parts,
            "fits": parts <= answer.settings.max_segments}


@mcp.tool()
def detect_language(text: str, country: str = "") -> str:
    """The language code Ghost Signal would answer in (country breaks ties, e.g. Persian vs Arabic letters)."""
    c = countries.from_code(country)
    return L.detect(text, c.lang if c else None)


@mcp.tool()
def wikipedia_search(query: str, language: str = "en") -> list[dict]:
    """The Wikipedia sources Ghost Signal would read for a question, in one language edition."""
    return [{"title": s.title, "url": s.url, "text": s.text[:500]} for s in sources.wikipedia(query, language)]


@mcp.tool()
def fixed_messages(language: str) -> dict:
    """All fixed replies (help, errors, reminders, STOP) for a language, for wording review."""
    return {key: answer.message(key, language) for key in L.MESSAGES["en"]}


if __name__ == "__main__":
    mcp.run()

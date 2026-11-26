"""The MCP tools wrap the same engine."""

import asyncio

from ghost_signal import mcp_server
from tests.test_answer_and_app import offline  # noqa: F401


def test_tools_are_listed():
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert {"ask", "check_sms", "detect_language", "wikipedia_search", "fixed_messages"} <= names


def test_ask_and_check():
    r = mcp_server.ask("dengue", "KE")
    assert r["kind"] == "answer" and r["segments"] <= 3
    assert mcp_server.check_sms("ສະບາຍດີ")["encoding"] == "UCS-2"
    assert mcp_server.detect_language("دنگی چیست", "IR") == "fa"
    assert set(mcp_server.fixed_messages("lo")) >= {"help", "stopped"}

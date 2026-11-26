# Design: MCP server

- `mcp.server.fastmcp.FastMCP`, one decorated function per tool, all calling the same
  modules the web server uses (no duplicated logic).
- The Kiro config sets `GHOST_USE_LLM=false` and an in-memory DB so the tools are free and
  leave no state; `check_sms`, `detect_language` and `fixed_messages` are auto-approved
  because they make no network calls.
- Used by the `language-reviewer` agent and the `help-and-readme-sync` hook.

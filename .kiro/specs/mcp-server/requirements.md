# Requirements: Ghost Signal as an MCP server

## Introduction
While building, we want Kiro's agent to try real messages in many languages and check SMS
rules without a phone. Exposing the engine over MCP makes Ghost Signal itself a Kiro tool.

## Requirement 1: Tools
**User Story:** As a builder in Kiro, I want to call the real engine from the agent, so that reviews and hooks use real replies.
1. THE server SHALL offer `ask(text, country)` returning the reply exactly as the phone gets it, with parts and encoding.
2. THE server SHALL offer `check_sms(text)`, `detect_language(text, country)`, `wikipedia_search(query, language)` and `fixed_messages(language)`.
3. THE server SHALL run over stdio with `python -m ghost_signal.mcp_server` and be configured in `.kiro/settings/mcp.json` with AI off by default.

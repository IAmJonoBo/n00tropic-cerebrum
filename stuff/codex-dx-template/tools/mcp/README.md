# MCP servers (optional)

Codex supports the Model Context Protocol (MCP) to grant _specific_ tools or documentation to the agent.
Configure servers in your `~/.codex/config.toml` using entries like:

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
```

Quick start:

- Add via CLI: `codex mcp add context7 -- npx -y @upstash/context7-mcp`
- Inspect active servers in the Codex TUI with `/mcp`

Keep MCP access minimal. Prefer read‑only docs; avoid write‑capable tools unless strictly required.

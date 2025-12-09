# n00 Docs MCP Server

A Model Context Protocol (MCP) server that exposes n00 Cerebrum documentation as read‑only tools.

## Features

- `list_tags()` — return all unique tags from documentation pages.
- `search(query)` — full-text search across all docs.
- `get_page(id)` — fetch an individual page (rendered HTML if available, otherwise AsciiDoc).

## Deploy locally

1. (Recommended) Create and activate a virtualenv in the repo root.
2. Install dependencies: `pip install -r mcp/docs_server/requirements.txt`
3. Run the server from the repo root: `python mcp/docs_server/server.py`  
   Or use the shortcut: `make mcp-dev`
4. The server is read-only and only touches `docs/` and `build/site/`.

## Activate in VS Code (GitHub Copilot Agent Mode)

Prereqs:

- VS Code 1.99 or later with the GitHub Copilot extension; Agent Mode in these builds includes MCP support. citeturn1search0turn1search10
- If you’re on an org/enterprise account, ensure the “Model Context Protocol” policy is enabled (it is disabled by default). citeturn1search0

Steps:

1. Start the server (see “Deploy locally”) or let Copilot start it on demand via config.
2. Create `.vscode/mcp.json` in this workspace with:
   ```json
   {
     "servers": {
       "n00-docs": {
         "command": "python",
         "args": ["${workspaceFolder}/mcp/docs_server/server.py"]
       }
     }
   }
   ```
3. Open Copilot Chat, switch the mode dropdown to **Agent**, click the tools (🔧) icon, and choose **Edit config**; VS Code opens `mcp.json` if it isn’t already. Save the file, then click **Start** at the top of the editor to launch the server. citeturn1search8
4. In the tools list you should see `n00-docs` with the three tools above. Try a prompt like “Use n00-docs to list_tags.”

## Tools reference

- `list_tags()` → returns a sorted list of unique tags.
- `search(query: str)` → returns matching pages with `id`, `title`, `url`, `tags`, `score`.
- `get_page(id: str)` → returns page content plus metadata (HTML if built, otherwise AsciiDoc).

## Security

This server is read-only: no write operations, and file access is restricted to `docs/` and `build/site/`.

# n00 Docs MCP Server

A Model Context Protocol (MCP) server providing read-only access to n00 Cerebrum documentation.

## Features

This MCP server exposes three tools for AI agents to interact with documentation:

- **`list_tags()`** - Returns all unique tags from documentation pages
- **`search(query)`** - Full-text search across all documentation pages
- **`get_page(id)`** - Retrieve a specific page by its ID

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running Locally

```bash
# From the repository root
python mcp/docs_server/server.py

# Or use the Makefile target
make mcp-dev
```

### MCP Client Configuration

Add this to your MCP client configuration (e.g., Claude Desktop, Cline):

```json
{
  "mcpServers": {
    "n00-docs": {
      "command": "python",
      "args": ["/path/to/n00tropic-cerebrum/mcp/docs_server/server.py"]
    }
  }
}
```

## Tools Reference

### list_tags()

Lists all unique tags found across documentation pages.

**Returns:** `list[str]` - Sorted list of unique tags

**Example:**

```python
tags = list_tags()
# Returns: ['diataxis:reference', 'domain:platform', 'audience:contrib', ...]
```

### search(query: str)

Searches documentation pages for the given query string.

**Parameters:**

- `query` (str): Search query string

**Returns:** `list[dict]` - List of matching pages with:

- `id` - Page identifier
- `title` - Page title
- `url` - Relative URL
- `tags` - List of page tags
- `score` - Match score

**Example:**

```python
results = search("antora migration")
# Returns pages containing the search terms, sorted by relevance
```

### get_page(id: str)

Retrieves a documentation page by its ID.

**Parameters:**

- `id` (str): Page identifier (relative path without extension, e.g., "index" or "search/index")

**Returns:** `dict` - Page data:

- `id` - Page identifier
- `format` - Content format ("html" or "asciidoc")
- `content` - Page content
- `title` - Page title (asciidoc format only)
- `tags` - Page tags (asciidoc format only)

**Example:**

```python
page = get_page("index")
# Returns the index page content and metadata
```

## Allowed Paths

The server only accesses:

- `docs/` - AsciiDoc source files
- `build/site/` - Built HTML files

All paths are restricted to the repository root.

## Development

To modify the server:

1. Edit `server.py`
2. Test locally: `python mcp/docs_server/server.py`
3. Verify tools work as expected with an MCP client

## Security

This is a **read-only** server. It provides no write capabilities and only accesses documentation files within the repository.

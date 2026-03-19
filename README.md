# `paprika-mcp`

This is an MCP server for the [Paprika recipe manager](https://www.paprikaapp.com).

> **Disclaimer:** This project is not affiliated with, endorsed by, or in any way associated with Paprika or its developers.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
# Edit .env with your Paprika email and password
```

## Tools

| Tool | Description |
|------|-------------|
| `list_recipes` | List all recipes (name, uid, categories, rating) |
| `get_recipe` | Get full recipe details by UID |
| `search_recipes` | Search recipes by keyword across names, ingredients, descriptions, and notes |
| `list_categories` | List all recipe categories |

## Usage with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "paprika": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/paprika-mcp", "paprika-mcp"],
      "env": {
        "PAPRIKA_EMAIL": "your-email@example.com",
        "PAPRIKA_PASSWORD": "your-password"
      }
    }
  }
}
```

## Usage with Claude Code

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "paprika": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/paprika-mcp", "paprika-mcp"],
      "env": {
        "PAPRIKA_EMAIL": "your-email@example.com",
        "PAPRIKA_PASSWORD": "your-password"
      }
    }
  }
}
```

## Development

Test with the built-in MCP Inspector:

```bash
PAPRIKA_EMAIL=you@example.com PAPRIKA_PASSWORD=yourpass \
  uv run fastmcp dev inspector src/paprika_mcp/server.py:mcp --with-editable .
```

This opens a web UI where you can call each tool interactively.


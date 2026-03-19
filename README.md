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

Test tools from the command line:

```bash
uv run fastmcp call src/paprika_mcp/server.py list_categories
uv run fastmcp call src/paprika_mcp/server.py list_recipes
uv run fastmcp call src/paprika_mcp/server.py search_recipes '{"query": "chicken"}'
uv run fastmcp call src/paprika_mcp/server.py get_recipe '{"uid": "some-recipe-uid"}'
```


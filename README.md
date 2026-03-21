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

## Remote deployment (Koyeb)

Deploy as a Docker container on [Koyeb](https://www.koyeb.com) (free tier, Frankfurt EU region) so you can use it from Claude on your phone.

The server doesn't store any Paprika passwords. Users authenticate with their own Paprika email/password via HTTP Basic auth. The server only allows emails in the `ALLOWED_EMAIL` list — Paprika itself validates the password.

### 1. Deploy to Koyeb

Install the CLI and log in:

```bash
brew install koyeb/tap/koyeb
koyeb login
```

Push this repo to GitHub, then deploy:

```bash
koyeb app create paprika-mcp

koyeb service create paprika-mcp \
  --app paprika-mcp \
  --git github.com/deutschmn/paprika-mcp \
  --git-branch main \
  --git-builder docker \
  --regions fra \
  --port 8000:http \
  --route /:8000 \
  --env "MCP_TRANSPORT=http" \
  --env "PORT=8000" \
  --env "ALLOWED_EMAIL=you@example.com"
```

Your server URL will be `https://paprika-mcp-YOUR_USER.koyeb.app/mcp`.

Check status:

```bash
koyeb service list --app paprika-mcp
```

### 2. Connect from Claude (mobile/web)

In Claude.ai, go to **Settings > Connectors > Add Connector** and add your server URL. Use your Paprika email and password when prompted for credentials.

### 3. Test the deployment

```bash
curl -u "you@example.com:your-paprika-password" https://your-app-name.koyeb.app/mcp
```

### Local Docker testing

```bash
docker build -t paprika-mcp .
docker run --rm -p 8000:8000 \
  -e ALLOWED_EMAIL="you@example.com" \
  -e MCP_TRANSPORT=http \
  paprika-mcp
```

```bash
curl -u "you@example.com:your-paprika-password" http://localhost:8000/mcp
```

## Development

### One-off tool calls

Each invocation starts a fresh server (no cache persistence):

```bash
uv run fastmcp call src/paprika_mcp/server.py list_categories
uv run fastmcp call src/paprika_mcp/server.py list_recipes
uv run fastmcp call src/paprika_mcp/server.py search_recipes '{"query": "chicken"}'
uv run fastmcp call src/paprika_mcp/server.py get_recipe '{"uid": "some-recipe-uid"}'
```

### Running a persistent server

Start the server on HTTP so the recipe cache stays warm across calls:

```bash
uv run fastmcp run src/paprika_mcp/server.py --transport streamable-http --port 8000
```

Then call tools against the running server:

```bash
uv run fastmcp call http://localhost:8000/mcp list_recipes
uv run fastmcp call http://localhost:8000/mcp search_recipes '{"query": "chicken"}'
uv run fastmcp call http://localhost:8000/mcp get_recipe '{"uid": "some-recipe-uid"}'
```


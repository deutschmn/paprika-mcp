FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cache layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy source
COPY src/ src/
COPY README.md ./
RUN uv sync --no-dev

ENV MCP_TRANSPORT=http
ENV PORT=8000

EXPOSE 8000

CMD ["uv", "run", "paprika-mcp"]

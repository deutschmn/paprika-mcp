from __future__ import annotations

import contextvars
import logging
import os
import sys

from fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")
log = logging.getLogger("paprika-mcp")

try:
    from .client import PaprikaClient, get_client
except ImportError:
    from client import PaprikaClient, get_client

mcp = FastMCP("Paprika Recipes")

_client_instance: PaprikaClient | None = None
_recipe_cache: dict[str, dict] = {}
_hash_cache: dict[str, str] = {}

# Set by auth middleware in HTTP mode
_current_password: contextvars.ContextVar[str] = contextvars.ContextVar("current_password")


def _client() -> PaprikaClient:
    global _client_instance
    try:
        password = _current_password.get()
        email = os.environ["ALLOWED_EMAIL"]
        if _client_instance is None or _client_instance.password != password:
            _client_instance = PaprikaClient(email, password)
    except LookupError:
        if _client_instance is None:
            _client_instance = get_client()
    return _client_instance


async def _refresh_cache() -> None:
    """Fetch recipe list and update cache for new/changed recipes."""
    client = _client()
    log.info("Fetching recipe list...")
    summaries = client.list_recipes()
    current_uids = {s["uid"] for s in summaries}

    to_fetch = [
        s["uid"] for s in summaries
        if _hash_cache.get(s["uid"]) != s.get("hash")
    ]

    if to_fetch:
        log.info("Fetching %d/%d recipes concurrently...", len(to_fetch), len(summaries))
        recipes = await client.get_recipes_batch(to_fetch)
        for uid, recipe in zip(to_fetch, recipes):
            _recipe_cache[uid] = recipe
            _hash_cache[uid] = next(
                s.get("hash", "") for s in summaries if s["uid"] == uid
            )
        log.info("Done fetching recipes.")
    else:
        log.info("All %d recipes cached, no changes.", len(summaries))

    for uid in list(_recipe_cache):
        if uid not in current_uids:
            del _recipe_cache[uid]
            del _hash_cache[uid]


def _recipe_summary(recipe: dict) -> dict:
    return {
        "uid": recipe.get("uid", ""),
        "name": recipe.get("name", ""),
        "categories": recipe.get("categories", []),
        "rating": recipe.get("rating", 0),
        "on_favorites": recipe.get("on_favorites", False),
    }


@mcp.tool()
async def list_recipes() -> list[dict]:
    """List all recipes in your Paprika library. Returns name, uid, categories, and rating for each recipe."""
    await _refresh_cache()
    return [_recipe_summary(r) for r in _recipe_cache.values()]


@mcp.tool()
async def get_recipe(uid: str) -> dict:
    """Get complete details for a recipe by its UID. Includes ingredients, directions, prep/cook time, servings, notes, source, and more."""
    if uid not in _recipe_cache:
        recipes = await _client().get_recipes_batch([uid])
        _recipe_cache[uid] = recipes[0]
    return _recipe_cache[uid]


@mcp.tool()
async def search_recipes(query: str) -> list[dict]:
    """Search recipes by keyword. Searches across recipe names, ingredients, descriptions, and notes. Returns matching recipes."""
    await _refresh_cache()
    query_lower = query.lower()
    results = []
    for recipe in _recipe_cache.values():
        searchable = " ".join(
            str(recipe.get(field, ""))
            for field in ("name", "ingredients", "description", "notes", "directions")
        ).lower()
        if query_lower in searchable:
            results.append(_recipe_summary(recipe))
    return results


@mcp.tool()
def list_categories() -> list[dict]:
    """List all recipe categories."""
    return _client().list_categories()


def _auth_middleware():
    """ASGI middleware that checks email matches ALLOWED_EMAIL and passes password through."""
    import base64

    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    allowed = os.environ.get("ALLOWED_EMAIL", "").lower()

    class EmailAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            auth = request.headers.get("authorization", "")
            if auth.startswith("Basic "):
                try:
                    decoded = base64.b64decode(auth[6:]).decode()
                    email, password = decoded.split(":", 1)
                    if email.lower() == allowed:
                        _current_password.set(password)
                        return await call_next(request)
                except Exception:
                    pass
            return JSONResponse({"error": "unauthorized"}, status_code=401)

    return Middleware(EmailAuthMiddleware)


def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn

        middleware = []
        allowed = os.environ.get("ALLOWED_EMAIL", "")
        if allowed:
            middleware.append(_auth_middleware())
            log.info("Auth enabled for %s", allowed)

        app = mcp.http_app(
            transport="streamable-http",
            middleware=middleware,
        )
        port = int(os.environ.get("PORT", "8000"))
        uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

from __future__ import annotations

import logging
import os
import re
import sys
import uuid

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


def _client() -> PaprikaClient:
    global _client_instance
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
            _hash_cache.pop(uid, None)


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


_UID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_uid(uid: str) -> None:
    if not uid or len(uid) > 200 or not _UID_RE.match(uid):
        raise ValueError(f"Invalid recipe UID: {uid!r}")


@mcp.tool()
async def get_recipe(uid: str) -> dict:
    """Get complete details for a recipe by its UID. Includes ingredients, directions, prep/cook time, servings, notes, source, and more."""
    _validate_uid(uid)
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
def create_recipe(
    name: str,
    ingredients: str = "",
    directions: str = "",
    description: str = "",
    notes: str = "",
    prep_time: str = "",
    cook_time: str = "",
    total_time: str = "",
    servings: str = "",
    source: str = "",
    source_url: str = "",
    rating: int = 0,
) -> dict:
    """Create a new recipe in your Paprika library.

    Args:
        name: Recipe name (required).
        ingredients: Ingredients, one per line.
        directions: Cooking directions/instructions.
        description: Short description of the recipe.
        notes: Additional notes.
        prep_time: Preparation time (e.g. "15 min").
        cook_time: Cooking time (e.g. "30 min").
        total_time: Total time (e.g. "45 min").
        servings: Number of servings (e.g. "4").
        source: Source attribution (e.g. "Grandma's cookbook").
        source_url: URL where the recipe was found.
        rating: Rating from 0 to 5.
    """
    uid = str(uuid.uuid4()).upper()
    recipe = {
        "uid": uid,
        "name": name,
        "ingredients": ingredients,
        "directions": directions,
        "description": description,
        "notes": notes,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "total_time": total_time,
        "servings": servings,
        "source": source,
        "source_url": source_url,
        "rating": rating,
        "categories": [],
    }
    result = _client().create_recipe(recipe)
    _recipe_cache.clear()
    _hash_cache.clear()
    return {"uid": uid, "name": name, "result": result}


@mcp.tool()
def list_categories() -> list[dict]:
    """List all recipe categories."""
    return _client().list_categories()


def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn

        secret = os.environ.get("MCP_SECRET", "")
        path = f"/mcp/{secret}" if secret else "/mcp"
        if secret:
            log.info("Serving on secret path: /mcp/<secret>")

        app = mcp.http_app(
            transport="streamable-http",
            path=path,
        )

        from starlette.responses import PlainTextResponse
        from starlette.routing import Route

        app.routes.insert(0, Route("/health", lambda r: PlainTextResponse("ok")))

        port = int(os.environ.get("PORT", "8000"))
        uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

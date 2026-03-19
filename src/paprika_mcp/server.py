from __future__ import annotations

from fastmcp import FastMCP

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


def _refresh_cache() -> None:
    """Fetch recipe list and update cache for new/changed recipes."""
    client = _client()
    summaries = client.list_recipes()
    current_uids = set()

    for s in summaries:
        uid = s["uid"]
        current_uids.add(uid)
        if _hash_cache.get(uid) != s.get("hash"):
            recipe = client.get_recipe(uid)
            _recipe_cache[uid] = recipe
            _hash_cache[uid] = s.get("hash", "")

    # Remove deleted recipes
    for uid in list(_recipe_cache):
        if uid not in current_uids:
            del _recipe_cache[uid]
            del _hash_cache[uid]


def _recipe_summary(recipe: dict) -> dict:
    """Extract a lightweight summary from a full recipe."""
    return {
        "uid": recipe.get("uid", ""),
        "name": recipe.get("name", ""),
        "categories": recipe.get("categories", []),
        "rating": recipe.get("rating", 0),
        "on_favorites": recipe.get("on_favorites", False),
    }


@mcp.tool()
def list_recipes() -> list[dict]:
    """List all recipes in your Paprika library. Returns name, uid, categories, and rating for each recipe."""
    _refresh_cache()
    return [_recipe_summary(r) for r in _recipe_cache.values()]


@mcp.tool()
def get_recipe(uid: str) -> dict:
    """Get complete details for a recipe by its UID. Includes ingredients, directions, prep/cook time, servings, notes, source, and more."""
    if uid not in _recipe_cache:
        recipe = _client().get_recipe(uid)
        _recipe_cache[uid] = recipe
    return _recipe_cache[uid]


@mcp.tool()
def search_recipes(query: str) -> list[dict]:
    """Search recipes by keyword. Searches across recipe names, ingredients, descriptions, and notes. Returns matching recipes."""
    _refresh_cache()
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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

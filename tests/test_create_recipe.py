"""Integration test: create a recipe, read it back, verify fields match, then trash it."""

import hashlib
import uuid
from datetime import datetime, timezone

import pytest

from paprika_mcp.client import get_client


TEXT_FIELDS = [
    "name", "ingredients", "directions", "description", "notes",
    "prep_time", "cook_time", "total_time", "servings", "source", "source_url",
]


@pytest.fixture(scope="module")
def client():
    return get_client()


def test_create_and_read_recipe(client):
    uid = str(uuid.uuid4()).upper()
    recipe = {
        "uid": uid,
        "name": f"MCP Integration Test {uid[:8]}",
        "ingredients": "1 cup flour\n2 eggs\n1/2 cup sugar",
        "directions": "Mix dry ingredients.\nAdd eggs.\nBake at 350°F for 30 min.",
        "description": "A test recipe created by the MCP integration test suite.",
        "notes": "Delete me if you see me.",
        "nutritional_info": "",
        "servings": "4",
        "difficulty": "",
        "prep_time": "10 min",
        "cook_time": "30 min",
        "total_time": "40 min",
        "source": "MCP Test",
        "source_url": "",
        "image_url": "",
        "photo": "",
        "photo_hash": "",
        "photo_large": "",
        "scale": "",
        "hash": hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest().upper(),
        "categories": [],
        "rating": 3,
        "in_trash": False,
        "is_pinned": False,
        "on_favorites": False,
        "on_grocery_list": False,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "photo_url": "",
    }

    # Create
    client.create_recipe(recipe)

    # Read back
    fetched = client.get_recipe(uid)
    assert fetched, f"Recipe {uid} not found after creation"

    # Verify text fields round-trip correctly
    for field in TEXT_FIELDS:
        assert fetched.get(field) == recipe[field], (
            f"Field '{field}' mismatch: got {fetched.get(field)!r}, expected {recipe[field]!r}"
        )
    assert fetched.get("rating") == recipe["rating"]
    assert fetched.get("uid") == uid
    assert fetched.get("in_trash") == False

    # Cleanup: trash the recipe so it doesn't pollute the app
    client.create_recipe({**recipe, "in_trash": True})

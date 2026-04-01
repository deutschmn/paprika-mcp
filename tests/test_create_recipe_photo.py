"""Integration test: create_recipe with photo_base64 uploads the photo and links it to the recipe."""

import base64
import hashlib
import uuid

import pytest

from paprika_mcp.client import get_client
from paprika_mcp.server import create_recipe, _recipe_cache, _hash_cache

# Minimal valid JPEG: 1×1 white pixel
_MINIMAL_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000"
    "ffdb004300010101010101010101010101010101"
    "0101010101010101010101010101010101010101"
    "010101010101010101010101010101010101ffc0"
    "000b080001000101011100ffc4001f0000010501"
    "010101010100000000000000000102030405060708"
    "090a0bffda00080101000000013fffd9"
)


@pytest.fixture(autouse=True)
def clear_cache():
    _recipe_cache.clear()
    _hash_cache.clear()
    yield
    _recipe_cache.clear()
    _hash_cache.clear()


def test_create_recipe_with_photo_base64():
    client = get_client()

    result = create_recipe(
        name=f"Photo Test {uuid.uuid4().hex[:6]}",
        ingredients="1 egg",
        directions="Boil it.",
        photo_base64=base64.b64encode(_MINIMAL_JPEG).decode(),
    )

    uid = result["uid"]
    assert uid, "Expected a UID back"

    try:
        fetched = client.get_recipe(uid)
        assert fetched.get("photo"), "photo filename should be set"
        assert fetched.get("photo_hash"), "photo_hash should be set"
        assert fetched["photo"].endswith(".jpg"), "photo filename should end with .jpg"
        assert len(fetched["photo_hash"]) == 64, "photo_hash should be 64-char SHA256 hex"

        expected_hash = hashlib.sha256(_MINIMAL_JPEG).hexdigest().upper()
        assert fetched["photo_hash"] == expected_hash, "photo_hash should match SHA256 of uploaded bytes"
    finally:
        raw = client.get_recipe(uid)
        client.create_recipe({**raw, "in_trash": True})


def test_create_recipe_without_photo():
    """Ensure photo-less creation still works and photo fields remain empty."""
    client = get_client()

    result = create_recipe(name=f"No Photo {uuid.uuid4().hex[:6]}")
    uid = result["uid"]

    try:
        fetched = client.get_recipe(uid)
        assert fetched.get("photo", "") == "", "photo should be empty"
        assert fetched.get("photo_hash", "") == "", "photo_hash should be empty"
    finally:
        raw = client.get_recipe(uid)
        client.create_recipe({**raw, "in_trash": True})

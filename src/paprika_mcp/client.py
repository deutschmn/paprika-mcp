from __future__ import annotations

import asyncio
import base64
import gzip
import json
import os
import stat
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.paprikaapp.com/api"
TOKEN_PATH = Path.home() / ".paprika-mcp-token.json"
MAX_CONCURRENT = 30


class PaprikaClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self._token: str | None = self._load_cached_token()

    def _load_cached_token(self) -> str | None:
        try:
            data = json.loads(TOKEN_PATH.read_text())
            return data.get("token")
        except Exception:
            return None

    def _save_cached_token(self, token: str) -> None:
        try:
            TOKEN_PATH.write_text(json.dumps({"token": token}))
            TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    def _authenticate(self) -> str:
        credentials = base64.b64encode(f"{self.email}:{self.password}".encode()).decode()
        response = httpx.post(
            f"{BASE_URL}/v1/account/login/",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"email": self.email, "password": self.password},
        )
        response.raise_for_status()
        token = response.json()["result"]["token"]
        self._token = token
        self._save_cached_token(token)
        return token

    def _ensure_token(self) -> str:
        if not self._token:
            self._authenticate()
        return self._token  # type: ignore[return-value]

    def _request(self, method: str, path: str) -> dict:
        token = self._ensure_token()

        def do_request() -> httpx.Response:
            return httpx.request(
                method,
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = do_request()

        if resp.status_code == 401:
            self._token = None
            self._authenticate()
            resp = do_request()

        resp.raise_for_status()
        return self._parse_response(resp)

    async def _async_request(self, client: httpx.AsyncClient, path: str) -> dict:
        resp = await client.get(f"{BASE_URL}{path}")
        if resp.status_code == 401:
            self._token = None
            self._authenticate()
            client.headers["Authorization"] = f"Bearer {self._token}"
            resp = await client.get(f"{BASE_URL}{path}")
        resp.raise_for_status()
        return self._parse_response(resp)

    def _parse_response(self, resp: httpx.Response) -> dict:
        result = resp.json().get("result", [])
        if isinstance(result, list):
            return {"items": [self._decompress(item) if isinstance(item, dict) and "data" in item else item for item in result]}
        if isinstance(result, dict) and "data" in result:
            return self._decompress(result)
        return result if isinstance(result, dict) else {"result": result}

    @staticmethod
    def _decompress(item: dict) -> dict:
        try:
            raw = base64.b64decode(item["data"])
            return json.loads(gzip.decompress(raw))
        except Exception:
            return item

    @staticmethod
    def _compress(data: dict) -> str:
        raw = json.dumps(data).encode()
        return base64.b64encode(gzip.compress(raw)).decode()

    def _post_request(self, path: str, data: dict) -> dict:
        token = self._ensure_token()

        def do_request() -> httpx.Response:
            return httpx.post(
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
                data=data,
            )

        resp = do_request()

        if resp.status_code == 401:
            self._token = None
            self._authenticate()
            resp = do_request()

        resp.raise_for_status()
        return self._parse_response(resp)

    def list_recipes(self) -> list[dict]:
        """Get lightweight recipe list (uid + hash only)."""
        result = self._request("GET", "/v2/sync/recipes/")
        return result.get("items", [])

    def get_recipe(self, uid: str) -> dict:
        """Get full recipe details by UID."""
        return self._request("GET", f"/v2/sync/recipe/{uid}/")

    async def get_recipes_batch(self, uids: list[str]) -> list[dict]:
        """Fetch multiple recipes concurrently."""
        token = self._ensure_token()
        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def fetch_one(client: httpx.AsyncClient, uid: str) -> dict:
            async with sem:
                return await self._async_request(client, f"/v2/sync/recipe/{uid}/")

        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        ) as client:
            tasks = [fetch_one(client, uid) for uid in uids]
            return await asyncio.gather(*tasks)

    def create_recipe(self, recipe: dict) -> dict:
        """Create or update a recipe. The recipe dict must include a 'uid' field."""
        uid = recipe["uid"]
        compressed = self._compress(recipe)
        return self._post_request(f"/v2/sync/recipe/{uid}/", {"data": compressed})

    def list_categories(self) -> list[dict]:
        """Get all recipe categories."""
        result = self._request("GET", "/v2/sync/categories/")
        return result.get("items", [])


def get_client() -> PaprikaClient:
    email = os.environ.get("PAPRIKA_EMAIL")
    password = os.environ.get("PAPRIKA_PASSWORD")
    if not email or not password:
        raise ValueError("Set PAPRIKA_EMAIL and PAPRIKA_PASSWORD environment variables")
    return PaprikaClient(email, password)

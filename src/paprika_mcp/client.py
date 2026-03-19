from __future__ import annotations

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

    def _request(self, method: str, path: str) -> dict:
        if not self._token:
            self._authenticate()

        def do_request() -> httpx.Response:
            return httpx.request(
                method,
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
            )

        resp = do_request()

        # Retry once on 401 (expired token)
        if resp.status_code == 401:
            self._token = None
            self._authenticate()
            resp = do_request()

        resp.raise_for_status()

        # Paprika API returns gzipped JSON in the result field
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

    def list_recipes(self) -> list[dict]:
        """Get lightweight recipe list (uid + hash only)."""
        result = self._request("GET", "/v2/sync/recipes/")
        return result.get("items", [])

    def get_recipe(self, uid: str) -> dict:
        """Get full recipe details by UID."""
        return self._request("GET", f"/v2/sync/recipe/{uid}/")

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

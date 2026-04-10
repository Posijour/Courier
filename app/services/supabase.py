from typing import Any

import httpx

from app.config import settings


class SupabaseError(RuntimeError):
    pass


class SupabaseClient:
    def __init__(self, url: str, key: str, timeout: float = 15.0) -> None:
        self.base_url = url.rstrip("/")
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }
        self.timeout = timeout

    async def select(
        self,
        table: str,
        params: dict[str, Any],
        *,
        single: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        data = await self._request("GET", f"/rest/v1/{table}", params=params)
        if single:
            return data[0] if data else None
        return data

    async def insert(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        upsert: bool = False,
    ) -> dict[str, Any] | None:
        prefer = ["return=representation"]
        if upsert:
            prefer.append("resolution=merge-duplicates")
        data = await self._request(
            "POST",
            f"/rest/v1/{table}",
            params=params,
            json=payload,
            headers={"Prefer": ",".join(prefer)},
        )
        return data[0] if data else None

    async def rpc(self, function_name: str, payload: dict[str, Any]) -> Any:
        return await self._request("POST", f"/rest/v1/rpc/{function_name}", json=payload)

    async def update(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        data = await self._request(
            "PATCH",
            f"/rest/v1/{table}",
            params=params,
            json=payload,
            headers={"Prefer": "return=representation"},
        )
        return data[0] if data else None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json,
                headers=request_headers,
            )

        if response.is_error:
            try:
                payload = response.json()
            except Exception:
                payload = response.text
            raise SupabaseError(f"Supabase error {response.status_code}: {payload}")

        if not response.content:
            return None
        return response.json()


supabase = SupabaseClient(
    url=settings.supabase_url,
    key=settings.supabase_key,
    timeout=settings.supabase_timeout_seconds,
)

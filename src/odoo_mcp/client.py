from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from .config import OdooConfig


class OdooJson2Error(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OdooJson2Client:
    def __init__(self, config: OdooConfig) -> None:
        self.config = config

    def call(self, model: str, method: str, **kwargs: Any) -> Any:
        url = f"{self.config.url}/json/2/{model}/{method}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "X-odoo-database": self.config.database,
        }

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(url, headers=headers, json=kwargs)
        except httpx.HTTPError as exc:
            raise OdooJson2Error(f"Could not connect to Odoo: {exc}") from exc

        if response.status_code >= 400:
            raise OdooJson2Error(
                self._error_message(response),
                status_code=response.status_code,
            )

        return response.json()

    def context_get(self) -> dict[str, Any]:
        result = self.call("res.users", "context_get")
        if not isinstance(result, dict):
            raise OdooJson2Error("Odoo returned an invalid context_get response")
        return result

    def search_read(
        self,
        model: str,
        domain: Sequence[Any],
        fields: Sequence[str] | None = None,
        *,
        offset: int = 0,
        limit: int | None = 20,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "domain": list(domain),
            "offset": offset,
        }
        if fields is not None:
            kwargs["fields"] = list(fields)
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order

        result = self.call(model, "search_read", **kwargs)
        if not isinstance(result, list):
            raise OdooJson2Error("Odoo returned an invalid search_read response")
        return result

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = None

        if isinstance(body, dict):
            message = body.get("message")
            if isinstance(message, str) and message:
                return message

        text = response.text.strip()
        if text:
            return text
        return f"Odoo request failed with HTTP {response.status_code}"

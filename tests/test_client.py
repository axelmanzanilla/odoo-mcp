from __future__ import annotations

import json

import httpx
import pytest

from odoo_mcp.client import OdooJson2Client, OdooJson2Error
from odoo_mcp.config import OdooConfig


def test_call_builds_json2_request() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = request.read().decode()
        return httpx.Response(200, json=[{"id": 1, "name": "Task"}])

    client = OdooJson2Client(
        OdooConfig(
            url="https://example.odoo.com",
            database="example",
            api_key="secret",
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.search_read(
        "project.task",
        [["id", "=", 1]],
        ["id", "name"],
        limit=5,
        order="id desc",
    )

    assert result == [{"id": 1, "name": "Task"}]
    assert captured["url"] == "https://example.odoo.com/json/2/project.task/search_read"
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert captured["headers"]["x-odoo-database"] == "example"
    assert json.loads(captured["body"]) == {
        "domain": [["id", "=", 1]],
        "offset": 0,
        "fields": ["id", "name"],
        "limit": 5,
        "order": "id desc",
    }


def test_call_raises_odoo_error_message() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"message": "Invalid apikey"})
    )

    client = OdooJson2Client(
        OdooConfig(
            url="https://example.odoo.com",
            database="example",
            api_key="bad",
        ),
        http_client=httpx.Client(transport=transport),
    )

    with pytest.raises(OdooJson2Error) as exc:
        client.context_get()

    assert str(exc.value) == "Invalid apikey"
    assert exc.value.status_code == 401

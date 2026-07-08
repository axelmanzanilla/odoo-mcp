from __future__ import annotations

import httpx
import pytest

from odoo_mcp.client import OdooJson2Client, OdooJson2Error
from odoo_mcp.config import OdooConfig


def test_call_builds_json2_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = request.read().decode()
        return httpx.Response(200, json=[{"id": 1, "name": "Task"}])

    transport = httpx.MockTransport(handler)

    def client_factory(*args, **kwargs):
        return original_client(transport=transport)

    monkeypatch.setattr(httpx, "Client", client_factory)

    client = OdooJson2Client(
        OdooConfig(
            url="https://example.odoo.com",
            database="example",
            api_key="secret",
        )
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
    assert '"domain":[["id","=",1]]' in captured["body"].replace(" ", "")
    assert '"fields":["id","name"]' in captured["body"].replace(" ", "")
    assert '"limit":5' in captured["body"].replace(" ", "")
    assert '"order":"id desc"' in captured["body"].replace(" ", "")


def test_call_raises_odoo_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    original_client = httpx.Client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"message": "Invalid apikey"})
    )

    def client_factory(*args, **kwargs):
        return original_client(transport=transport)

    monkeypatch.setattr(httpx, "Client", client_factory)

    client = OdooJson2Client(
        OdooConfig(
            url="https://example.odoo.com",
            database="example",
            api_key="bad",
        )
    )

    with pytest.raises(OdooJson2Error) as exc:
        client.context_get()

    assert str(exc.value) == "Invalid apikey"
    assert exc.value.status_code == 401

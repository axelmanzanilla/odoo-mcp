from __future__ import annotations

from typing import Any

import pytest

from odoo_mcp.client import OdooJson2Error
from odoo_mcp.tools import (
    DEFAULT_TASK_FIELDS,
    DEFAULT_TASK_ORDER,
    TASK_DETAIL_FIELDS,
    get_task,
    list_my_tasks,
)


class FakeClient:
    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context
        self.search_read_calls: list[dict[str, Any]] = []

    def context_get(self) -> dict[str, Any]:
        return self.context

    def search_read(self, model, domain, fields=None, *, offset=0, limit=20, order=None):
        self.search_read_calls.append(
            {
                "model": model,
                "domain": domain,
                "fields": fields,
                "offset": offset,
                "limit": limit,
                "order": order,
            }
        )
        return [
            {
                "id": 10,
                "name": "Test task",
                "project_id": [3, "Project"],
                "stage_id": False,
                "state": "01_in_progress",
                "priority": "2",
            }
        ]


def test_list_my_tasks_uses_numeric_uid_domain() -> None:
    client = FakeClient({"uid": 42})

    result = list_my_tasks(client, limit=7, offset=2)

    assert result == [
        {
            "id": 10,
            "name": "Test task",
            "project_id": [3, "Project"],
            "project_id_display": {"id": 3, "name": "Project"},
            "stage_id": False,
            "stage_id_display": None,
            "state": "01_in_progress",
            "state_display": "In Progress",
            "priority": "2",
            "priority_display": "High priority",
        }
    ]
    assert client.search_read_calls == [
        {
            "model": "project.task",
            "domain": [
                ["user_ids", "in", 42],
                ["has_template_ancestor", "=", False],
                ["has_project_template", "=", False],
            ],
            "fields": DEFAULT_TASK_FIELDS,
            "offset": 2,
            "limit": 7,
            "order": DEFAULT_TASK_ORDER,
        }
    ]


def test_list_my_tasks_rejects_missing_uid() -> None:
    client = FakeClient({})

    with pytest.raises(OdooJson2Error, match="numeric uid"):
        list_my_tasks(client)


def test_get_task_reads_one_task_by_id() -> None:
    client = FakeClient({"uid": 42})

    result = get_task(client, 10)

    assert result["id"] == 10
    assert result["state_display"] == "In Progress"
    assert result["priority_display"] == "High priority"
    assert client.search_read_calls == [
        {
            "model": "project.task",
            "domain": [["id", "=", 10]],
            "fields": TASK_DETAIL_FIELDS,
            "offset": 0,
            "limit": 1,
            "order": None,
        }
    ]


def test_get_task_reports_missing_task() -> None:
    class EmptyClient(FakeClient):
        def search_read(self, model, domain, fields=None, *, offset=0, limit=20, order=None):
            return []

    with pytest.raises(OdooJson2Error, match="not found"):
        get_task(EmptyClient({"uid": 42}), 99)

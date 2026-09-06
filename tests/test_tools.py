from __future__ import annotations

from typing import Any

import pytest

from odoo_mcp.client import OdooJson2Error
from odoo_mcp.tools import (
    ASSIGNMENT_MESSAGE_FIELDS,
    ASSIGNMENT_TRACKING_FIELDS,
    DEFAULT_TASK_FIELDS,
    DEFAULT_TASK_ORDER,
    MAX_ACTIVITY_RECORDS,
    TASK_DETAIL_FIELDS,
    TIMESHEET_ACTIVITY_FIELDS,
    get_task,
    list_my_tasks,
    list_my_worked_tasks,
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


class WorkedTasksClient:
    def __init__(self, *, tracking_error: OdooJson2Error | None = None) -> None:
        self.tracking_error = tracking_error
        self.search_read_calls: list[dict[str, Any]] = []

    def context_get(self) -> dict[str, Any]:
        return {"uid": 42, "tz": "America/Mexico_City"}

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
        if model == "res.users":
            return [
                {
                    "id": 42,
                    "name": "Axel Rodrigo Manzanilla Martin (armm)",
                    "tz": "America/Mexico_City",
                }
            ]
        if model == "mail.tracking.value":
            if self.tracking_error:
                raise self.tracking_error
            return [
                {
                    "id": 100,
                    "old_value_char": "",
                    "new_value_char": "Axel Rodrigo Manzanilla Martin (armm)",
                    "mail_message_id": [200, False],
                },
                {
                    "id": 101,
                    "old_value_char": "Axel Rodrigo Manzanilla Martin (armm)",
                    "new_value_char": ("Axel Rodrigo Manzanilla Martin (armm), Another User"),
                    "mail_message_id": [201, False],
                },
            ]
        if model == "mail.message":
            return [
                {
                    "id": 200,
                    "date": "2024-01-02 05:30:00",
                    "res_id": 10,
                    "author_id": [7, "Project Manager"],
                }
            ]
        if model == "account.analytic.line":
            return [
                {
                    "id": 300,
                    "date": "2024-01-03",
                    "unit_amount": 2.0,
                    "task_id": [10, "Assigned and timesheeted"],
                },
                {
                    "id": 301,
                    "date": "2024-01-02",
                    "unit_amount": 1.5,
                    "task_id": [11, "Timesheet only"],
                },
            ]
        if model == "project.task":
            return [
                {
                    "id": 10,
                    "name": "Assigned and timesheeted",
                    "project_id": [3, "Project"],
                    "stage_id": [4, "In Progress"],
                    "state": "01_in_progress",
                    "priority": "1",
                    "user_ids": [],
                },
                {
                    "id": 11,
                    "name": "Timesheet only",
                    "project_id": [3, "Project"],
                    "stage_id": [4, "In Progress"],
                    "state": "01_in_progress",
                    "priority": "0",
                    "user_ids": [42],
                },
            ]
        raise AssertionError(f"Unexpected model: {model}")


def test_list_my_worked_tasks_combines_assignments_and_timesheets() -> None:
    client = WorkedTasksClient()

    result = list_my_worked_tasks(client, "2024-01-01", "2024-01-31")

    assert result["user"] == {"id": 42, "name": "Axel Rodrigo Manzanilla Martin (armm)"}
    assert result["period"] == {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "timezone": "America/Mexico_City",
    }
    assert result["source_status"] == {
        "assignment_history": True,
        "timesheets": True,
    }
    assert result["warnings"] == []
    assert result["total"] == 2
    assert [task["id"] for task in result["tasks"]] == [10, 11]

    task = result["tasks"][0]
    assert task["activity_sources"] == ["assignment", "timesheet"]
    assert task["last_activity_date"] == "2024-01-03"
    assert task["assignment_activity"] == {
        "event_count": 1,
        "events": [
            {
                "assigned_at": "2024-01-01T23:30:00-06:00",
                "assigned_by": {"id": 7, "name": "Project Manager"},
            }
        ],
    }
    assert task["timesheet_activity"] == {
        "entry_count": 1,
        "total_hours": 2.0,
        "dates": ["2024-01-03"],
    }

    assert client.search_read_calls[:5] == [
        {
            "model": "res.users",
            "domain": [["id", "=", 42]],
            "fields": ["id", "name", "tz"],
            "offset": 0,
            "limit": 1,
            "order": None,
        },
        {
            "model": "mail.tracking.value",
            "domain": [
                ["field_id.model", "=", "project.task"],
                ["field_id.name", "=", "user_ids"],
                ["mail_message_id.model", "=", "project.task"],
                ["mail_message_id.date", ">=", "2024-01-01 06:00:00"],
                ["mail_message_id.date", "<", "2024-02-01 06:00:00"],
                ["new_value_char", "ilike", "Axel Rodrigo Manzanilla Martin (armm)"],
            ],
            "fields": ASSIGNMENT_TRACKING_FIELDS,
            "offset": 0,
            "limit": MAX_ACTIVITY_RECORDS + 1,
            "order": "id desc",
        },
        {
            "model": "mail.message",
            "domain": [["id", "in", [200]], ["model", "=", "project.task"]],
            "fields": ASSIGNMENT_MESSAGE_FIELDS,
            "offset": 0,
            "limit": 1,
            "order": "date desc, id desc",
        },
        {
            "model": "account.analytic.line",
            "domain": [
                ["user_id", "=", 42],
                ["task_id", "!=", False],
                ["date", ">=", "2024-01-01"],
                ["date", "<=", "2024-01-31"],
            ],
            "fields": TIMESHEET_ACTIVITY_FIELDS,
            "offset": 0,
            "limit": MAX_ACTIVITY_RECORDS + 1,
            "order": "date desc, id desc",
        },
        {
            "model": "project.task",
            "domain": [
                ["id", "in", [10, 11]],
                ["has_template_ancestor", "=", False],
                ["has_project_template", "=", False],
            ],
            "fields": DEFAULT_TASK_FIELDS,
            "offset": 0,
            "limit": 2,
            "order": None,
        },
    ]


def test_list_my_worked_tasks_reports_unavailable_assignment_history() -> None:
    client = WorkedTasksClient(tracking_error=OdooJson2Error("Access denied"))

    result = list_my_worked_tasks(client, "2024-01-01", "2024-01-31", limit=1)

    assert result["source_status"] == {
        "assignment_history": False,
        "timesheets": True,
    }
    assert result["warnings"] == ["Assignment history is unavailable: Access denied"]
    assert result["total"] == 2
    assert result["tasks"][0]["activity_sources"] == ["timesheet"]


@pytest.mark.parametrize(
    ("start_date", "end_date", "message"),
    [
        ("January 2024", "2024-01-31", "start_date must use YYYY-MM-DD"),
        ("2024-02-01", "2024-01-31", "end_date must be on or after start_date"),
    ],
)
def test_list_my_worked_tasks_validates_period(
    start_date: str,
    end_date: str,
    message: str,
) -> None:
    with pytest.raises(OdooJson2Error, match=message):
        list_my_worked_tasks(WorkedTasksClient(), start_date, end_date)

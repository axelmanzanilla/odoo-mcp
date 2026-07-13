from __future__ import annotations

from collections.abc import Sequence
from html.parser import HTMLParser
from typing import Any

from .client import OdooJson2Client, OdooJson2Error

DEFAULT_LIMIT = 20
DEFAULT_TASK_ORDER = "priority desc, sequence, date_deadline asc, id desc"
DEFAULT_TASK_FIELDS = [
    "id",
    "name",
    "display_name",
    "description",
    "project_id",
    "stage_id",
    "state",
    "priority",
    "date_deadline",
    "user_ids",
    "tag_ids",
    "write_date",
]
TASK_DETAIL_FIELDS = [
    *DEFAULT_TASK_FIELDS,
    "create_date",
    "date_assign",
    "date_last_stage_update",
    "allocated_hours",
    "partner_id",
    "company_id",
    "parent_id",
    "child_ids",
    "subtask_count",
]
TASK_STATE_LABELS = {
    "01_in_progress": "In Progress",
    "02_changes_requested": "Changes Requested",
    "03_approved": "Approved",
    "1_done": "Done",
    "1_canceled": "Canceled",
    "04_waiting_normal": "Waiting",
}
TASK_PRIORITY_LABELS = {
    "0": "Low priority",
    "1": "Medium priority",
    "2": "High priority",
    "3": "Urgent",
}
DEFAULT_MESSAGE_ORDER = "date desc, id desc"
DEFAULT_MESSAGE_FIELDS = [
    "id",
    "date",
    "author_id",
    "email_from",
    "message_type",
    "subtype_id",
    "subject",
    "body",
]


def odoo_context(client: OdooJson2Client) -> dict[str, Any]:
    return client.context_get()


def odoo_search_read(
    client: OdooJson2Client,
    model: str,
    domain: Sequence[Any],
    fields: Sequence[str] | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order: str | None = None,
) -> list[dict[str, Any]]:
    return client.search_read(
        model,
        domain,
        fields,
        limit=limit,
        offset=offset,
        order=order,
    )


def list_my_tasks(
    client: OdooJson2Client,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order: str = DEFAULT_TASK_ORDER,
    fields: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    context = client.context_get()
    uid = context.get("uid")
    if not isinstance(uid, int):
        raise OdooJson2Error("Odoo context_get response did not include a numeric uid")

    domain = [
        ["user_ids", "in", uid],
        ["has_template_ancestor", "=", False],
        ["has_project_template", "=", False],
    ]
    records = client.search_read(
        "project.task",
        domain,
        fields or DEFAULT_TASK_FIELDS,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [_format_task(record) for record in records]


def get_task(
    client: OdooJson2Client,
    task_id: int,
    fields: Sequence[str] | None = None,
) -> dict[str, Any]:
    records = client.search_read(
        "project.task",
        [["id", "=", task_id]],
        fields or TASK_DETAIL_FIELDS,
        limit=1,
    )
    if not records:
        raise OdooJson2Error(f"Task {task_id} was not found or is not accessible")
    return _format_task(records[0])


def list_record_messages(
    client: OdooJson2Client,
    model: str,
    record_id: int,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order: str = DEFAULT_MESSAGE_ORDER,
    fields: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    records = client.search_read(
        "mail.message",
        [["model", "=", model], ["res_id", "=", record_id]],
        fields or DEFAULT_MESSAGE_FIELDS,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [_format_message(record) for record in records]


def _format_message(record: dict[str, Any]) -> dict[str, Any]:
    formatted = dict(record)

    for field in ("author_id", "subtype_id"):
        if field in formatted:
            formatted[f"{field}_display"] = _format_many2one(formatted[field])

    body = formatted.get("body")
    if isinstance(body, str):
        formatted["body_text"] = _html_to_text(body)

    return formatted


class _HTMLTextExtractor(HTMLParser):
    _BREAK_TAGS = {"br", "p", "div", "li", "tr", "table", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._BREAK_TAGS:
            self._chunks.append("\n")

    def text(self) -> str:
        return "".join(self._chunks)


def _html_to_text(html_value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html_value)
    text = parser.text().replace("\xa0", " ")
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _format_task(record: dict[str, Any]) -> dict[str, Any]:
    formatted = dict(record)

    for field in ("project_id", "stage_id", "partner_id", "company_id", "parent_id"):
        if field in formatted:
            formatted[f"{field}_display"] = _format_many2one(formatted[field])

    if "state" in formatted:
        formatted["state_display"] = TASK_STATE_LABELS.get(
            formatted["state"],
            formatted["state"],
        )

    if "priority" in formatted:
        formatted["priority_display"] = TASK_PRIORITY_LABELS.get(
            formatted["priority"],
            formatted["priority"],
        )

    return formatted


def _format_many2one(value: Any) -> dict[str, Any] | None:
    if not value:
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return {"id": value[0], "name": value[1]}
    if isinstance(value, int):
        return {"id": value, "name": None}
    return {"id": None, "name": str(value)}

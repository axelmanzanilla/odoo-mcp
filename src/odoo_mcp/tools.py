from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .client import OdooJson2Client, OdooJson2Error

DEFAULT_LIMIT = 20
MAX_ACTIVITY_RECORDS = 5_000
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
ASSIGNMENT_TRACKING_FIELDS = [
    "id",
    "old_value_char",
    "new_value_char",
    "mail_message_id",
]
ASSIGNMENT_MESSAGE_FIELDS = ["id", "date", "res_id", "author_id"]
TIMESHEET_ACTIVITY_FIELDS = ["id", "date", "unit_amount", "task_id"]


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


def list_my_worked_tasks(
    client: OdooJson2Client,
    start_date: str,
    end_date: str,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    """Return tasks assigned to or timesheeted by the current user in a period."""
    period_start, period_end = _parse_date_period(start_date, end_date)
    if limit < 0:
        raise OdooJson2Error("limit must be zero or greater")
    if offset < 0:
        raise OdooJson2Error("offset must be zero or greater")

    context = client.context_get()
    uid = context.get("uid")
    if not isinstance(uid, int):
        raise OdooJson2Error("Odoo context_get response did not include a numeric uid")

    users = client.search_read(
        "res.users",
        [["id", "=", uid]],
        ["id", "name", "tz"],
        limit=1,
    )
    if not users or not isinstance(users[0].get("name"), str):
        raise OdooJson2Error(f"Odoo user {uid} was not found or has no display name")

    user = users[0]
    user_name = user["name"]
    timezone_name = user.get("tz") or context.get("tz") or "UTC"
    try:
        user_timezone = ZoneInfo(timezone_name)
    except (TypeError, ZoneInfoNotFoundError) as exc:
        raise OdooJson2Error(f"Odoo returned an invalid user timezone: {timezone_name!r}") from exc

    utc_start, utc_end = _utc_period_bounds(period_start, period_end, user_timezone)
    warnings: list[str] = []

    try:
        assignments_by_task = _assignment_activity(
            client,
            user_name=user_name,
            utc_start=utc_start,
            utc_end=utc_end,
            user_timezone=user_timezone,
        )
        assignment_history_available = True
    except OdooJson2Error as exc:
        assignments_by_task = {}
        assignment_history_available = False
        warnings.append(f"Assignment history is unavailable: {exc}")

    try:
        timesheets_by_task = _timesheet_activity(
            client,
            uid=uid,
            period_start=period_start,
            period_end=period_end,
        )
        timesheets_available = True
    except OdooJson2Error as exc:
        timesheets_by_task = {}
        timesheets_available = False
        warnings.append(f"Timesheets are unavailable: {exc}")

    task_ids = set(assignments_by_task) | set(timesheets_by_task)
    ordered_task_ids = sorted(
        task_ids,
        key=lambda task_id: (
            _last_activity_date(task_id, assignments_by_task, timesheets_by_task),
            task_id,
        ),
        reverse=True,
    )
    page_task_ids = ordered_task_ids[offset : offset + limit]

    task_records = []
    if page_task_ids:
        task_records = client.search_read(
            "project.task",
            [
                ["id", "in", page_task_ids],
                ["has_template_ancestor", "=", False],
                ["has_project_template", "=", False],
            ],
            DEFAULT_TASK_FIELDS,
            limit=len(page_task_ids),
        )
    tasks_by_id = {
        record["id"]: record for record in task_records if isinstance(record.get("id"), int)
    }

    tasks = []
    for task_id in page_task_ids:
        record = tasks_by_id.get(task_id)
        if record is None:
            continue

        assignment_events = assignments_by_task.get(task_id, [])
        timesheet_activity = timesheets_by_task.get(
            task_id,
            {"entry_count": 0, "total_hours": 0.0, "dates": []},
        )
        activity_sources = []
        if assignment_events:
            activity_sources.append("assignment")
        if timesheet_activity["entry_count"]:
            activity_sources.append("timesheet")

        formatted = _format_task(record)
        formatted.update(
            {
                "activity_sources": activity_sources,
                "last_activity_date": _last_activity_date(
                    task_id,
                    assignments_by_task,
                    timesheets_by_task,
                ).isoformat(),
                "assignment_activity": {
                    "event_count": len(assignment_events),
                    "events": assignment_events,
                },
                "timesheet_activity": timesheet_activity,
            }
        )
        tasks.append(formatted)

    return {
        "user": {"id": uid, "name": user_name},
        "period": {
            "start_date": period_start.isoformat(),
            "end_date": period_end.isoformat(),
            "timezone": timezone_name,
        },
        "source_status": {
            "assignment_history": assignment_history_available,
            "timesheets": timesheets_available,
        },
        "warnings": warnings,
        "total": len(ordered_task_ids),
        "offset": offset,
        "limit": limit,
        "tasks": tasks,
    }


def _assignment_activity(
    client: OdooJson2Client,
    *,
    user_name: str,
    utc_start: str,
    utc_end: str,
    user_timezone: ZoneInfo,
) -> dict[int, list[dict[str, Any]]]:
    tracking_values = client.search_read(
        "mail.tracking.value",
        [
            ["field_id.model", "=", "project.task"],
            ["field_id.name", "=", "user_ids"],
            ["mail_message_id.model", "=", "project.task"],
            ["mail_message_id.date", ">=", utc_start],
            ["mail_message_id.date", "<", utc_end],
            ["new_value_char", "ilike", user_name],
        ],
        ASSIGNMENT_TRACKING_FIELDS,
        limit=MAX_ACTIVITY_RECORDS + 1,
        order="id desc",
    )
    _check_activity_record_limit(tracking_values, "assignment changes")

    assignment_message_ids = {
        message_id
        for tracking in tracking_values
        if _tracked_assignee_contains(tracking.get("new_value_char"), user_name)
        and not _tracked_assignee_contains(tracking.get("old_value_char"), user_name)
        and (message_id := _many2one_id(tracking.get("mail_message_id"))) is not None
    }
    if not assignment_message_ids:
        return {}

    messages = client.search_read(
        "mail.message",
        [["id", "in", sorted(assignment_message_ids)], ["model", "=", "project.task"]],
        ASSIGNMENT_MESSAGE_FIELDS,
        limit=len(assignment_message_ids),
        order="date desc, id desc",
    )

    events_with_dates: dict[int, list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)
    for message in messages:
        task_id = message.get("res_id")
        if not isinstance(task_id, int):
            continue
        assigned_at = _odoo_datetime_to_local(message.get("date"), user_timezone)
        if assigned_at is None:
            continue
        events_with_dates[task_id].append(
            (
                assigned_at,
                {
                    "assigned_at": assigned_at.isoformat(timespec="seconds"),
                    "assigned_by": _format_many2one(message.get("author_id")),
                },
            )
        )

    return {
        task_id: [event for _, event in sorted(events, key=lambda item: item[0], reverse=True)]
        for task_id, events in events_with_dates.items()
    }


def _timesheet_activity(
    client: OdooJson2Client,
    *,
    uid: int,
    period_start: date,
    period_end: date,
) -> dict[int, dict[str, Any]]:
    timesheets = client.search_read(
        "account.analytic.line",
        [
            ["user_id", "=", uid],
            ["task_id", "!=", False],
            ["date", ">=", period_start.isoformat()],
            ["date", "<=", period_end.isoformat()],
        ],
        TIMESHEET_ACTIVITY_FIELDS,
        limit=MAX_ACTIVITY_RECORDS + 1,
        order="date desc, id desc",
    )
    _check_activity_record_limit(timesheets, "timesheet entries")

    activity: dict[int, dict[str, Any]] = {}
    dates_by_task: dict[int, set[str]] = defaultdict(set)
    for timesheet in timesheets:
        task_id = _many2one_id(timesheet.get("task_id"))
        timesheet_date = timesheet.get("date")
        if task_id is None or not isinstance(timesheet_date, str):
            continue

        summary = activity.setdefault(
            task_id,
            {"entry_count": 0, "total_hours": 0.0, "dates": []},
        )
        summary["entry_count"] += 1
        unit_amount = timesheet.get("unit_amount")
        if isinstance(unit_amount, (int, float)) and not isinstance(unit_amount, bool):
            summary["total_hours"] += unit_amount
        dates_by_task[task_id].add(timesheet_date)

    for task_id, summary in activity.items():
        summary["total_hours"] = round(summary["total_hours"], 6)
        summary["dates"] = sorted(dates_by_task[task_id], reverse=True)
    return activity


def _last_activity_date(
    task_id: int,
    assignments_by_task: dict[int, list[dict[str, Any]]],
    timesheets_by_task: dict[int, dict[str, Any]],
) -> date:
    activity_dates = [
        date.fromisoformat(event["assigned_at"][:10])
        for event in assignments_by_task.get(task_id, [])
    ]
    timesheet_dates = timesheets_by_task.get(task_id, {}).get("dates", [])
    activity_dates.extend(date.fromisoformat(value) for value in timesheet_dates)
    return max(activity_dates)


def _parse_date_period(start_date: str, end_date: str) -> tuple[date, date]:
    parsed_dates = []
    for field_name, value in (("start_date", start_date), ("end_date", end_date)):
        try:
            parsed = date.fromisoformat(value)
        except (TypeError, ValueError):
            raise OdooJson2Error(f"{field_name} must use YYYY-MM-DD format") from None
        if parsed.isoformat() != value:
            raise OdooJson2Error(f"{field_name} must use YYYY-MM-DD format")
        parsed_dates.append(parsed)

    period_start, period_end = parsed_dates
    if period_end < period_start:
        raise OdooJson2Error("end_date must be on or after start_date")
    return period_start, period_end


def _utc_period_bounds(
    period_start: date,
    period_end: date,
    user_timezone: ZoneInfo,
) -> tuple[str, str]:
    local_start = datetime.combine(period_start, time.min, tzinfo=user_timezone)
    local_end = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=user_timezone)
    return (_format_odoo_utc(local_start), _format_odoo_utc(local_end))


def _format_odoo_utc(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    )


def _odoo_datetime_to_local(value: Any, user_timezone: ZoneInfo) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(user_timezone)


def _tracked_assignee_contains(value: Any, user_name: str) -> bool:
    if not isinstance(value, str):
        return False
    return (
        value == user_name
        or value.startswith(f"{user_name}, ")
        or value.endswith(f", {user_name}")
        or f", {user_name}, " in value
    )


def _many2one_id(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], int):
        return value[0]
    return None


def _check_activity_record_limit(records: Sequence[Any], source: str) -> None:
    if len(records) > MAX_ACTIVITY_RECORDS:
        raise OdooJson2Error(
            f"The period contains more than {MAX_ACTIVITY_RECORDS} {source}; use a narrower period"
        )


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

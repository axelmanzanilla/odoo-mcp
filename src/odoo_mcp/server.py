from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import OdooJson2Client
from .config import OdooConfig
from . import tools


mcp = FastMCP("odoo-mcp")


def get_client() -> OdooJson2Client:
    return OdooJson2Client(OdooConfig.from_env())


@mcp.tool()
def odoo_context() -> dict[str, Any]:
    """Return the authenticated Odoo user's context."""
    return tools.odoo_context(get_client())


@mcp.tool()
def odoo_search_read(
    model: str,
    domain: list[Any],
    fields: list[str] | None = None,
    limit: int = tools.DEFAULT_LIMIT,
    offset: int = 0,
    order: str | None = None,
) -> list[dict[str, Any]]:
    """Read Odoo records using a model, domain, and optional field list."""
    return tools.odoo_search_read(
        get_client(),
        model=model,
        domain=domain,
        fields=fields,
        limit=limit,
        offset=offset,
        order=order,
    )


@mcp.tool()
def list_my_tasks(
    limit: int = tools.DEFAULT_LIMIT,
    offset: int = 0,
    order: str = tools.DEFAULT_TASK_ORDER,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List project tasks assigned to the authenticated Odoo user."""
    return tools.list_my_tasks(
        get_client(),
        limit=limit,
        offset=offset,
        order=order,
        fields=fields,
    )


@mcp.tool()
def get_task(task_id: int, fields: list[str] | None = None) -> dict[str, Any]:
    """Read one project task by ID with friendly display values."""
    return tools.get_task(get_client(), task_id=task_id, fields=fields)


def main() -> None:
    mcp.run(transport="stdio")

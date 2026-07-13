# Contributing to odoo-mcp

Thanks for your interest in contributing! This document explains how to set up
a development environment, run the checks, and add new MCP tools.

## Development setup

```bash
git clone https://github.com/axelmanzanilla/odoo-mcp.git
cd odoo-mcp
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Running tests and lint

```bash
pytest
ruff check .
ruff format --check .
```

All tests must pass and lint must be clean before a pull request can be merged.
Tests do not require a real Odoo instance: the HTTP layer is exercised with
`httpx.MockTransport`, and tool logic is tested with fake clients.

## Project layout

The code follows a layered design. Keep each layer focused:

| Module | Responsibility |
| --- | --- |
| `src/odoo_mcp/config.py` | Read configuration from environment variables. |
| `src/odoo_mcp/client.py` | HTTP transport to Odoo's External JSON-2 API. No business logic. |
| `src/odoo_mcp/tools.py` | Tool implementations. Pure functions that take a client as their first argument. No MCP or HTTP details. |
| `src/odoo_mcp/server.py` | FastMCP registration. Thin wrappers that create the client and delegate to `tools`. |

As the tool count grows, `tools.py` is expected to become a `tools/` package
with one module per domain (for example `tasks.py`, `sales.py`, `contacts.py`).

## Adding a new MCP tool

Suppose you want a tool that lists sale orders. Three steps:

1. **Implement the logic in `tools.py`** as a pure function that takes the
   client as its first argument. Reuse `client.call(model, method, **kwargs)`
   or `client.search_read(...)` — never make HTTP requests directly:

   ```python
   def list_sale_orders(
       client: OdooJson2Client,
       limit: int = DEFAULT_LIMIT,
       offset: int = 0,
   ) -> list[dict[str, Any]]:
       return client.search_read(
           "sale.order",
           [["state", "not in", ["cancel"]]],
           ["id", "name", "partner_id", "amount_total", "state"],
           limit=limit,
           offset=offset,
       )
   ```

2. **Register it in `server.py`** with a thin `@mcp.tool()` wrapper. The
   docstring becomes the tool description shown to AI agents, so make it
   clear and action-oriented:

   ```python
   @mcp.tool()
   def list_sale_orders(
       limit: int = tools.DEFAULT_LIMIT,
       offset: int = 0,
   ) -> list[dict[str, Any]]:
       """List sale orders visible to the authenticated Odoo user."""
       return tools.list_sale_orders(get_client(), limit=limit, offset=offset)
   ```

3. **Add tests in `tests/`** using a fake client (see `tests/test_tools.py`
   for the pattern). Assert both the returned value and the exact
   `search_read` call your tool makes.

Finally, document the new tool in the README's Tools section.

## Design guidelines

- **No Odoo addons.** The server must work against stock Odoo through public
  external APIs only. Do not require anything to be installed inside the Odoo
  database.
- **Odoo owns access control.** Do not build permission logic into tools;
  model access, field access, and record rules are enforced by the Odoo user
  behind the API key.
- **Read-only by default.** Tools that create, update, or delete records need
  extra care: name them explicitly (`create_...`, `delete_...`) and document
  the risk in the tool docstring.
- **Never commit credentials.** Use placeholder values like
  `https://example.odoo.com` and `your-api-key` in docs and tests.
- **Document dependencies in `pyproject.toml`**, not in ad hoc install steps.

## Pull requests

- Keep changes scoped: one feature or fix per PR.
- Update the README and this guide if commands, tool names, or supported Odoo
  versions change.
- Describe how you tested the change (unit tests, and against a real Odoo
  instance if applicable).

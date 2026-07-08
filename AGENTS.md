# AGENTS.md

## Project Context

`odoo-mcp` is an open-source MCP server for Odoo.

The project goal is to let AI agents interact with Odoo databases without requiring any Odoo addon installation. This is important because many Odoo SaaS / Odoo Online databases cannot install custom addons.

The MCP server should run outside Odoo and communicate with Odoo through public external APIs.

## Current Direction

- Build this as a local Python MCP server.
- Users install it with Python, `pip`, and project dependencies.
- Users do not install anything inside their Odoo database.
- Users do not manually keep a localhost server running.
- MCP clients such as Claude Desktop, Cursor, or other agents should launch the MCP server process automatically from their MCP configuration.
- The first documented install path is source-based:
  - Clone the repository.
  - Create a virtual environment.
  - Install with `pip install -e .`.
  - Point the MCP client at the virtualenv executable.

## Odoo Integration

- Target Odoo 19+ through the External JSON-2 API.
- Older Odoo versions may be supported later through legacy RPC APIs.
- Odoo remains the source of truth for permissions and access control.
- The API user configured for this MCP server should have the minimum Odoo access rights required.
- Do not require custom Odoo modules.
- Do not assume database administrator access.

## Implemented Tooling

The initial implementation is a Python package under `src/odoo_mcp`.

Implemented read-only MCP tools:

- `odoo_context`: calls `res.users/context_get`.
- `odoo_search_read`: generic wrapper around `<model>/search_read`.
- `list_my_tasks`: lists `project.task` records assigned to the authenticated user with friendly display values.
- `get_task`: reads one `project.task` by ID with friendly display values.

`list_my_tasks` first calls `res.users/context_get` to get the numeric `uid`, then calls `project.task/search_read` with:

```python
[
    ["user_ids", "in", uid],
    ["has_template_ancestor", "=", False],
    ["has_project_template", "=", False],
]
```

The package entry point is configured in `pyproject.toml`:

```text
odoo-mcp = "odoo_mcp.server:main"
```

Runtime dependencies are:

- `httpx>=0.27,<1`
- `mcp>=1.27,<2`

Dev/test dependency:

- `pytest>=8,<9`

## Planned Tooling

Future MCP tools should expand generic Odoo model operations:

- Read specific records by ID.
- Create records.
- Update records.
- Delete records.
- Call existing public model methods.
- Inspect model fields.

Higher-level tools may be added later for common workflows:

- Contacts
- Products
- Sales
- Invoices
- Inventory
- CRM

## Packaging Assumptions

- The eventual command-line entry point should be named `odoo-mcp`.
- The README currently assumes users can run the executable from:
  - `.venv/bin/odoo-mcp` on Linux/macOS.
  - `.venv\Scripts\odoo-mcp.exe` on Windows.
- Keep the project friendly to Odoo developers and administrators who are already familiar with Python and `pip`.
- Avoid requiring `uv`, Docker, or a hosted server for the initial version.

## Security Notes

- Never commit real Odoo URLs, API keys, passwords, or production credentials.
- Prefer environment variables for runtime configuration.
- Use placeholder credentials in examples.
- Recommend dedicated Odoo API users with minimal permissions.
- Treat write/delete/call-method tools carefully because they can mutate Odoo data.

## Repository State

At the time this file was created, the repository was minimal:

- `README.md`
- `LICENSE`
- `AGENTS.md`

The README already contains:

- Project description.
- Installation instructions using Python, virtualenv, and `pip install -e .`.
- MCP client configuration examples.
- Compatibility notes for Odoo 19+ and External JSON-2 API.
- Planned tools.
- Security guidance.

## Agent Working Notes

- Keep changes scoped and pragmatic.
- Preserve the no-addon architecture unless the user explicitly changes direction.
- When adding implementation files, prefer a standard Python package layout with a console script entry point.
- Update README examples if package names, commands, or supported Odoo versions change.
- If adding dependencies, document them through normal Python packaging files rather than ad hoc install steps.

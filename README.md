# odoo-mcp

An open-source MCP server for Odoo that connects through Odoo's External JSON-2 API.

No Odoo addon installation is required. Provide your Odoo URL, database name, and API key, then expose safe MCP tools for reading and operating on Odoo models.

## Installation

`odoo-mcp` runs locally on the user's machine. MCP clients such as Claude Desktop or Cursor launch the server process automatically, so users do not need to manually keep a localhost server running.

### Prerequisites

- Python 3.10+
- `pip`
- An Odoo database with access to the External JSON-2 API
- An Odoo API key

### Install from source

```bash
git clone https://github.com/axelmanzanilla/odoo-mcp.git
cd odoo-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows, activate the virtual environment with:

```powershell
.venv\Scripts\activate
```

### MCP client configuration

Point your MCP client to the `odoo-mcp` executable inside the virtual environment:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "/path/to/odoo-mcp/.venv/bin/odoo-mcp",
      "env": {
        "ODOO_URL": "https://example.odoo.com",
        "ODOO_DB": "example",
        "ODOO_API_KEY": "your-api-key"
      }
    }
  }
}
```

On Windows, use the virtual environment executable path:

```json
"command": "C:\\path\\to\\odoo-mcp\\.venv\\Scripts\\odoo-mcp.exe"
```

## Compatibility

`odoo-mcp` is planned for Odoo 19+ instances with access to the External JSON-2 API.

Support for older Odoo versions may be added later through legacy RPC APIs.

## Planned Tools

The initial implementation provides read-only tools:

- `odoo_context`: return the authenticated Odoo user's context, including `uid`.
- `odoo_search_read`: call `search_read` on an Odoo model with a provided domain and field list.
- `list_my_tasks`: list Project tasks assigned to the authenticated user with friendly display values.
- `get_task`: read one Project task by ID with friendly display values.

`list_my_tasks` follows Odoo's own My Tasks action domain:

```python
[
    ("user_ids", "in", uid),
    ("has_template_ancestor", "=", False),
    ("has_project_template", "=", False),
]
```

When calling Odoo through the external API, `uid` is resolved first through `res.users/context_get` and then sent as a numeric user ID.

Future goals include additional generic MCP tools for common Odoo model operations:

- Read specific records by ID.
- Create records.
- Update records.
- Delete records.
- Call existing public model methods.
- Inspect model fields.

Higher-level tools may be added for common Odoo workflows such as contacts, products, sales, invoices, inventory, and CRM.

## Security

Use a dedicated Odoo API user with the minimum access rights required for your use case.

Odoo remains the source of truth for access control. Model permissions, field access, and record rules are enforced by the Odoo user associated with the API key.

Do not commit API keys or production credentials to this repository.

## License

MIT

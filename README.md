# odoo-mcp

An open-source MCP server for Odoo that connects through Odoo's External JSON-2 API.

No Odoo addon installation is required. Provide your Odoo URL, database name, and API key, then expose safe MCP tools for reading and operating on Odoo models.

## Compatibility

`odoo-mcp` is planned for Odoo 19+ instances with access to the External JSON-2 API.

Support for older Odoo versions may be added later through legacy RPC APIs.

## Planned Tools

The initial goal is to provide generic MCP tools for common Odoo model operations:

- Search and read records.
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

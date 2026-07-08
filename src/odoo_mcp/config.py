from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class OdooConfig:
    url: str
    database: str
    api_key: str
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "OdooConfig":
        missing = [
            name
            for name in ("ODOO_URL", "ODOO_DB", "ODOO_API_KEY")
            if not os.environ.get(name)
        ]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required environment variable(s): {names}")

        return cls(
            url=os.environ["ODOO_URL"].rstrip("/"),
            database=os.environ["ODOO_DB"],
            api_key=os.environ["ODOO_API_KEY"],
        )

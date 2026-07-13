from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OdooConfig:
    url: str
    database: str
    api_key: str
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> OdooConfig:
        missing = [
            name for name in ("ODOO_URL", "ODOO_DB", "ODOO_API_KEY") if not os.environ.get(name)
        ]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required environment variable(s): {names}")

        timeout = cls.timeout
        timeout_raw = os.environ.get("ODOO_TIMEOUT")
        if timeout_raw:
            try:
                timeout = float(timeout_raw)
            except ValueError:
                raise ValueError(
                    f"ODOO_TIMEOUT must be a number of seconds, got {timeout_raw!r}"
                ) from None

        return cls(
            url=os.environ["ODOO_URL"].rstrip("/"),
            database=os.environ["ODOO_DB"],
            api_key=os.environ["ODOO_API_KEY"],
            timeout=timeout,
        )

from __future__ import annotations

import pytest

from odoo_mcp.config import OdooConfig


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODOO_URL", "https://example.odoo.com/")
    monkeypatch.setenv("ODOO_DB", "example")
    monkeypatch.setenv("ODOO_API_KEY", "secret")

    config = OdooConfig.from_env()

    assert config.url == "https://example.odoo.com"
    assert config.database == "example"
    assert config.api_key == "secret"


def test_config_from_env_reads_optional_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODOO_URL", "https://example.odoo.com")
    monkeypatch.setenv("ODOO_DB", "example")
    monkeypatch.setenv("ODOO_API_KEY", "secret")

    monkeypatch.delenv("ODOO_TIMEOUT", raising=False)
    assert OdooConfig.from_env().timeout == 30.0

    monkeypatch.setenv("ODOO_TIMEOUT", "5.5")
    assert OdooConfig.from_env().timeout == 5.5

    monkeypatch.setenv("ODOO_TIMEOUT", "not-a-number")
    with pytest.raises(ValueError, match="ODOO_TIMEOUT"):
        OdooConfig.from_env()


def test_config_from_env_reports_missing_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODOO_URL", raising=False)
    monkeypatch.delenv("ODOO_DB", raising=False)
    monkeypatch.delenv("ODOO_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc:
        OdooConfig.from_env()

    message = str(exc.value)
    assert "ODOO_URL" in message
    assert "ODOO_DB" in message
    assert "ODOO_API_KEY" in message

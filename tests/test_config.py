from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType
from unittest.mock import patch


def load_config_module() -> ModuleType:
    sys.modules.pop("src.config", None)

    import src.config

    return importlib.reload(src.config)


def test_settings_loads_values_from_environment() -> None:
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test_db",
        },
        clear=False,
    ):
        config_module = load_config_module()

    assert config_module.settings.app_env == "test"
    assert config_module.settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/test_db"

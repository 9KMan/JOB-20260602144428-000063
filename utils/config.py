"""
Configuration loader for GTN Trade API services.
Supports environment variable interpolation.
"""
import os
import re
import yaml
from typing import Any, Dict


class Config:
    """Configuration manager with environment variable support."""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from config.yaml."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config.yaml'
        )

        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

        self._interpolate_env_vars(self._config)

    def _interpolate_env_vars(self, config: Dict[str, Any]) -> None:
        """Recursively interpolate environment variables in config."""
        for key, value in config.items():
            if isinstance(value, dict):
                self._interpolate_env_vars(value)
            elif isinstance(value, str):
                config[key] = self._replace_env_vars(value)

    def _replace_env_vars(self, value: str) -> str:
        """Replace ${VAR} or ${VAR:default} patterns with env vars."""
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) or ''
            return os.environ.get(var_name, default)

        return re.sub(pattern, replacer, value)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value by key path."""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value


config = Config()
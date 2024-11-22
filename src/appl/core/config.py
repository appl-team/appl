import os
from typing import Any

import addict
import yaml
from loguru import logger

from .io import get_ext, load_file

DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE = os.path.join(DIR, "..", "default_configs.yaml")


class Configs(addict.Dict):
    """A Dictionary class that allows for dot notation access to nested dictionaries."""

    def getattrs(self, key: str, default: Any = None) -> Any:
        """Get a value from a nested dictionary using a dot-separated key string."""
        if "." in key:
            keys = key.split(".")
        else:
            keys = [key]
        prefix = "."
        v = self
        try:
            for k in keys:
                v = getattr(v, k)
                prefix += k + "."
            return v
        except KeyError as e:
            msg = f"{e} not found in prefix '{prefix}'"

            if default is None:  # check if key exists in default configs
                try:
                    # fallback to default configs
                    default = DEFAULT_CONFIGS.getattrs(key)
                except Exception:
                    pass

            if default is not None:
                logger.warning(f"{msg}, using default: {default}")
                return default
            logger.error(msg)
            raise e

    def to_yaml(self) -> str:
        """Convert the Configs object to a YAML string."""
        return yaml.dump(self.to_dict())

    def __missing__(self, key: str) -> None:
        raise KeyError(key)


def load_config(file: str, *args: Any, **kwargs: Any) -> Configs:
    """Load a config file and return the data as a dictionary."""
    ext = get_ext(file)
    if ext not in [".json", ".yaml", ".yml", ".toml"]:
        raise ValueError(f"Unsupported config file type {ext}")
    content = load_file(file, *args, **kwargs)
    return Configs(content)


DEFAULT_CONFIGS = load_config(DEFAULT_CONFIG_FILE)
"""The static default configs loaded from the default config file."""
# singleton
configs = DEFAULT_CONFIGS.deepcopy()
"""The global configs"""

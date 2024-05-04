import json
import os

import addict
import toml
import yaml

from .types import *

# from importlib import import_module # read python
PLAIN_TEXT_FILES = [".txt", ".log", ".md", ".html"]


def makedirs(file: str) -> None:
    """Make the directory of the file if it does not exist."""
    if folder := os.path.dirname(file):
        os.makedirs(folder, exist_ok=True)


def get_ext(file: str) -> str:
    """Get the extension of a file."""
    return os.path.splitext(file)[1]


def dump_file(
    data: Any,
    file: str,
    mode: str = "w",
    ensure_folder_exists: bool = True,
    file_type: Optional[str] = None,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Write the data to a file based on the file extension."""
    if file_type is None:
        file_type = get_ext(file)
    if ensure_folder_exists:
        makedirs(file)

    if file_type == ".json":
        dump_func: Callable = json.dump
    elif file_type in [".yaml", ".yml"]:
        dump_func = yaml.dump
    elif file_type == ".toml":
        dump_func = toml.dump
    elif file_type in PLAIN_TEXT_FILES:

        def dump_func(data, f, *args, **kwargs):
            f.write(data)

    else:
        raise ValueError(f"Unsupported file type {file_type}")
    with open(file, mode) as f:
        dump_func(data, f, *args, **kwargs)


def load_file(
    file: str,
    mode: str = "r",
    file_type: Optional[str] = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Load a file based on the file extension and return the data."""
    if file_type is None:
        file_type = get_ext(file)
    if file_type == ".json":
        load_func: Callable = json.load
    elif file_type in [".yaml", ".yml"]:
        load_func = yaml.safe_load
    elif file_type == ".toml":
        load_func = toml.load
    # elif file_type == ".py":
    #     load_func = import_module
    elif file_type in PLAIN_TEXT_FILES:

        def load_func(f, *args, **kwargs):
            return f.read()

    else:
        raise ValueError(f"Unsupported file type {file_type}")
    with open(file, mode) as f:
        return load_func(f, *args, **kwargs)

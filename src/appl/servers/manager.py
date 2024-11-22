import copy
import threading
from typing import Any, Dict, Optional

from litellm import model_list, provider_list
from loguru import logger

from ..core.config import configs
from ..core.server import BaseServer, DummyServer


def _init_server(
    model: str,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> BaseServer:
    """Initialize a server based on the model, provider and other arguments."""
    if provider is None:
        provider = model.split("/")[0]

    is_custom_llm = provider.split("/")[0] == "custom"
    custom_llm_provider = (
        provider[len("custom/") :] or "openai" if is_custom_llm else None
    )  # "openai" is the default provider for custom models

    if model == "_dummy":
        server: BaseServer = DummyServer()  # for testing purposes
    elif is_custom_llm or model in model_list or provider in provider_list:
        from .api import APIServer

        msg = f"Initializing APIserver for model {model}"
        if base_url is not None:
            msg += f" with address {base_url}"
        logger.info(msg)
        server = APIServer(
            model,
            base_url=base_url,
            api_key=api_key,
            custom_llm_provider=custom_llm_provider,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown model {model}")

    return server


def _get_server_configs(name: str) -> dict:
    server_configs = {}
    if name not in configs.get("servers", {}):
        logger.warning(
            f"Server {name} not found in configs, using the server name as model name"
        )
        server_configs["model"] = name
    else:
        server_configs = configs.servers[name]
    for _ in range(100):  # prevent infinite loop (max 100 templates)
        if "template" not in server_configs:
            break
        server_configs = copy.deepcopy(server_configs)
        template_name = server_configs.pop("template")
        if template_name not in configs.servers:
            raise ValueError(f"Server config template {template_name} not found")
        template_config = configs.servers[template_name]
        # override template config
        server_configs = {**template_config, **server_configs}
    if "template" in server_configs:
        raise ValueError(f"Template loop detected in server config {name}")
    return server_configs


class ServerManager:
    """The manager for all servers."""

    def __init__(self) -> None:
        """Initialize the server manager."""
        self._lock = threading.Lock()
        self._servers: Dict[str, BaseServer] = {}

    def register_server(self, name: str, server: BaseServer) -> None:
        """Register a server with a name."""
        self._servers[name] = server

    def close_server(self, name: str) -> None:
        """Close a server by name."""
        if name in self._servers:
            self._servers[name].close()
            del self._servers[name]

    def get_server(self, name: Optional[str]) -> BaseServer:
        """Get a server by name. If name is None, get the default server."""
        if name is None:
            name = configs.getattrs("servers.default")

        with self._lock:
            if name not in self._servers:
                server_configs = _get_server_configs(name)
                server = _init_server(**server_configs)
                self.register_server(name, server)
        return self._servers[name]

    @property
    def default_server(self) -> BaseServer:
        """The default server."""
        if "default" not in self._servers:
            raise ValueError("Default server not found")
        return self._servers["default"]


# Singleton server manager
server_manager = ServerManager()

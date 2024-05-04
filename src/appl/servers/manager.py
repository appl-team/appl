from litellm import model_list, provider_list

from ..core.config import configs
from ..core.server import BaseServer, DummyServer
from ..core.types import *


def _init_server(
    model: str,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    is_custom_llm: bool = False,
    **kwargs: Any,
) -> BaseServer:
    """Initialize a server based on the model, provider and other arguments."""
    if provider is None:
        provider = model.split("/")[0]

    if model == "_dummy":
        server: BaseServer = DummyServer()  # for testing purposes
    elif provider == "api" or model in model_list or provider in provider_list:
        from .api import APIServer

        msg = f"Initializing APIserver for model {model}"
        if base_url is not None:
            msg += f" with address {base_url}"
        logger.info(msg)
        server = APIServer(
            model,
            base_url=base_url,
            api_key=api_key,
            is_custom_llm=is_custom_llm,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown model {model}")

    return server


class ServerManager:
    """The manager for all servers."""

    def __init__(self) -> None:
        """Initialize the server manager."""
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

        if name not in self._servers:
            if name in configs.get("servers", {}):
                server_config: dict = configs.servers[name]
                server = _init_server(**server_config)
                self.register_server(name, server)
            else:
                raise ValueError(f"Server {name} not found")
        return self._servers[name]

    @property
    def default_server(self) -> BaseServer:
        """The default server."""
        if "default" not in self._servers:
            raise ValueError("Default server not found")
        return self._servers["default"]


# Singleton server manager
server_manager = ServerManager()

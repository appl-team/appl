import time
from functools import cached_property

from pydantic import BaseModel, model_validator

from .config import Configs, configs
from .globals import global_vars
from .types import *


class TraceEventBase(BaseModel):
    """A base class for trace events."""

    name: str
    """The name of the event."""
    time_stamp: float = None  # type: ignore
    """The time stamp of the event."""

    @model_validator(mode="after")
    def _check_time_stamp(self) -> "TraceEventBase":
        if self.time_stamp is None:
            # Set the time stamp to the current time if it is not set
            self.time_stamp = time.time()  # type: ignore
        return self


class FunctionCallEvent(TraceEventBase):
    """A class representing a function call event."""

    args: Dict
    """The arguments of the function call."""


class FunctionReturnEvent(TraceEventBase):
    """A class representing a function return event."""

    pass


class GenerationInitEvent(TraceEventBase):
    """A class representing a generation init event."""

    pass


class GenerationResponseEvent(TraceEventBase):
    """A class representing a generation response event."""

    args: Dict
    """The arguments of the generation call."""
    ret: Any
    """The return value of the generation call."""


class CompletionRequestEvent(TraceEventBase):
    """A class representing a completion request event."""

    pass


class CompletionResponseEvent(TraceEventBase):
    """A class representing a completion response event."""

    args: Dict
    """The arguments of the completion call."""
    ret: Any
    """The return value of the completion call."""
    cost: Optional[float]
    """The api cost of the completion call."""


class TraceNode(BaseModel):
    """The node of a trace tree containing information about trace events."""

    type: str
    """The type of the trace node."""
    name: str
    """The name of the trace node."""
    parent: Optional["TraceNode"] = None
    """The parent of the trace node."""
    children: List["TraceNode"] = []
    """The children of the trace node."""
    args: Optional[Dict] = None
    """The arguments of the trace node."""
    ret: Any = None
    """The return value of the trace node."""
    start_time: float = 0.0
    """The start time of the trace node."""
    end_time: float = 0.0
    """The end time of the trace node."""
    info: Dict = {}
    """The extra information of the trace node."""

    @property
    def runtime(self) -> float:
        """The runtime of the trace node."""
        return self.end_time - self.start_time


def add_to_trace(event: TraceEventBase) -> None:
    """Add an event to the trace."""
    if global_vars.trace_engine:
        global_vars.trace_engine.append(event)


class TraceEngineBase(ABC):
    """A base class for trace engines."""

    @property
    @abstractmethod
    def events(self) -> List[TraceEventBase]:
        """The list of events in the trace."""
        raise NotImplementedError

    @cached_property
    def min_timestamp(self) -> float:
        """The minimum time stamp of the events in the trace."""
        return min([event.time_stamp for event in self.events])

    @property
    @abstractmethod
    def trace_nodes(self) -> Dict[str, TraceNode]:
        """The dictionary of trace nodes in the trace."""
        raise NotImplementedError

    @abstractmethod
    def append(self, event: TraceEventBase) -> None:
        """Append an event to the trace."""
        raise NotImplementedError

    @abstractmethod
    def find_cache(self, name: str, args: Dict) -> Any:
        """Find a completion result in the cache.

        Args:
            name: The name of the completion.
            args: The arguments of the completion.

        Returns:
            The completion result if found, otherwise None.
        """
        raise NotImplementedError


def find_in_cache(
    name: str, args: Dict, cache: Optional[TraceEngineBase] = None
) -> Any:
    """Find a completion result in the cache.

    Args:
        name: The name of the completion.
        args: The arguments of the completion.
        cache: The cache to search in. Defaults to the global resume cache.

    Returns:
        The completion result if found, otherwise None.
    """
    if cache is None:
        if "resume_cache" in global_vars:
            cache = global_vars.resume_cache
    if cache is not None:
        return cache.find_cache(name, args)
    return None


class TracePrinterBase(ABC):
    """A base class for trace printers."""

    @abstractmethod
    def print(self, trace: TraceEngineBase, meta_data: Optional[Configs] = None) -> Any:
        """Print the trace."""
        raise NotImplementedError

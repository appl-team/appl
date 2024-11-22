import threading
import time
from abc import ABC, abstractmethod
from functools import cached_property
from inspect import signature
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, overload

from loguru import logger
from pydantic import BaseModel, model_validator

from .config import Configs, configs
from .globals import global_vars, inc_global_var
from .utils import wraps


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
    parent_func: Optional[str] = None
    """The name of the parent function."""


class FunctionReturnEvent(TraceEventBase):
    """A class representing a function return event."""

    ret: Any = None
    """The return value of the function."""


class GenerationInitEvent(TraceEventBase):
    """A class representing a generation init event."""

    parent_func: Optional[str] = None
    """The name of the parent function."""


class GenerationResponseEvent(TraceEventBase):
    """A class representing a generation response event."""

    args: Dict
    """The arguments of the generation call."""
    ret: Any
    """The return value of the generation call."""


class CompletionRequestEvent(TraceEventBase):
    """A class representing a completion request event."""

    parent_func: Optional[str] = None
    """The name of the parent function."""


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


F = TypeVar("F", bound=Callable)


@overload
def traceable(func: F) -> F: ...


@overload
def traceable(
    func: Optional[str] = None,
    *,
    metadata: Optional[Dict] = None,
) -> Callable[[F], F]: ...


def traceable(
    func: Optional[Union[F, str]] = None,
    *,
    metadata: Optional[Dict] = None,
) -> Union[F, Callable[[F], F]]:
    """Make a function traceable.

    Args:
        func (str): The custom name of the function.
        metadata (Dict): The meta information of the function to be traced.
    """
    # TODO: record metadata
    name: Optional[str] = None

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_id = name
            if func_id is None:
                func_id = func.__qualname__
            func_run_cnt = inc_global_var(func_id) - 1
            func_id += f"_{func_run_cnt}"
            logger.info(
                f"Tracking function {func_id} with parent {global_vars.current_func.get()} in thread {threading.current_thread()}"
            )

            def _get_bind_args():
                sig = signature(func)
                kwargs_copy = kwargs.copy()
                # remove special args that do not need to be passed
                for key in ["_ctx", "_locals", "_globals"]:
                    if key not in sig.parameters:
                        kwargs_copy.pop(key, None)
                return sig.bind_partial(*args, **kwargs_copy)

            if global_vars.trace_engine:
                # NOTE: compute repr(args) might be time-consuming
                # TODO: jsonify the args
                add_to_trace(
                    FunctionCallEvent(
                        name=func_id,
                        args={
                            k: repr(v) for k, v in _get_bind_args().arguments.items()
                        },
                    )
                )

            # set the current function, used for the function calls inside to get the parent function
            token = global_vars.current_func.set(func_id)

            # call the inner function
            ret = func(*args, **kwargs)

            # reset the current function name after the function call
            global_vars.current_func.reset(token)
            if global_vars.trace_engine:
                add_to_trace(FunctionReturnEvent(name=func_id, ret=repr(ret)))
                # TODO: replace the return value with the actual value when the computation of future is finished (in trace)
                # TODO: jsonify the ret
            return ret

        return wrapper  # type: ignore

    if callable(func):
        return decorator(func)  # type: ignore
    else:
        name = func
        return decorator


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

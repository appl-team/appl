import os
import pickle
from threading import Lock

from ..core.trace import (
    CompletionRequestEvent,
    CompletionResponseEvent,
    FunctionCallEvent,
    FunctionReturnEvent,
    GenerationInitEvent,
    GenerationResponseEvent,
    TraceEngineBase,
    TraceEventBase,
    TraceNode,
)
from ..core.types import *


class TraceEngine(TraceEngineBase):
    """The engine used to record the trace of a program execution."""

    def __init__(self, filename: str, mode: str = "write", strict: bool = True) -> None:
        """Initialize the TraceEngine.

        Args:
            filename: The filename storing the trace.
            mode: The mode of the trace, "write" or "read". Defaults to "write".
            strict:
                Whether to match strictly when used as a cache. Defaults to True.

                - True: matching according to the generation id, prompts, and
                    parameters. And cache stops to work whenever a match failed.
                - False: only matching prompts and parameters.
        """
        self._mode = mode
        self._strict = strict
        self._events: List[TraceEventBase] = []  # events read from the file
        self._trace_nodes: Dict[str, TraceNode] = {}
        self._gen_cache: Dict[str, List[Any]] = {}
        self._lock = Lock()
        self._func_stack: List[str] = []

        if mode == "write":
            if os.path.exists(filename):
                logger.warning(f"Trace file {filename} already exists, overwriting")
            self._file = open(filename, "wb+")
        elif mode == "read":
            if not os.path.exists(filename):
                raise FileNotFoundError(f"Trace file {filename} not found")
            self._file = open(filename, "rb+")
            self._read()
        else:
            raise ValueError(f"Invalid mode {mode}, only 'write' or 'read' allowed.")

    @property
    def events(self) -> List[TraceEventBase]:
        """The list of events in the trace."""
        return self._events

    @property
    def trace_nodes(self) -> Dict[str, TraceNode]:
        """The dictionary of trace nodes."""
        return self._trace_nodes

    def append(self, event: TraceEventBase) -> None:
        """Append an event to the trace."""
        if self._mode == "write":
            with self._lock:
                logger.debug(f"add to trace {event}")
                pickle.dump(event, self._file)
                self._file.flush()

        self._events.append(event)
        name, time_stamp = event.name, event.time_stamp
        assert name is not None
        if isinstance(event, FunctionCallEvent):
            newnode = self._add_node(name, self._last_func, type="func")
            newnode.start_time = time_stamp
            newnode.args = event.args
            self._func_stack.append(name)
        elif isinstance(event, FunctionReturnEvent):
            node = self._get_node(name)
            if node:
                node.end_time = time_stamp
            self._pop_func()
        elif isinstance(event, GenerationInitEvent):
            newnode = self._add_node(name, self._last_func)
            newnode.start_time = time_stamp
        elif isinstance(event, GenerationResponseEvent):
            node = self._get_node(name)
            if node:
                node.end_time = time_stamp
                node.args = event.args
                node.ret = event.ret
        elif isinstance(event, CompletionRequestEvent):
            # Use name + "_raw" to represent the raw completion request
            newnode = self._add_node(name + "_raw", name)
            newnode.start_time = time_stamp
        elif isinstance(event, CompletionResponseEvent):
            node = self._get_node(name + "_raw")
            if node:
                node.end_time = time_stamp
                node.args = event.args
                node.ret = event.ret
                node.info["cost"] = event.cost

            # cached for raw completion response
            key = self._cache_key(name, event.args)
            if key not in self._gen_cache:
                self._gen_cache[key] = []
            self._gen_cache[key].append(event.ret)

    def find_cache(self, name: str, args: Dict) -> Any:
        """Find a cached response for a generation request.

        Args:
            name: The name of the generation request.
            args: The arguments of the generation request.
        """
        with self._lock:
            entry_list = self._gen_cache.get(self._cache_key(name, args), None)
            if not entry_list or len(entry_list) == 0:
                return None
            entry = entry_list.pop(0)
            return entry

    def _add_node(
        self, name: str, parent_name: Optional[str] = None, type: str = "gen"
    ) -> TraceNode:
        parent = self._get_node(parent_name)
        newnode = TraceNode(type=type, name=name, parent=parent)
        if name in self._trace_nodes:
            raise ValueError(f"Node {name} already exists in trace")
        self._trace_nodes[name] = newnode
        if parent:
            parent.children.append(newnode)
        return newnode

    def _get_node(self, name: Optional[str]) -> Optional[TraceNode]:
        if name is None:
            return None
        if name not in self._trace_nodes:
            raise ValueError(f"Node {name} not found in trace")
        return self._trace_nodes[name]

    @property
    def _last_func(self) -> Optional[str]:
        if len(self._func_stack):
            return self._func_stack[-1]
        return None

    def _pop_func(self) -> str:
        return self._func_stack.pop()

    def _cache_key(self, name: str, args: Dict) -> str:
        if self._strict:
            return f"{name} {args}"
        else:
            return f"{args}"

    def _read(self) -> None:
        while True:
            try:
                event: TraceEventBase = pickle.load(self._file)
                self.append(event)
            except EOFError:
                break

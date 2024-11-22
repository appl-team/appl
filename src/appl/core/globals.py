import contextvars
import threading
from argparse import Namespace
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum
from typing import Any, Union

# Singleton stats object
global_vars = Namespace()
global_vars.lock = threading.Lock()

# tracing
global_vars.trace_engine = None
global_vars.gen_cnt = 0
global_vars.current_func = contextvars.ContextVar("current_func", default=None)

# thread-level vars
thread_local = threading.local()

# streaming
global_vars.live = None
global_vars.live_lock = threading.Lock()

# executors (to be replaced by appl.init())
global_vars.llm_thread_executor = ThreadPoolExecutor(
    max_workers=10, thread_name_prefix="llm"
)
global_vars.general_thread_executor = ThreadPoolExecutor(
    max_workers=20, thread_name_prefix="general"
)
global_vars.general_process_executor = ProcessPoolExecutor(max_workers=10)


def get_thread_local(name: str, default: Any = None) -> Any:
    """Get the value of a thread-local variable."""
    return getattr(thread_local, name, default)


def set_thread_local(name: str, value: Any) -> None:
    """Set the value of a thread-local variable."""
    setattr(thread_local, name, value)


def inc_thread_local(name: str, delta: Union[int, float] = 1) -> Any:
    """Increment a thread-local variable by a delta and return the new value."""
    value = get_thread_local(name, 0)
    value += delta
    setattr(thread_local, name, value)
    return value


def get_global_var(name: str, default: Any = None) -> Any:
    """Get the value of a global variable."""
    with global_vars.lock:
        return getattr(global_vars, name, default)


def set_global_var(name: str, value: Any) -> None:
    """Set the value of a global variable."""
    with global_vars.lock:
        setattr(global_vars, name, value)


def inc_global_var(name: str, delta: Union[int, float] = 1) -> Any:
    """Increment a global variable by a delta and return the new value."""
    with global_vars.lock:
        value = getattr(global_vars, name, 0)
        value += delta
        setattr(global_vars, name, value)
    return value


class ExecutorType(str, Enum):
    """The type of the executor."""

    LLM_THREAD_POOL = "llm_thread_pool"
    GENERAL_THREAD_POOL = "general_thread_pool"
    GENERAL_PROCESS_POOL = "general_process_pool"
    NEW_THREAD = "new_thread"
    NEW_PROCESS = "new_process"


def get_executor(
    executor_type: ExecutorType,
) -> Union[ThreadPoolExecutor, ProcessPoolExecutor]:
    """Get the executor of a given type."""
    if executor_type == ExecutorType.LLM_THREAD_POOL:
        return global_vars.llm_thread_executor
    elif executor_type == ExecutorType.GENERAL_THREAD_POOL:
        return global_vars.general_thread_executor
    elif executor_type == ExecutorType.GENERAL_PROCESS_POOL:
        return global_vars.general_process_executor
    elif executor_type == ExecutorType.NEW_THREAD:
        return ThreadPoolExecutor(max_workers=1)
    elif executor_type == ExecutorType.NEW_PROCESS:
        return ProcessPoolExecutor(max_workers=1)
    else:
        raise ValueError(f"Invalid executor type: {executor_type}")

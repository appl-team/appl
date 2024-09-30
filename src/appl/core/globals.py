import threading

from .types import *

# Singleton stats object
global_vars = Namespace()
global_vars.lock = threading.Lock()

# tracing
global_vars.trace_engine = None
global_vars.gen_cnt = 0

# thread-level vars
thread_local = threading.local()


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

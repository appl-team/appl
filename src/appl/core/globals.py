from threading import Lock

from .types import *

# Singleton stats object
global_vars = Namespace()
global_vars.lock = Lock()

# tracing
global_vars.trace_engine = None
global_vars.gen_cnt = 0


def inc_global(name: str, delta: Union[int, float] = 1) -> Any:
    """Increment a global variable by a delta and return the new value."""
    with global_vars.lock:
        value = getattr(global_vars, name, 0)
        value += delta
        setattr(global_vars, name, value)
    return value

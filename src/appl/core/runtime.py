"""helper functions for runtime execution within the compiled function."""

from argparse import Namespace
from typing import Any, Callable, Dict

from .context import PromptContext
from .types import CallFuture, StringFuture


def appl_with_ctx(
    *args: Any,
    _func: Callable,
    _ctx: PromptContext = PromptContext(),
    _globals: Any = None,
    _locals: Any = None,
    **kwargs: Any,
) -> Any:
    """Forward context to prompt functions."""
    if _func is globals:
        # use the globals when calling the function
        return _globals
    if _func is locals:
        # use the locals when calling the function
        return _locals
    if _func in (exec, eval):
        # fix the globals and locals for exec and eval
        if len(args) < 2 and "globals" not in kwargs:
            args = args + (_globals,)
        elif len(args) < 3 and "locals" not in kwargs:
            args = args + (_locals,)
    if getattr(_func, "__need_ctx__", False):
        kwargs["_ctx"] = _ctx  # add the context to the kwargs
    return _func(*args, **kwargs)


def appl_execute(
    s: Any,
    _ctx: PromptContext = PromptContext(),
) -> None:
    """Interact with the prompt context using the given value."""
    _ctx.grow(s)


def appl_format(
    value: Any, format_spec: str = "", conversion: int = -1
) -> StringFuture:
    """Create a StringFuture object that represents the formatted string."""
    if conversion >= 0:
        conversion_func: Dict[str, Callable] = {"s": str, "r": repr, "a": ascii}
        if (c := chr(conversion)) not in conversion_func:
            raise ValueError(f"Invalid conversion character: {c}")
        value = StringFuture(CallFuture(conversion_func[c], value))

    return StringFuture(CallFuture(format, value, format_spec))

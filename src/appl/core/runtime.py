"""helper functions for runtime execution within the compiled function."""

import inspect

from .config import configs
from .context import PromptContext
from .generation import Generation
from .message import BaseMessage
from .printer import PromptRecords
from .promptable import Promptable, promptify
from .types import *


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
    if s is None:
        return
    if isinstance(s, str):
        add_str = True
        if _ctx._is_first_str:
            docstring = _ctx._func_docstring
            if docstring is not None:
                docstring = inspect.cleandoc(docstring)
            if _ctx._include_docstring:
                if docstring is None:
                    logger.warning(
                        f"No docstring found for {_ctx._func_name}, cannot include it."
                    )
                else:
                    assert s == docstring, f"Docstring mismatch: {s}"
            elif s == docstring and _ctx._docstring_quote_count != 1:
                add_str = False
                if configs.getattrs(
                    "settings.logging.display.docstring_warning", False
                ):
                    logger.warning(
                        f'The docstring """{s}""" for `{_ctx._func_name}` is excluded from the prompt. '
                        "To include the docstring, set include_docstring=True in the @ppl function."
                    )
        if add_str:
            _ctx.add_string(StringFuture(s))
        _ctx._is_first_str = False
    elif isinstance(s, StringFuture):
        _ctx.add_string(s)
    elif isinstance(s, PromptRecords):
        _ctx.add_records(s)
    elif isinstance(s, BaseMessage):
        _ctx.add_message(s)
    elif isinstance(s, Image):
        _ctx.add_image(s)
    elif isinstance(s, Generation):
        appl_execute(s.as_prompt(), _ctx)
    elif isinstance(s, Promptable):
        # recursively apply
        appl_execute(promptify(s), _ctx)
    elif isinstance(s, Sequence):
        # sequence of items, recursively apply
        for x in s:
            appl_execute(x, _ctx)
    elif isinstance(s, Namespace):  # for advanced usage only
        logger.info(f"updating context variables using the namespace: {s}")
        _ctx._set_vars(s)
    else:
        logger.warning(f"Cannot convert {s} of type {type(s)} to prompt, ignore.")


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

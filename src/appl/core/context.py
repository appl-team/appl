from __future__ import annotations

import inspect
from argparse import Namespace
from copy import deepcopy
from typing import Any, Iterable, Optional

from loguru import logger
from PIL.ImageFile import ImageFile

from .globals import global_vars
from .message import BaseMessage, Conversation, SystemMessage
from .printer import PrinterPop, PrinterPush, PromptPrinter, PromptRecords
from .promptable import Promptable, promptify
from .types import ContentPart, Image, String, StringFuture


class PromptContext:
    """The context of the APPL function."""

    def __init__(self, globals_: Optional[Namespace] = None):
        """Initialize the PromptContext object.

        Args:
            globals_: The global namespace of the APPL function.
        """
        if globals_ is None:
            # create a new namespace (should inside __init__)
            globals_ = Namespace()
        self.globals = globals_
        # set default values
        if "messages" not in globals_:
            self.messages = Conversation(system_messages=[], messages=[])
        if "printer" not in globals_:
            self.printer = PromptPrinter()
        if "is_outmost" not in globals_:
            self.is_outmost = True

        # local vars start with "_"
        self.locals = Namespace()
        self._records = PromptRecords()
        self._func_name: Optional[str] = None
        self._func_docstring: Optional[str] = None
        self._docstring_as: Optional[str] = None
        self._docstring_quote_count: Optional[int] = None
        self._is_first_str: bool = True

    @property
    def records(self) -> PromptRecords:
        """The prompt records of the context."""
        return self._records

    def set_records(self, records: PromptRecords) -> None:
        """Set the prompt records of the context."""
        self._records = records

    def grow(self, s: Any) -> "PromptContext":
        """Grow the prompt context and return the updated context."""
        if s is None:
            return self
        if isinstance(s, str):
            add_str = True
            if self._is_first_str:
                docstring = self._func_docstring
                if docstring is not None:
                    docstring = inspect.cleandoc(docstring)
                if self._docstring_as is not None:
                    if docstring is None:
                        logger.warning(
                            f"No docstring found for {self._func_name}, cannot include it."
                        )
                    else:
                        assert s == docstring, f"Docstring mismatch: {s}"
                        if self._docstring_as == "system":
                            self.add_message(SystemMessage(s))
                            add_str = False
                        elif self._docstring_as != "user":
                            raise ValueError(
                                f"Unknown message role for docstring: {self._docstring_as}."
                                "Only support 'system' and 'user' now."
                            )
                        # else: user message, treat as a normal string
                elif s == docstring and self._docstring_quote_count != 1:
                    add_str = False
                    if global_vars.configs.settings.logging.display.docstring_warning:
                        logger.warning(
                            f'The docstring """{s}""" for `{self._func_name}` is excluded from the prompt. '
                            "To include the docstring, set the message role in `docstring_as` in the @ppl function."
                        )
                # else: single quote string as docstring, treat as a normal string
            if add_str:
                self.add_string(StringFuture(s))
            self._is_first_str = False
        elif isinstance(s, StringFuture):
            self.add_string(s)
        elif isinstance(s, PromptRecords):
            self.add_records(s)
        elif isinstance(s, BaseMessage):
            self.add_message(s)
        elif isinstance(s, ContentPart):  # Image, Audio, ...
            self.add_content_part(s)
        elif isinstance(s, ImageFile):
            self.add_content_part(Image.from_image(s))
        elif isinstance(s, Promptable):
            # recursively apply
            self.grow(promptify(s))
        elif isinstance(s, Iterable):
            # iterable items, recursively apply
            for x in s:
                self.grow(x)
        elif isinstance(s, Namespace):  # for advanced usage only
            logger.info(f"updating context variables using the namespace: {s}")
            self._set_vars(s)
        else:
            logger.warning(f"Cannot convert {s} of type {type(s)} to prompt, ignore.")
        return self

    def add_string(self, string: String) -> None:
        """Add a string to the prompt context."""
        if isinstance(string, str):
            string = StringFuture(string)
        self.messages.extend(self.printer(string))
        self.records.record(string)

    def add_content_part(self, content_part: ContentPart) -> None:
        """Add a content part to the prompt context."""
        self.messages.extend(self.printer(content_part))
        self.records.record(content_part)

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the prompt context."""
        self.messages.extend(self.printer(message))
        self.records.record(message)

    def add_records(self, records: PromptRecords, write_to_prompt: bool = True) -> None:
        """Add prompt records to the prompt context."""
        if write_to_prompt:
            self.messages.extend(self.printer(records))
        self.records.extend(records)

    def push_printer(self, push_args: PrinterPush) -> None:
        """Push a new printer state to the prompt context."""
        self.printer.push(push_args)
        self.records.record(push_args)

    def pop_printer(self) -> None:
        """Pop a printer state from the prompt context."""
        self.printer.pop()
        self.records.record(PrinterPop())

    def copy(self) -> "PromptContext":
        """Create a new prompt context that copies the globals."""
        return PromptContext(globals_=deepcopy(self.globals))

    def inherit(self) -> "PromptContext":
        """Create a new prompt context that has the same globals."""
        return PromptContext(globals_=self.globals)

    def _set_vars(self, vars: Namespace) -> None:
        for k, v in vars.items():
            setattr(self, k, v)

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to locals and globals."""
        # logger.debug("getattr", name)
        if name == "locals":
            return self.locals
        if name == "globals":
            return self.globals
        # Locals have higher priority
        if name in self.locals:
            return getattr(self.locals, name)
        if name in self.globals:
            return getattr(self.globals, name)
        # Not found, raise AttributeError
        if "_" + name in self.locals:
            raise AttributeError(
                f"Attribute '{name}' is local to the function, add '_' to access it."
            )
        raise AttributeError(f"Attribute '{name}' not found.")

    def __setattr__(self, name: str, val: Any) -> None:
        """Forward attribute assignment to vars."""
        # logger.debug("setattr", name, val)
        if name == "locals":
            self.__dict__["locals"] = val
        elif name == "globals":
            self.__dict__["globals"] = val
        elif name.startswith("_"):
            setattr(self.locals, name, val)
        else:
            setattr(self.globals, name, val)

    def __repr__(self) -> str:
        return f"PromptContext(globals={self.globals!r}, locals={self.locals!r})"

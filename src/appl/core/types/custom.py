from enum import Enum


class ResponseType(str, Enum):
    """The type of generation response."""

    TEXT = "text"
    """A text completion."""
    TOOL_CALL = "tool_calls"
    """A list of tool calls."""
    OBJECT = "obj"
    """An instance of a response model."""
    IMAGE = "image"
    """An image."""
    UNFINISHED = "unfinished"
    """The response is not finished."""

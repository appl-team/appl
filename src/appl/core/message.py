from __future__ import annotations

from dataclasses import dataclass

from pydantic import model_validator
from termcolor import COLORS, colored

from .config import configs
from .tool import ToolCall
from .types import *


def get_role_color(role: MessageRole) -> Optional[str]:
    """Get the color of the message based on the role."""
    color_dict = configs.getattrs("settings.messages.colors", {})
    return color_dict.get(role.type, None)


def get_colored_role_text(role: Optional[MessageRole], content: str) -> str:
    """Get the colored text based on the role."""
    if role:
        color = get_role_color(role)
        if color in COLORS:
            return colored(content, color)  # type: ignore
    return content


class BaseMessage(BaseModel, ABC):
    """The base class for messages."""

    content: Any = Field(..., description="The content of the message")
    role: Optional[MessageRole] = Field(
        None, description="The role of the messages owner"
    )
    info: Optional[Dict] = Field(
        {}, description="Additional information for the message"
    )

    def __init__(self, content: Any = None, *args: Any, **kwargs: Any) -> None:
        """Create a message with content and extra arguments.

        Provides a more flexible way to create a message.
        """
        super().__init__(content=content, *args, **kwargs)

    @property
    def is_system(self) -> bool:
        """Whether the message is a system message."""
        return self.role is not None and self.role.is_system

    @property
    def is_user(self) -> bool:
        """Whether the message is a user message."""
        return self.role is not None and self.role.is_user

    @property
    def is_ai(self) -> bool:
        """Whether the message is an assistant message."""
        return self.role is not None and self.role.is_assistant

    @property
    def is_tool(self) -> bool:
        """Whether the message is a tool message."""
        return self.role is not None and self.role.is_tool

    def validate_role(self, target_role: MessageRole) -> None:
        """Validate the role of the message, fill the role if not provided."""
        target_type = target_role.type
        if target_type is None:
            raise ValueError("Target role type must be provided.")
        if self.role is None:
            self.role = target_role
        elif self.role.type is None:
            # fill the role type as the target type
            self.role = MessageRole(type=target_type, name=self.role.name)
        elif self.role.type != target_type:
            raise ValueError(f"Invalid role for {target_type} message: {self.role}")

    def should_merge(self, other: "BaseMessage") -> bool:
        """Whether the message should be merged with the other message."""
        if self.is_tool or other.is_tool:
            # not merge tool messages
            return False
        if self.content is None or other.content is None:
            return False
        return self.role == other.role

    def get_content(self, as_str: bool = False) -> Any:
        """Get the content of the message.

        Materialize the content if it is a FutureValue.
        """
        content = self.content
        if content is not None:
            if isinstance(content, ContentList):
                return content.get_contents()  # return a list of dict
            if isinstance(content, FutureValue):
                # materialize the content
                content = content.val
            if as_str:  # not apply to ContentList
                content = str(content)
        return content

    # TODO: implement classmethod: from dict
    def get_dict(self, default_role: Optional[MessageRole] = None) -> Dict[str, Any]:
        """Return a dict representation of the message."""
        # materialize the content using str()
        role = self.role or default_role
        if role is None:
            raise ValueError("Role or default role must be provided.")
        if role.type is None:
            if default_role and default_role.type:
                role = MessageRole(type=default_role.type, name=role.name)
            else:
                raise ValueError("Role type must be provided.")
        data = {"content": self.get_content(as_str=True), **role.get_dict()}
        return data

    def merge(self: "Message", other: "BaseMessage") -> Optional["Message"]:
        """Merge the message with another message."""
        if self.should_merge(other):
            # merge the content
            res = self.model_copy()
            if isinstance(other.content, ContentList) and not isinstance(
                res.content, ContentList
            ):
                res.content = ContentList(contents=[res.content])
            res.content += other.content
            return res
        return None

    def str_with_default_role(self, default_role: Optional[MessageRole] = None) -> str:
        """Return the string representation of the message with default role."""
        return self._get_colored_content(self.role or default_role)

    def _get_serialized_content(self, role: Optional[MessageRole] = None) -> str:
        if role is None:
            return f"{self.content}"
        return f"{role}: {self.content}"

    def _get_colored_content(self, role: Optional[MessageRole] = None) -> str:
        return get_colored_role_text(role, self._get_serialized_content(role))

    def __str__(self) -> str:
        return self._get_colored_content(self.role)

    def __repr__(self) -> str:
        return f"Message(role={self.role!r}, content={self.content!r})"


Message = TypeVar("Message", bound=BaseMessage)


class ChatMessage(BaseMessage):
    """A message in the chat conversation."""

    def __init__(
        self,
        content: Any = None,
        *,
        role: Optional[MessageRole] = None,
        **kwargs: Any,
    ) -> None:
        """Create a chat message with content and extra arguments."""
        super().__init__(content=content, role=role, **kwargs)


class SystemMessage(BaseMessage):
    """A system message in the conversation."""

    def __init__(
        self,
        content: Any = None,
        *,
        role: Optional[MessageRole] = None,
        **kwargs: Any,
    ) -> None:
        """Create a system message with content and extra arguments."""
        super().__init__(content=content, role=role, **kwargs)
        self.validate_role(SYSTEM_ROLE)


class UserMessage(BaseMessage):
    """A user message in the conversation."""

    def __init__(
        self,
        content: Any = None,
        *,
        role: Optional[MessageRole] = None,
        **kwargs: Any,
    ) -> None:
        """Create a user message with content and extra arguments."""
        super().__init__(content=content, role=role, **kwargs)
        self.validate_role(USER_ROLE)


class AIMessage(BaseMessage):
    """An assistant message in the conversation."""

    tool_calls: List[ToolCall] = Field(
        [], description="The tool calls generated by the model."
    )

    def __init__(
        self,
        content: Any = None,
        *,
        role: Optional[MessageRole] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        **kwargs: Any,
    ) -> None:
        """Create an assistant message with content and extra arguments."""
        if tool_calls is None:
            tool_calls = []
        super().__init__(content=content, role=role, tool_calls=tool_calls, **kwargs)
        self.validate_role(ASSISTANT_ROLE)

    def get_dict(self, default_role: Optional[MessageRole] = None) -> Dict[str, Any]:
        """Return a dict representation of the message."""
        data = super().get_dict(default_role)
        if len(self.tool_calls):
            data["tool_calls"] = [call.get_dict() for call in self.tool_calls]
        return data

    def _get_serialized_content(self, role: Optional[MessageRole] = None) -> str:
        assert role == self.role, "Role must be the same as the message role."
        s = f"{self.role}:"
        if self.content is not None:
            s += f" {self.content}"
        if len(self.tool_calls):
            s += f" {self.tool_calls}"
        return s

    def __repr__(self) -> str:
        return (
            f"AIMessage(role={self.role!r}, content={self.content!r}, "
            f"tool_calls={self.tool_calls!r})"
        )


class ToolMessage(BaseMessage):
    """A tool message in the conversation."""

    tool_call_id: str = Field(
        ..., description="Tool call that this message is responding to."
    )
    has_error: bool = Field(
        False, description="Whether the message is an error message."
    )

    def __init__(
        self,
        content: Any = None,
        *,
        role: Optional[MessageRole] = None,
        tool_call_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Create a tool message with content and extra arguments."""
        super().__init__(
            content=content, role=role, tool_call_id=tool_call_id, **kwargs
        )
        self.validate_role(TOOL_ROLE)

    def get_dict(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Return a dict representation of the message."""
        data = super().get_dict(*args, **kwargs)
        data["tool_call_id"] = self.tool_call_id
        return data


MESSAGE_CLASS_DICT = {
    None: ChatMessage,
    SYSTEM: SystemMessage,
    USER: UserMessage,
    ASSISTANT: AIMessage,
    TOOL: ToolMessage,
}


def as_message(
    role: Optional[MessageRole],
    content: StrOrImg,
    *args: Any,
    **kwargs: Any,
) -> BaseMessage:
    """Create a message with role, content and extra arguments."""
    role_type = role.type if role else None
    if role_type not in MESSAGE_CLASS_DICT:
        raise ValueError(f"Unknown role: {role}")
    cls = MESSAGE_CLASS_DICT[role_type]
    if isinstance(content, Image):
        content = ContentList(contents=[content])  # type: ignore
    return cls(content=content, role=role, *args, **kwargs)


def collapse_messages(messages: List[Message]) -> List[Message]:
    """Collapse a list of the messages by merging the messages with the same sender."""
    res = []
    msg: Optional[Message] = None
    for m in messages:
        if msg is None:
            msg = m
        else:
            if (tmp := msg.merge(m)) is not None:
                # merge success, update the msg
                msg = tmp
            else:
                # merge failed, append the old message to the list
                res.append(msg)
                # a new message starts
                msg = m
    if msg is not None:
        res.append(msg)
    return res


class Conversation(BaseModel):
    """A conversation containing messages."""

    system_messages: List[SystemMessage] = Field([], description="The system messages")
    messages: List[BaseMessage] = Field(
        [], description="The messages in the conversation"
    )

    @property
    def has_message_role(self) -> bool:
        """Whether the conversation has message roles."""
        return any(m.role is not None for m in self.system_messages + self.messages)

    def collapse(self) -> "Conversation":
        """Collapse the messages in the conversation."""
        self.system_messages = collapse_messages(self.system_messages)
        if len(self.system_messages) > 1:
            raise ValueError("System messages cannot be fully collapsed.")
        self.messages = collapse_messages(self.messages)
        return self

    def materialize(self) -> None:
        """Materialize the messages in the conversation."""
        str(self)

    def set_system_messages(self, messages: List[SystemMessage]) -> None:
        """Set the system messages."""
        if len(self.system_messages):
            logger.warning("Overwriting system message.")
        self.system_messages = messages

    def append(self, message: Message) -> None:
        """Append a message to the conversation."""
        if message.is_system:
            if len(self.messages):
                # NOTE: Now allow appending system message after other messages
                # raise ValueError("Cannot append system message after other messages.")

                # Added a warning instead
                logger.warning(
                    "Modifying system message after other types of messages."
                )
            self.system_messages.append(message)  # type: ignore
        else:
            self.messages.append(message)

    def extend(self, other: "Conversation") -> None:
        """Extend the conversation with another conversation."""
        for sys_m in other.system_messages:
            self.append(sys_m)
        for m in other.messages:
            self.append(m)

    # TODO: implement classmethod: from list of dict
    def as_list(
        self, default_role: Optional[MessageRole] = USER_ROLE
    ) -> List[Dict[str, str]]:
        """Return a list of dict representation of the conversation."""
        self.collapse()
        res = [m.get_dict() for m in self.system_messages]
        res += [m.get_dict(default_role) for m in self.messages]
        return res

    def make_copy(self):
        """Make a copy of the conversation."""
        return Conversation(
            system_messages=self.system_messages.copy(),
            messages=self.messages.copy(),
        )

    def __repr__(self) -> str:
        return f"Conversation({self.system_messages!r}, {self.messages!r})"

    def __str__(self) -> str:
        self.collapse()
        role = USER_ROLE if self.has_message_role else None
        contents = [m.str_with_default_role() for m in self.system_messages]
        contents += [m.str_with_default_role(role) for m in self.messages]
        return "\n".join(contents)

    def __iter__(self) -> Iterator[BaseMessage]:  # type: ignore
        """Iterate over messages, excluding the system message."""
        return iter(self.messages)

    def __getitem__(self, index: int) -> BaseMessage:
        """Get message by index, excluding the system message."""
        return self.messages[index]

    def __len__(self) -> int:
        """Length of the conversation, excluding the system message."""
        return len(self.messages)

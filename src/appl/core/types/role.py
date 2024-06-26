from .basic import *

# Roles
SYSTEM = "system"
USER = "user"
ASSISTANT = "assistant"
TOOL = "tool"


class MessageRole(BaseModel):
    """The role of the message owner."""

    type: Optional[str] = None
    name: Optional[str] = None

    def __init__(self, type: Optional[str] = None, name: Optional[str] = None):
        """Initialize the MessageRole object.

        Args:
            type: The type of the role.
            name: An optional name for the role, differentiate between roles of the same type."
        """
        super().__init__(type=type, name=name)

    @property
    def is_system(self) -> bool:
        """Whether the role is a system role."""
        return self.type == SYSTEM

    @property
    def is_user(self) -> bool:
        """Whether the role is a user role."""
        return self.type == USER

    @property
    def is_assistant(self) -> bool:
        """Whether the role is an assistant role."""
        return self.type == ASSISTANT

    @property
    def is_tool(self) -> bool:
        """Whether the role is a tool role."""
        return self.type == TOOL

    def get_dict(self) -> Dict[str, Any]:
        """Get the role as a dictionary."""
        data = {"role": self.type}
        if self.name:
            data["name"] = self.name
        return data

    def __str__(self) -> str:
        s = str(self.type)
        if self.name:
            s += f"({self.name})"
        return s

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MessageRole):
            return self.type == other.type and self.name == other.name
        return False


SYSTEM_ROLE = MessageRole(SYSTEM)
"""The system role with name not specified."""
USER_ROLE = MessageRole(USER)
"""The user role with name not specified."""
ASSISTANT_ROLE = MessageRole(ASSISTANT)
"""The assistant role with name not specified."""
TOOL_ROLE = MessageRole(TOOL)
"""The tool role with name not specified."""

import inspect
import json
from abc import ABC, abstractmethod
from inspect import Signature

from docstring_parser import Docstring, parse
from openai.types.chat import ChatCompletionMessageToolCall
from pydantic import ConfigDict, create_model, field_serializer

from .types import *

# from pydantic._internal._model_construction import ModelMetaclass


class BaseTool(BaseModel, ABC):
    """The base class for a Tool."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the Tool")
    """The name of the Tool."""
    short_desc: str = Field("", description="The short description of the Tool")
    """The short description of the Tool."""
    long_desc: str = Field("", description="The long description of the Tool")
    """The long description of the Tool."""
    params: type[BaseModel] = Field(..., description="The parameters of the Tool")
    """The parameters of the Tool."""
    returns: type[BaseModel] = Field(..., description="The return of the Tool")
    """The return of the Tool."""
    raises: List[Dict[str, Optional[str]]] = Field(
        [], description="The exceptions raised by the Tool"
    )
    """The exceptions raised by the Tool."""
    examples: List[str] = Field([], description="The examples of the Tool")
    """The examples of the Tool."""
    info: Dict = Field({}, description="Additional information of the Tool")
    """Additional information of the Tool."""

    # TODO: add toolkit option
    def __init__(self, func: Callable, **predefined: Any):
        """Create a tool from a function."""
        name = func.__name__
        sig = inspect.signature(func)
        doc = func.__doc__
        super().__init__(name=name, **self.parse_data(sig, doc, predefined))
        self._predefined = predefined
        self._func = func
        self.__name__ = name
        self.__signature__ = sig  # type: ignore
        self.__doc__ = doc  # overwrite the doc string

    @classmethod
    def parse_data(
        cls, sig: Signature, docstring: Optional[str], predefined: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse data from the signature and docstring of a function."""
        doc = parse(docstring or "")
        data: Dict[str, Any] = {
            "short_desc": doc.short_description or "",
            "long_desc": doc.long_description or "",
        }

        # build params
        params = {}
        doc_param = {p.arg_name: p for p in doc.params}
        for name, param in sig.parameters.items():
            anno = param.annotation
            default = param.default

            if default is param.empty:
                default = ...  # required
            if name in doc_param:
                # fill in desc for the param
                default = Field(default, description=doc_param[name].description)
                # fill in type annotation if not annotated in the function
                if (anno is param.empty) and (doc_param[name].type_name is not None):
                    # use type annotation from docstring
                    anno = doc_param[name].type_name
            # replace empty annotation with Any
            if anno is param.empty:
                anno = Any
            if name not in predefined:
                params[name] = (anno, default)
        data["params"] = create_model("parameters", **params)  # type: ignore

        # build returns
        anno = sig.return_annotation
        if anno is sig.empty:
            if (doc.returns is not None) and (doc.returns.type_name is not None):
                # use type annotation from docstring
                anno = doc.returns.type_name
            else:
                anno = Any
        default = ...  # required
        if doc.returns is not None:
            # fill in desc for the return
            default = Field(..., description=doc.returns.description)
        data["returns"] = create_model("returns", returns=(anno, default))

        # build raises
        data["raises"] = [
            {"type": exc.type_name, "desc": exc.description} for exc in doc.raises
        ]

        # build examples
        data["examples"] = doc.examples
        return data

    @property
    def openai_schema(self) -> dict:
        """Get the OpenAI schema of the tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self._get_description(),
                "parameters": self.params.model_json_schema(),
            },
        }

    def to_str(self) -> str:
        """Represent the tool as a string."""
        s = f"def {self.name}{self.__signature__}:\n"
        s += f'    """{self.__doc__}"""'
        return s

    @abstractmethod
    def _get_description(self) -> str:
        raise NotImplementedError

    @field_serializer("params", when_used="json")
    def _serialize_params(self, params: type[BaseModel]) -> dict:
        return params.model_json_schema()

    @field_serializer("returns", when_used="json")
    def _serialize_returns(self, returns: type[BaseModel]) -> dict:
        return returns.model_json_schema()

    def __str__(self) -> str:
        return self.to_str()

    def _call(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.update(self._predefined)  # use predefined kwargs
        return self._func(*args, **kwargs)

    __call__ = _call


class Tool(BaseTool):
    """The Tool class that can be called by LLMs."""

    def __init__(self, func: Callable, use_short_desc: bool = False, **kwargs: Any):
        """Create a tool from a function.

        Args:
            func: The function to create the tool from.
            use_short_desc:
                Whether to use the short description instead of the full description.
            kwargs: Additional arguments for the tool.
        """
        super().__init__(func=func, **kwargs)
        self._use_short_desc = use_short_desc

    def _get_description(self):
        if not self.short_desc:
            logger.warning(f"Tool {self.name} has no description.")
            return self.name

        if (not self.long_desc) or self._use_short_desc:
            return self.short_desc

        # use full desc
        return self.short_desc + "\n\n" + self.long_desc


class ToolCall(BaseModel):
    """The class representing a tool call."""

    id: str = Field(..., description="The ID of the tool call.")
    """The ID of the tool call."""
    name: str = Field(..., description="The name of the function to call.")
    """The name of the function to call."""
    args: str = Field(..., description="The arguments to call the function with.")
    """The arguments to call the function with."""

    def get_dict(self):
        """Get the OpenAI format dictionary representation of the tool call."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.args,
            },
        }

    @classmethod
    def from_dict(cls, call: Dict) -> "ToolCall":
        """Create a ToolCall from a dictionary in the OpenAI format."""
        # throw error if incorrect format
        return cls(
            id=call["id"],
            name=call["function"]["name"],
            args=call["function"]["arguments"],
        )

    @classmethod
    def from_openai_tool_call(cls, call: ChatCompletionMessageToolCall) -> "ToolCall":
        """Create a ToolCall from an OpenAI tool call."""
        return cls(
            id=call.id,
            name=call.function.name,
            args=call.function.arguments,
        )

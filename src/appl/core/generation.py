from __future__ import annotations

import json
import time

from . import trace
from .config import configs
from .context import PromptContext
from .globals import inc_global
from .message import AIMessage, BaseMessage, ToolMessage
from .promptable import Promptable
from .response import CompletionResponse
from .server import BaseServer, GenArgs
from .tool import BaseTool, ToolCall
from .trace import GenerationInitEvent, add_to_trace
from .types import *


class Generation:
    """Represents a generation call to the model."""

    def __init__(
        self,
        server: BaseServer,
        args: GenArgs,
        *,
        mock_response: Optional[Union[CompletionResponse, str]] = None,
        lazy_eval: bool = False,
        _ctx: Optional[PromptContext] = None,
        **kwargs: Any,
        # kwargs used for extra args for the create method
    ) -> None:
        """Initialize the Generation object.

        Args:
            server: An LLM server where the generation request will be sent.
            args: The arguments of the generation call.
            mock_response: A mock response for the generation call.
            lazy_eval: If True, the generation call will be evaluated lazily.
            _ctx: The prompt context filled automatically by the APPL function.
            **kwargs: Extra arguments for the generation call.
        """
        # name needs to be unique and ordered, so it has to be generated in the main thread
        self._id = inc_global("gen_cnt") - 1  # take the value before increment

        self._server = server
        self._args = args
        self._ctx = _ctx
        self._extra_args = kwargs

        add_to_trace(GenerationInitEvent(name=self.id))
        if isinstance(mock_response, CompletionResponse):
            self._call = lambda: mock_response
        else:
            if mock_response:
                # use litellm's mock response
                kwargs.update({"mock_response": mock_response})
            # TODO: supports custom postprocessing messages
            self._call = CallFuture(
                self._server.create,
                lazy_eval=lazy_eval,
                args=args,
                gen_id=self.id,
                **kwargs,
            )

        # tools
        self._tools: Sequence[BaseTool] = args.tools
        self._name2tools = {tool.name: tool for tool in self._tools}

    @property
    def id(self) -> str:
        """The unique ID of the generation."""
        return f"@gen_{self._id}"

    def __call__(self):
        """Get the response of the generation call."""
        return self._call()

    @property
    def response(self) -> CompletionResponse:
        """The response of the generation call."""
        # NOTE: the result of the call will be cached in the CallFuture
        return self._call()

    @property
    def response_type(self) -> ResponseType:
        """The type of the response."""
        return self.response.type

    @property
    def is_message(self) -> bool:
        """Whether the response is a text message."""
        return self.response_type == ResponseType.TEXT

    @property
    def is_tool_call(self) -> bool:
        """Whether the response is a tool call."""
        return self.response_type == ResponseType.TOOL_CALL

    @property
    def is_obj(self) -> bool:
        """Whether the response is an object."""
        return self.response_type == ResponseType.OBJECT

    @property
    def message(self) -> Optional[str]:
        """The message of the response."""
        return self.response.message

    @property
    def tool_calls(self) -> List[ToolCall]:
        """The tool calls of the response."""
        return self.response.tool_calls

    @property
    def response_obj(self) -> Any:
        """The object of the response."""
        return self.response.response_obj

    @property
    def results(self) -> Any:
        """The results of the response."""
        return self.response.results

    @property
    def str_future(self) -> StringFuture:
        """The StringFuture representation of the response."""
        return StringFuture(self)

    def _call_tool(
        self, name: str, args: str, parallel: bool = False, use_process: bool = False
    ) -> Any:
        try:
            kwargs = json.loads(args)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing args: {args}") from e
        args_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        if configs.getattrs("settings.logging.display.tool_calls"):
            logger.info(f"Running tool call: {name}({args_str})")

        if name not in self._name2tools:
            raise ValueError(f"Error: Tool {name} not found")
        tool = self._name2tools[name]
        try:
            if parallel:
                res = CallFuture(tool, use_process=use_process, **kwargs)
            else:
                res = tool(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Error running tool call: {name}({args_str})") from e

        return res

    def run_tool_calls(
        self,
        filter_fn: Optional[Callable[[List[ToolCall]], List[ToolCall]]] = None,
        parallel: bool = False,
        use_process: bool = False,
        log_results: Optional[bool] = None,
    ) -> List[ToolMessage]:
        """Run all tool calls in the generation and return the results.

        Args:
            filter_fn:
                A function that takes a list of ToolCall objects and returns
                a filtered list of ToolCall objects. This function can be
                used to filter the tool calls that will be run.
            parallel: If True, run the tool calls in parallel. Default to False.
            use_process:
                If True, run the tool calls in separate processes,
                effective when parallel is True. Default to False.
            log_results:
                If True, log the results of the tool calls. Note This will wait for
                the results to be ready. Default to use the setting in configs.

        Returns:
            A list of ToolMessage objects.
        """
        if not self.is_tool_call:
            raise ValueError("Error: The Generation is not a tool call")
        if log_results is None:
            log_results = configs.getattrs("settings.logging.display.tool_results")
        tool_calls = self.tool_calls
        if filter_fn:
            tool_calls = filter_fn(tool_calls)
        messages = []
        for tc in tool_calls:
            role = MessageRole(TOOL, tc.name)
            try:
                tool_result = self._call_tool(
                    tc.name, tc.args, parallel=parallel, use_process=use_process
                )
                msg = ToolMessage(
                    tool_result, role=role, tool_call_id=tc.id, has_error=False
                )
            except Exception as e:
                logger.error(f"Error running tool call: {tc.name}({tc.args})")
                logger.error(e)
                msg = ToolMessage(str(e), role=role, tool_call_id=tc.id, has_error=True)
            messages.append(msg)
        if log_results:  # this will wait for the results to be ready
            for msg in messages:
                logger.info(f"Tool call result: {msg}")
        return messages

    def as_prompt(self) -> Union[AIMessage, StringFuture]:
        """Get the response of the generation as a promptable object."""
        if self._args.tools:
            if self.is_tool_call:
                return AIMessage(tool_calls=self.tool_calls)
        return StringFuture(self._call)

    def __add__(self, other: Union[String, "Generation"]) -> StringFuture:
        # Assume generation is a string
        if isinstance(other, Generation):
            return self.str_future + other.str_future
        elif isinstance(other, (str, StringFuture)):
            return self.str_future + other
        raise TypeError(
            f"unsupported operand type(s) for +: 'Generation' and '{type(other)}'"
        )

    def __radd__(self, other: String) -> StringFuture:
        # Assume generation is a string
        if isinstance(other, (str, StringFuture)):
            return other + self.str_future
        raise TypeError(
            f"unsupported operand type(s) for +: '{type(other)}' and 'Generation'"
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.response, name)

    def __str__(self) -> str:
        return str(self.response.results)

    def __repr__(self) -> str:
        return repr(str(self))

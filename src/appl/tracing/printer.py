import copy
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from litellm import ModelResponse
from loguru import logger

from ..compositor import Tagged as OriginalTagged
from ..core.config import Configs
from ..core.io import load_file
from ..core.printer import PromptRecords
from ..core.trace import (
    CompletionRequestEvent,
    CompletionResponseEvent,
    FunctionCallEvent,
    FunctionReturnEvent,
    GenerationInitEvent,
    GenerationResponseEvent,
    TraceEngineBase,
    TraceEventBase,
    TraceNode,
    TracePrinterBase,
)
from ..func import partial, ppl, records

folder = os.path.dirname(__file__)

Tagged = partial(OriginalTagged, indent_inside=4)


def timestamp_to_iso(time_stamp: float) -> str:
    """Convert the timestamp to the ISO format."""
    return datetime.fromtimestamp(time_stamp, timezone.utc).isoformat()


class TraceHTMLPrinter(TracePrinterBase):
    """The printer used to print the trace in the format of HTML."""

    def __init__(self):
        """Initialize the printer."""
        super().__init__()
        self._generation_style = "text-success-emphasis bg-Success-subtle list-group-item d-flex justify-content-between align-items-center"
        self._time_style = "position-absolute top-0 start-100 translate-middle badge rounded-pill bg-info"
        self._cost_style = "position-absolute bottom-0 start-100 translate-middle badge rounded-pill bg-warning"
        self._longest_shown_output = 70

        self._head = load_file(os.path.join(folder, "header.html"))
        self._color_map = {
            "user": "text-bg-info",
            "assistant": "text-bg-warning",
            "system": "text-bg-success",
        }

    @ppl
    def print(self, trace: TraceEngineBase, meta_data: Optional[Configs] = None) -> str:
        """Print the trace in the format of HTML."""
        with Tagged("html"):
            self._head
            with Tagged("body"):
                for node in trace.trace_nodes.values():
                    if node.parent is None:
                        self._print_node(node, trace.min_timestamp)
        if meta_data:
            with Tagged("table", attrs={"class": "table small"}):
                if start_time := meta_data.getattrs("info.start_time"):
                    self._make_line("Start Time", start_time)
                self._make_line("Full Configs", f"<pre>{meta_data.to_yaml()}</pre>")
        return str(records())

    @ppl
    def _print_messages(self, messages: List[Union[str, Dict]]) -> PromptRecords:
        def display(message: Union[str, Dict]) -> str:
            return f'<div style="white-space: pre-wrap;">{message}</div>'

        with Tagged("ul", attrs={"class": "list-group small"}):
            for message in messages:
                with Tagged("li", attrs={"class": "list-group-item"}):
                    if (
                        isinstance(message, dict)
                        and "role" in message
                        and "content" in message
                    ):
                        color = self._color_map.get(message["role"], "text-bg-info")
                        f"<span class='badge {color}'>{message['role']}</span>"
                        display(message["content"])
                    else:
                        display(message)
        return records()

    @ppl
    def _print_genargs(self, args: Dict, output: Optional[str] = None) -> PromptRecords:
        with Tagged("table", attrs={"class": "table small"}):
            for k, v in args.items():
                with Tagged("tr"):
                    with Tagged("th"):
                        f"{k}"
                    with Tagged("td"):
                        if k == "messages":
                            self._print_messages(v)
                        elif k in ["response_format"]:
                            f"<pre>{json.dumps(v, indent=2)}</pre>"
                        elif k in ["response_model"]:
                            f"<pre>{v}</pre>"
                        elif k == "stop":
                            repr(v)
                        else:
                            f"{v}"
            if output is not None:
                self._make_line("output", output)
        return records()

    @ppl
    def _print_gen(self, node: TraceNode, min_timestamp: float = 0.0) -> PromptRecords:
        name = node.name
        if node.args is not None:
            completion = node.children[0] if node.children else None
            with Tagged("ul", attrs={"class": "list-group m-1"}):
                li_attrs = {"class": self._generation_style}
                li_attrs.update(self._toggle_attrs(name))
                with Tagged("li", attrs=li_attrs):
                    f"<div><b>{name}:</b> {node.ret}</div>"
                    if completion and (runtime := completion.runtime) > 0:
                        f"<span class='{self._time_style}'>{runtime:.2e} s</span>"
                    if completion and (cost := completion.info.get("cost")):
                        f"<span class='{self._cost_style}'>$ {cost:.2e}</span>"
                with Tagged(
                    "li", attrs={"class": "list-group-item collapse", "id": name}
                ):
                    self._print_genargs(node.args, node.ret)
        else:
            li_attrs = {
                "class": "list-group-item text-warning-emphasis bg-warning-subtle"
            }
            with Tagged("ul", attrs={"class": "list-group m-1"}):
                with Tagged("li", attrs=li_attrs):
                    "Unfinished Generation"
        return records()

    @ppl
    def _print_func(self, node: TraceNode, min_timestamp: float = 0.0) -> PromptRecords:
        name = node.name
        with Tagged("ul", attrs={"class": "list-group m-2"}):
            li_attrs = {"class": "text-center bg-light list-group-item"}
            li_attrs.update(self._toggle_attrs(name, True))
            with Tagged("li", attrs=li_attrs):
                f"<b>{name}</b>"
            with Tagged("li", attrs={"class": "list-group-item show", "id": name}):
                # display details for the function
                # ? display time, args and kwargs
                # with Tagged("table", attrs={"class": "table small"}):
                #     start = node.start_time - min_timestamp
                #     end = node.end_time - min_timestamp
                #     runtime = end - start
                #     self._make_line(
                #         "Time", f"{runtime:.2e} s (from {start:.2e} to {end:.2e})"
                #     )
                #     # if node.args:
                #     #     func_args = node.args["args"]
                #     #     self._make_line("args", func_args)
                #     #     func_kwargs = node.args["kwargs"]
                #     #     for k, v in func_kwargs.items():
                #     #         self._make_line(k, v)
                for child in node.children:
                    self._print_node(child, min_timestamp)
        return records()

    def _print_node(self, node: TraceNode, min_timestamp: float = 0.0) -> Any:
        if node.type == "func":
            return self._print_func(node, min_timestamp)
        else:
            return self._print_gen(node, min_timestamp)

    def _toggle_attrs(self, name: str, expanded: bool = False) -> Dict:
        return {
            "data-bs-toggle": "collapse",
            "href": f"#{name}",
            "role": "button",
            "aria-controls": name,
            "aria-expanded": "true" if expanded else "false",
        }

    def _make_line(self, k: str, v: Any) -> str:
        return f"<tr><th>{k}</th><td>{v}</td></tr>"


class TraceLunaryPrinter(TracePrinterBase):
    """The printer used to log the trace to lunary."""

    def print(
        self, trace: TraceEngineBase, meta_data: Optional[Configs] = None
    ) -> None:
        """Log the trace to lunary."""
        import lunary

        project_id = os.environ.get(
            "LUNARY_PUBLIC_KEY", "1c1975c5-13b9-4977-8003-89fff5c71c27"
        )
        url = os.environ.get("LUNARY_API_URL", "http://localhost:3333")
        logger.info(f"project_id: {project_id}, api url: {url}")
        lunary.config(app_id=project_id, api_url=url)

        suffix = f"_{uuid.uuid4().hex}"
        logger.info(f"suffix: {suffix}")

        def get_parent_run_id(node: TraceNode) -> Optional[str]:
            if node.parent is None:
                return None
            return node.parent.name + suffix

        """Log the trace to lunary."""
        for node in trace.trace_nodes.values():
            if node.type == "func":
                logger.info(
                    f"sending func event {node.name} to lunary with parent {get_parent_run_id(node)}"
                )
                lunary.track_event(
                    "chain",
                    "start",
                    run_id=node.name + suffix,
                    name=node.name,
                    parent_run_id=get_parent_run_id(node),
                    input=node.args,
                    timestamp=timestamp_to_iso(node.start_time),
                )
                lunary.track_event(
                    "chain",
                    "end",
                    run_id=node.name + suffix,
                    output=node.ret,
                    timestamp=timestamp_to_iso(node.end_time),
                )

            elif node.type == "gen":
                logger.info(
                    f"sending llm event {node.name} to lunary with parent {get_parent_run_id(node)}"
                )

                # skip the raw generation, support for legacy traces
                # if node.name.endswith("_raw"):
                #     continue
                metadata = copy.deepcopy(node.args or {})
                model_name = metadata.pop("model", node.name)
                messages = metadata.pop("messages", "")
                metadata["gen_ID"] = node.name
                lunary.track_event(
                    "llm",
                    "start",
                    run_id=node.name + suffix,
                    name=model_name,
                    parent_run_id=get_parent_run_id(node),
                    metadata=metadata,
                    input=messages,
                    timestamp=timestamp_to_iso(node.start_time),
                )
                lunary.track_event(
                    "llm",
                    "end",
                    run_id=node.name + suffix,
                    output={"role": "assistant", "content": node.ret},
                    timestamp=timestamp_to_iso(node.end_time),
                )
            elif node.type == "raw_llm":
                logger.info(
                    f"sending raw llm event {node.name} to lunary with parent {get_parent_run_id(node)}"
                )
                metadata = copy.deepcopy(node.args or {})
                model_name = metadata.pop("model", node.name)
                messages = metadata.pop("messages", "")
                lunary.track_event(
                    "llm",
                    "start",
                    run_id=node.name + suffix,
                    name=model_name,
                    parent_run_id=get_parent_run_id(node),
                    metadata=metadata,
                    input=messages,
                    timestamp=timestamp_to_iso(node.start_time),
                )
                response: ModelResponse = node.ret  # complete response
                lunary.track_event(
                    "llm",
                    "end",
                    run_id=node.name + suffix,
                    output={
                        "role": "assistant",
                        "content": response.choices[0].message.content,  # type: ignore
                        # TODO: support tool calls
                    },
                    timestamp=timestamp_to_iso(node.end_time),
                )


class TraceYAMLPrinter(TracePrinterBase):
    """The printer used to print the trace in the format of YAML."""

    def print(
        self, trace: TraceEngineBase, meta_data: Optional[Configs] = None
    ) -> None:
        """Print the trace in the format of YAML."""
        # TODO: implement the YAML printer
        pass


class TraceProfilePrinter(TracePrinterBase):
    """The printer used to print the trace in the format of profile."""

    def __init__(self, display_functions: bool = False):
        """Initialize the printer.

        Args:
            display_functions: Whether to display the function calls.
        """
        self._display_functions = display_functions

    def build_event(self, event: TraceEventBase, min_timestamp: float) -> Dict:
        """Build the event for the trace."""
        ts = str((event.time_stamp - min_timestamp) * 1e6)
        data = {"pid": 0, "tid": 0, "name": event.name, "ts": ts}
        # TODO: add args to the trace
        if isinstance(event, CompletionRequestEvent):
            data["cat"] = "gen"
            data["ph"] = "b"
            data["id"] = event.name
        elif isinstance(event, CompletionResponseEvent):
            data["cat"] = "gen"
            data["ph"] = "e"
            data["id"] = event.name
            data["cost"] = event.cost
            data["output"] = event.ret.dict()
        elif self._display_functions:
            if isinstance(event, FunctionCallEvent):
                data["cat"] = "func"
                data["ph"] = "B"
                data["tid"] = "main"
            elif isinstance(event, FunctionReturnEvent):
                data["cat"] = "func"
                data["ph"] = "E"
                data["tid"] = "main"
        return data

    def print(
        self, trace: TraceEngineBase, meta_data: Optional[Configs] = None
    ) -> Dict:
        """Print the trace in the format of Chrome tracing."""
        events = []
        for event in trace.events:
            if data := self.build_event(event, trace.min_timestamp):
                events.append(data)
        return {"traceEvents": events}

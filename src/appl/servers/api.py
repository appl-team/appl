import asyncio
import time
from functools import wraps
from importlib.metadata import version

import litellm
import yaml
from litellm import (
    CustomStreamWrapper,
    ModelResponse,
    completion_cost,
    stream_chunk_builder,
)
from litellm.exceptions import NotFoundError
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from ..core.config import configs
from ..core.message import Conversation
from ..core.response import CompletionResponse
from ..core.server import BaseServer, GenArgs
from ..core.tool import ToolCall
from ..core.trace import (
    CompletionRequestEvent,
    CompletionResponseEvent,
    add_to_trace,
    find_in_cache,
)
from ..core.types import *
from ..utils import _langsmith_traceable
from ..version import __version__

try:
    # instructor<0.5.0
    from instructor.patch import wrap_chatcompletion  # type: ignore

    def patch(create: Callable, mode: Mode) -> Callable:
        """Patch the `create` method.

        Enables the following features:
        - `response_model` parameter to parse the response from OpenAI's API
        - `max_retries` parameter to retry the function if the response is not valid
        - `validation_context` parameter to validate the response using the pydantic model
        - `strict` parameter to use strict json parsing
        """
        return wrap_chatcompletion(create, mode)

except ImportError:
    from instructor.patch import patch  # type: ignore

try:
    from instructor.mode import Mode
except ImportError:
    # old version of instructor
    from instructor.patch import Mode  # type: ignore

if configs.getattrs("settings.misc.suppress_litellm_debug_info"):
    litellm.suppress_debug_info = True


# wrap the completion function # TODO: wrap the acompletion function?
@wraps(litellm.completion)
def chat_completion(**kwargs: Any) -> CompletionResponse:
    """Wrap the litellm.completion function to add tracing and logging."""
    if "gen_id" not in kwargs:
        raise ValueError("gen_id is required for tracing completion generation.")
    gen_id = kwargs.pop("gen_id")
    raw_response_holder = []
    if "_raw_response_holder" in kwargs:
        raw_response_holder = kwargs.pop("_raw_response_holder")
    add_to_trace(CompletionRequestEvent(name=gen_id))

    log_llm_call_args = configs.getattrs("settings.logging.display.llm_raw_call_args")
    log_llm_response = configs.getattrs("settings.logging.display.llm_raw_response")
    log_llm_usage = configs.getattrs("settings.logging.display.llm_raw_usage")
    log_llm_cache = configs.getattrs("settings.logging.display.llm_cache")
    if log_llm_call_args:
        logger.info(f"Call completion [{gen_id}] with args: {kwargs}")

    @_langsmith_traceable(
        name=f"ChatCompletion_{gen_id}",
        run_type="llm",
        metadata={"appl": "completion", "appl_version": __version__},
    )  # type: ignore
    def wrapped(**inner_kwargs: Any) -> Tuple[Any, bool]:
        if cache_ret := find_in_cache(gen_id, inner_kwargs):
            if log_llm_cache:
                logger.info("Found in cache, using cached response...")
            if inner_kwargs.get("stream", False):
                raise ValueError("Not support stream using cache yet.")
                # TODO: support rebuild the stream from cached response
            raw_response = cache_ret
        else:
            if log_llm_cache:
                logger.info("Not found in cache, creating response...")
            raw_response = litellm.completion(**inner_kwargs)
        return raw_response, cache_ret is not None

    try:
        raw_response, use_cache = wrapped(**kwargs)
    except Exception as e:
        # log the error information for debugging
        logger.error(f"Error encountered for the completion: {e}")
        logger.info(f"kwargs:\n{kwargs}")
        raise e

    if raw_response_holder is not None:
        raw_response_holder.append(raw_response)

    def post_completion(response: CompletionResponse) -> None:
        raw_response = response.complete_response
        cost = 0.0 if use_cache else response.cost
        response.cost = cost  # update the cost
        event = CompletionResponseEvent(
            name=gen_id, args=kwargs, ret=raw_response, cost=cost
        )
        add_to_trace(event)
        if log_llm_response:
            logger.info(f"Completion [{gen_id}] response: {response}")
        if log_llm_usage and response.usage is not None:
            logger.info(f"Completion [{gen_id}] usage: {response.usage}")

    return CompletionResponse(
        raw_response=raw_response, post_finish_callbacks=[post_completion]
    )  # type: ignore


# TODO: add default batch_size, to avoid too many requests
class APIServer(BaseServer):
    """The server for API models. It is a wrapper of litellm.completion."""

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        custom_llm_provider: Optional[str] = None,
        wrap_mode: Optional[Mode] = Mode.JSON,
        cost_currency: str = "USD",
        **kwargs: Any,
    ) -> None:
        """Initialize the API server.

        See [LiteLLM](https://docs.litellm.ai/docs/providers)
        for available models and providers.
        See [completion](https://docs.litellm.ai/docs/completion/input#input-params-1)
        for available options.
        """
        super().__init__()
        self._wrap_mode = wrap_mode
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._custom_llm_provider = custom_llm_provider
        if custom_llm_provider is not None and api_key is None:
            self._api_key = "NotRequired"  # bypass the api_key check of litellm
        self._cost_currency = cost_currency
        self._default_args = kwargs

    @property
    def model_name(self):
        """The model name."""
        return self._model

    def _get_create_args(self, args: GenArgs, **kwargs: Any) -> dict:
        # supports custom postprocess create_args
        create_args = self._default_args.copy()
        postprocess = kwargs.pop("postprocess_args", None)
        if self._base_url is not None:
            create_args["base_url"] = self._base_url
        if self._api_key is not None:
            create_args["api_key"] = self._api_key
        if self._custom_llm_provider:
            create_args["custom_llm_provider"] = self._custom_llm_provider
        create_args.update(kwargs)  # update create_args with other kwargs

        # add args to create_args
        create_args.update(args.preprocess(self._convert, is_openai=True))
        if postprocess is not None:
            create_args = postprocess(create_args)

        return create_args

    def _create(self, **kwargs: Any) -> CompletionResponse:
        response: CompletionResponse = None  # type: ignore
        # to store raw response when patched completion meets error
        kwargs["_raw_response_holder"] = []

        response_model = kwargs.get("response_model", None)
        response_format = kwargs.get("response_format", None)
        if self._wrap_mode is not None and response_model is not None:

            def wrapper(**inner_kwargs: Any) -> CompletionResponse:
                nonlocal response
                response = chat_completion(**inner_kwargs)
                return response

            try:
                # Use instructor.patch to enable using a pydantic model as response model
                # added arguments: response_model, validation_context, max_retries
                patched = patch(create=wrapper, mode=self._wrap_mode)
                results = patched(**kwargs)
                # fill in the response_model and response_obj
                response.response_model = response_model
                response.set_response_obj(results)
                # TODO?: update the cost for multiple retries
                # instructor has updated the total usage for retries
                # ?? response.cost = completion_cost({"usage": response.usage})
            except Exception as e:
                # log the error information for debugging
                logger.error(f"Error encountered for the patched completion: {e}")
                _raw_response_holder = kwargs.pop("_raw_response_holder", [])
                logger.info(f"kwargs:\n{yaml.dump(kwargs)}")
                if _raw_response_holder:
                    logger.info(f"raw_response:\n{_raw_response_holder[0]}")
                raise e
        else:
            wrapped_attribute = kwargs.pop("_wrapped_attribute", None)
            response = chat_completion(**kwargs)
            if isinstance(response_format, type) and issubclass(
                response_format, BaseModel
            ):
                response.response_model = response_format
                assert (
                    response.response_obj is None
                ), "response_obj should not be set yet."
                # retrieve the response message and convert it to the response model
                # fetching the results will stream the response if it is a streaming
                response_obj = response_format.model_validate_json(response.results)
                if wrapped_attribute:
                    assert hasattr(
                        response_obj, wrapped_attribute
                    ), f"should have attribute {wrapped_attribute} in the response"
                    response_obj = getattr(response_obj, wrapped_attribute)
                response.set_response_obj(response_obj)
        return response

    def _convert(self, conversation: Conversation) -> List[Dict[str, str]]:
        return conversation.as_list()

    def close(self):
        """Close the server."""
        pass

"""Import types from dependencies"""

from litellm.types.utils import Delta, Function, ModelResponse
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import (
    ChoiceDelta,
    ChoiceDeltaToolCallFunction,
)

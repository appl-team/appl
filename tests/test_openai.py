"""Testing openai API calls

NOTE: The tests could cost money if you have an openai key set.
NOTE: Some tests might fail due to randomness in the API.
You can skip these tests by setting the environment variable SKIP_MODEL_CALL_TESTS=1
"""

import os
import sys

import pytest
from loguru import logger

import appl
from appl import AIRole, Generation, Image, UserRole, as_tool, gen, ppl
from appl.const import NEWLINE

appl.init()
# NOTE: init here could influence other tests in other files.


@ppl
def add():
    "1+2="
    return str(gen(max_tokens=10)).strip()


try:
    add()
    reason = None
    openai_api_callable = True
except Exception as e:
    reason = str(e)
    openai_api_callable = False

skip_tests = os.environ.get("SKIP_LLM_CALL_TESTS") == "1"
pytestmark = [
    pytest.mark.skipif(skip_tests, reason="Skipped due to setting"),
    pytest.mark.skipif(
        not openai_api_callable,
        reason=f"Error encountered when calling openai API: {reason}",
    ),
]


# @pytest.mark.skipif(skip_tests, reason="Skipped due to setting")
def test_openai():
    assert "3" in add()


def test_tool_call():
    def special_number(x: int) -> int:
        """A function to calculate the special number of an integer."""
        return x**2 + 1

    tools = [as_tool(special_number)]

    @ppl
    def func(x: int):
        f"What's the special number of {x}?"
        res = gen(tools=tools)
        return [x.get_content() for x in res.run_tool_calls()]

    assert func(5) == [special_number(5)]


IMAGE_URL = "https://maproom.wpenginepowered.com/wp-content/uploads/OpenAI_Logo.svg_-500x123.png"


def test_image():
    @ppl
    def query():
        "Look, it's a commercial logo."
        Image(IMAGE_URL)
        "What's the text on the image? "
        "Your output should be in the format: The text on the image is: ..."
        return gen("gpt4-turbo", stop=NEWLINE)

    assert "OpenAI" in str(query())

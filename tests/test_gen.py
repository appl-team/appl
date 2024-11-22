from typing import List

import pytest

import appl
from appl import (
    AIRole,
    CompletionResponse,
    PromptRecords,
    SystemMessage,
    gen,
    ppl,
    records,
)


def test_gen():
    appl.init()

    @ppl
    def func():
        "Hello"
        return gen("_dummy", mock_response="World")

    assert str(func()) == "World"

    @ppl
    def dummy():
        "Hello"
        return gen("_dummy")

    assert "dummy" in str(dummy())


def test_chat_gen():
    appl.init()
    name = "Test"
    p: List[PromptRecords] = []

    @ppl(auto_prime=True)
    def chat_gen():
        SystemMessage(f"Your name is {name}")
        reply = None
        while True:
            yield reply
            with AIRole():
                (reply := gen("_dummy", mock_response="World"))
            p.append(records())

    chat = chat_gen()
    assert str(chat.send("Hello")) == "World"
    print(p[0].as_convo().as_list())
    assert p[0].as_convo().as_list() == [
        {"role": "system", "content": "Your name is Test"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "World"},
    ]
    assert str(chat.send("Hello again")) == "World"
    assert p[1].as_convo().as_list() == [
        {"role": "system", "content": "Your name is Test"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "World"},
        {"role": "user", "content": "Hello again"},
        {"role": "assistant", "content": "World"},
    ]


def test_gen_error():
    with pytest.raises(ValueError) as excinfo:
        gen(mock_response="World")

    error_msg = str(excinfo.value)
    assert "PromptContext" in error_msg or "appl.init" in error_msg

import appl
from appl import ppl, records
from appl.func import gen

appl.init()


@ppl
def func(stream=True):
    # adopted from https://cookbook.openai.com/examples/how_to_stream_completions
    "Count to 100, with a comma between each number and no newlines. E.g., 1, 2, 3, ..."
    return gen(stream=stream)


content = func(stream=False)
print(f"Content: {content}")

content = func(stream=True)
print(f"Content: {content}")

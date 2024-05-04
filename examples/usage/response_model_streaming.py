# https://jxnl.github.io/instructor/why/?h=iterable#partial-extraction
from typing import List

from instructor import OpenAISchema, Partial
from rich.console import Console

import appl
from appl import Generation, gen, ppl

appl.init()


class User(OpenAISchema):
    name: str
    age: int
    email: str


class Info(OpenAISchema):
    users: List[User]


@ppl
def extract_info() -> Generation:
    f"randomly generate 5 users."
    return gen(response_model=Partial[Info], stream=True).response_obj


console = Console()

for extraction in extract_info():
    obj = extraction.model_dump()
    console.clear()
    console.print(obj)

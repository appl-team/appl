# https://jxnl.github.io/instructor/why/?h=iterable#partial-extraction
from typing import List

from pydantic import BaseModel
from rich.console import Console

import appl
from appl import Generation, gen, ppl
from instructor import Partial

appl.init()


class User(BaseModel):
    name: str
    age: int


class Info(BaseModel):
    users: List[User]


@ppl
def extract_info() -> Generation:
    f"randomly generate 3 users."
    return gen(response_model=Partial[Info], stream=True).response_obj


console = Console()

for extraction in extract_info():
    obj = extraction.model_dump()
    console.clear()
    console.print(obj)

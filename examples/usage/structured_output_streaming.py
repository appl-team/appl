# https://jxnl.github.io/instructor/why/?h=iterable#partial-extraction
from typing import List

import appl
from appl import Generation, gen, ppl
from appl.core import make_panel
from instructor import Partial
from pydantic import BaseModel
from rich.live import Live

appl.init()


class User(BaseModel):
    name: str
    age: int


class Info(BaseModel):
    users: List[User]


@ppl
def generate_info() -> Info:
    f"randomly generate 3 users."
    return gen(response_format=Info, stream=True).response_obj


print(f"Generated Info: {generate_info()}")
# streaming is displayed but not return a generator object


@ppl
def generate_info_instructor():
    f"randomly generate 3 users."
    return gen(response_model=Partial[Info], stream=True).response_obj


with Live(make_panel("Waiting for Response ..."), auto_refresh=0.5) as live:
    for response in generate_info_instructor():
        # returned object is a generator containing partial response
        obj = response.model_dump_json(indent=2)
        live.update(make_panel(str(obj), language="json"))

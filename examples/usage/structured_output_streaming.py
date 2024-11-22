# https://jxnl.github.io/instructor/why/?h=iterable#partial-extraction
from typing import List

from instructor import Partial
from pydantic import BaseModel

import appl
from appl import gen, ppl
from appl.core import get_live, make_panel

appl.init()


class User(BaseModel):
    name: str
    age: int


class Info(BaseModel):
    users: List[User]


@ppl
def generate_info() -> Info:
    f"randomly generate 10 users."
    return gen(response_format=Info, stream=True).response_obj


print(f"Generated Info: {generate_info()}")
# streaming is displayed but not return a generator object


@ppl
def generate_info_instructor():
    f"randomly generate 10 users."
    return gen(response_model=Partial[Info], stream=True).response_obj


print("Generated Info:", generate_info_instructor())
# streaming is displayed but not return a generator object

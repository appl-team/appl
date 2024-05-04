from typing import List

from instructor import OpenAISchema, Partial
from rich.console import Console

import appl
from appl import gen, ppl

appl.init()


class GCDAndLCM(OpenAISchema):
    gcd: int
    lcm: int


@ppl
def gcd_lcm(a, b):
    f"Return the greatest common divisor and the least common multiple of {a} and {b}"
    return gen(response_model=GCDAndLCM)


print(gcd_lcm(24, 32))

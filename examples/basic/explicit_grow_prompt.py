import appl
from appl import gen, grow, ppl

appl.init()


@ppl
def count(word: str, char: str):
    grow(f"How many {char}s are there in {word}?")
    return gen()


print(count("hello", "l"))

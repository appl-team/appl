import appl
from appl import convo, gen, grow, ppl

appl.init()


@ppl
def count(word: str, char: str):
    grow(f"How many {char}s are there in {word}?")
    return gen(messages=convo())


print(count("hello", "l"))
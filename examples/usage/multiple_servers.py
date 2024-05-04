import appl
from appl import ppl
from appl.func import gen

appl.init()


@ppl
def add1(a, b):
    f"what's {a} plus {b}?"
    return gen("azure-gpt35")
    # The default server is "gpt35-turbo", if not specified


@ppl
def add2(a, b):
    f"what's {a} plus {b}?"
    return gen("gpt4-turbo")


@ppl
def add3(a, b):
    f"what's {a} plus {b}?"
    return gen("moonshot-8k")


@ppl
def add4(a, b):
    f"what's {a} plus {b}?"
    return gen("srt-llama2")


# print(add1("one", "two"))
# print(add2("three", "four"))
# print(add3("five", "six"))
# print(add4("seven", "eight"))

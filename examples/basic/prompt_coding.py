import appl
from appl import BracketedDefinition as Def
from appl import define, empty_line, ppl, records
from appl.compositor import *


# declare the input and output requirements classes for reference
class InputReq(Def):
    name = "Input Requirement"


class OutputReq(Def):
    name = "Output Requirement"


# Alternatively, but not recommended, you can define classes as follows:
# InputReq = define("Input Requirement")
# OutputReq = define("Output Requirement")


@ppl
def requirements(opr: str):
    "Requirements"
    with NumberedList():
        # complete the input requirement
        InputReq(desc="The input should be two numbers.")
        # complete the output requirement
        OutputReq(desc=f"The output should be the {opr} of the two numbers.")
    return records()


@ppl
def instruction(language: str):
    "Instruction"
    with LineSeparated():
        # The naming can be used to distinguish:
        # variable naming (e.g. language): the dynamic input
        # class naming (e.g. InputReq): the reference to the concept
        f"Write a function in {language} that satisfies the {InputReq} and {OutputReq}."
    return records()


@ppl
def get_prompt(opr: str, language: str):
    with LineSeparated(indexing="##"):
        requirements(opr)  # the returned prompt will be formatted using the compositor
        empty_line()  # create an empty line regardless of other compositor
        instruction(language)
    return records()


print("=== First prompt ===")
print(get_prompt("sum", "Python"))
print("")
print("=== Second prompt ===")
print(get_prompt("product", "C++"))

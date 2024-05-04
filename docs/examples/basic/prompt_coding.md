---
hide:
  - toc
---


# Prompt Coding Helpers

We provide two types of helpers, `Compositor` and `Definition`, to facilitate coding prompts in a modularized and maintainable way. These helpers were originally designed in [PromptCoder](https://github.com/dhh1995/PromptCoder) and have been used to develop prompts in the [ToolEmu](https://github.com/ryoungj/ToolEmu) project with more than 20k tokens in total. By leveraging Python's idiomatic features, we have enhanced the usability and flexibility of these helpers.

The `Compositor` organizes the prompts within its context into a structured prompt. For example, the `NumberedList` would compose a list of text into a numbered list:
```python
with NumberedList():
    f"First item"
    f"Second item"
>>> composed into >>>
1. First item
2. Second item
```
You can also nest the compositors to create more complex structures.

The `Definition` class provides a standardized way to define concepts and refer to them in the prompts. Once a concept is defined by subclassing `Definition`, you can refer to it in the prompts by using the class name. Meanwhile, you need to include the concept's description somewhere in the prompt by instantiating the class with the description as an argument. This design ensures the consistency of the concept's definition and usage in the prompts.

We use the example in [PromptCoder](https://github.com/dhh1995/PromptCoder?tab=readme-ov-file#usage) to illustrate the usage of these helpers:

```python
import appl
from appl import BracketedDefinition as Def
from appl import define, ppl, records
from appl.compositor import *

# declare the input and output requirements classes for reference
class InputReq(Def):
    name = "Input Requirement"

class OutputReq(Def):
    name = "Output Requirement"

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
        with FreshLine():
            f""  # create an empty line regardless of other compositor
        instruction(language)
    return records()
```
The result of `get_prompt("sum", "Python")` will be:
```md
## Requirements
1. Input Requirement: The input should be two numbers.
2. Output Requirement: The output should be the sum of the two numbers.

## Instruction
Write a function in Python that satisfies the [Input Requirement] and [Output Requirement].
```
 
Overall, these helpers provide a more structured and maintainable way to write dynamic prompts.

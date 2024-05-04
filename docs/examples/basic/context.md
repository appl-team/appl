---
hide:
  - toc
---
In this example, we show different ways APPL can handle prompt contexts. The "context" of the prompt refers to the previous tokens to be considered by the LLM during the generation of new tokens. The new tokens would then subsequently be included in the context.

APPL allows for flexible control of prompt contexts. For each of the `@ppl`-annotated APPL function, we can specify one of four ways to handle the context:

1. `new`: Create a completely new context. 
2. `copy`: Create a new context with the caller's current context as the prefix. It will inherit the caller's context but only write to the new copy.
3. `same`: The reference of the caller's context will be passed to the callee. They share the same context and any modifications to the context by the callee will be effective for the caller.
4. `resume`: Resume the function's context from the last time it was called. Detailed in the multi agent chat [example](../advanced/multi_agent_chat.md).


```python linenums="1"
import appl
from appl import convo, gen, ppl, records

appl.init()


@ppl # (1)
def intro():
    f"Today is 2024/02/29."
    return records()


@ppl("inherit_ctx") # (2)
def addon():
    f"Dates should be in the format of YYYY/MM/DD."
    # The newly captured prompt will influence the caller's context


@ppl("copy_ctx")  # (3)
def query(question: str):
    # the prompts here will not influence the caller's context
    f"Q: {question}"
    f"A: "
    # print(convo())  # display the conversation used for the generation
    return gen()


@ppl
def ask_questions(questions: list[str]):
    # long prompt can be decomposed into several smaller `appl functions`

    # method 1 (recommended): build the sub-prompts in an empty context
    intro()  # (4)

    # method 2: use the same context and modify it in the function
    addon()  # (5)

    return [query(q) for q in questions]


questions = [
    "What's the date tomorrow?",
    "What's the date yesterday?",
    "How many dates passed since 2024/02/02?",
]
for res in ask_questions(questions):
    print(res)
```

1. use empty context, equivalent to @ppl("new_ctx") or @ppl("new")
2. inherit the caller's context, equivalent to @ppl("inherit")
3. copy the caller's context, equivalent to @ppl("copy")
4. returns prompt records, will be captured in this context
5. returns None, not captured, but the context is modified inside

In the above example, two lines are provided to the LLM as context:
```
Today is 2024/02/29.
Dates should be in the format of YYYY/MM/DD.
```
However, they're appended to the context differently:

1. The first line is generated through calling `intro()`, which creates a new context and returns the string `Today is 2024/02/09` with `records()`. This is then appended into the main context by mentioning the result on line 33.
2. The second line is generated in `addon()`. Differently from the first, this function inherits the main context, then appends the `Dates should be ...` line after the previous by mutating the context.

The output will resemble the following:
```
2024/03/01
2024/02/28
27 dates have passed since 2024/02/02.
```

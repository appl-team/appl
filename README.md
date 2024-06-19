# 🍎APPL: A Prompt Programming Language

[![python](https://img.shields.io/badge/Python-3.9%2B-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://mit-license.org/)


**APPL** is A Prompt Programming Language that extends Python to provide a Natural, Intuitive, Convenient, and Efficient (NICE) way to utilize Large Language Models (LLMs) such as GPT in your program.

<video style="width: 100%" src="https://github.com/appl-team/appl/assets/12556773/5d75d3db-1b1c-48c9-97ec-e9d72a387e49" type="video/mp4" controls></video>

## Key Features
- **Readability and maintainability via seamless integration with Python.**  APPL seamlessly embeds natural language prompts into Python programs, maintaining prompts' readability while inheriting modularity, reusability, dynamism and the ecosystem from the host programming language.
- **Flexible prompt engineering.**  Except for allowing the utilization of Python control flows and the modularized decomposition of prompts, APPL offers prompt coding helpers to facilitate programming prompts in a modularized and maintainable way.
- **Automatic parallelization via asynchronous computation.**  APPL schedules LLM calls asynchronously, leveraging potential independence among them to facilitate efficient parallelization. This offloads the burden of users to manage synchronization manually, with almost no extra work.
- **Smooth tool calling integration.**  APPL provides intuitive ways to transform Python functions into tools that can be called by LLMs, making it easy for users to integrate existing Python libraries and functions with LLMs.
- **Tracing and Failure Recovery.** APPL traces the execution of LLM calls and supports recovery from failures, which is essential for debugging and error handling in the LLM programming paradigm.
- **More Features.** APPL also provides a unified interface for multiple LLM backends using [`litellm`](https://docs.litellm.ai/docs/), structured generations using [`instructor`](https://python.useinstructor.com/), and many other features.

<!-- TODO: RoadMap -->

## Quick Start

### Installation
You can simply install APPL from PyPI using pip:
```bash
pip install -U applang
```
More installation options can be found in the [installation guide](https://appl-team.github.io/appl/install).

### Setup
You need to set up API keys or your own LLM backends to interact with LLMs.

In this guide, we use OpenAI API as the default backend.
You can set your OpenAI API key in the `.env` file in the root directory of your project:
```
OPENAI_API_KEY=<your openai api key>
```
or export it as an environment variable:
```bash
export OPENAI_API_KEY=<your openai api key>
```

For setting up other backends, enabling tracing and recovering from traces, please refer to the [setup guide](https://appl-team.github.io/appl/setup).

### Hello World

To begin, let's create a simple function that uses LLM to respond to a greeting.

```python
import appl
from appl import gen, ppl

appl.init()  # initialize APPL

@ppl  # the @ppl decorator marks the function as an `APPL function`
def greeting(name: str):
    f"Hello World! My name is {name}."  # Add text to the prompt
    return gen()  # call the default LLM with the current prompt

print(greeting("APPL"))  # call `greeting` as a normal Python function
```

The prompt for the generation is:
```
Hello World! My name is APPL.
```

The output will look like
```
Nice to meet you, APPL!
```

In this example, the `@ppl` decorator (`@` stands for `a` here) marks the `hello_world` function as an *APPL function*. Within such a function, the standalone string `f"Hello World! My name is {name}."` is added to the prompt, and the `gen()` function calls LLM to generate responses using the current prompt.

### Question Answering

Let's then implement a question-answering system using APPL. In this example, the APPL program answers multiple questions about a quotation by first extracting the author's name (inspired by [this cookbook](https://cookbook.openai.com/articles/how_to_work_with_large_language_models)). [Here](https://colab.research.google.com/drive/1khZcleOrdLOWtUB4EMEQCjGA1vBaARI9) is a runnable Colab notebook of this example.

```python linenums="1" hl_lines="9 14 15 17"
import appl
from appl import AIRole, gen, ppl
from appl.const import NEWLINE

appl.init()

@ppl(ctx="copy")  # copy the context from caller
def get_answer(question: str):
    question  # append to the prompt
    return gen()  # return as a future object

@ppl  # marks APPL function
def answer_questions(quotation: str, questions: list[str]):
    "Extract the name of the author from the quotation below and answer questions."
    quotation  # append to the prompt
    with AIRole():  # assistant message
        f"The name of the author is {gen(stop=NEWLINE)}"  # specify the prefix
    return [get_answer(q) for q in questions]  # parallelize calls

quotation = '"Simplicity is the ultimate sophistication." -- Leonardo da Vinci'
questions = [
    "In what era did the author live?",
    # more questions can be added here
]
for ans in answer_questions(quotation, questions):
    print(ans)
```

The resulting conversation for the first question would look like (generated responses are in **bold**):

| Role        | Message                                                                                                                                            |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| *User*      | Extract the name of the author from the quotation below and answer questions.<br>"Simplicity is the ultimate sophistication." -- Leonardo da Vinci |
| *Assistant* | The name of the author is **Leonardo da Vinci.**                                                                                                   |
| *User*      | In what era did the author live?                                                                                                                   |
| *Assistant* | **Leonardo da Vinci lived during the Renaissance era.**                                                                                            |

In *APPL functions*, [expression statements](https://docs.python.org/3/reference/simple_stmts.html#expression-statements) are captured as prompts based on the type of its value. <!-- TODO: link to the language explanation doc-->
Notably, the f-string is processed part by part, so the `gen` function inside the f-string intuitively uses the contents before that. In this example, `The name of the author is ` serves as a prefix to guide the completion of the author's name.

After the author's name is extracted, the `get_answer` function is called multiple times in parallel to answer the questions, with the context being copied (detailed in [context-management](#context-management)), demonstrating the automatic parallelization feature of APPL.

## Usage by Examples
We provide a series of examples to demonstrate the usage of APPL. Some examples in this section are simplified for demonstration purposes. See runnable examples in the [examples](examples/basic) directory.

### Context Management
Each *APPL function* has a **context**, which contains the prompts captured in the function. There are four different ways to pass the context when calling another *APPL function* (the callee) in an *APPL function* (the caller): **new**, **copy**, **same**, and **resume**.

![Context Management](https://raw.githubusercontent.com/appl-team/appl/main/docs/_assets/context.png)

1. **new**: The default behavior, create a new empty context.
2. **copy**: This is similar to *call by value* in programming languages. The callee's context is a copy of the caller's context, therefore the changes in the callee's context won't affect the caller's context.
3. **same**: This is similar to *call by reference* in programming languages. The callee's context is the same as the caller's context, therefore the changes in the callee's context will affect the caller's context.
4. **resume**: This resumes the context of the function each time it is called, i.e., the context is preserved across calls, making the function stateful. It copies the caller's context for the first call as the initial context. It is useful when you want to continue the conversation from the last call.

In the following example, we illustrate the usage of the first three context management methods and ways to decompose long prompts into smaller pieces using *APPL functions*. 

```python
import appl
from appl import convo, gen, ppl, records

appl.init()

@ppl  # use empty context
def intro():
    f"Today is 2024/02/29."
    return records()

@ppl(ctx="same")  # same as the caller's context
def addon():
    f"Dates should be in the format of YYYY/MM/DD."
    # The newly captured prompt will influence the caller's context

@ppl(ctx="copy")  # copy the caller's context
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
    intro()  # returns prompt records, will be captured in this context
    # method 2: use the same context and modify it in the function
    addon()  # returns None, not captured, but the context is modified inside
    return [query(q) for q in questions]
 
questions = [
    "What's the date tomorrow?",
    "What's the date yesterday?",
    "How many dates passed since 2024/02/02?",
]
for res in ask_questions(questions):
    print(res)
```

Three queries are independent and run in parallel, where the prompts and possible responses of the generations are shown below:

<table>
  <tr>
    <th>First query</th>
    <th>Second query</th>
    <th>Third query</th>
  </tr>
  <tr>
    <td colspan="3">
    Today is 2024/02/29.<br>
    Dates should be in the format of YYYY/MM/DD.
    </td>
  </tr>
  <tr>
    <td>Q: What's the date tomorrow?</td>
    <td>Q: What's the date yesterday?</td>
    <td>Q: How many dates passed since 2024/02/02?</td>
  </tr>
  <tr>
    <td>A: <strong>2024/03/01</strong></td>
    <td>A: <strong>2024/02/28</strong></td>
    <td>A: <strong>27 dates have passed since 2024/02/02.</strong></td>
  </tr>
</table>

Note the `records()` function retrieves the prompt records captured in the current function, and the `convo()` function retrieves the full conversation in the context. They are analogous to the `locals()` and `globals()` functions in Python.

### Concurrent Execution

The parallelization of multiple queries in the last example is achieved using [asynchronous computation](https://docs.python.org/3/library/concurrent.futures.html). In APPL, the `gen` function automatically starts a new thread (or process) and does not block the main thread. The generation result is not synchronized (waited) until its value is needed, making the execution of multiple independent LLM calls easily concurrent.

Many prompt engineering techniques like [Self-Consistency (CoT-SC)](https://arxiv.org/abs/2203.11171) and [Tree of Thoughts (ToT)](https://arxiv.org/abs/2305.10601) involve non-sequential LLM calls such as branching and gathering. The following example demonstrates how to use APPL to naturally exploit the independence among the reasoning paths in CoT-SC to parallelize the execution.

```python
def get_mode(answers: list[str]):
    """Get the mode of the answers"""
    return max(set(answers), key=answers.count)

def marginalize(results: list):
    """Get the answer from the results and get the mode of the answers"""
    
    # explicitly syncronize the results using str()
    answers = [parse_answer(str(res)) for res in results]
    # detailed implementation of `parse_answer` are omitted here

    return get_mode(answers)

@ppl
def cot_consistency(cot_examples: list[str], question: str, num_trials: int):
    cot_examples # the list of examples are captured into prompt one-by-one
    question
    results = [gen() for _ in range(num_trials)] # concurrent generation
    return marginalize(results) # marginalize the reasoning paths to get the answer
```

### LLM Tool Calling

![APPL_runtime](https://raw.githubusercontent.com/appl-team/appl/main/docs/_assets/appl_runtime.png)

Integrating tools significantly enhances the capabilities of LLMs. APPL introduces a seamless method to transform Python functions into tools accessible by LLMs (provided the backend LLM supports tool calls). When the `gen` function is provided with Python functions, APPL automatically transforms them into tools by extracting information from the signature and docstring of the functions. Such integration facilitates leveraging existing Python libraries and functions directly within LLMs.

Consider the example below, where we transform a Python function, `is_lucky`, into a callable tool. During execution, `gpt-3.5-turbo` smartly invokes the `is_lucky` tool with the appropriate arguments. Subsequently, the function executes with these arguments and the result is returned.

```python
import sympy

import appl
from appl import Generation, as_tool, gen, ppl, records

appl.init()

def is_lucky(x: int) -> bool:
    """Determine whether the input number is a lucky number.

    Args:
        x (int): The input number to be checked.

    Returns:
        bool: True if the number is a lucky number, False otherwise.
    """
    return sympy.isprime(x + 3)

@ppl
def func(x):
    f"Is {x} a lucky number?"

    # Initiate the generation with tool `unique_number``,
    # which is built into a tool by automatically extracting
    # information from the function signature and docstring.
    # And then store the tool call messages into the prompt
    (actions := gen(tools=[is_lucky]))

    # Execute the tool calls and retrieve the results.
    results = actions.run_tool_calls()  # results is a list of ToolMessage

    # Return the first result from the tool execution.
    return results[0].get_content()
```

### Prompt Coding Helpers

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

Please see the [example](examples/basic) for more details.

## Cookbook
For more detailed usage and examples, please refer to the [cookbook](https://appl-team.github.io/appl/cookbook).

## Citation and Acknowledgment
If you find APPL helpful, please consider citing our paper:
```bibtex
<to be added>
```

We would like to thank the open-source community for their contributions, where we learned from or used these libraries in our project, including
[instructor](https://github.com/jxnl/instructor),
[LiteLLM](https://github.com/BerriAI/litellm),
[LMQL](https://github.com/eth-sri/lmql),
[Guidance](https://github.com/guidance-ai/guidance),
[SGLang](https://github.com/sgl-project/sglang) and
[autogen](https://github.com/microsoft/autogen).

## License
This project is licensed under the terms of the MIT License.

---
hide:
  - toc
---

This example implements Chain-of-Thoughts + Self Consistency:

* **Chain-of-thoughts prompting** enhances the LLM's ability to perform complex reasoning though providing examples of intermediate reasoning steps.
* **Self consistency** samples different reasoning pathes from the LLM then marginalizes to generate a consensus. 

Below is an illustration of this method from the paper "Self-Consistency Improves Chain of Thought Reasoning in Language Models"[^1].

![CoT-SC Example](../../_assets/cot_sc.png){: style="width:600px"}

The implementation below shows an example of determining if a set of numbers add up to an even number ([source](https://www.promptingguide.ai/techniques/cot)).

```python linenums="1"
import time

import appl
from appl import gen, ppl

appl.init()


def parse_answer(answer: str):
    """parse the ANS from: The answer is [ANS]."""
    if (key := "The answer is ") in answer:
        return answer.split(key)[-1].split(".")[0].strip()
    return None


def get_mode(answers: list[str]):
    """Get the mode of the answers"""
    return max(set(answers), key=answers.count)


def marginalize(results: list):
    """Get the answer from the results and get the mode of the answers"""
    # explicitly syncronize the results using str()
    answers = [parse_answer(str(res)) for res in results]

    return get_mode(answers)


@ppl
def cot_consistency(cot_examples: list[str], question: str, num_trials: int):
    cot_examples  # (1)
    question
    results = [gen() for _ in range(num_trials)]  # (2)
    return marginalize(results)  # (3)


@ppl
def cot_consistency_sequential(cot_examples: list[str], question: str, num_trials: int):
    cot_examples  # (4)
    question
    results = [str(gen()) for _ in range(num_trials)]  # (5)
    return marginalize(results)  # (6)


# example from https://www.promptingguide.ai/techniques/cot
cot_examples = [
    (
        "The odd numbers in this group add up to an even number: 4, 8, 9, 15, 12, 2, 1.\n"
        "A: Adding all the odd numbers (9, 15, 1) gives 25. The answer is False."
    ),
    (
        "The odd numbers in this group add up to an even number: 17, 10, 19, 4, 8, 12, 24.\n"
        "A: Adding all the odd numbers (17, 19) gives 36. The answer is True."
    ),
]
question = (
    "The odd numbers in this group add up to an even number: 15, 32, 5, 13, 82, 7, 1."
)

n = 5
start_time = time.time()
print(f"Parallel CoT-SC Answer: {cot_consistency(cot_examples, question, n)}")
print(f"Parallel CoT-SC takes {time.time() - start_time:.2f} seconds")

start_time = time.time()
print(
    f"Sequential CoT-SC Answer: {cot_consistency_sequential(cot_examples, question, n)}"
)
print(f"Sequential CoT-SC takes {time.time() - start_time:.2f} seconds")
```

1. the list of examples are captured into prompt one-by-one 
2. concurrent generation
3. marginalize the reasoning paths to get the answer
4. the list of examples are captured into prompt one-by-one
5. explicit syncronization
6. marginalize the reasoning paths to get the answer

It is noteworthy that APPL's asynchronous execution can greatly speed up text generation. In the `cot_consistency` function we executed the `n` paths in parallel (instead of waiting sequentially for each to finish in `cot_consistency_sequential`). Indeed, we gain a large speedup over sequential execution, as shown in the output below:

```
Parallel CoT-SC Answer: False
Parallel CoT-SC takes 1.74 seconds
Sequential CoT-SC Answer: False
Sequential CoT-SC takes 7.42 seconds
```

[^1]: https://arxiv.org/abs/2203.11171
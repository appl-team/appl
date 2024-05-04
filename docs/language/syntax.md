# Syntax of APPL

## Basic Syntax
APPL syntax consists of using `@ppl` decorators to mark functions as `appl functions` and writing prompts within these functions. Here's an example of basic syntax:

```python
@ppl
def greet(name: str):
    f"Hello, {name}!"
    return records()
```

In the above example, the `@ppl` decorator marks the function `greet` as an `appl function`. 

!!! warning
    When using multiple decorators, make sure to use `@ppl` as the last decorator.


# Using Instructor

[Instrcutor](https://github.com/jxnl/instructor/) is a Python library that makes it a breeze to work with structured outputs from LMs. APPL uses `instructor` to support specifying the structure of the output, with a simple argument `response_model`.

## Get Started

Let's reimplement the example from the [instructor](https://github.com/jxnl/instructor/?tab=readme-ov-file#get-started-in-minutes):

```python linenums="1"
--8<-- "examples/usage/use_instructor.py"
```

## With Streaming

When using streaming, the `response_obj` is a generator that yields partial objects.
Let's slightly modify the [example](https://python.useinstructor.com/why/#partial-extraction) from instructor:

```python linenums="1"
--8<-- "examples/usage/use_instructor_streaming.py"
```

It will gradually print the output:

```python
{
    'users': [
        {'name': 'Alice', 'age': 25},
        {'name': 'Bob', 'age': 30},
        {'name': 'Charlie', 'age': 20}
    ]
}
```
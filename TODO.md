# TODO
- [ ] cookbooks
  - [x] intro/quickstart
  - [ ] usage
  - [ ] advanced
- [ ] examples
  - [ ] rearrange the examples
  - [ ] react
- [x] docs (api docstring)
- [ ] Some clean-up
  - [x] check mypy
- [x] support streaming if base model supports.
  - [x] return iterable
- support string oprs as stringfuture
  - [x] format
  - [x] slice
  - [ ] etc..
- support restrict generation
  - [x] openai backend (instructor)
  - [ ] srt backend (translate to regex, or wait srt to support)
- Unify generation arguments (e.g. temperature, max_token, stops, top_k, top_p)
  - [x] openai and litellm backend
  - [x] srt
  - [x] other models
- [x] test result caching, loading and display
  - [x] improve display
- [ ] support reference variables
  - [x] declearation and definition
    - [ ] supports gen in desc (current can do in an ad-hoc way)
  - [ ] reference to one item by its name or index. E.g. Figure 1.
- [x] support batching with multiple workers
  - [x] to test
- support other models
  - [x] support other apis by litellm (vllm included)
  - [x] support local models
    - [x] srt
    - [ ] langchain
    - [ ] llamacpp

## tutorials
This part of the project documentation focuses on a
**learning-oriented** approach. You'll learn how to
get started with the code in this project.

> **Note:** Expand this section by considering the
> following points:

- Help newcomers with getting started
- Teach readers about your library by making them
    write code
- Inspire confidence through examples that work for
    everyone, repeatably
- Give readers an immediate sense of achievement
- Show concrete examples, no abstractions
- Provide the minimum necessary explanation
- Avoid any distractions

## how-to-guide
This part of the project documentation focuses on a
**problem-oriented** approach. You'll tackle common
tasks that you might have, with the help of the code provided in this project.

## explanation
This part of the project documentation focuses on an
**understanding-oriented** approach.

> **Note:** Expand this section by considering the
> following points:

- Give context and background on your library
- Explain why you created it
- Provide multiple examples and approaches of how
    to work with it
- Help the reader make connections
- Avoid writing instructions or technical descriptions
    here
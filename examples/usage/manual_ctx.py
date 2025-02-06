from typing import Optional

from appl import Generation, PromptContext, convo, gen, need_ctx, ppl, traceable
from appl.compositor import Tagged


# Example 1: manual context management
@traceable  # optional, for tracing
def manual_ctx_func(p: Optional[PromptContext] = None) -> Generation:
    p = p or PromptContext()
    with Tagged("example", _ctx=p):
        p.grow("1+2=3")
    p.grow("2+3=")
    print("===== prompt =====")
    print(p.messages)
    # <example>
    # 1+2=3
    # </example>
    # 2+3=
    return gen(_ctx=p)


print("answer:", manual_ctx_func())


# Example 2: call ppl functions with manual context
# specify the context passing method ("copy" in this example)
@ppl(ctx="copy")
def ppl_func():
    "3+4="
    print("===== prompt =====")
    print(convo())
    # <example>
    # 1+2=3
    # </example>
    # 3+4=
    return gen()


p = PromptContext().grow("<example>").grow("1+2=3").grow("</example>")
print("answer:", ppl_func(_ctx=p))


# Example 3: call manual context functions with ppl functions
# To call functions written in automatic context (with @ppl), you can pass the context manually:
@need_ctx
@traceable
def manual_func_with_ctx(_ctx: Optional[PromptContext] = None):
    _ctx = _ctx or PromptContext()
    _ctx.grow("4+5=")
    print("===== prompt =====")
    print(_ctx.messages)
    # <example>
    # 1+2=3
    # </example>
    # 4+5=
    return gen(_ctx=_ctx)


@ppl
def another_ppl_func():
    with Tagged("example"):
        "1+2=3"
    return manual_func_with_ctx()


print("answer:", another_ppl_func())

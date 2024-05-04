from typing import Optional

import appl
from appl import AIRole, PromptContext, SystemMessage, gen, ppl, records

appl.init()


class Agent(object):
    def __init__(self, name: Optional[str] = None):
        self._name = name
        self._setup()

    @ppl
    def _setup(self):
        if self._name:
            SystemMessage(f"Your name is {self._name}.")
        self.chat(None)  # setup the context

    @ppl(ctx="resume")  # The context is resumed from the last call to chat
    def chat(self, msg: Optional[str]):
        if msg is None:  # first call to setup the context
            return
        msg  # add to the prompt
        with AIRole():
            (reply := gen(max_tokens=50))  # generate reply and add to the prompt
        return reply


alice = Agent("Alice")
bob = Agent("Bob")
msg = "Hello"
for i in range(2):
    msg = str(alice.chat(msg))
    print("Alice:", msg)
    msg = str(bob.chat(msg))
    print("Bob:", msg)

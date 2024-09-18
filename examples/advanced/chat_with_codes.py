# Usage: python examples/advanced/chat_with_codes.py

import glob
import os

import seedir as sd

import appl
from appl import AIRole, gen, ppl, records
from appl.core import load_file

appl.init()


@ppl
def chat(intro: str, source: str, ext: str = ".py"):
    f"===== README ====="
    intro
    f"===== directory structure ====="
    f"The source code is organized as follows:"
    sd.seedir(source, style="spaces", printout=False, exclude_folders=["__pycache__"])
    f"===== source ====="
    f"The contents of the source code are as follows:"
    for name in glob.glob(os.path.join(source, "**", f"*{ext}"), recursive=True):
        f"===== {name} ====="
        with open(name, "r", encoding="utf-8") as f:
            f.read()  # load the file contents and put in the prompt
    f"===== chat ====="
    f"Now begin the chat about the project:"
    f""
    while True:
        print("User:")
        (query := input())
        if query.startswith("exit"):
            break
        print("Assistant:")
        with AIRole():
            str(gen(stream=True))


if __name__ == "__main__":
    readme = load_file("README.md", open_kwargs=dict(encoding="utf-8"))
    chat(readme, "./src/appl", ".py")

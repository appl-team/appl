# Usage: python examples/advanced/chat_with_codes.py

import glob
import os
from argparse import ArgumentParser

import appl
import seedir as sd
from appl import AIRole, gen, ppl, records
from appl.const import EMPTY
from appl.core import load_file, make_panel
from prompt_toolkit.shortcuts import prompt
from rich.console import Console

parser = ArgumentParser()
parser.add_argument("--intro-file", type=str, default="./README.md")
parser.add_argument("--source", type=str, default="./src/appl")
parser.add_argument("--ext", type=str, default=".py")

args = parser.parse_args()

appl.init()


@ppl
def chat(intro: str, source: str, ext: str = ".py"):
    "===== Introduction ====="
    intro
    "===== directory structure ====="
    "The source code is organized as follows:"
    sd.seedir(source, style="spaces", printout=False, exclude_folders=["__pycache__"])
    "===== source ====="
    "The contents of the source code are as follows:"
    for name in glob.glob(os.path.join(source, "**", f"*{ext}"), recursive=True):
        f"===== {name} ====="
        with open(name, "r", encoding="utf-8") as f:
            f.read()  # load the file contents and put in the prompt
    "===== chat ====="
    "Now begin the chat about the project:"
    EMPTY
    console = Console()
    while True:
        (query := prompt("User: "))
        if query.startswith("exit"):
            break
        console.print(make_panel(query, title="User"))
        with AIRole():
            str(gen(stream=True).streaming(title="Assistant"))


if __name__ == "__main__":
    with open(args.intro_file, "r", encoding="utf-8") as f:
        intro = f.read()
    chat(intro, args.source, args.ext)

import glob

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
    for f in glob.glob(source + f"/*{ext}"):
        f"===== {f} ====="
        with open(f, "r") as file:
            file.read()  # put in the prompt
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
    readme = load_file("README.md")
    chat(readme, "./appl", ".py")

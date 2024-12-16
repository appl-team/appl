from loguru import logger

import appl
from appl import gen, ppl

# option 1: update part of the configs in a dict
# appl.init(servers={"default": "gpt-4o"})

# option 2: get options from command line
parser = appl.get_parser()
parser.add_argument("--name", type=str, default="APPL")
args = parser.parse_args()
appl.update_appl_configs(args.appl)
# python cmd_args.py --appl.servers.default gpt-4o


@ppl  # the @ppl decorator marks the function as an `APPL function`
def greeting(name: str):
    f"Hello World! My name is {name}."  # Add text to the prompt
    return gen()  # call the default LLM with the current prompt


print(greeting(args.name))  # call `hello_world` as a normal Python function

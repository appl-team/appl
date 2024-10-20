import os
import shutil

from rich.panel import Panel
from rich.style import StyleType
from rich.syntax import Syntax

from .config import configs
from .types import *


def make_panel(
    content: str,
    *,
    title: Optional[str] = None,
    style: StyleType = "none",
    language: Optional[str] = None,
    truncate: bool = False,
) -> Panel:
    """Display a panel in the terminal with the given title and content."""
    if truncate:
        terminal_height = shutil.get_terminal_size().lines
        content = os.linesep.join(content.splitlines()[-terminal_height + 2 :])

    rich_configs = configs.getattrs("settings.logging.display.rich")
    if language is None:
        language = rich_configs.get("language", "markdown")
    theme = rich_configs.get("theme", "monokai")
    line_numbers = rich_configs.get("line_numbers", False)
    word_wrap = rich_configs.get("word_wrap", True)

    syntax = Syntax(
        content, language, theme=theme, line_numbers=line_numbers, word_wrap=word_wrap
    )
    return Panel(syntax, title=title, style=style)

"""appl - A Prompt Programming Language."""

from __future__ import annotations

import datetime
import inspect
import os
import sys
from importlib.metadata import version

import pendulum
import toml
import yaml
from dotenv import load_dotenv
from loguru import logger

logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")  # set to INFO
try:
    __version__ = version("applang")
except Exception:
    __version__ = "unknown"

from typing import Callable, Optional

from .compositor import ApplStr as Str
from .compositor import iter
from .core import (
    BracketedDefinition,
    CallFuture,
    CompletionResponse,
    Definition,
    Generation,
    Image,
    Indexing,
    Promptable,
    PromptContext,
    PromptPrinter,
    PromptRecords,
    StringFuture,
    Tool,
)
from .core import appl_compile as compile
from .core import appl_execute as execute
from .core import appl_format as format
from .core import appl_with_ctx as with_ctx
from .core.config import Configs, configs, load_config
from .core.globals import global_vars
from .core.io import dump_file, load_file
from .core.message import (
    AIMessage,
    Conversation,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from .core.promptable import define, define_bracketed, promptify
from .func import (
    as_func,
    as_tool,
    as_tool_choice,
    call,
    convo,
    empty_line,
    gen,
    need_ctx,
    openai_tool_schema,
    partial,
    ppl,
    records,
    reset_context,
    str_future,
)
from .role_changer import AIRole, SystemRole, ToolRole, UserRole
from .servers import server_manager
from .tracing import TraceEngine
from .utils import (
    LoguruFormatter,
    find_dotenv,
    find_files,
    get_folder,
    get_meta_file,
    timeit,
)


def _get_loguru_format():
    return LoguruFormatter(
        max_length=configs.getattrs("settings.logging.max_length"),
        suffix_length=configs.getattrs("settings.logging.suffix_length"),
    ).loguru_format


logger.remove()  # Remove default handler
# update default handler for the loguru logger
logger.add(sys.stderr, level="INFO", format=_get_loguru_format())  # default
global_vars.initialized = False


def init(
    resume_cache: Optional[str] = None,
    update_config_hook: Optional[Callable] = None,
) -> None:
    """Initialize APPL with dotenv and config files.

    Args:
        resume_cache: Path to the trace file used as resume cache. Defaults to None.
        update_config_hook: A hook to update the configs. Defaults to None.
    """
    with global_vars.lock:
        # only initialize once
        if global_vars.initialized:
            logger.warning("APPL has already been initialized, ignore")
            return
        global_vars.initialized = True

    now = pendulum.instance(datetime.datetime.now())
    # Get the previous frame in the stack, i.e., the one calling this function
    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller_path = frame.f_back.f_code.co_filename  # Get file_path of the caller
        caller_funcname = frame.f_back.f_code.co_name  # Get function name of the caller
        caller_basename = os.path.basename(caller_path).split(".")[0]
        caller_folder = os.path.dirname(caller_path)  # Get folder of the caller
        caller_folder = get_folder(caller_folder)
        dotenvs = find_files(caller_folder, [".env"])
        appl_config_files = find_files(
            caller_folder, ["appl.yaml", "appl.yml", "appl.json", "appl.toml"]
        )
        # load dotenvs and appl configs from outer to inner with override
        for dotenv in dotenvs[::-1]:
            load_dotenv(dotenv, override=True)
            logger.info("Loaded dotenv from {}".format(dotenv))
        for config_file in appl_config_files[::-1]:
            override_configs = load_config(config_file)
            logger.info("Loaded configs from {}".format(config_file))
            configs.update(override_configs)
            if configs.getattrs("settings.logging.display.configs_update"):
                logger.info(f"update configs:\n{yaml.dump(override_configs.to_dict())}")
    else:
        caller_basename, caller_funcname = "appl", "<module>"
        dotenvs, appl_config_files = [], []
        logger.error(
            "Cannot find the caller of appl.init(), fail to load .env and appl configs"
        )

    if update_config_hook:
        update_config_hook(configs)
    log_format = configs.getattrs("settings.logging.format")
    log_level = configs.getattrs("settings.logging.log_level")
    log_file = configs.getattrs("settings.logging.log_file")
    # set logger level for loguru
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=log_level, format=_get_loguru_format())
    if log_file.get("enabled", False):
        if (log_file_format := log_file.get("path_format", None)) is not None:
            log_file_path = (
                log_file_format.format(
                    basename=caller_basename, funcname=caller_funcname, time=now
                )
                + ".log"
            )
            log_file.path = log_file_path
            file_log_level = log_file.get("log_level", None) or log_level
            logger.info(f"Logging to file: {log_file_path} with level {file_log_level}")
            # no need to overwrite the default format when writing to file
            logger.add(log_file_path, level=file_log_level, format=log_format)

    configs["info"] = Configs(
        {
            "start_time": now.format("YYYY-MM-DD HH:mm:ss"),
            "dotenvs": dotenvs,
            "appl_configs": appl_config_files,
        }
    )
    if configs.getattrs("settings.logging.display.configs"):
        logger.info(f"Using configs:\n{yaml.dump(configs.to_dict())}")

    tracing = configs.getattrs("settings.tracing")
    strict_match = tracing.get("strict_match", True)
    if tracing.get("enabled", False):
        if (trace_file_format := tracing.get("path_format", None)) is not None:
            prefix = trace_file_format.format(
                basename=caller_basename, funcname=caller_funcname, time=now
            )
            trace_file_path = f"{prefix}.pkl"
            meta_file = f"{prefix}_meta.json"
            tracing.trace_file = trace_file_path
            logger.info(f"Tracing file: {trace_file_path}")
            dump_file(configs.to_dict(), meta_file)
            global_vars.trace_engine = TraceEngine(
                trace_file_path, mode="write", strict=strict_match
            )
        else:
            logger.warning("Tracing is enabled but no trace file is specified")

    resume_cache = resume_cache or os.environ.get("APPL_RESUME_TRACE", None)
    if resume_cache:
        global_vars.resume_cache = resume_cache
        logger.info(f"Using resume cache: {resume_cache}")
        global_vars.resume_cache = TraceEngine(
            resume_cache, mode="read", strict=strict_match
        )

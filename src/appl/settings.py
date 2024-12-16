import datetime
import os
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

import litellm
import pendulum
import yaml
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

from .caching import DBCache
from .core.config import (
    APPLConfigs,
    CachingSettings,
    ConcurrencySettings,
    ConfigsDict,
    LoggingSettings,
    MiscSettings,
    TracingSettings,
    load_config,
)
from .core.globals import global_executors, global_vars
from .core.io import dump_file
from .core.patch import patch_threading
from .core.trace import TraceEngineBase
from .core.types import (
    ExecutorNotFoundError,
    ExecutorType,
    GitInfo,
    MetaData,
    is_thread_executor,
)
from .tracing import TraceEngine
from .utils import LoguruFormatter, find_files, get_git_info
from .version import __version__

APPL_CONFIG_FILES = ["appl.yaml", "appl.yml", "appl.json", "appl.toml"]


def _setup_logging(configs: LoggingSettings, remove_existing: bool = True) -> None:
    """Set up the logging."""
    log_file = (
        configs.log_file.path_format.format(
            basename=global_vars.metadata.exec_file_basename,
            time=global_vars.now,
        )
        + ".log"
    )

    if remove_existing:
        # set logger level for loguru
        if global_vars.metadata.log_file and (
            not configs.enable_file or global_vars.metadata.log_file != log_file
        ):
            logger.warning(
                f"Configs are updated, disabling log file {global_vars.metadata.log_file}"
            )
        logger.remove()  # Remove default handler
        if configs.enable_stderr:
            logger.add(sys.stderr, level=configs.log_level, format=_get_loguru_format())

    if configs.enable_file:
        file_log_level = configs.log_file.log_level or configs.log_level
        # no need to overwrite the default format when writing to file
        logger.add(log_file, level=file_log_level, format=configs.format)

        if global_vars.metadata.log_file != log_file:
            logger.info(f"Logging to file: {log_file} with level {file_log_level}")
        global_vars.metadata.log_file = log_file


def _setup_concurrency(configs: ConcurrencySettings) -> None:
    """Set up the concurrency."""

    def _setup_executor(
        executor_type: ExecutorType, max_workers: int, name: str = "general"
    ) -> None:
        try:
            executor = global_executors.get_executor(executor_type)
            if executor._max_workers == max_workers:  # type: ignore
                return  # same workers, no change
            executor.shutdown(wait=True)
        except ExecutorNotFoundError:  # executor not found
            pass

        # create a new executor
        if is_thread_executor(executor_type):
            executor = ThreadPoolExecutor(
                max_workers=max_workers, thread_name_prefix=name
            )
        else:
            executor = ProcessPoolExecutor(max_workers=max_workers)
        global_executors.set_executor(executor_type, executor)
        logger.debug(f"{executor_type.value} set to {max_workers} workers")

    _setup_executor(ExecutorType.LLM_THREAD_POOL, configs.llm_max_workers, name="llm")
    _setup_executor(ExecutorType.GENERAL_THREAD_POOL, configs.thread_max_workers)
    _setup_executor(ExecutorType.GENERAL_PROCESS_POOL, configs.process_max_workers)


def _setup_caching(
    configs: CachingSettings, old_configs: Optional[CachingSettings] = None
) -> None:
    """Set up the caching."""
    if configs.enabled:
        if old_configs is None or configs.folder != old_configs.folder:
            db_file = os.path.expanduser(os.path.join(configs.folder, "cache.db"))
            logger.info(f"Using cache folder: {configs.folder}")
            global_vars.llm_cache = DBCache(db_file)
    else:
        global_vars.llm_cache = None


def _get_trace_file_prefix() -> str:
    return global_vars.configs.settings.tracing.path_format.format(
        basename=global_vars.metadata.exec_file_basename,
        time=global_vars.now,
    )


def _setup_tracing(configs: TracingSettings) -> None:
    """Set up the tracing."""
    if global_vars.trace_engine and global_vars.trace_engine.events:
        logger.warning(
            f"Tracing is already enabled at {global_vars.metadata.trace_file} "
            "cannot setup tracing again."
        )
        return

    if configs.enabled:
        if configs.patch_threading:
            patch_threading()
        trace_file = f"{_get_trace_file_prefix()}.pkl"
        if trace_file != global_vars.metadata.trace_file:
            logger.info(f"Tracing file set to: {trace_file}")
            global_vars.metadata.trace_file = trace_file
            global_vars.trace_engine = TraceEngine(
                trace_file, mode="write", strict=configs.strict_match
            )

    else:
        global_vars.metadata.trace_file = None
        global_vars.trace_engine = None

    resume_trace = configs.trace_to_resume or os.environ.get("APPL_RESUME_TRACE", None)
    if resume_trace:
        logger.info(f"Using resume cache: {resume_trace}")
        global_vars.resume_trace = TraceEngine(
            resume_trace, mode="read", strict=configs.strict_match
        )
    else:
        global_vars.resume_trace = None


def _setup_misc(configs: MiscSettings) -> None:
    """Set up the misc settings."""
    litellm.suppress_debug_info = configs.suppress_litellm_debug_info


def _get_loguru_format():
    return LoguruFormatter(
        max_length=global_vars.configs.settings.logging.max_length,
        suffix_length=global_vars.configs.settings.logging.suffix_length,
    ).loguru_format


def merge_configs(original_configs: APPLConfigs, **kwargs: Any) -> APPLConfigs:
    """Return a new APPLConfigs with the overridden configs."""
    configs_dict = ConfigsDict(**original_configs.model_dump())
    configs_dict.update(**kwargs)
    return APPLConfigs(**configs_dict.to_dict())


def _appl_init():
    """Initialize the APPL."""
    logger.remove()  # Remove default handler
    # update default handler for the loguru logger
    logger.add(sys.stderr, level="INFO", format=_get_loguru_format())  # default

    cwd = os.getcwd()
    exec_file_path = os.path.expanduser(os.path.abspath(sys.argv[0]))

    try:
        git_info = get_git_info()
    except Exception as e:
        logger.warning(f"git info not found: {e}")
        git_info = GitInfo()

    # ===== Load and Update Configs ======
    # find and load dotenvs and appl configs (from outer to inner)
    # find dotenvs starting from the current working directory
    dotenvs = find_files(cwd, [".env"])[::-1]
    # find appl configs starting from the file being executed
    appl_config_files = find_files(exec_file_path, APPL_CONFIG_FILES)[::-1]

    for dotenv in dotenvs:
        load_dotenv(dotenv, override=True)
        logger.info("Loaded dotenv from {}".format(dotenv))

    all_configs_from_files = [
        (config_file, load_config(config_file)) for config_file in appl_config_files
    ]

    global_vars.metadata = MetaData(
        appl_version=__version__,
        cwd=cwd,
        run_cmd=f"{Path(sys.executable).stem} {' '.join(sys.argv)}",
        git_info=git_info,
        start_time=global_vars.now.format("YYYY-MM-DD HH:mm:ss"),
        exec_file_path=exec_file_path,
        exec_file_basename=Path(exec_file_path).stem,
        dotenvs=dotenvs,
        appl_config_files=appl_config_files,
    )

    # merge configs from outer to inner with override
    display_configs_update = global_vars.configs.settings.logging.display.configs_update

    # determine if we should display the configs update
    for _, configs in all_configs_from_files:
        display_configs_update = (
            configs.get("settings", {})
            .get("logging", {})
            .get("display", {})
            .get("configs_update", display_configs_update)
        )

    for config_file, override_configs in all_configs_from_files:
        logger.info("Loaded configs from {}".format(config_file))
        new_configs = merge_configs(global_vars.configs, **override_configs.to_dict())
        global_vars.configs = new_configs
        if display_configs_update:
            logger.info(f"Update configs:\n{yaml.dump(override_configs.to_dict())}")

    default_server = global_vars.configs.servers.get("default", None)
    if default_server:
        logger.info(f"Default server is now configured to {default_server}")
    else:
        logger.warning(
            "Default server is not configured with appl config files, "
            "You need to configure it with environment variables or command line arguments."
            # TODO: add env var and cmd args name.
        )

    # ===== Setup Logging ======
    _setup_logging(global_vars.configs.settings.logging)

    # ===== Setup Concurrency ======
    _setup_concurrency(global_vars.configs.settings.concurrency)

    # ===== Setup Caching ======
    _setup_caching(global_vars.configs.settings.caching)

    # ===== Setup Tracing ======
    _setup_tracing(global_vars.configs.settings.tracing)

    # ===== Setup Misc ======
    _setup_misc(global_vars.configs.settings.misc)

    # ===== Setup Metadata ======
    meta_file = f"{_get_trace_file_prefix()}_meta.json"
    static_metadata = global_vars.configs.metadata
    dump_file(
        {
            **static_metadata,
            **asdict(global_vars.metadata),
            "configs": global_vars.configs.model_dump(),
        },
        meta_file,
    )

    if global_vars.configs.settings.logging.display.configs:
        logger.info(f"Using configs:\n{yaml.dump(global_vars.configs.model_dump())}")


def update_appl_configs(new_configs: APPLConfigs) -> None:
    """Update the global configs.

    Note: Update in the middle might cause unexpected behavior.
    """
    _setup_logging(new_configs.settings.logging)
    _setup_concurrency(new_configs.settings.concurrency)
    _setup_caching(new_configs.settings.caching, global_vars.configs.settings.caching)
    _setup_tracing(new_configs.settings.tracing)
    _setup_misc(new_configs.settings.misc)
    global_vars.configs = new_configs


# init when imported
_appl_init()

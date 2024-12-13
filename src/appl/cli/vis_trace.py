import os

from appl import dump_file, load_config, load_file
from appl.core.trace import TracePrinterBase
from appl.tracing import (
    TraceEngine,
    TraceHTMLPrinter,
    TraceLangfusePrinter,
    TraceLunaryPrinter,
    TraceProfilePrinter,
    TraceYAMLPrinter,
)
from appl.utils import get_meta_file

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=str)
    parser.add_argument(
        "--platform",
        "-p",
        type=str,
        choices=["langfuse", "lunary"],
        help="The platform to print the trace to",
        default=None,
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./dumps/trace.html",
        help="mode determined by the file extension, support html, json and yaml",
    )
    args = parser.parse_args()
    if args.platform and args.platform not in ["langfuse", "lunary"]:
        raise ValueError(f"Unsupported platform: {args.platform}")

    trace_path = args.trace
    if not os.path.exists(trace_path):
        trace_path += ".pkl"
    if not os.path.exists(trace_path):
        raise FileNotFoundError(f"Trace file not found: {args.trace}")
    meta_file_path = get_meta_file(trace_path)
    configs = load_config(meta_file_path)

    def _get_printer() -> TracePrinterBase:
        if args.platform in ["langfuse", "lunary"]:
            return (
                TraceLangfusePrinter()
                if args.platform == "langfuse"
                else TraceLunaryPrinter()
            )
        else:
            file_ext = args.output.split(".")[-1]
            if file_ext == "html":
                return TraceHTMLPrinter()
            elif file_ext == "json":
                return TraceProfilePrinter()
            elif file_ext == "yaml":
                return TraceYAMLPrinter()
            else:
                raise ValueError(f"Unsupported file extension: {file_ext}")

    trace = TraceEngine(trace_path, mode="read")
    printer = _get_printer()
    if args.platform:
        printer.print(trace, configs)
    else:
        print(f"Outputting to {args.output}")
        dump_file(printer.print(trace, configs), args.output)

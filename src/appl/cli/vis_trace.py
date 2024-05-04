import os

from appl import dump_file, load_config, load_file
from appl.tracing import TraceEngine, TraceHTMLPrinter, TraceProfilePrinter
from appl.utils import get_meta_file

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=str)
    parser.add_argument("--output", "-o", type=str, default="./dumps/trace.html")
    args = parser.parse_args()

    trace_path = args.trace
    if not os.path.exists(trace_path):
        trace_path += ".pkl"
    if not os.path.exists(trace_path):
        raise FileNotFoundError(f"Trace file not found: {args.trace}")
    meta_file_path = get_meta_file(trace_path)
    configs = load_config(meta_file_path)
    trace = TraceEngine(trace_path, mode="read")
    print(f"Outputting to {args.output}")
    is_html = args.output.endswith(".html")
    printer = TraceHTMLPrinter() if is_html else TraceProfilePrinter()
    dump_file(printer.print(trace, configs), args.output)

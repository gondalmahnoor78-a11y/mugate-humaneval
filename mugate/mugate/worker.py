"""Sandbox worker. Run as `python -I worker.py`; reads one JSON job on stdin and streams one JSON
result line per item on stdout. The parent process enforces per-item timeouts and memory limits
and restarts the worker after a timeout or crash. Standard library only."""
import contextlib
import copy
import io
import json
import math
import sys
import time

OUT = sys.stdout


def emit(d):
    OUT.write(json.dumps(d) + "\n")
    OUT.flush()


def norm(x):
    if isinstance(x, float):
        return "nan" if math.isnan(x) else round(x, 9)
    if isinstance(x, (list, tuple)):
        return [type(x).__name__] + [norm(v) for v in x]
    if isinstance(x, dict):
        return ["dict"] + sorted((repr(k), repr(norm(v))) for k, v in x.items())
    if isinstance(x, (set, frozenset)):
        return ["set"] + sorted(repr(norm(v)) for v in x)
    return x


def run_suite(item, entry, sink):
    ns = {"__name__": "__mugate__"}
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            exec(compile(item["src"], "<P>", "exec"), ns)
            exec(compile(item["suite"], "<T>", "exec"), ns)
            ns["check"](ns[entry])
        return {"id": item["id"], "status": "pass", "t": time.perf_counter() - t0}
    except KeyboardInterrupt:
        raise
    except BaseException as e:  # includes SystemExit, RecursionError, MemoryError
        return {"id": item["id"], "status": "fail", "exc": type(e).__name__, "t": time.perf_counter() - t0}


def run_cov(item, entry, sink):
    ns = {"__name__": "__mugate__"}
    hit = set()

    def local(frame, event, arg):
        if event == "line":
            hit.add(frame.f_lineno)
        return local

    def glob(frame, event, arg):
        return local if frame.f_code.co_filename == "<P>" else None

    status = "pass"
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            exec(compile(item["src"], "<P>", "exec"), ns)
            exec(compile(item["suite"], "<T>", "exec"), ns)
            sys.settrace(glob)
            try:
                ns["check"](ns[entry])
            finally:
                sys.settrace(None)
    except KeyboardInterrupt:
        raise
    except BaseException as e:
        status = "fail:" + type(e).__name__
    return {"id": item["id"], "status": status, "lines": sorted(hit)}


def outcome(fn, args, sink):
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            r = fn(*copy.deepcopy(args))
        return repr(norm(r))
    except KeyboardInterrupt:
        raise
    except BaseException as e:
        return "EXC:" + type(e).__name__


def run_diff(item, entry, inputs, base, sink):
    ns = {"__name__": "__mugate__"}
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            exec(compile(item["src"], "<P>", "exec"), ns)
        fn = ns[entry]
    except BaseException as e:
        return {"id": item["id"], "load_error": type(e).__name__}
    outs = {}
    for i in item["idx"]:
        o = outcome(fn, inputs[i], sink)
        if base is not None and o != base[str(i)]:
            return {"id": item["id"], "first_diff": i, "mut_out": o[:200]}
        outs[str(i)] = o
    if base is None:
        return {"id": item["id"], "outs": outs}
    return {"id": item["id"], "first_diff": -1}


def main():
    sys.setrecursionlimit(3000)
    job = json.loads(sys.stdin.read())
    entry, mode = job["entry"], job["mode"]
    sink = io.StringIO()
    inputs = [eval(s) for s in job.get("inputs", [])]
    for item in job["items"]:
        if mode == "suite":
            r = run_suite(item, entry, sink)
        elif mode == "cov":
            r = run_cov(item, entry, sink)
        elif mode == "diff":
            r = run_diff(item, entry, inputs, job.get("base"), sink)
        else:
            raise ValueError(mode)
        sink.seek(0)
        sink.truncate()
        emit(r)


if __name__ == "__main__":
    main()

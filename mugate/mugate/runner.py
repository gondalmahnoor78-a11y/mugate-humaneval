"""Parent-side execution: spawns isolated `python -I worker.py` processes, enforces a per-item
wall-clock timeout (watchdog) and a 1 GiB memory cap, and restarts the worker after a timeout or
crash. Works on Windows (Job Object memory limit) and POSIX (RLIMIT_AS)."""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

WORKER = Path(__file__).with_name("worker.py")
MEM_LIMIT = 1 << 30
STARTUP_SLACK = 10.0
STATS = {"spawns": 0, "timeouts": 0, "crashes": 0, "items": 0}

_job_handle = None


def _windows_job():
    global _job_handle
    if _job_handle is not None:
        return _job_handle
    import ctypes
    from ctypes import wintypes

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class EXTENDED(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    h = k32.CreateJobObjectW(None, None)
    info = EXTENDED()
    info.BasicLimitInformation.LimitFlags = 0x100 | 0x2000  # PROCESS_MEMORY | KILL_ON_JOB_CLOSE
    info.ProcessMemoryLimit = MEM_LIMIT
    if not k32.SetInformationJobObject(h, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise OSError("SetInformationJobObject failed")
    _job_handle = (k32, h)
    return _job_handle


def _spawn():
    STATS["spawns"] += 1
    kw = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
              text=True, encoding="utf-8")
    if os.name != "nt":
        def limit():
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT * 2, MEM_LIMIT * 2))
        kw["preexec_fn"] = limit
    p = subprocess.Popen([sys.executable, "-I", str(WORKER)], **kw)
    if os.name == "nt":
        k32, h = _windows_job()
        k32.AssignProcessToJobObject(h, int(p._handle))
    return p


def _kill(p):
    try:
        p.kill()
    except Exception:
        pass
    try:
        p.wait(timeout=5)
    except Exception:
        pass


def _writer(p, payload):
    try:
        p.stdin.write(payload)
        p.stdin.close()
    except Exception:
        pass


def _reader(p, q):
    try:
        for line in p.stdout:
            q.put(line)
    except Exception:
        pass
    q.put(None)


def run_job(header, items, timeout):
    """Run `items` (dicts with unique string 'id') in as few worker processes as possible.
    Returns {id: result}. A result of {'status': 'timeout'} or {'status': 'crash'} marks items whose
    execution exceeded `timeout` seconds or killed the worker."""
    results, i = {}, 0
    while i < len(items):
        p = _spawn()
        payload = json.dumps(dict(header, items=items[i:]))
        threading.Thread(target=_writer, args=(p, payload), daemon=True).start()
        q = queue.Queue()
        threading.Thread(target=_reader, args=(p, q), daemon=True).start()
        first = True
        while i < len(items):
            try:
                line = q.get(timeout=timeout + (STARTUP_SLACK if first else 0.0))
            except queue.Empty:
                results[items[i]["id"]] = {"id": items[i]["id"], "status": "timeout"}
                STATS["timeouts"] += 1
                i += 1
                _kill(p)
                break
            first = False
            if line is None:
                results[items[i]["id"]] = {"id": items[i]["id"], "status": "crash"}
                STATS["crashes"] += 1
                i += 1
                _kill(p)
                break
            d = json.loads(line)
            results[d["id"]] = d
            STATS["items"] += 1
            i += 1
        else:
            _kill(p)
    return results


def run_isolated(header, items, timeout):
    """One fresh interpreter per item (the reproducibility-first mode used for cost comparison)."""
    out = {}
    for it in items:
        out.update(run_job(header, [it], timeout))
    return out

"""Rendering of test suites into HumanEval-style `check(candidate)` functions, plus the seven
synthetic test-weakening operators (W1-W7) used for RQ2.

An agent case is either (args_tuple, expected_value) or ("EXPR", "<boolean python expression
that may call candidate>")."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent_tests"

HELPERS = '''
import math
def _mg_eq(a, b):
    num = (int, float)
    if isinstance(a, num) and isinstance(b, num) and not isinstance(a, bool) and not isinstance(b, bool) \\
            and (isinstance(a, float) or isinstance(b, float)):
        return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) == type(b) and len(a) == len(b) and all(_mg_eq(x, y) for x, y in zip(a, b))
    return a == b
'''

WEAKENINGS = {
    "W1": ("No-oracle (call, then assert True)", "trivial assertion"),
    "W2": ("Tautological oracle (assert f(x) == f(x))", "trivial assertion"),
    "W3": ("Type-only oracle (assert isinstance(f(x), T))", "weak oracle"),
    "W4": ("Exception-swallowing (try/except Exception: pass)", "weak oracle"),
    "W5": ("Test deletion (keep first case only)", "deleted tests"),
    "W6": ("Skipped tests (dead if False: branch)", "skipped tests"),
    "W7": ("Mocked-out logic (stub returns expected value)", "mocked-out logic"),
}


def load_cases(name):
    """Load CASES dict from agent_tests/<name>.py (empty dict if the file does not exist)."""
    path = AGENT_DIR / f"{name}.py"
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location(f"agent_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CASES


def is_expr(case):
    return isinstance(case[0], str) and case[0] == "EXPR"


def _call(case):
    return f"candidate(*{case[0]!r})"


def case_lines(case, mode="sound"):
    if is_expr(case):
        e = case[1]
        return {
            "sound": [f"assert ({e})"],
            "W1": [f"_ = ({e})", "assert True"],
            "W2": [f"assert ({e}) == ({e})"],
            "W3": [f"assert isinstance(({e}), bool)"],
            "W4": ["try:", f"    assert ({e})", "except Exception:", "    pass"],
            "W6": ["if False:", f"    assert ({e})"],
            "W7": ["assert True"],
        }[mode]
    c, x = _call(case), repr(case[1])
    return {
        "sound": [f"assert _mg_eq({c}, {x})"],
        "W1": [f"_ = {c}", "assert True"],
        "W2": [f"assert _mg_eq({c}, {c})"],
        "W3": [f"assert isinstance({c}, type({x}))"],
        "W4": ["try:", f"    assert _mg_eq({c}, {x})", "except Exception:", "    pass"],
        "W6": ["if False:", f"    assert _mg_eq({c}, {x})"],
        "W7": [f"assert _mg_eq((lambda *a, **k: {x})(*{case[0]!r}), {x})"],
    }[mode]


def render(cases, mode="sound"):
    if mode == "W5":
        cases, mode = cases[:1], "sound"
    body = []
    for c in cases:
        body += ["    " + l for l in case_lines(c, mode)]
    if not body:
        body = ["    pass"]
    return HELPERS + "\ndef check(candidate):\n" + "\n".join(body) + "\n"

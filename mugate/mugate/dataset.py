"""HumanEval loading and the fixed, seeded 50-task sample."""
import ast
import gzip
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "HumanEval.jsonl.gz"
SAMPLE_SEED = 42
SAMPLE_N = 50


def load_all():
    with gzip.open(DATA, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sample_ids(seed=SAMPLE_SEED, n=SAMPLE_N):
    return sorted(random.Random(seed).sample(range(164), n))


def load_sample(seed=SAMPLE_SEED, n=SAMPLE_N):
    tasks = load_all()
    return [tasks[i] for i in sample_ids(seed, n)]


def program(task):
    """Ground-truth program P = prompt + canonical solution (original text, not re-formatted)."""
    return task["prompt"] + task["canonical_solution"]


def prompt_line_count(task):
    """Number of source lines that belong to the prompt. Lines > this value are mutation-eligible."""
    p = task["prompt"]
    return p.count("\n") if p.endswith("\n") else p.count("\n") + 1


def mutable_stmt_lines(task):
    """Line numbers of statements written by the solver (after the prompt), used for line coverage."""
    k = prompt_line_count(task)
    tree = ast.parse(program(task))
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) \
                    and isinstance(first.value.value, str):
                docs.add(id(first))
    return sorted({n.lineno for n in ast.walk(tree)
                   if isinstance(n, ast.stmt) and n.lineno > k and id(n) not in docs})

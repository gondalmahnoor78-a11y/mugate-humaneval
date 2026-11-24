"""AST-level first-order mutation engine (stdlib only).

Nine operators. Gate group (shown to the agent): AOR, ROR, LCR, UOD, CND.
Held-out group (never shown): CRP, RVR, SDL, BCR.
Only nodes whose line lies after the prompt (i.e. solver-written code) are mutated.
"""
import ast
import difflib
from dataclasses import dataclass, asdict

GATE_OPS = ["AOR", "ROR", "LCR", "UOD", "CND"]
HELD_OPS = ["CRP", "RVR", "SDL", "BCR"]
ALL_OPS = GATE_OPS + HELD_OPS

BIN = {ast.Add: [ast.Sub], ast.Sub: [ast.Add], ast.Mult: [ast.Div], ast.Div: [ast.Mult],
       ast.FloorDiv: [ast.Div], ast.Mod: [ast.FloorDiv], ast.Pow: [ast.Mult]}
CMP = {ast.Lt: [ast.LtE, ast.Gt], ast.LtE: [ast.Lt, ast.GtE], ast.Gt: [ast.GtE, ast.Lt],
       ast.GtE: [ast.Gt, ast.LtE], ast.Eq: [ast.NotEq], ast.NotEq: [ast.Eq],
       ast.Is: [ast.IsNot], ast.IsNot: [ast.Is], ast.In: [ast.NotIn], ast.NotIn: [ast.In]}
SDL_TYPES = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr)


@dataclass
class Mutant:
    mid: str
    op: str
    group: str
    line: int
    src: str
    diff: str

    def to_dict(self):
        return asdict(self)


def _docstring_nodes(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body:
            f = n.body[0]
            if isinstance(f, ast.Expr) and isinstance(f.value, ast.Constant) and isinstance(f.value.value, str):
                out.add(id(f))
                out.add(id(f.value))
    return out


def _set(attr, value_factory):
    def f(c):
        setattr(c, attr, value_factory())
        return c
    return f


def _variants(parent, field, child, docs):
    """Yield (op, transform) where transform(child_copy) -> replacement node."""
    v = []
    if isinstance(child, ast.BinOp) and type(child.op) in BIN:
        for new in BIN[type(child.op)]:
            v.append(("AOR", _set("op", new)))
    if isinstance(child, ast.AugAssign) and type(child.op) in BIN:
        for new in BIN[type(child.op)]:
            v.append(("AOR", _set("op", new)))
    if isinstance(child, ast.Compare):
        for i, op in enumerate(child.ops):
            for new in CMP.get(type(op), []):
                def f(c, i=i, new=new):
                    c.ops[i] = new()
                    return c
                v.append(("ROR", f))
    if isinstance(child, ast.BoolOp):
        v.append(("LCR", _set("op", ast.Or if isinstance(child.op, ast.And) else ast.And)))
    if isinstance(child, ast.UnaryOp) and isinstance(child.op, (ast.Not, ast.USub)):
        v.append(("UOD", lambda c: c.operand))
    if field == "test" and isinstance(parent, (ast.If, ast.While, ast.IfExp)):
        v.append(("CND", lambda c: ast.UnaryOp(op=ast.Not(), operand=c)))
    if field == "ifs" and isinstance(parent, ast.comprehension):
        v.append(("CND", lambda c: ast.UnaryOp(op=ast.Not(), operand=c)))
    if isinstance(child, ast.Constant) and id(child) not in docs:
        val = child.value
        if isinstance(val, bool):
            v.append(("CRP", _set("value", lambda val=val: not val)))
        elif isinstance(val, int):
            v.append(("CRP", _set("value", lambda val=val: val + 1)))
            v.append(("CRP", _set("value", lambda val=val: val - 1)))
        elif isinstance(val, float):
            v.append(("CRP", _set("value", lambda val=val: val + 1.0)))
        elif isinstance(val, str) and not isinstance(parent, ast.JoinedStr):
            v.append(("CRP", _set("value", (lambda: "") if val else (lambda: "_"))))
    if isinstance(child, ast.Return) and child.value is not None and not (
            isinstance(child.value, ast.Constant) and child.value.value is None):
        v.append(("RVR", _set("value", lambda: ast.Constant(value=None))))
    if isinstance(child, SDL_TYPES) and id(child) not in docs and isinstance(getattr(parent, field, None), list):
        v.append(("SDL", lambda c: ast.Pass()))
    if isinstance(child, ast.Break):
        v.append(("BCR", lambda c: ast.Continue()))
    if isinstance(child, ast.Continue):
        v.append(("BCR", lambda c: ast.Break()))
    return v


def _children(parent):
    for field, value in ast.iter_fields(parent):
        if isinstance(value, ast.AST):
            yield field, None, value
        elif isinstance(value, list):
            for i, x in enumerate(value):
                if isinstance(x, ast.AST):
                    yield field, i, x


def generate_mutants(src, first_mutable_line):
    """All syntactically valid, textually distinct first-order mutants of `src`.

    first_mutable_line: nodes with lineno >= this value are eligible (solver-written code).
    """
    tree = ast.parse(src)
    base = ast.unparse(tree)
    docs = _docstring_nodes(tree)
    plan = []
    for pi, parent in enumerate(ast.walk(tree)):
        for field, li, child in _children(parent):
            ln = getattr(child, "lineno", None)
            if ln is None or ln < first_mutable_line:
                continue
            for k, (op, _) in enumerate(_variants(parent, field, child, docs)):
                plan.append((pi, field, li, k, op, ln))
    seen, out = {base}, []
    for pi, field, li, k, op, ln in plan:
        t = ast.parse(src)
        d2 = _docstring_nodes(t)
        parent = list(ast.walk(t))[pi]
        child = getattr(parent, field) if li is None else getattr(parent, field)[li]
        transform = _variants(parent, field, child, d2)[k][1]
        new = transform(child)
        if li is None:
            setattr(parent, field, new)
        else:
            getattr(parent, field)[li] = new
        ast.fix_missing_locations(t)
        try:
            m_src = ast.unparse(t)
            compile(m_src, "<mutant>", "exec")
        except Exception:
            continue  # stillborn
        if m_src in seen:
            continue  # duplicate or identical to original
        seen.add(m_src)
        diff = "\n".join(l for l in difflib.unified_diff(base.splitlines(), m_src.splitlines(), lineterm="", n=0)
                         if l[:1] in "+-" and not l.startswith(("+++", "---")))
        group = "gate" if op in GATE_OPS else "held"
        out.append(Mutant(f"m{len(out):03d}", op, group, ln, m_src, diff))
    return out

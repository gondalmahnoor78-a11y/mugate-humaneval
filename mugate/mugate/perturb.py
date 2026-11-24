"""Input perturbation for the differential-testing equivalence audit. Seeds come from the
agent's own test inputs (never from the human tests or the canonical solution)."""
import random

MAX_ABS_INT = 10 ** 6


def _perturb_value(x, rng, depth=0):
    if isinstance(x, bool):
        return [not x]
    if isinstance(x, int):
        c = [x + 1, x - 1, -x, 0, 2 * x, x + rng.randint(-10, 10)]
        return [v for v in c if abs(v) <= MAX_ABS_INT]
    if isinstance(x, float):
        return [x + 0.5, -x, 0.0, x * 2, round(x + rng.uniform(-3, 3), 3)]
    if isinstance(x, str):
        out = [x[::-1], x[:-1], x + x[:1], x.upper(), x.lower(), x.swapcase(), ""]
        if len(x) >= 2:
            l = list(x)
            i, j = rng.randrange(len(l)), rng.randrange(len(l))
            l[i], l[j] = l[j], l[i]
            out.append("".join(l))
            k = rng.randrange(len(x))
            out.append(x[:k] + x[k] + x[k:])
        return out
    if isinstance(x, (list, tuple)):
        seq = list(x)
        out = [seq[::-1], seq[:-1], seq + seq[:1], []]
        if len(seq) >= 2:
            s2 = seq[:]
            rng.shuffle(s2)
            out.append(s2)
        if seq and depth < 2:
            i = rng.randrange(len(seq))
            for v in _perturb_value(seq[i], rng, depth + 1):
                s3 = seq[:]
                s3[i] = v
                out.append(s3)
        return [type(x)(o) if isinstance(x, tuple) else o for o in out]
    return []


def generate_inputs(arg_tuples, seed, n_max=400):
    """Original agent inputs first, then random single-argument perturbations, de-duplicated."""
    rng = random.Random(seed)
    seen, out = set(), []

    def add(t):
        r = repr(t)
        if r not in seen and len(r) < 2000:
            seen.add(r)
            out.append(r)

    for t in arg_tuples:
        add(tuple(t))
    if not arg_tuples:
        return out
    stall = 0
    while len(out) < n_max and stall < 2000:
        base = list(rng.choice(arg_tuples))
        if not base:
            break
        pos = rng.randrange(len(base))
        cands = _perturb_value(base[pos], rng)
        if not cands:
            stall += 1
            continue
        b2 = base[:]
        b2[pos] = rng.choice(cands)
        before = len(out)
        add(tuple(b2))
        stall = stall + 1 if len(out) == before else 0
    return out[:n_max]

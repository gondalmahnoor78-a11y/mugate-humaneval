"""Small statistics helpers (stdlib only): task-level cluster bootstrap and Wilcoxon signed-rank."""
import math
import random


def pooled(num, den, idx):
    n = sum(num[i] for i in idx)
    d = sum(den[i] for i in idx)
    return n / d if d else float("nan")


def bootstrap_ratio(num, den, B=10000, seed=0):
    """95% percentile CI for sum(num)/sum(den), resampling tasks (clusters) with replacement."""
    rng = random.Random(seed)
    n = len(num)
    vals = sorted(pooled(num, den, [rng.randrange(n) for _ in range(n)]) for _ in range(B))
    return vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def bootstrap_paired_diff(num_a, num_b, den, B=10000, seed=0):
    """95% CI for pooled(num_a)/den - pooled(num_b)/den with paired task resampling."""
    rng = random.Random(seed)
    n = len(den)
    vals = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        vals.append(pooled(num_a, den, idx) - pooled(num_b, den, idx))
    vals.sort()
    return vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def wilcoxon(diffs):
    """Two-sided Wilcoxon signed-rank test (zeros dropped, average ranks for ties, normal
    approximation with tie correction and continuity correction). Returns (W+, n_nonzero, p)."""
    d = [x for x in diffs if abs(x) > 1e-12]
    n = len(d)
    if n == 0:
        return 0.0, 0, 1.0
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    ties = []
    while i < n:
        j = i
        while j + 1 < n and abs(abs(d[order[j + 1]]) - abs(d[order[i]])) < 1e-12:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        ties.append(j - i + 1)
        i = j + 1
    wp = sum(r for r, x in zip(ranks, d) if x > 0)
    mu = n * (n + 1) / 4
    var = n * (n + 1) * (2 * n + 1) / 24 - sum(t ** 3 - t for t in ties) / 48
    if var <= 0:
        return wp, n, 1.0
    z = (abs(wp - mu) - 0.5) / math.sqrt(var)
    p = math.erfc(max(z, 0) / math.sqrt(2))
    return wp, n, min(1.0, p)


def sign_test(diffs):
    """Exact two-sided sign test on non-zero differences."""
    pos = sum(1 for x in diffs if x > 1e-12)
    neg = sum(1 for x in diffs if x < -1e-12)
    n = pos + neg
    if n == 0:
        return pos, neg, 1.0
    k = min(pos, neg)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return pos, neg, min(1.0, p)


def mean_sd(xs):
    xs = [x for x in xs if not (isinstance(x, float) and math.isnan(x))]
    if not xs:
        return float("nan"), float("nan")
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0
    return m, sd

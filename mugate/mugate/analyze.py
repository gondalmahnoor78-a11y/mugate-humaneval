"""Compute every number reported in the paper from the raw result files. Writes
results/summary.json and results/per_task.csv.

Killable set (denominator of the adjusted mutation score):
  K* = {mutants killed by at least one sound suite}
       U {sound-suite survivors with an audit-found, within-precondition distinguishing input}
Survivors with no audit difference are 'equivalent (audit)'. Survivors whose only audit
difference lies outside the documented precondition are 'equivalent under contract'; this
judgement is manual and recorded with a rationale in analysis/equivalence_labels.json.
Unlike the original draft, K* does not depend on any suite failing to kill a mutant: a survivor
with a valid distinguishing input stays in the denominator and lowers every suite's score.
"""
import csv
import json
import math
from collections import Counter, defaultdict

from . import dataset as D
from . import stats as ST
from .mutation import ALL_OPS
from .pipeline import RES, SOUND, WEAK, ROUNDS, load, load_kept

LABELS = D.ROOT / "analysis" / "equivalence_labels.json"
BOOT_SEEDS = [0, 1, 2, 3, 4]
B = 10000


def killed(km, tid, s, mid):
    return km[tid][s]["status"][mid] != "pass"


def main():
    mu, km, cov = load("mutants.json"), load("kill_matrix.json"), load("coverage.json")
    audit0 = load("audit_seed0.json")["tasks"]
    labels = json.loads(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}
    kept = load_kept()
    rep = load("repair.json")
    tids = list(mu)
    allm = [(t, m) for t in tids for m in mu[t]]

    # --- survivors and equivalence classification
    surv, classes = [], {}
    for t, m in allm:
        if any(killed(km, t, s, m["mid"]) for s in SOUND):
            continue
        key = f"{t}:{m['mid']}"
        a = audit0[t]["mutants"][m["mid"]]
        if a["verdict"] == "no_difference":
            cls = "equivalent_audit"
        else:
            lab = labels.get(key)
            if lab is None:
                raise SystemExit(f"missing manual label for {key} (audit verdict {a['verdict']})")
            cls = lab["label"]
        classes[key] = cls
        surv.append((t, m, cls, a))
    killable = {(t, m["mid"]) for t, m in allm if any(killed(km, t, s, m["mid"]) for s in SOUND)}
    killable |= {(t, m["mid"]) for t, m, cls, _ in surv if cls == "killable"}

    # --- audit seed stability (seeds 1-4 run on survivors only)
    stab = {}
    for sd in [1, 2, 3, 4]:
        p = RES / f"audit_seed{sd}.json"
        if p.exists():
            a = json.loads(p.read_text())["tasks"]
            stab[str(sd)] = Counter(a[t]["mutants"][m["mid"]]["verdict"] for t, m, _, _ in surv)
    stab["0"] = Counter(a["verdict"] for _, _, _, a in surv)

    # --- mutation scores
    def num_den(s, group=None, op=None, adjusted=True):
        num, den = [], []
        for t in tids:
            ms = [m for m in mu[t] if (group is None or m["group"] == group) and (op is None or m["op"] == op)
                  and (not adjusted or (t, m["mid"]) in killable)]
            den.append(len(ms))
            num.append(sum(1 for m in ms if killed(km, t, s, m["mid"])))
        return num, den

    res = {"n_tasks": len(tids), "n_mutants": len(allm), "n_killable": len(killable),
           "n_gate_mutants": sum(1 for _, m in allm if m["group"] == "gate"),
           "n_held_mutants": sum(1 for _, m in allm if m["group"] == "held"),
           "mutants_by_op": dict(Counter(m["op"] for _, m in allm)),
           "killable_by_op": dict(Counter(m["op"] for t, m in allm if (t, m["mid"]) in killable)),
           "survivor_classes": dict(Counter(classes.values())), "n_survivors": len(surv),
           "survivors_by_op": dict(Counter(m["op"] for _, m, _, _ in surv)),
           "audit_seed_stability": {k: dict(v) for k, v in stab.items()},
           "repair": rep["summary"], "dropped_cases": rep["dropped"]}
    suites = {}
    for s in SOUND + WEAK:
        d = {}
        for name, kw in [("adj", {}), ("raw", {"adjusted": False}), ("adj_gate", {"group": "gate"}),
                         ("adj_held", {"group": "held"})]:
            num, den = num_den(s, **kw)
            d[name] = {"killed": sum(num), "total": sum(den), "ms": sum(num) / sum(den) if sum(den) else float("nan")}
        num, den = num_den(s)
        cis = [ST.bootstrap_ratio(num, den, B, sd) for sd in BOOT_SEEDS]
        d["adj"]["ci95"] = [sum(c[0] for c in cis) / len(cis), sum(c[1] for c in cis) / len(cis)]
        d["adj"]["ci95_seed_range"] = [[min(c[0] for c in cis), max(c[0] for c in cis)],
                                       [min(c[1] for c in cis), max(c[1] for c in cis)]]
        per_task = [n / dd if dd else float("nan") for n, dd in zip(num, den)]
        d["per_task_mean_sd"] = ST.mean_sd(per_task)
        d["tasks_perfect"] = sum(1 for x in per_task if x == 1.0)
        d["delta_gate"] = d["adj_held"]["ms"] - d["adj_gate"]["ms"]
        d["by_op"] = {op: dict(zip(("killed", "total"), map(sum, num_den(s, op=op)))) for op in ALL_OPS}
        suites[s] = d
    res["suites"] = suites

    # --- paired comparisons
    comps = {}
    for a, b in [("vanilla", "human"), ("blind", "vanilla"), ("gate", "vanilla"), ("gate", "blind"),
                 ("gate", "human"), ("blind", "human")]:
        na, den = num_den(a)
        nb, _ = num_den(b)
        cis = [ST.bootstrap_paired_diff(na, nb, den, B, sd) for sd in BOOT_SEEDS]
        diffs = [(x - y) / d for x, y, d in zip(na, nb, den) if d]
        w, n_nz, p = ST.wilcoxon(diffs)
        pos, neg, p_sign = ST.sign_test(diffs)
        comps[f"{a}-{b}"] = {"diff_pp": 100 * (sum(na) - sum(nb)) / sum(den),
                             "ci95_pp": [100 * sum(c[0] for c in cis) / len(cis), 100 * sum(c[1] for c in cis) / len(cis)],
                             "wilcoxon_W+": w, "n_nonzero": n_nz, "wilcoxon_p": p,
                             "tasks_better": pos, "tasks_worse": neg, "sign_p": p_sign,
                             "mutants_only_a": sum(1 for t in tids for m in mu[t] if (t, m["mid"]) in killable
                                                   and killed(km, t, a, m["mid"]) and not killed(km, t, b, m["mid"])),
                             "mutants_only_b": sum(1 for t in tids for m in mu[t] if (t, m["mid"]) in killable
                                                   and killed(km, t, b, m["mid"]) and not killed(km, t, a, m["mid"]))}
    res["comparisons"] = comps

    # --- coverage
    covs = {}
    for s in SOUND:
        per = [cov[t][s]["covered"].__len__() / cov[t][s]["n_stmt"] for t in tids if cov[t][s]["n_stmt"]]
        covs[s] = {"mean": sum(per) / len(per), "tasks_full": sum(1 for x in per if x == 1.0)}
    res["coverage"] = covs
    nv, dv = num_den("vanilla")
    full_cov_imperfect = []
    for i, t in enumerate(tids):
        c = len(cov[t]["vanilla"]["covered"]) / cov[t]["vanilla"]["n_stmt"]
        if c == 1.0 and dv[i] and nv[i] < dv[i]:
            full_cov_imperfect.append({"task": t, "ms": nv[i] / dv[i], "killed": nv[i], "killable": dv[i]})
    res["vanilla_full_coverage_but_ms_below_1"] = sorted(full_cov_imperfect, key=lambda x: x["ms"])
    xs = [len(cov[t]["vanilla"]["covered"]) / cov[t]["vanilla"]["n_stmt"] for t in tids]
    ys = [n / d if d else float("nan") for n, d in zip(nv, dv)]
    pts = [(x, y) for x, y in zip(xs, ys) if not math.isnan(y)]
    mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    sxx, syy = sum((p[0] - mx) ** 2 for p in pts), sum((p[1] - my) ** 2 for p in pts)
    res["vanilla_cov_ms_pearson"] = sxy / math.sqrt(sxx * syy) if sxx and syy else float("nan")

    # --- gate round effort
    n_extra = {t: len(kept["gate"].get(t, [])) for t in tids}
    surv0 = load("survivors_round0.json")
    res["gate_round"] = {"tasks_with_survivors_shown": sum(1 for v in surv0.values() if v),
                         "survivors_shown": sum(len(v) for v in surv0.values()),
                         "tasks_revised": sum(1 for v in n_extra.values() if v),
                         "extra_cases_total": sum(n_extra.values()),
                         "extra_cases_per_task": sum(n_extra.values()) / len(tids),
                         "blind_extra_cases_total": sum(len(kept["blind"].get(t, [])) for t in tids),
                         "vanilla_cases_total": sum(len(kept["vanilla"].get(t, [])) for t in tids),
                         "human_assert_lines": None}
    shown = {(t, mid) for t, v in surv0.items() for mid in v}
    res["gate_round"]["shown_killable"] = sum(1 for x in shown if x in killable)
    res["gate_round"]["shown_killed_after"] = sum(1 for t, mid in shown if (t, mid) in killable and killed(km, t, "gate", mid))

    # --- timing from the evaluation run
    ts = [v for t in tids for s in SOUND for k, v in km[t][s]["t"].items() if v is not None]
    ts.sort()
    res["exec_time_median_ms"] = 1000 * ts[len(ts) // 2]
    res["evaluate_meta"] = load("evaluate_meta.json")
    try:
        res["cost"] = load("cost.json")
    except FileNotFoundError:
        res["cost"] = None
    res["survivors"] = [{"task": t, "mid": m["mid"], "op": m["op"], "group": m["group"], "diff": m["diff"],
                         "class": cls, "audit": a} for t, m, cls, a in surv]
    (RES / "summary.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    with open(RES / "per_task.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task", "mutants", "killable"] + [f"ms_{s}" for s in SOUND + WEAK] + [f"cov_{s}" for s in SOUND])
        for i, t in enumerate(tids):
            row = [t, len(mu[t]), dv[i]]
            for s in SOUND + WEAK:
                n, d = num_den(s)
                row.append(f"{n[i] / d[i]:.4f}" if d[i] else "")
            for s in SOUND:
                row.append(f"{len(cov[t][s]['covered']) / cov[t][s]['n_stmt']:.4f}")
            w.writerow(row)
    print(json.dumps({s: round(100 * suites[s]["adj"]["ms"], 2) for s in suites}))
    print("killable", len(killable), "of", len(allm), "survivors", len(surv), res["survivor_classes"])


if __name__ == "__main__":
    main()

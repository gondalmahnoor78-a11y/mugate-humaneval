"""RQ3 cost and CPU-scaling measurements on this machine.

1. Gate-check overhead: run the vanilla suite on each task's gate mutants (a) batched in one
   warm worker per task and (b) isolated, one fresh interpreter per mutant. Repeated R times.
2. Process-level parallel scaling of the full evaluation workload for one suite (1 vs 2 workers).
3. Baseline: one run of the suite on P alone (what an ungated pipeline pays).
"""
import json
import os
import platform
import statistics
import time

from . import pipeline as PL
from . import runner as R


def gate_check(tasks, kept, isolated):
    per = []
    for ti in tasks:
        src = PL.suite_sources(ti, kept)["vanilla"]
        items = [{"id": m.mid, "src": m.src, "suite": src} for m in ti["mutants"] if m.group == "gate"]
        if not items:
            per.append(0.0)
            continue
        t0 = time.perf_counter()
        (R.run_isolated if isolated else R.run_job)({"mode": "suite", "entry": ti["entry"]}, items, PL.TIMEOUT)
        per.append(time.perf_counter() - t0)
    return per


def base_run(tasks, kept):
    per = []
    for ti in tasks:
        src = PL.suite_sources(ti, kept)["vanilla"]
        t0 = time.perf_counter()
        R.run_job({"mode": "suite", "entry": ti["entry"]}, [{"id": "P", "src": ti["P"], "suite": src}], PL.TIMEOUT)
        per.append(time.perf_counter() - t0)
    return per


def full_suite_scaling(tasks, kept, jobs):
    def one(ti):
        src = PL.suite_sources(ti, kept)["human"]
        PL.run_suite_on(ti, src, [("P", ti["P"])] + [(m.mid, m.src) for m in ti["mutants"]])
    t0 = time.perf_counter()
    PL.pmap(one, tasks, jobs)
    return time.perf_counter() - t0


def main(reps=3):
    tasks = PL.task_infos()
    kept = PL.load_kept()
    out = {"machine": {"platform": platform.platform(), "processor": platform.processor(),
                       "cpu_count": os.cpu_count(), "python": platform.python_version()}}
    batched, isolated, base = [], [], []
    for r in range(reps):
        batched.append(gate_check(tasks, kept, False))
        isolated.append(gate_check(tasks, kept, True))
        base.append(base_run(tasks, kept))
        print("rep", r, "batched", round(sum(batched[-1]), 2), "isolated", round(sum(isolated[-1]), 2),
              "base", round(sum(base[-1]), 2), flush=True)

    def summ(runs):
        per_task_means = [statistics.mean(x) for x in zip(*runs)]
        totals = [sum(r) for r in runs]
        return {"mean_per_task_s": statistics.mean(per_task_means), "sd_total_s": statistics.stdev(totals) if len(totals) > 1 else 0.0,
                "total_s_runs": totals, "per_task_mean_s": per_task_means}
    out["gate_check_batched"] = summ(batched)
    out["gate_check_isolated"] = summ(isolated)
    out["suite_on_P_only"] = summ(base)
    out["n_gate_mutants"] = sum(1 for ti in tasks for m in ti["mutants"] if m.group == "gate")
    scal = {}
    for j in (1, 2):
        scal[str(j)] = [full_suite_scaling(tasks, kept, j) for _ in range(reps)]
        print("workers", j, scal[str(j)], flush=True)
    out["scaling_human_suite_all_mutants_s"] = scal
    PL.save("cost.json", out)


if __name__ == "__main__":
    main()

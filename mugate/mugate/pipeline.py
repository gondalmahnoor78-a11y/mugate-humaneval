"""MuGate experimental pipeline.

Stages (run in this order; see README.md):
  repair     drop agent cases that fail on the canonical solution P (assertion repair)
  survivors  run the repaired vanilla suite on the gate-group mutants; write SURVIVORS.md feedback
  evaluate   run every suite on P and on every mutant; line coverage of the sound suites
  audit      differential-testing equivalence audit (all mutants), for a given input seed
"""
import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import dataset as D
from . import mutation as M
from . import perturb as PT
from . import runner as R
from . import suites as S

RES = D.ROOT / "results"
TIMEOUT = 2.0          # seconds per (program, suite) execution
AUDIT_TIMEOUT = 20.0   # seconds per mutant over all audit inputs
ROUNDS = ["vanilla", "blind", "gate"]
SOUND = ["human", "vanilla", "blind", "gate"]
WEAK = ["W1", "W2", "W3", "W4", "W5", "W6", "W7"]
_lock = threading.Lock()


def log(*a):
    with _lock:
        print(time.strftime("%H:%M:%S"), *a, flush=True)


def pmap(fn, xs, jobs):
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(fn, xs))


def task_infos():
    out = []
    for t in D.load_sample():
        P = D.program(t)
        k = D.prompt_line_count(t)
        out.append(dict(id=t["task_id"], entry=t["entry_point"], P=P, k=k, test=t["test"],
                        mutants=M.generate_mutants(P, k + 1), stmt_lines=D.mutable_stmt_lines(t)))
    return out


def save(name, obj):
    RES.mkdir(exist_ok=True)
    (RES / name).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def load(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- repair
def repair(tasks, jobs):
    raw = {r: S.load_cases(r) for r in ROUNDS}

    def one(ti):
        items = [{"id": f"{r}|{j}", "src": ti["P"], "suite": S.render([c])}
                 for r in ROUNDS for j, c in enumerate(raw[r].get(ti["id"], []))]
        return ti["id"], R.run_job({"mode": "suite", "entry": ti["entry"]}, items, TIMEOUT)

    kept = {r: {} for r in ROUNDS}
    dropped = []
    for tid, res in pmap(one, tasks, jobs):
        for r in ROUNDS:
            cs = raw[r].get(tid, [])
            kept[r][tid] = [c for j, c in enumerate(cs) if res[f"{r}|{j}"]["status"] == "pass"]
            for j, c in enumerate(cs):
                st = res[f"{r}|{j}"]
                if st["status"] != "pass":
                    dropped.append({"task": tid, "round": r, "case": repr(c), "outcome": st.get("exc", st["status"])})
    summary = {r: {"raw": sum(len(v) for v in raw[r].values()), "kept": sum(len(v) for v in kept[r].values())}
               for r in ROUNDS}
    save("repair.json", {"summary": summary, "dropped": dropped,
                         "kept": {r: {k: [repr(c) for c in v] for k, v in kept[r].items()} for r in ROUNDS}})
    log("repair:", summary, "dropped:", len(dropped))
    return kept


def load_kept():
    import ast as _ast
    d = load("repair.json")["kept"]
    return {r: {k: [_ast.literal_eval(c) for c in v] for k, v in d[r].items()} for r in ROUNDS}


def suite_sources(ti, kept):
    v = kept["vanilla"].get(ti["id"], [])
    out = {"human": ti["test"], "vanilla": S.render(v),
           "blind": S.render(v + kept["blind"].get(ti["id"], [])),
           "gate": S.render(v + kept["gate"].get(ti["id"], []))}
    for w in WEAK:
        out[w] = S.render(v, w)
    return out


def run_suite_on(ti, suite_src, programs, timeout=TIMEOUT):
    items = [{"id": pid, "src": src, "suite": suite_src} for pid, src in programs]
    return R.run_job({"mode": "suite", "entry": ti["entry"]}, items, timeout)


# ----------------------------------------------------------------------------- survivors
def survivors(tasks, kept, jobs):
    def one(ti):
        progs = [("P", ti["P"])] + [(m.mid, m.src) for m in ti["mutants"] if m.group == "gate"]
        return ti, run_suite_on(ti, S.render(kept["vanilla"].get(ti["id"], [])), progs)

    report, data = ["# Surviving gate mutants shown to the agent (feedback round 1)\n",
                    "Each entry is a first-order mutant of the candidate program that the agent's current (vanilla) "
                    "suite does NOT detect. Lines prefixed '-' are original code, '+' the mutated code. "
                    "Held-out mutants are never listed here.\n"], {}
    for ti, res in pmap(one, tasks, jobs):
        assert res["P"]["status"] == "pass", (ti["id"], res["P"])
        surv = [m for m in ti["mutants"] if m.group == "gate" and res[m.mid]["status"] == "pass"]
        data[ti["id"]] = [m.mid for m in surv]
        if surv:
            report.append(f"\n## {ti['id']} (`{ti['entry']}`) - {len(surv)} surviving gate mutant(s)\n")
            for m in surv:
                report.append(f"\n{m.mid} [{m.op}]\n```diff\n{m.diff}\n```\n")
    (D.ROOT / "agent_tests" / "SURVIVORS.md").write_text("".join(report), encoding="utf-8")
    save("survivors_round0.json", data)
    log("survivors: tasks with survivors =", sum(1 for v in data.values() if v),
        "total =", sum(len(v) for v in data.values()))


# ----------------------------------------------------------------------------- evaluate
def evaluate(tasks, kept, jobs):
    t_start = time.perf_counter()
    jobs_list = []
    for ti in tasks:
        srcs = suite_sources(ti, kept)
        for sname in SOUND + WEAK:
            jobs_list.append((ti, sname, srcs[sname]))

    def one(job):
        ti, sname, src = job
        progs = [("P", ti["P"])] + [(m.mid, m.src) for m in ti["mutants"]]
        t0 = time.perf_counter()
        res = run_suite_on(ti, src, progs)
        return ti["id"], sname, res, time.perf_counter() - t0

    kill = {}
    for tid, sname, res, dt in pmap(one, jobs_list, jobs):
        kill.setdefault(tid, {})[sname] = {"wall_s": dt, "status": {k: v["status"] for k, v in res.items()},
                                           "t": {k: v.get("t") for k, v in res.items()}}
    # coverage of sound suites on P
    def cov(ti):
        srcs = suite_sources(ti, kept)
        items = [{"id": s, "src": ti["P"], "suite": srcs[s]} for s in SOUND]
        res = R.run_job({"mode": "cov", "entry": ti["entry"]}, items, TIMEOUT)
        want = set(ti["stmt_lines"])
        return ti["id"], {s: {"covered": sorted(set(res[s].get("lines", [])) & want), "n_stmt": len(want),
                              "status": res[s]["status"]} for s in SOUND}
    coverage = dict(pmap(cov, tasks, jobs))
    mutants = {ti["id"]: [m.to_dict() for m in ti["mutants"]] for ti in tasks}
    save("mutants.json", mutants)
    save("kill_matrix.json", kill)
    save("coverage.json", coverage)
    save("evaluate_meta.json", {"wall_s": time.perf_counter() - t_start, "jobs": jobs, "timeout_s": TIMEOUT,
                                "runner_stats": dict(R.STATS)})
    log("evaluate done in", round(time.perf_counter() - t_start, 1), "s;", dict(R.STATS))


# ----------------------------------------------------------------------------- audit
def audit(tasks, kept, seed, jobs, only=None):
    t_start = time.perf_counter()

    def one(ti):
        args = [c[0] for r in ROUNDS for c in kept[r].get(ti["id"], []) if not S.is_expr(c)]
        inputs = PT.generate_inputs(args, seed)
        hdr = {"mode": "diff", "entry": ti["entry"], "inputs": inputs, "base": None}
        base = R.run_job(hdr, [{"id": f"b{i}", "src": ti["P"], "idx": [i]} for i in range(len(inputs))], TIMEOUT)
        outs = {}
        for i in range(len(inputs)):
            o = base[f"b{i}"].get("outs", {}).get(str(i))
            if o is not None and not o.startswith("EXC:"):
                outs[str(i)] = o
        valid = sorted(int(i) for i in outs)
        muts = [m for m in ti["mutants"] if only is None or m.mid in only.get(ti["id"], ())]
        hdr2 = {"mode": "diff", "entry": ti["entry"], "inputs": inputs, "base": outs}
        res = R.run_job(hdr2, [{"id": m.mid, "src": m.src, "idx": valid} for m in muts], AUDIT_TIMEOUT)
        per = {}
        for m in muts:
            r = res[m.mid]
            if "first_diff" in r:
                fd = r["first_diff"]
                per[m.mid] = {"verdict": "differs" if fd >= 0 else "no_difference",
                              "input": inputs[fd] if fd >= 0 else None,
                              "P_out": outs.get(str(fd)) if fd >= 0 else None, "mut_out": r.get("mut_out")}
            else:
                per[m.mid] = {"verdict": r.get("status", "load_error")}
        return ti["id"], {"n_inputs": len(inputs), "n_valid": len(valid), "mutants": per}

    out = dict(pmap(one, tasks, jobs))
    save(f"audit_seed{seed}.json", {"seed": seed, "wall_s": time.perf_counter() - t_start, "tasks": out})
    log(f"audit seed {seed} done in", round(time.perf_counter() - t_start, 1), "s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["repair", "survivors", "evaluate", "audit", "all"])
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--survivors-only", action="store_true",
                    help="audit only mutants that no sound suite kills (needs kill_matrix.json)")
    a = ap.parse_args()
    tasks = task_infos()
    log("tasks:", len(tasks), "mutants:", sum(len(t["mutants"]) for t in tasks))
    if a.stage in ("repair", "all"):
        repair(tasks, a.jobs)
    if a.stage == "survivors":
        survivors(tasks, load_kept(), a.jobs)
    if a.stage in ("evaluate", "all"):
        evaluate(tasks, load_kept(), a.jobs)
    if a.stage in ("audit", "all"):
        only = None
        if a.survivors_only:
            km = load("kill_matrix.json")
            only = {tid: {mid for mid in d["human"]["status"] if mid != "P"
                          and all(d[s]["status"][mid] == "pass" for s in SOUND)} for tid, d in km.items()}
        audit(tasks, load_kept(), a.seed, a.jobs, only)


if __name__ == "__main__":
    main()

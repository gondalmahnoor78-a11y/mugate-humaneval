"""Generate the LaTeX tables of the paper from results/summary.json (no hand-typed numbers)."""
import json

from .dataset import ROOT
from .mutation import ALL_OPS, GATE_OPS
from .suites import WEAKENINGS

RES, OUT = ROOT / "results", ROOT / "paper" / "tables"
DESC = {"AOR": r"Arithmetic operator replacement (\texttt{+}$\leftrightarrow$\texttt{-}, \texttt{*}$\leftrightarrow$\texttt{/}, \texttt{//}$\to$\texttt{/}, \texttt{\%}$\to$\texttt{//}, \texttt{**}$\to$\texttt{*})",
        "ROR": r"Relational operator replacement (\texttt{<}$\to$\texttt{<=}/\texttt{>}, \texttt{==}$\leftrightarrow$\texttt{!=}, \texttt{in}$\leftrightarrow$\texttt{not in}, \dots)",
        "LCR": r"Logical connector replacement (\texttt{and}$\leftrightarrow$\texttt{or})",
        "UOD": r"Unary operator deletion (\texttt{not}, unary \texttt{-})",
        "CND": r"Condition negation (\texttt{if}, \texttt{while}, ternary, comprehension filter)",
        "CRP": r"Constant replacement ($c\pm1$, Boolean flip, string $\to$ \texttt{\textquotesingle\textquotesingle})",
        "RVR": r"Return value replacement ($\to$ \texttt{None})",
        "SDL": r"Statement deletion (assignment/expression $\to$ \texttt{pass})",
        "BCR": r"\texttt{break}$\leftrightarrow$\texttt{continue}"}
SNAME = {"human": "Human (reference)", "vanilla": "Agent, vanilla", "blind": "Agent, +blind",
         "gate": "Agent, +gate R1"}


def sgn(x):
    """Signed number for text or math mode (true minus sign); exact zero printed without sign."""
    if abs(x) < 0.05:
        return "\\ensuremath{0.0}"
    return "\\ensuremath{" + f"{x:+.1f}" + "}"


def pct(x, d=1):
    return f"{100 * x:.{d}f}"


def write(name, body):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.tex").write_text(body, encoding="utf-8")


def main():
    S = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    su, g = S["suites"], S["gate_round"]

    # Table: dataset and mutant statistics
    sc = S["survivor_classes"]
    rows = [("HumanEval tasks in sample (seed 42)", f"{S['n_tasks']} / 164"),
            ("Agent cases written / kept after assertion repair (vanilla)", f"{S['repair']['vanilla']['raw']} / {S['repair']['vanilla']['kept']}"),
            ("Agent cases written / kept (blind augmentation)", f"{S['repair']['blind']['raw']} / {S['repair']['blind']['kept']}"),
            ("Agent cases written / kept (gate round 1)", f"{S['repair']['gate']['raw']} / {S['repair']['gate']['kept']}"),
            ("First-order mutants generated (all operators)", f"{S['n_mutants']}"),
            (r"\quad gate group (AOR, ROR, LCR, UOD, CND)", f"{S['n_gate_mutants']}"),
            (r"\quad held-out group (CRP, RVR, SDL, BCR)", f"{S['n_held_mutants']}"),
            ("Mutants surviving all four sound suites", f"{S['n_survivors']}"),
            (r"\quad equivalent (no difference on any audit input)", f"{sc.get('equivalent_audit', 0)}"),
            (r"\quad equivalent under the documented precondition", f"{sc.get('equivalent_precondition', 0)}"),
            (r"\quad killable (valid distinguishing input found)", f"{sc.get('killable', 0)}"),
            ("Killable mutants (adjusted denominator)", f"{S['n_killable']} ({pct(S['n_killable'] / S['n_mutants'])}\\%)")]
    body = "\\begin{tabular}{@{}lr@{}}\n\\toprule\nStatistic & Value\\\\\n\\midrule\n"
    body += "".join(f"{a} & {b}\\\\\n" for a, b in rows) + "\\bottomrule\n\\end{tabular}\n"
    write("tab_dataset", body)

    # Table: operators
    body = "\\begin{tabular}{@{}llp{6.3cm}rrr@{}}\n\\toprule\nOp. & Group & Mutation & Gen. & Killable & Surv.\\\\\n\\midrule\n"
    for op in ALL_OPS:
        body += (f"{op} & {'gate' if op in GATE_OPS else 'held-out'} & {DESC[op]} & {S['mutants_by_op'].get(op, 0)} & "
                 f"{S['killable_by_op'].get(op, 0)} & {S['survivors_by_op'].get(op, 0)}\\\\\n")
    body += "\\bottomrule\n\\end{tabular}\n"
    write("tab_operators", body)

    # Table: RQ1 main results
    cov = S["coverage"]
    ncases = {"human": "--", "vanilla": g["vanilla_cases_total"], "blind": g["vanilla_cases_total"] + g["blind_extra_cases_total"],
              "gate": g["vanilla_cases_total"] + g["extra_cases_total"]}
    body = ("\\begin{tabular}{@{}lrrrrrrr@{}}\n\\toprule\n"
            "Suite & Cases & Killed & Adj.\\ MS (\\%) & 95\\% CI & Raw MS & Line cov. & Perfect\\\\\n"
            " &  & /" + str(S["n_killable"]) + " &  & (bootstrap) & (\\%) & (\\%) & tasks\\\\\n\\midrule\n")
    for s in ["human", "vanilla", "blind", "gate"]:
        a = su[s]["adj"]
        body += (f"{SNAME[s]} & {ncases[s]} & {a['killed']} & {pct(a['ms'])} & [{pct(a['ci95'][0])}, {pct(a['ci95'][1])}] & "
                 f"{pct(su[s]['raw']['ms'])} & {pct(cov[s]['mean'])} & {su[s]['tasks_perfect']}/{S['n_tasks']}\\\\\n")
    body += "\\bottomrule\n\\end{tabular}\n"
    write("tab_rq1", body)

    # Table: paired comparisons
    lab = {"vanilla-human": "Vanilla $-$ Human", "blind-vanilla": "Blind $-$ Vanilla", "gate-vanilla": "Gate R1 $-$ Vanilla",
           "gate-blind": "Gate R1 $-$ Blind", "gate-human": "Gate R1 $-$ Human", "blind-human": "Blind $-$ Human"}
    body = ("\\begin{tabular}{@{}lrrrrr@{}}\n\\toprule\nComparison & $\\Delta$ MS (pp) & 95\\% CI (pp) & Tasks +/$-$ & "
            "Wilcoxon $p$ & Sign $p$\\\\\n\\midrule\n")
    for k in ["vanilla-human", "blind-vanilla", "gate-vanilla", "gate-blind", "gate-human"]:
        c = S["comparisons"][k]
        body += (f"{lab[k]} & {sgn(c['diff_pp'])} & [{sgn(c['ci95_pp'][0])}, {sgn(c['ci95_pp'][1])}] & "
                 f"{c['tasks_better']}/{c['tasks_worse']} & {c['wilcoxon_p']:.3f} & {c['sign_p']:.3f}\\\\\n")
    body += "\\bottomrule\n\\end{tabular}\n"
    write("tab_comparisons", body)

    # Table: gate vs held-out
    body = ("\\begin{tabular}{@{}lrrr@{}}\n\\toprule\nSuite & Gate MS (\\%) & Held-out MS (\\%) & $\\Delta_{gate}$ (pp)\\\\\n"
            f" & (/{su['human']['adj_gate']['total']}) & (/{su['human']['adj_held']['total']}) & \\\\\n\\midrule\n")
    for s in ["human", "vanilla", "blind", "gate"]:
        body += (f"{SNAME[s]} & {pct(su[s]['adj_gate']['ms'])} & {pct(su[s]['adj_held']['ms'])} & "
                 f"{sgn(100 * su[s]['delta_gate'])}\\\\\n")
    body += "\\bottomrule\n\\end{tabular}\n"
    write("tab_heldout", body)

    # Table: RQ2 weakening
    body = ("\\begin{tabular}{@{}llrr@{}}\n\\toprule\nID & Transformation of the sound vanilla cases & Adj.\\ MS (\\%) & "
            "Raw MS (\\%)\\\\\n\\midrule\n")
    body += f"-- & none (sound vanilla suite) & {pct(su['vanilla']['adj']['ms'])} & {pct(su['vanilla']['raw']['ms'])}\\\\\n"
    for w in sorted(WEAKENINGS, key=lambda x: -su[x]["adj"]["ms"]):
        d, _ = WEAKENINGS[w]
        d = d.replace("==", "$==$").replace("_", "\\_")
        body += f"{w} & {d} & {pct(su[w]['adj']['ms'])} & {pct(su[w]['raw']['ms'])}\\\\\n"
    body += "\\bottomrule\n\\end{tabular}\n"
    write("tab_rq2", body)

    # Table: RQ3 cost
    c = S.get("cost") or {}
    gb, gi, gp = c.get("gate_check_batched", {}), c.get("gate_check_isolated", {}), c.get("suite_on_P_only", {})
    rows = [("Tasks with $\\geq$1 surviving gate mutant shown", f"{g['tasks_with_survivors_shown']} / {S['n_tasks']}"),
            ("Surviving gate mutants shown to the agent", f"{g['survivors_shown']}"),
            (r"\quad of which killable (non-equivalent)", f"{g['shown_killable']}"),
            (r"\quad of which killed after round 1", f"{g['shown_killed_after']}"),
            ("Tasks in which the agent added cases", f"{g['tasks_revised']} / {S['n_tasks']}"),
            ("Cases added in round 1 (total / per task)", f"{g['extra_cases_total']} / {g['extra_cases_per_task']:.2f}"),
            ("Cases added by blind augmentation (total)", f"{g['blind_extra_cases_total']}")]
    if gb:
        rows += [("Suite run on $P$ only, mean per task (s)", f"{gp['mean_per_task_s']:.3f}"),
                 ("Gate check, warm batched worker, mean per task (s)", f"{gb['mean_per_task_s']:.3f}"),
                 ("Gate check, one interpreter per mutant, mean per task (s)", f"{gi['mean_per_task_s']:.3f}"),
                 ("Median single suite execution inside the worker (ms)", f"{S['exec_time_median_ms']:.2f}")]
    body = "\\begin{tabular}{@{}lr@{}}\n\\toprule\nQuantity & Value\\\\\n\\midrule\n"
    body += "".join(f"{a} & {b}\\\\\n" for a, b in rows) + "\\bottomrule\n\\end{tabular}\n"
    write("tab_rq3", body)
    write_numbers(S)
    print("tables written to", OUT)


def write_numbers(S):
    """paper/numbers.tex: one macro per number used in the running text."""
    su, g, cm, rp = S["suites"], S["gate_round"], S["comparisons"], S["repair"]
    m = {}
    m["nTasks"] = S["n_tasks"]
    m["nMut"], m["nGateMut"], m["nHeldMut"] = S["n_mutants"], S["n_gate_mutants"], S["n_held_mutants"]
    m["nKillable"] = S["n_killable"]
    m["pctKillable"] = pct(S["n_killable"] / S["n_mutants"])
    m["nSurv"] = S["n_survivors"]
    sc = S["survivor_classes"]
    m["nEqAudit"], m["nEqPre"], m["nSurvKillable"] = sc.get("equivalent_audit", 0), sc.get("equivalent_precondition", 0), sc.get("killable", 0)
    words = {"human": "Human", "vanilla": "Vanilla", "blind": "Blind", "gate": "Gate"}
    for s, w in words.items():
        d = su[s]
        m[f"ms{w}"] = pct(d["adj"]["ms"])
        m[f"killed{w}"] = d["adj"]["killed"]
        m[f"lo{w}"], m[f"hi{w}"] = pct(d["adj"]["ci95"][0]), pct(d["adj"]["ci95"][1])
        m[f"raw{w}"] = pct(d["raw"]["ms"])
        m[f"msGateGrp{w}"], m[f"msHeldGrp{w}"] = pct(d["adj_gate"]["ms"]), pct(d["adj_held"]["ms"])
        m[f"delta{w}"] = sgn(100 * d["delta_gate"])
        m[f"perfect{w}"] = d["tasks_perfect"]
    for k, w in {"vanilla-human": "VanHum", "blind-vanilla": "BliVan", "gate-vanilla": "GatVan", "gate-blind": "GatBli",
                 "gate-human": "GatHum"}.items():
        c = cm[k]
        m[f"d{w}"] = sgn(c["diff_pp"])
        m[f"ciLo{w}"], m[f"ciHi{w}"] = sgn(c["ci95_pp"][0]), sgn(c["ci95_pp"][1])
        m[f"pW{w}"], m[f"pS{w}"] = f"{c['wilcoxon_p']:.3f}", f"{c['sign_p']:.3f}"
        m[f"up{w}"], m[f"down{w}"] = c["tasks_better"], c["tasks_worse"]
        m[f"onlyA{w}"], m[f"onlyB{w}"] = c["mutants_only_a"], c["mutants_only_b"]
    for w, name in zip(["W1", "W2", "W3", "W4", "W5", "W6", "W7"], ["One", "Two", "Three", "Four", "Five", "Six", "Seven"]):
        m[f"msW{name}"] = pct(su[w]["adj"]["ms"])
    m["covMean"] = pct(S["coverage"]["vanilla"]["mean"])
    m["covFull"] = S["coverage"]["vanilla"]["tasks_full"]
    fc = S["vanilla_full_coverage_but_ms_below_1"]
    m["nFullCovImperfect"] = len(fc)
    m["worstTask"] = fc[0]["task"] if fc else "--"
    m["worstMS"] = pct(fc[0]["ms"]) if fc else "--"
    m["pearsonCovMs"] = "\\ensuremath{" + f"{S['vanilla_cov_ms_pearson']:.2f}" + "}"
    m["casesVanillaRaw"], m["casesVanillaKept"] = rp["vanilla"]["raw"], rp["vanilla"]["kept"]
    m["casesBlindRaw"], m["casesBlindKept"] = rp["blind"]["raw"], rp["blind"]["kept"]
    m["casesGateRaw"], m["casesGateKept"] = rp["gate"]["raw"], rp["gate"]["kept"]
    raw_all = sum(rp[r]["raw"] for r in rp)
    kept_all = sum(rp[r]["kept"] for r in rp)
    m["casesAllRaw"], m["casesDropped"] = raw_all, raw_all - kept_all
    m["repairRate"] = pct((raw_all - kept_all) / raw_all)
    m["tasksShown"], m["survShown"], m["survShownKillable"] = g["tasks_with_survivors_shown"], g["survivors_shown"], g["shown_killable"]
    m["survShownKilled"], m["tasksRevised"], m["gateCases"] = g["shown_killed_after"], g["tasks_revised"], g["extra_cases_total"]
    m["gateCasesPerTask"] = f"{g['extra_cases_per_task']:.2f}"
    m["blindCases"] = g["blind_extra_cases_total"]
    m["execMedianMs"] = f"{S['exec_time_median_ms']:.2f}"
    m["evalWallMin"] = f"{S['evaluate_meta']['wall_s'] / 60:.1f}"
    m["nTimeouts"] = S["evaluate_meta"]["runner_stats"]["timeouts"]
    c = S.get("cost")
    if c:
        gb, gi, gp = c["gate_check_batched"], c["gate_check_isolated"], c["suite_on_P_only"]
        m["costBase"] = f"{gp['mean_per_task_s']:.3f}"
        m["costBatched"] = f"{gb['mean_per_task_s']:.3f}"
        m["costIsolated"] = f"{gi['mean_per_task_s']:.3f}"
        m["costRatio"] = f"{gi['mean_per_task_s'] / gb['mean_per_task_s']:.1f}"
        m["costOverBase"] = f"{gb['mean_per_task_s'] / gp['mean_per_task_s']:.1f}"
        sc1, sc2 = c["scaling_human_suite_all_mutants_s"]["1"], c["scaling_human_suite_all_mutants_s"]["2"]
        a1, a2 = sum(sc1) / len(sc1), sum(sc2) / len(sc2)
        m["scaleOne"], m["scaleTwo"], m["speedup"] = f"{a1:.1f}", f"{a2:.1f}", f"{a1 / a2:.2f}"
        m["cpuName"] = "AMD Athlon Silver 3050U"
    lines = ["% Auto-generated by mugate/make_tables.py from results/summary.json. Do not edit by hand.\n"]
    for k, v in m.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    (ROOT / "paper" / "numbers.tex").write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

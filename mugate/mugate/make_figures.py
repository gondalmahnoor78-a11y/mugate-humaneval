"""Generate all data figures (PDF for LaTeX, PNG for preview) from results/summary.json and
results/per_task.csv. Every plotted number is read from those files."""
import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .dataset import ROOT  # noqa: E402
from .mutation import ALL_OPS, GATE_OPS  # noqa: E402

RES, FIG, PAPER_FIG = ROOT / "results", ROOT / "figures", ROOT / "paper" / "figures"
plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
SUITE_LABEL = {"human": "Human\n(reference)", "vanilla": "Agent\nvanilla", "blind": "Agent\n+blind", "gate": "Agent\n+gate (R1)"}
GREYS = ["#d9d9d9", "#a6a6a6", "#6e6e6e", "#2b2b2b"]


def save(fig, name):
    FIG.mkdir(exist_ok=True)
    PAPER_FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=300)
    fig.savefig(PAPER_FIG / f"{name}.pdf")  # copy used by paper/main.tex
    plt.close(fig)


def main():
    S = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    su = S["suites"]
    sound = ["human", "vanilla", "blind", "gate"]

    # Fig 2: adjusted MS with bootstrap CI
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    ms = [100 * su[s]["adj"]["ms"] for s in sound]
    lo = [100 * su[s]["adj"]["ci95"][0] for s in sound]
    hi = [100 * su[s]["adj"]["ci95"][1] for s in sound]
    ax.bar(range(4), ms, color=GREYS, edgecolor="black", linewidth=0.6, width=0.62)
    ax.errorbar(range(4), ms, yerr=[[m - l for m, l in zip(ms, lo)], [h - m for m, h in zip(ms, hi)]],
                fmt="none", ecolor="black", capsize=3, linewidth=0.8)
    for i, m in enumerate(ms):
        ax.text(i, hi[i] + 0.25, f"{m:.1f}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(4), [SUITE_LABEL[s] for s in sound], fontsize=7.5)
    ymin = max(0, min(lo) - 4)
    ax.set_ylim(ymin, 101.5)
    ax.set_ylabel("Adjusted mutation score (%)")
    save(fig, "fig2_ms_by_suite")

    # Fig 3: gate vs held-out
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    w = 0.36
    g = [100 * su[s]["adj_gate"]["ms"] for s in sound]
    h = [100 * su[s]["adj_held"]["ms"] for s in sound]
    ax.bar([i - w / 2 for i in range(4)], g, w, color="#3b3b3b", edgecolor="black", linewidth=0.6, label="gate group (shown)")
    ax.bar([i + w / 2 for i in range(4)], h, w, color="white", edgecolor="black", hatch="////", linewidth=0.6,
           label="held-out group (never shown)")
    for i in range(4):
        ax.text(i - w / 2, g[i] + 0.2, f"{g[i]:.1f}", ha="center", va="bottom", fontsize=6.5)
        ax.text(i + w / 2, h[i] + 0.2, f"{h[i]:.1f}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(range(4), [SUITE_LABEL[s] for s in sound], fontsize=7.5)
    ax.set_ylim(max(0, min(g + h) - 5), 101.5)
    ax.set_ylabel("Adjusted mutation score (%)")
    ax.legend(fontsize=6.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    save(fig, "fig3_gate_vs_heldout")

    # Fig 4: weakening operators
    weak = ["W6", "W7", "W4", "W1", "W2", "W3", "W5"]
    names = {"W1": "W1 no-oracle", "W2": "W2 tautological", "W3": "W3 type-only", "W4": "W4 exception-swallowing",
             "W5": "W5 test deletion", "W6": "W6 skipped tests", "W7": "W7 mocked-out unit"}
    vals = [100 * su[x]["adj"]["ms"] for x in weak]
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ax.barh(range(len(weak)), vals, color="#8c8c8c", edgecolor="black", linewidth=0.6, height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.1f}", va="center", fontsize=7)
    ref = 100 * su["vanilla"]["adj"]["ms"]
    ax.axvline(ref, ls="--", color="black", lw=0.9)
    ax.text(ref - 1.5, 0.2, f"sound vanilla\nsuite ({ref:.1f})", ha="right", va="center", fontsize=6.5)
    ax.set_yticks(range(len(weak)), [names[x] for x in weak], fontsize=7.5)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Adjusted mutation score (%)")
    save(fig, "fig4_weakening")

    # Fig 5: survival rate by operator for the sound suites
    tot = S["killable_by_op"]
    ops = [op for op in ALL_OPS if tot.get(op, 0) > 0]  # operators with no killable mutant in the sample are omitted
    fig, ax = plt.subplots(figsize=(4.8, 2.3))
    w = 0.2
    for k, s in enumerate(sound):
        rates = []
        for op in ops:
            d = su[s]["by_op"][op]
            rates.append(100 * (1 - d["killed"] / d["total"]) if d["total"] else 0)
        ax.bar([i + (k - 1.5) * w for i in range(len(ops))], rates, w, color=GREYS[k], edgecolor="black",
               linewidth=0.5, label=SUITE_LABEL[s].replace("\n", " "))
    ax.set_xticks(range(len(ops)), [f"{op}\nn={tot.get(op, 0)}" for op in ops], fontsize=7)
    n_gate = sum(1 for op in ops if op in GATE_OPS)
    ax.axvline(n_gate - 0.5, color="black", lw=0.8, ls=":")
    ymax = ax.get_ylim()[1] * 1.25
    ax.set_ylim(0, ymax)
    ax.text((n_gate - 1) / 2, ymax * 0.98, "gate group (shown)", ha="center", va="top", fontsize=7)
    ax.text(n_gate + (len(ops) - n_gate - 1) / 2, ymax * 0.98, "held-out group (never shown)", ha="center", va="top", fontsize=7)
    ax.set_ylabel("Surviving killable\nmutants (%)")
    ax.legend(fontsize=6.5, frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    save(fig, "fig5_survival_by_operator")

    # Fig 6: coverage vs mutation score per task (vanilla)
    rows = list(csv.DictReader(open(RES / "per_task.csv", encoding="utf-8")))
    xs = [100 * float(r["cov_vanilla"]) for r in rows if r["ms_vanilla"]]
    ys = [100 * float(r["ms_vanilla"]) for r in rows if r["ms_vanilla"]]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    from collections import Counter
    cnt = Counter((round(x, 1), round(y, 1)) for x, y in zip(xs, ys))
    pts = list(cnt)
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=[14 if cnt[p] == 1 else 30 for p in pts],
               facecolor=["white" if cnt[p] == 1 else "black" for p in pts], edgecolor="black", linewidth=0.7)
    for p in pts:
        if cnt[p] > 1:
            ax.annotate(f"{cnt[p]} tasks", p, xytext=(-6, 0), textcoords="offset points", ha="right", va="center", fontsize=6.5)
    ax.set_xlabel("Line coverage of solver-written code (%)")
    ax.set_ylabel("Adjusted mutation score (%)")
    ax.set_xlim(min(xs) - 5, 101.5)
    ax.set_ylim(min(ys) - 5, 102)
    save(fig, "fig6_coverage_vs_ms")
    print("figures written to", FIG)


if __name__ == "__main__":
    main()

# MuGate: a mutation-guided quality gate for LLM-authored unit tests (verified rebuild)

This folder contains the complete, re-runnable pipeline behind the Springer paper in `paper/`.
Every number, table and figure in the paper is generated from the files in `results/` by the
scripts below; nothing is typed in by hand.

## Requirements

* Python 3.12 (tested with CPython 3.12.10 on Windows 11; the runner also supports Linux/macOS).
* Standard library only for the experiments. `matplotlib==3.9.2` is needed only for figures.
* CPU only. No GPU is used or useful (see `reports/GPU_CPU_REPORT.md`).
* `data/HumanEval.jsonl.gz` from https://github.com/openai/human-eval
  (SHA-256 `B796127E635A67F93FB35C04F4CB03CF06F38C8072EE7CEE8833D7BEE06979EF`).

## Reproduce (about 20-30 min on a 2-core laptop)

```
python -m mugate.stage_prompts                 # agent_tests/PROMPTS.md (prompts only)
python -m mugate.pipeline repair               # assertion repair -> results/repair.json
python -m mugate.pipeline survivors            # agent_tests/SURVIVORS.md (feedback for round 1)
python -m mugate.pipeline evaluate             # results/kill_matrix.json, coverage.json, mutants.json
python -m mugate.pipeline audit --seed 0       # equivalence audit, all mutants
python -m mugate.pipeline audit --seed 1 --survivors-only   # repeat for seeds 1..4
python -m mugate.cost                          # results/cost.json (RQ3 cost, CPU scaling)
python -m mugate.analyze                       # results/summary.json, results/per_task.csv
python -m mugate.make_figures                  # figures/*.pdf, figures/*.png
python -m mugate.make_tables                   # paper/tables/*.tex
```

## Layout

| Path | Content |
|---|---|
| `mugate/dataset.py` | HumanEval loading, seeded 50-task sample (seed 42), mutable lines |
| `mugate/mutation.py` | 9 AST mutation operators; gate group AOR/ROR/LCR/UOD/CND, held-out CRP/RVR/SDL/BCR |
| `mugate/worker.py`, `mugate/runner.py` | sandboxed execution: `python -I` worker, per-item watchdog timeout (2 s), 1 GiB memory cap, restart on timeout/crash |
| `mugate/suites.py` | rendering of suites; weakening operators W1-W7 |
| `mugate/perturb.py` | input perturbation for the differential equivalence audit |
| `mugate/pipeline.py` | stages repair / survivors / evaluate / audit |
| `mugate/analyze.py`, `mugate/stats.py` | all reported statistics (bootstrap CIs, Wilcoxon, sign test) |
| `mugate/cost.py` | gate overhead (batched vs isolated) and 1 vs 2 worker scaling |
| `agent_tests/` | prompts given to the agent, the agent's cases per round, survivor feedback |
| `analysis/equivalence_labels.json` | manual, justified labels for audit-distinguishable survivors |
| `results/` | raw and summarised outputs |
| `reports/` | technical audit, GPU/CPU report, old-vs-new comparison, consistency checklist |

## Who wrote the agent tests

The agent-authored cases in `agent_tests/` were written by Claude (Anthropic), acting as the
test-writing agent, from `PROMPTS.md` only (vanilla, blind), and from `SURVIVORS.md` (round 1).
The same model instance also built the pipeline; see the threats-to-validity section of the
paper for the consequences of this design.

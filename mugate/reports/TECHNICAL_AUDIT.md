# Technical audit of the MuGate project (Assignment #03)

Date of audit: 23 November 2026. Auditor: Claude (Anthropic), working in Claude Code.

## 1. What was provided

| Item | Location | Status |
|---|---|---|
| Paper draft (IEEE-style, 10 pages) | `RM/26i-7825 Assignment#03.pdf` | read in full |
| LaTeX source of the draft | `RM/main.tex`, `RM/MuGate_LaTeX_Report.zip` | zip holds `main.tex` + 3 PNG figures (Fig. 2-4) |
| Source code, data, results | none in `RM/` | **missing** |
| Repository cited in the paper | `github.com/gondalmahnoor78-a11y/26i-7825-mugate` | **HTTP 404: the repository does not exist or is private** |
| Only public repository of the account | `github.com/gondalmahnoor78-a11y/mutgate` (2 commits, 7 Nov 2026) | inspected file by file |

## 2. Critical finding: the draft's results cannot be traced to any code

The draft reports a study on **50 HumanEval tasks** with **Claude-written tests**, **827 raw / 778
killable mutants**, **nine operators with a gate/held-out split**, `survivors.py`,
`equivalence_audit.py`, `agent_tests/`, `results/analysis.json`, `mugate/mutation.py`,
`mugate/worker.py` and `mugate/runner.py`.

None of these files exists in anything provided. The public `mutgate` repository implements a
**different study**:

| Aspect | Paper draft claims | `mutgate` repository actually implements |
|---|---|---|
| Benchmark | 50 HumanEval tasks (seed 42) | 12 hand-written toy tasks (`tasks.py`: leap year, clamp, fizzbuzz, ...) |
| Who writes the tests | Claude, from prompt only | **No LLM at all.** README: "Suites modelling agent behaviour are constructed programmatically; no LLM was run." |
| Operators | 9 (AOR, ROR, LCR, UOD, CND / CRP, RVR, SDL, BCR) | 8 (AOR, ROR, COR, NEG, CRP, RVR, SDL, ASR), no gate/held-out split |
| Gate threshold | tau = 1.0 | tau = 0.7 |
| Main metric | adjusted mutation score | false-acceptance rate of wrong patches |
| Revision | agent writes new cases from survivors | "oracle-assisted revision": picks *human* test cases |
| Results file | `results/analysis.json` | `results.json` (none of the draft's numbers appear in it) |
| Execution | `python3 -I` subprocess per run, 2 GB limit | in-process `exec`, `SIGALRM` timer (Linux-only; does not run on Windows) |

**None** of the draft's headline numbers (96.5 %, 97.3 %, 97.9 %, 100 %, 778/827, 22.6 %, 3.6 %,
0.28 s, 353 cases, 2 repaired cases, 49 equivalent mutants) can be reproduced from, or found in,
any provided artefact. The three PNG figures in the zip show those numbers, but the code that
produced them was not provided. I cannot tell whether that code exists elsewhere; on the evidence
available the draft's results are **unverifiable** and must not be submitted.

## 3. Problems in the `mutgate` repository (for completeness)

1. `harness.py` uses `signal.SIGALRM` / `setitimer` and fails on Windows.
2. `make_figures.py` and `experiments.py` write to `results/` and `figures/`, which are not in the repo;
   `results.json` sits at the root instead.
3. `build_paper.py` requires `python-docx`, which is not declared anywhere.
4. Agent behaviour is simulated by fixed rules (e.g. "snapshot" = expected values copied from the
   patch), so the study says nothing about real LLM-written tests.
5. On correct patches, `spec` and `snapshot` and `human` and `prune` are identical by construction,
   so several reported contrasts are tautological.
6. `revise()` draws cases from the hidden human suite. That is an oracle upper bound, not a
   mitigation an agent could apply.

## 4. Methodological weaknesses in the draft (even if its code existed)

1. **Circular denominator.** "Killable" was defined as "killed by at least one suite, including the
   gated suite itself", so the gated suite scores 100 % almost by definition. The draft
   acknowledged this only in a late caveat. *Fixed in the rebuild:* survivors stay in the
   denominator unless an independent differential audit finds no valid distinguishing input.
2. **No uncertainty.** No CIs, no tests, no seeds; differences of 0.8 pp were interpreted.
   *Fixed:* task-level cluster bootstrap (5 seeds x 10 000 resamples), Wilcoxon and sign tests.
3. **W6/W7 are 0 % by construction.** A skipped or mocked test never calls the unit, so
   its mutation score is 0 % by definition, not an empirical finding. *Fixed:* reported as sanity anchors.
4. **Unequal gate/held-out groups.** The operator split makes the held-out group mostly CRP mutants,
   so a gate/held-out difference mixes generalisation with operator difficulty. *Kept, but now discussed.*
5. **Cost claim unmeasured.** "Two to three orders of magnitude" faster batching was asserted, not measured.
   *Fixed:* batched vs isolated execution measured on this machine.
6. **Coverage claim.** "Collapse mutation score while leaving coverage unaffected" is false for W6/W7
   (they execute nothing). *Corrected.*
7. **Experimenter = agent.** The same model wrote the tests and designed the study. *Disclosed as a
   threat to validity, with blinding by stage.*

## 5. What the rebuilt pipeline implements (verified by running it)

* `mugate/` package: 9 AST operators restricted to solver-written lines; sandboxed `python -I`
  workers with a 2 s watchdog and a 1 GiB Job-Object memory cap; assertion repair; survivor
  feedback; evaluation of 4 sound suites and 7 weakened suites against all 883 mutants; line
  coverage; differential equivalence audit with 5 input seeds; bootstrap statistics.
* Agent tests written by Claude in three blinded stages (prompts only, then survivors only).
* Everything reported in the new paper is produced by `analyze.py`, `make_tables.py`, `make_figures.py`.

## 6. What remains out of scope or unverifiable

* The draft's original results (see Section 2).
* The full agentic loop (the agent writing both patch and tests): not implemented, as in the draft.
* Other models and benchmarks: a single agent (Claude) on 50 HumanEval tasks.

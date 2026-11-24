# Previously reported vs newly verified results

**Important.** The "previous" numbers come from the draft PDF. No code or data that produced them
was provided (see `TECHNICAL_AUDIT.md`), so they could not be re-run. The "new" numbers come from the
rebuilt pipeline in this folder, re-run end to end on 23 Nov 2026, and are reproducible with the
commands in `README.md`. The two studies share the design (50 HumanEval tasks, seed 42, Claude as
test writer, 9 operators, gate/held-out split, 7 weakenings), so the comparison is meaningful at the
level of conclusions, but **the task sample, mutants and agent-written cases are not identical**.
The draft's sample cannot be reconstructed, because its task list was never published.

| Quantity | Draft (unverifiable) | Verified rebuild | Comment |
|---|---|---|---|
| Tasks | 50 | 50 | seed 42 via `random.sample(range(164), 50)`; draft's exact list unknown |
| Raw mutants | 827 | 883 | different operator details / sample |
| Killable (adjusted denominator) | 778 (94.1 %) | 833 (94.3 %) | new denominator is independent of the evaluated suites |
| Survivors of all sound suites | 49 | 52 | |
| ...equivalent | 34 (no difference) + 15 (precondition) | 36 + 14 | |
| ...genuine faults missed by every suite | 0 | **2** | HumanEval/114 m023, HumanEval/129 m040 |
| Agent cases written / dropped by repair | 353 / 2 | 425 / 2 | |
| Human tests, adjusted MS | 97.3 % | 97.6 % [95.6, 99.1] | close |
| Vanilla agent, adjusted MS | 96.5 % | 96.3 % [93.3, 99.0] | close; difference to human not significant in either |
| Blind (+3 cases/task) | 97.9 % | **98.3 %** [96.6, 99.7] | now the best suite and the only significant gain (+2.0 pp, CI [0.3, 4.3]) |
| Gate round 1 | **100.0 %** | **97.6 %** [94.8, 99.5] | the draft's 100 % came from its circular denominator |
| Gate-group MS after round 1 | 100 % | 100 % | agrees |
| Held-out MS, vanilla to gate | 96.3 to **100.0 %** | 95.7 to **96.4 %** | **contradicts the draft**: feedback did not generalise to held-out mutants |
| Delta_gate before / after | +0.9 / 0.0 pp | -1.7 / -3.6 pp | sign convention identical (held minus gate) |
| Tasks revised in round 1 | 8 / 50 | 4 / 50 | |
| Extra assertions per task | 0.30 | 0.18 | |
| W1 no-oracle | 22.6 % | 22.2 % | agrees |
| W2 tautological | 22.6 % | 22.3 % | agrees |
| W3 type-only | 32.5 % | 31.8 % | agrees |
| W4 exception-swallowing | 3.6 % | 3.4 % | agrees |
| W5 keep one case | 66.8 % | 67.5 % | agrees |
| W6 / W7 | 0 % / 0 % | 0 % / 0 % | 0 % by construction in both |
| Tasks with full coverage but MS < 100 % (vanilla) | 8 | 9 | worst: HumanEval/40 at 73.3 % (draft) vs 75.0 % (new) |
| Mean line coverage | 99.8 % | 99.8 % | |
| Gate overhead per task | 0.28 s (unbatched) | 0.670 s batched, 2.173 s isolated, 0.158 s ungated baseline (laptop CPU) | the draft's "2-3 orders of magnitude" batching gain was not measured; the measured gain is 3.2x |
| Statistics | none | bootstrap CIs, Wilcoxon, sign test, 5 audit seeds, 5 bootstrap seeds | |

## Why the conclusions changed

1. **Denominator.** The draft counted a mutant as killable if *any* suite, including the gated suite,
   killed it. Survivors of all suites were removed. The gated suite could therefore only miss mutants
   that another suite killed, which pushed it towards 100 %. The rebuild keeps every survivor with a
   valid distinguishing input in the denominator and found two such genuine faults.
2. **Held-out generalisation.** In the rebuild the feedback round killed every killable gate mutant
   shown, but most held-out survivors are constant-replacement (CRP) mutants of a kind the agent never saw.
   The draft's claim that held-out mutants also reach 100 % does not reproduce.
3. **Blind augmentation** is stronger than the draft reported, and its gain is the only one with a
   confidence interval excluding zero.

## What did reproduce

* Agent tests are close to human tests on HumanEval (difference not significant).
* Weakening operators collapse mutation score in the same order with nearly identical values.
* Coverage is near-complete and uninformative about mutation score.
* One feedback round closes the gate group.

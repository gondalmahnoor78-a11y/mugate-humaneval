# Final consistency checklist

Status legend: [x] verified, [!] verified with a caveat, [ ] not done / not possible here.

## Code and execution
- [x] Pipeline runs end to end on this machine (Windows 11, CPython 3.12.10, standard library only).
- [x] Sandbox: every (program, suite) pair runs in a `python -I` worker with a 2 s watchdog and a 1 GiB memory cap; 237 timeouts and 0 crashes in the main run.
- [x] All four sound suites pass on every reference program P (checked in `analyze`/`evaluate`).
- [x] Assertion repair applied: 2 of 425 agent cases dropped, both listed in `results/repair.json`.
- [!] Determinism: a second full run reproduced 10 261 of 10 263 kill statuses (`results/determinism_check.json`). Both differences are timeout-borderline mutants in weakened suites (W2, W5); all sound-suite results, coverage and mutants were identical; the largest effect on a reported score is 0.1 pp (W2). Reported numbers come from run 1.
- [x] Equivalence audit repeated with 5 input seeds; identical classification of all 52 survivors.
- [x] Bootstrap repeated with 5 seeds; CI endpoints vary by at most 0.2 pp.
- [!] The agent (Claude) generated each suite once; sampling variance of the agent is not measured (stated as a threat).

## Numbers, tables, figures
- [x] Every number in the paper's running text comes from `paper/numbers.tex`, generated from `results/summary.json`.
- [x] Every results table (`paper/tables/*.tex`) is generated from `results/summary.json`.
- [x] Every data figure (`figures/*.pdf|png`, copied to `paper/figures/`) is generated from `results/summary.json` / `per_task.csv`.
- [!] Three numbers are typed in the text by hand (Sect. 8.5: "22 of 31", "20", "8" CRP survivors); checked against `summary.json` -> `suites.*.by_op`.
- [x] All tables and figures have captions and are referenced and discussed in the text.
- [x] Figure 1 (workflow) matches the implemented stages (repair, survivors, evaluate, audit) and parameters (2 s, 1 GiB, R = 1).
- [x] Abstract numbers = macros = tables (same source).
- [x] Conclusion answers RQ1-RQ3 and states H1 (not supported), H2 (supported), H3 (not supported).

## References
- [x] All 18 draft references exist (arXiv / Crossref); 2 bibliographic errors corrected (MutGen title, Deljouyi pages).
- [x] 4 references added (Jia & Harman 2011; Papadakis et al. 2019; Just et al. 2014; Liu et al. 2023), each verified by DOI.
- [x] Claims about cited work in the paper are limited to what the arXiv abstracts / well-known contributions state.
- [!] The draft quoted specific numbers from MutGen (89.5 %/89.1 %) and SWE Atlas (10-15 points, quoted phrases) that are not in the abstracts; they were removed from the new paper rather than repeated unverified.

## Format
- [x] Springer LNCS class (`llncs`), `splncs04` bibliography style, abstract < 250 words, keywords with `\and`.
- [x] Section order follows the requested 16-part structure (Research Gap, Objectives/RQs, Architecture, Threats as separate sections).
- [x] LaTeX lint: all macros defined, braces and environments balanced, all `\cite` keys in `refs.bib`, all `\ref` labels defined.
- [ ] **Not compiled here** (no LaTeX installed, by your choice). Compile on Overleaf with the official Springer LNCS template and check page breaks and float placement.

## Items you must complete before submission
- [x] Repository URL inserted in the Data availability paragraph: https://github.com/gondalmahnoor78-a11y/mugate-humaneval
- [ ] Re-upload the repository with its folder structure (24 Nov 2026 upload is flat: all 61 files at the top level, `paper/tables/*.tex` and `paper/figures/fig1_workflow.tex` missing), so that the README commands run.
- [ ] Confirm author details and affiliation (Dr. Akhtar Jamil's e-mail and ORCID are not in the draft).
- [ ] Decide how to present the use of Claude as both experimenter and test-writing agent to your supervisor and venue (disclosed in Sect. 10).
- [ ] Do not reuse any number from the old draft: it cannot be traced to code (see `TECHNICAL_AUDIT.md`).

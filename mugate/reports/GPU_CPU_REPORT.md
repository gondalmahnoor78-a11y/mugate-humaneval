# Does MuGate need a GPU?

**Short answer: no.** Neither the experiments nor the method benefit from a GPU, and none was used.
The draft's statement "no GPU; none of the methods evaluated require one" is correct; this report
backs it with measurements.

## Hardware and software used

| Item | Value |
|---|---|
| CPU | AMD Athlon Silver 3050U, 2 cores / 2 threads |
| RAM | 3.4 GB |
| GPU | AMD Radeon integrated graphics (no CUDA; not used) |
| OS / Python | Windows 11 Home 10.0.22631, CPython 3.12.10 |
| Dependencies | standard library only (matplotlib 3.9.2 for figures) |

## What the workload actually is

1. **Mutant generation:** parsing and unparsing small ASTs, milliseconds in total.
2. **Test execution:** about 10 000 executions of a short Python program plus a short test function
   (50 tasks x 11 suites x 884 programs). Each execution is CPython bytecode interpretation:
   branches, dictionary and list operations, string handling and recursion.
3. **Equivalence audit:** the same kind of execution on up to 400 inputs per mutant.
4. **Statistics:** bootstrap over 50 tasks (5 x 10 000 resamples of 50 integers), well under a second.
5. **Test writing:** done by the LLM agent as a hosted service; no local inference.

GPUs accelerate large, regular numerical computations (matrix/tensor operations) on thousands of
simple cores. CPython bytecode cannot run on a GPU, and the workload has no tensor
computation to offload. Rewriting the HumanEval functions for a GPU would change the programs under
test and invalidate the experiment.

## Measurements (`results/cost.json`, 3 repetitions each)

| Measurement | Result |
|---|---|
| Median duration of one suite execution inside a warm worker | 0.63 ms |
| Run the agent suite once on P (ungated pipeline), per task | 0.158 s |
| Gate check, all gate mutants in one warm worker, per task | 0.670 s |
| Gate check, one fresh interpreter per mutant, per task | 2.173 s (3.2x slower than batched) |
| Human suite against all 883 mutants, 1 worker process | 124.5 s |
| Same, 2 worker processes | 68.2 s (speed-up 1.82 on 2 cores) |
| Full evaluation (11 suites x 884 programs x 50 tasks), 2 workers | 10.9 min |
| Equivalence audit, all mutants, seed 0 | 7.0 min |

Interpretation:

* A single test execution takes under a millisecond; time is dominated by **process start-up**
  (each worker is a fresh, isolated interpreter) and by the **2 s timeouts** of the 237 non-terminating
  mutant runs. Neither cost depends on arithmetic throughput.
* The workload is **embarrassingly parallel across mutants** and scales almost linearly with CPU
  processes (1.82x on 2 cores). On a machine with *k* cores the expected wall time is roughly the
  measured time x 2/*k*.
* The draft claimed that batching would reduce the overhead "by roughly two to three orders of
  magnitude". The measured gain from batching is **3.2x**, because the timeouts of looping mutants
  do not shrink with batching. The rewritten paper reports the measured value.

## Conclusion

A GPU would give no speed-up and would add an unjustified hardware requirement. The scientifically
relevant scaling dimension is the number of CPU processes, which the paper reports. The whole study
reproduces in about 20 minutes on a low-end two-core laptop.

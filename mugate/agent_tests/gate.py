"""Agent-authored test cases, feedback round 1 (MuGate gate).

Author: Claude (Anthropic) acting as the test-writing agent. Information available: PROMPTS.md,
the agent's own vanilla cases, and SURVIVORS.md (surviving GATE mutants only; held-out mutants
never shown). Expected values are derived from the docstring specification, not from the code.
The agent+gate suite = vanilla + these cases.

Agent's triage of the 18 survivors (recorded before evaluation):
  HumanEval/35  m004  e > m  -> e >= m           : same maximum returned; judged equivalent, no case
  HumanEval/39  m034  p-1 -> p+1 inside min(...) : range bound unchanged for p >= 2; judged equivalent
  HumanEval/40  m002, m005  allow re-using an element  -> cases below
  HumanEval/59  m012  range(2, n-1)              : differs only for prime n, excluded by docstring
  HumanEval/71  m011, m013  degenerate triangle (a+c == b, b+c == a) -> cases below
  HumanEval/108 m007, m011                       : n == 0 and n/(-1) give same digit-sum sign; judged equivalent
  HumanEval/114 m016  s < 0 -> s <= 0            : zero-sum handling; zero cases added defensively
  HumanEval/129 m004 judged equivalent (min neighbour <= n*n-1 always); m005, m021/m022, m052 -> cases below
  HumanEval/135 m013  < -> <=                    : differs only with duplicates, excluded by docstring
  HumanEval/148 m006  < -> <=                    : equal planets give () either way; judged equivalent
  HumanEval/151 m006  > 0 -> >= 0                : 0 is even, contributes nothing; judged equivalent
"""
CASES = {
    "HumanEval/40": [(([1, -2],), False), (([2, 3, -4],), False)],
    "HumanEval/71": [((1, 2, 1), -1), ((2, 1, 1), -1)],
    "HumanEval/114": [(([0, 0],), 0), (([2, 0, -1, 0, 3],), -1)],
    "HumanEval/129": [(([[1, 3], [4, 2]], 2), [1, 3]), (([[3, 2], [1, 4]], 2), [1, 3]),
                      (([[1, 9, 8], [2, 7, 6], [3, 4, 5]], 2), [1, 2])],
}

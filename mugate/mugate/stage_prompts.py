"""Stage 1: write ONLY the prompts (signature + docstring) of the sampled tasks to
agent_tests/PROMPTS.md. This is the sole information the test-writing agent receives for the
vanilla and blind suites. Canonical solutions and human tests are deliberately not written."""
from .dataset import ROOT, load_sample


def main():
    tasks = load_sample()
    out = ["# Prompts given to the test-writing agent (signature + docstring only)\n",
           f"Sample: seed 42, {len(tasks)} of 164 HumanEval tasks.\n"]
    for t in tasks:
        out.append(f"\n## {t['task_id']}  (entry point: `{t['entry_point']}`)\n\n```python\n{t['prompt'].rstrip()}\n```\n")
    (ROOT / "agent_tests" / "PROMPTS.md").write_text("".join(out), encoding="utf-8")
    print("task ids:", [t["task_id"] for t in tasks])


if __name__ == "__main__":
    main()

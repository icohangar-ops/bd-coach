"""Run DLP regex tests against test_fixtures.yaml. CI fails if any expectation breaks."""
from __future__ import annotations

import pathlib
import re
import sys

import yaml


def main() -> int:
    root = pathlib.Path(__file__).parent
    rules = yaml.safe_load((root / "restricted_hr_comp.yaml").read_text())
    fixtures = yaml.safe_load((root / "test_fixtures.yaml").read_text())

    block_patterns = [re.compile(r["pattern"]) for r in rules["rules"]["block_for_non_ceo"]]

    failures: list[str] = []

    for sample in fixtures["must_block_for_non_ceo"]:
        if not any(p.search(sample) for p in block_patterns):
            failures.append(f"MISS (should block): {sample}")

    for sample in fixtures["must_pass_for_non_ceo"]:
        if any(p.search(sample) for p in block_patterns):
            failures.append(f"FALSE POSITIVE (should pass): {sample}")

    if failures:
        print("DLP TEST FAILURES:")
        for f in failures:
            print("  " + f)
        return 1

    print(
        f"DLP tests passed: {len(fixtures['must_block_for_non_ceo'])} blocked, "
        f"{len(fixtures['must_pass_for_non_ceo'])} passed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

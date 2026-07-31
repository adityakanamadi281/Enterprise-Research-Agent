"""Offline structural evaluation for the research safety contract."""

import json
from pathlib import Path


def main() -> None:
    cases = json.loads(
        (Path(__file__).parents[1] / "tests/fixtures/eval_questions.json").read_text()
    )
    for case in cases:
        assert len(case["question"]) >= 12
        assert case["required_terms"], "Every golden question needs acceptance terms"
    print(f"Validated {len(cases)} research evaluation cases.")


if __name__ == "__main__":
    main()

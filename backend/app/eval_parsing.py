from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.services.parsing_eval import diagnose_resume_parse, evaluate_resume_parse, load_eval_spec


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Evaluate resume parsing quality.")
    parser.add_argument(
        "--fixtures",
        default="fixtures/resume_parsing",
        help="Directory containing resume parsing fixtures.",
    )
    parser.add_argument("--sample", help="Only evaluate one sample directory name.")
    parser.add_argument("--show-diff", action="store_true", help="Show parse diagnostics.")
    args = parser.parse_args()

    fixture_root = Path(args.fixtures)
    sample_dirs = sorted(path for path in fixture_root.iterdir() if path.is_dir())
    if args.sample:
        sample_dirs = [path for path in sample_dirs if path.name == args.sample]
    specs = [load_eval_spec(sample_dir) for sample_dir in sample_dirs]
    results = [evaluate_resume_parse(spec) for spec in specs]
    overall = summarize(results)
    payload: dict[str, object] = {"samples": results, "overall": overall}
    if args.show_diff:
        payload["diagnostics"] = [diagnose_resume_parse(spec) for spec in specs]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def summarize(results: list[dict[str, object]]) -> dict[str, object]:
    if not results:
        return {
            "sample_count": 0,
            "char_recall": 0,
            "keyword_recall": 0,
            "section_recall": 0,
            "truncated_count": 0,
        }

    return {
        "sample_count": len(results),
        "char_recall": round(avg(results, "char_recall"), 4),
        "keyword_recall": round(avg(results, "keyword_recall"), 4),
        "section_recall": round(avg(results, "section_recall"), 4),
        "truncated_count": sum(1 for result in results if result["truncated"]),
    }


def avg(results: list[dict[str, object]], key: str) -> float:
    return sum(float(result[key]) for result in results) / len(results)


if __name__ == "__main__":
    main()

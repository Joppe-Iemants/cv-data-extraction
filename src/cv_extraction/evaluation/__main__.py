"""Command-line entry point: python -m cv_extraction.evaluation."""

import argparse
import json

from .runner import ROOT, evaluate_run

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-ids", nargs="+", required=True)
    parser.add_argument("--allow-draft", action="store_true", help="Explicitly permit provisional reference scores.")
    parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()
    for run_id in dict.fromkeys(args.run_ids):
        summary = evaluate_run(ROOT, run_id, args.allow_draft, args.overwrite)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

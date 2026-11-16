"""
Command line entry point.

    python run_dq.py                 # in-memory run, prints summary
    python run_dq.py --db dq.db      # keep metadata + results in a sqlite file
"""
import argparse
import logging
import sys

sys.path.insert(0, "src")

from dq_framework.engine import run  # noqa: E402
from dq_framework.metadata import get_connection, init_metadata  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Run metadata-driven DQ checks")
    parser.add_argument("--db", default=":memory:", help="sqlite file for metadata/results")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    conn = get_connection(args.db)
    init_metadata(conn)

    run_id, status, results = run(conn)

    print(f"\nRun {run_id} -> {status}\n")
    print(f"{'dataset':<10} {'rule':<24} {'failed':>7} {'pass%':>7}  status")
    print("-" * 60)
    for r in results:
        print(f"{r['dataset_name']:<10} {r['rule_name']:<24} "
              f"{str(r['failed_records']):>7} {str(r['pass_pct']):>7}  {r['status']}")

    return 1 if status == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())

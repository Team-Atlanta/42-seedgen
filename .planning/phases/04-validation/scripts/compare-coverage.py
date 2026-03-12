#!/usr/bin/env python3
"""
Coverage Comparison and Assertion Script

Compares baseline vs seed coverage and asserts measurable improvement.
Used to validate VALD-02: Seeds demonstrate coverage improvement over baseline.
"""

import json
import sys
import argparse


def load_coverage(path: str) -> dict:
    """
    Load coverage data from llvm-cov JSON export.

    Args:
        path: Path to coverage JSON file

    Returns:
        Dict with keys: branches_covered, branches_total, functions_covered, functions_total
    """
    try:
        with open(path, 'r') as f:
            data = json.load(f)

        totals = data['data'][0]['totals']

        return {
            'branches_covered': totals['branches']['covered'],
            'branches_total': totals['branches']['count'],
            'functions_covered': totals['functions']['covered'],
            'functions_total': totals['functions']['count']
        }
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Error loading coverage from {path}: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Coverage file not found: {path}", file=sys.stderr)
        sys.exit(1)


def main():
    """Compare baseline and seeds coverage and assert improvement."""
    parser = argparse.ArgumentParser(
        description='Compare baseline and seeds coverage, assert improvement'
    )
    parser.add_argument('baseline_json', help='Path to baseline coverage JSON')
    parser.add_argument('seeds_json', help='Path to seeds coverage JSON')

    args = parser.parse_args()

    # Load both coverage files
    print("Loading coverage data...")
    baseline = load_coverage(args.baseline_json)
    seeds = load_coverage(args.seeds_json)

    # Calculate improvements
    branch_improvement = seeds['branches_covered'] - baseline['branches_covered']
    function_improvement = seeds['functions_covered'] - baseline['functions_covered']

    # Calculate percentages (avoid division by zero)
    baseline_branch_pct = (baseline['branches_covered'] / max(baseline['branches_total'], 1)) * 100
    seeds_branch_pct = (seeds['branches_covered'] / max(seeds['branches_total'], 1)) * 100
    branch_pct_improvement = seeds_branch_pct - baseline_branch_pct

    baseline_func_pct = (baseline['functions_covered'] / max(baseline['functions_total'], 1)) * 100
    seeds_func_pct = (seeds['functions_covered'] / max(seeds['functions_total'], 1)) * 100
    func_pct_improvement = seeds_func_pct - baseline_func_pct

    # Print comparison
    print("")
    print("=" * 60)
    print("Coverage Comparison Results")
    print("=" * 60)
    print("")
    print("BRANCH COVERAGE:")
    print(f"  Baseline: {baseline['branches_covered']}/{baseline['branches_total']} ({baseline_branch_pct:.2f}%)")
    print(f"  With seeds: {seeds['branches_covered']}/{seeds['branches_total']} ({seeds_branch_pct:.2f}%)")
    print(f"  Improvement: +{branch_improvement} branches ({branch_pct_improvement:+.2f} percentage points)")
    print("")
    print("FUNCTION COVERAGE:")
    print(f"  Baseline: {baseline['functions_covered']}/{baseline['functions_total']} ({baseline_func_pct:.2f}%)")
    print(f"  With seeds: {seeds['functions_covered']}/{seeds['functions_total']} ({seeds_func_pct:.2f}%)")
    print(f"  Improvement: +{function_improvement} functions ({func_pct_improvement:+.2f} percentage points)")
    print("")
    print("=" * 60)

    # Assert measurable improvement
    # Following 04-RESEARCH.md guidance: use relative comparison (>0%) not absolute thresholds
    if branch_improvement > 0 or function_improvement > 0:
        print("✓ VALIDATION PASSED: Seeds demonstrate measurable coverage improvement")
        print("")
        if branch_improvement > 0:
            print(f"  • Branch coverage improved by {branch_improvement} ({branch_pct_improvement:.2f} percentage points)")
        if function_improvement > 0:
            print(f"  • Function coverage improved by {function_improvement} ({func_pct_improvement:.2f} percentage points)")
        print("")
        sys.exit(0)
    else:
        print("✗ VALIDATION FAILED: Seeds did not improve coverage over baseline", file=sys.stderr)
        print(f"  Branch improvement: {branch_improvement}", file=sys.stderr)
        print(f"  Function improvement: {function_improvement}", file=sys.stderr)
        print("", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

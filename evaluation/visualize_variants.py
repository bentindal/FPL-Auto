#!/usr/bin/env python3
import json
import sys
from pathlib import Path

VARIANT_RESULTS_PATH = 'evaluation/variant_results.json'
BASELINE_RESULTS_PATH = 'evaluation/baseline_results.json'
PLOT_DIR = Path('evaluation/plots')
PLOT_DIR.mkdir(exist_ok=True)

def load_results():
    with open(VARIANT_RESULTS_PATH) as f:
        variants = json.load(f)
    with open(BASELINE_RESULTS_PATH) as f:
        baselines = json.load(f)
    return variants, baselines

def print_variant_summary(variants, baselines):
    """Print text-based summary of variant results."""
    print("\n" + "="*80)
    print("PHASE 6: TRANSFER VARIANT EVALUATION RESULTS")
    print("="*80 + "\n")

    # Extract baseline
    baseline_current = baselines['current']
    baseline_current_iter = baseline_current['test_iterations'][0]
    baseline_current_mean = baseline_current_iter['test_metrics']['total_points']
    baseline_current_ci = (baseline_current_mean, baseline_current_mean)  # Single point estimate

    print(f"BASELINE_CURRENT: {baseline_current_mean:.0f} [{baseline_current_ci[0]:.0f}, {baseline_current_ci[1]:.0f}]")
    print()

    # Variant results
    variant_names = [k for k in sorted(variants.keys()) if k != 'significance_report']

    print("VARIANT RESULTS (sorted by total_points):")
    print("-" * 80)

    variant_data = []
    for name in variant_names:
        ci = variants[name]['confidence_intervals']['total_points']
        mean = ci['mean']
        lower = ci['ci_lower']
        upper = ci['ci_upper']

        variant_data.append({
            'name': name,
            'mean': mean,
            'lower': lower,
            'upper': upper,
            'vs_baseline': mean - baseline_current_mean,
        })

    # Sort by mean total_points
    variant_data.sort(key=lambda x: x['mean'], reverse=True)

    for i, var in enumerate(variant_data, 1):
        vs = var['vs_baseline']
        vs_sign = "+" if vs > 0 else ""
        ci_width = var['upper'] - var['lower']
        sig = " (SIGNIFICANT)" if not ci_overlap(
            (var['lower'], var['upper']),
            baseline_current_ci
        ) else ""

        print(f"{i}. {var['name']:20s} | {var['mean']:6.0f} [{var['lower']:6.0f}, {var['upper']:6.0f}] | {vs_sign}{vs:5.0f}{sig}")

    print()

def ci_overlap(ci1, ci2):
    """Check if two CIs overlap. Returns True if overlap, False if non-overlapping (significant)."""
    return not (ci1[1] < ci2[0] or ci2[1] < ci1[0])

def print_per_season_breakdown(variants):
    """Print per-season results for each variant."""
    print("\nPER-SEASON BREAKDOWN:")
    print("-" * 80)

    variant_names = sorted([k for k in variants.keys() if k != 'significance_report'])

    for name in variant_names:
        iterations = variants[name]['test_iterations']
        print(f"\n{name}:")
        for it in iterations:
            season = it['test_season']
            points = it['test_results']['total_points']
            sharpe = it['test_metrics'].get('sharpe_ratio', 0)
            print(f"  {season}: {points:.0f} points (Sharpe: {sharpe:.2f})")

def print_significance_report(variants):
    """Print significance report if available."""
    if 'significance_report' in variants:
        report = variants['significance_report']
        winners = report.get('winners', [])

        print("\nWINNERS (vs BASELINE_CURRENT):")
        print("-" * 80)

        if winners:
            for winner in winners:
                print(f"  {winner['variant']}: +{winner['improvement_points']:.0f} points vs {winner['beats']}")
        else:
            print("  No variants significantly beat BASELINE_CURRENT (overlapping CIs)")

        print()

def generate_variant_plots(variants, baselines):
    """Generate summary visualization data."""
    print_variant_summary(variants, baselines)
    print_per_season_breakdown(variants)
    print_significance_report(variants)
    print("="*80)

if __name__ == '__main__':
    try:
        variants, baselines = load_results()
        generate_variant_plots(variants, baselines)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run 'python3 evaluation/compare_variants.py' first", file=sys.stderr)
        sys.exit(1)

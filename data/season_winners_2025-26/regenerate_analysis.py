#!/usr/bin/env python3
"""
Regenerate analysis files with CORRECT transfer data extraction.

The original analysis.json files had incomplete transfer data.
This script fixes it by properly extracting from raw gameweek files.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

ARCHIVE_DIR = Path(__file__).parent

def regenerate_manager_analysis(manager_id):
    """
    Generate correct analysis for a manager by reading raw gameweek data.
    """
    mgr_dir = ARCHIVE_DIR / str(manager_id)

    # Load complete season
    with open(mgr_dir / '_complete_season.json') as f:
        season = json.load(f)

    # Load metadata
    with open(ARCHIVE_DIR / 'MASTER_SUMMARY.json') as f:
        master = json.load(f)

    mgr_meta = next((m for m in master['top_managers'] if m['manager_id'] == manager_id), None)

    if not mgr_meta:
        print(f"Manager {manager_id} not found in master summary")
        return None

    # Extract statistics from raw data
    captaincy_counts = Counter()
    chip_usage = defaultdict(list)
    player_appearances = Counter()
    transfer_data = []
    points_data = []

    for gw_str, data in season.items():
        gw = int(gw_str)
        entry = data['entry_history']
        picks = data.get('picks', [])

        # Points tracking
        points_data.append({
            'gw': gw,
            'points': entry['points'],
            'total': entry['total_points'],
            'rank': entry['rank']
        })

        # Captaincy
        for pick in picks:
            if pick.get('is_captain'):
                captaincy_counts[pick['element']] += 1
            player_appearances[pick['element']] += 1

        # Chips
        if data.get('active_chip') and data['active_chip'] != 'None':
            chip_usage[data['active_chip']].append(gw)

        # Transfers (CORRECT extraction from entry_history)
        transfers = entry.get('event_transfers', 0)
        cost = entry.get('event_transfers_cost', 0)
        if transfers > 0:
            transfer_data.append({
                'gw': gw,
                'count': transfers,
                'cost': cost
            })

    # Build analysis object
    analysis = {
        'manager': mgr_meta,
        'captaincy': {
            'top_choices': dict(captaincy_counts.most_common(10)),
            'total_gameweeks': len(season)
        },
        'chip_usage': {
            chip: {
                'gameweeks': sorted(gws),
                'count': len(gws)
            }
            for chip, gws in sorted(chip_usage.items())
        },
        'squad': {
            'total_unique_players': len(player_appearances),
            'most_selected': dict(player_appearances.most_common(15))
        },
        'transfers': {
            'total': sum(t['count'] for t in transfer_data),
            'gameweeks_with_transfers': len(transfer_data),
            'avg_per_transfer_gw': round(
                sum(t['cost'] for t in transfer_data) / len(transfer_data), 1
            ) if transfer_data else 0,
            'gw_breakdown': transfer_data
        },
        'performance': {
            'total_points': entry['total_points'],
            'final_rank': entry['overall_rank'],
            'best_gw': max(points_data, key=lambda x: x['points']) if points_data else None,
            'worst_gw': min(points_data, key=lambda x: x['points']) if points_data else None,
            'avg_gw_points': round(sum(p['points'] for p in points_data) / len(points_data), 1) if points_data else 0
        }
    }

    return analysis

def main():
    """Regenerate all 30 manager analyses."""
    print("🔄 Regenerating analysis files with correct transfer data...\n")

    # Load master to get all manager IDs
    with open(ARCHIVE_DIR / 'MASTER_SUMMARY.json') as f:
        master = json.load(f)

    success_count = 0
    error_count = 0

    for i, mgr in enumerate(master['top_managers'], 1):
        mgr_id = mgr['manager_id']
        mgr_name = mgr['player_name']

        try:
            analysis = regenerate_manager_analysis(mgr_id)

            if analysis:
                # Save analysis
                analysis_file = ARCHIVE_DIR / str(mgr_id) / 'analysis.json'
                with open(analysis_file, 'w') as f:
                    json.dump(analysis, f, indent=2, default=str)

                transfers = analysis['transfers']['total']
                print(f"[{i:2d}/30] {mgr_name:25s} ✓ ({transfers} transfers)")
                success_count += 1
            else:
                print(f"[{i:2d}/30] {mgr_name:25s} ⚠ No metadata found")
                error_count += 1

        except Exception as e:
            print(f"[{i:2d}/30] {mgr_name:25s} ✗ {str(e)[:40]}")
            error_count += 1

    print(f"\n{'='*70}")
    print(f"✓ Regeneration complete: {success_count}/30 successful")
    if error_count > 0:
        print(f"⚠ Errors: {error_count}")

    # Show corrected summary
    print(f"\n{'='*70}")
    print("CORRECTED TRANSFER SUMMARY")
    print(f"{'='*70}\n")

    all_transfers = []
    for mgr in master['top_managers']:
        try:
            analysis = json.load(open(ARCHIVE_DIR / str(mgr['manager_id']) / 'analysis.json'))
            all_transfers.append((mgr['player_name'], analysis['transfers']['total']))
        except:
            pass

    total_transfers = sum(t[1] for t in all_transfers)
    avg = total_transfers / len(all_transfers) if all_transfers else 0

    print(f"Total transfers (all 30): {total_transfers}")
    print(f"Average per manager: {avg:.1f}")

    if all_transfers:
        min_t = min(t[1] for t in all_transfers)
        max_t = max(t[1] for t in all_transfers)
        print(f"Range: {min_t} - {max_t}")
        print(f"\nTop 5 most active (transfers):")
        for name, count in sorted(all_transfers, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {name:25s}: {count}")

if __name__ == '__main__':
    main()

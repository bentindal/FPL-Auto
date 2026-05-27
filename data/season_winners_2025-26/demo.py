#!/usr/bin/env python3
"""
Demo: Using the FPL Season Winners Archive with Player Names

Shows how to:
1. Load player mappings
2. Convert player IDs to names
3. Analyze elite team compositions
4. View captaincy patterns with names
"""

import json
from pathlib import Path

# Initialize paths
ARCHIVE_DIR = Path(__file__).parent

def load_player_map():
    """Load player ID → info mapping"""
    with open(ARCHIVE_DIR / 'player_mapping.json') as f:
        return json.load(f)

def load_master_summary():
    """Load aggregated stats"""
    with open(ARCHIVE_DIR / 'MASTER_SUMMARY.json') as f:
        return json.load(f)

def load_manager_season(manager_id):
    """Load a manager's complete season data"""
    with open(ARCHIVE_DIR / str(manager_id) / '_complete_season.json') as f:
        return json.load(f)

def load_manager_analysis(manager_id):
    """Load a manager's strategy analysis"""
    with open(ARCHIVE_DIR / str(manager_id) / 'analysis.json') as f:
        return json.load(f)

def id_to_name(player_id, players):
    """Convert player ID to name"""
    player_data = players.get(str(player_id), {})
    return player_data.get('name', f'Unknown (ID: {player_id})')

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def demo_1_player_mappings():
    """Demo 1: Basic player mappings"""
    print_section("Demo 1: Player ID → Name Mappings")

    players = load_player_map()

    # Show key players
    key_players = [430, 449, 5, 16, 381, 382, 249, 283]
    print("Key players from elite squads:")
    for pid in key_players:
        p = players[str(pid)]
        print(f"  Player {pid:3d} → {p['name']:25s} ({p['position_name']}, {p['team']}, £{p['price']:.1f})")

def demo_2_elite_captaincy():
    """Demo 2: Elite captaincy choices with names"""
    print_section("Demo 2: Elite Captaincy Choices (with names)")

    players = load_player_map()
    master = load_master_summary()

    captains = master['captaincy_meta']['most_captained_overall']
    print("Most captained players across top 30 managers:\n")

    for i, (player_id, count) in enumerate(list(captains.items())[:5], 1):
        name = id_to_name(int(player_id), players)
        pct = (count / (30 * 38)) * 100
        bar = '█' * int(pct * 3)
        print(f"  {i}. {name:25s}: {count:2d} times ({pct:4.1f}%) {bar}")

def demo_3_top_manager_squad():
    """Demo 3: Season winner's squad analysis"""
    print_section("Demo 3: Season Winner's Squad (Ivan Peula)")

    players = load_player_map()
    analysis = load_manager_analysis(3244539)
    mgr = analysis['manager']

    print(f"Manager: {mgr['player_name']} ({mgr['team_name']})")
    print(f"Points: {mgr['points']} (Rank: {mgr['rank']})\n")

    print("Top 10 most selected players:")
    most_selected = analysis['squad']['most_selected']
    for i, (player_id, gw_count) in enumerate(list(most_selected.items())[:10], 1):
        name = id_to_name(int(player_id), players)
        p = players[str(player_id)]
        bar = '█' * (gw_count // 4)
        print(f"  {i:2d}. {name:25s}: {gw_count:2d}/38 GWs {bar}")

def demo_4_gw_lineup():
    """Demo 4: View a gameweek lineup with player names"""
    print_section("Demo 4: Ivan Peula's GW1 Lineup")

    players = load_player_map()
    season = load_manager_season(3244539)

    gw1 = season['1']
    picks = gw1['picks']

    print(f"Gameweek 1 Performance:")
    print(f"  Points: {gw1['entry_history']['points']}")
    print(f"  Rank: {gw1['entry_history']['rank']}")
    print(f"  Total Points: {gw1['entry_history']['total_points']}\n")

    print(f"Active Chip: {gw1.get('active_chip', 'None')}\n")

    print("Squad:")
    for i, pick in enumerate(picks, 1):
        name = id_to_name(pick['element'], players)
        p = players[str(pick['element'])]
        pos_name = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}[p['position']]
        mult = '(C)' if pick.get('is_captain') else '(VC)' if pick.get('is_vice_captain') else ''
        print(f"  {i:2d}. {name:25s} ({pos_name}) {mult}")

def demo_5_compare_managers():
    """Demo 5: Compare top 3 managers' captaincy"""
    print_section("Demo 5: Compare Top 3 Managers' Captaincy Strategy")

    players = load_player_map()
    master = load_master_summary()

    top_3 = master['top_managers'][:3]

    for mgr in top_3:
        mgr_id = mgr['manager_id']
        try:
            analysis = load_manager_analysis(mgr_id)

            print(f"\n{mgr['player_name']} (#{mgr['rank']}, {mgr['points']} pts):")
            print(f"  Top captains:")

            captains = analysis['captaincy']['top_choices']
            for player_id, count in list(captains.items())[:3]:
                name = id_to_name(int(player_id), players)
                print(f"    • {name:25s}: {count} times")
        except Exception as e:
            print(f"\n{mgr['player_name']}: (data not available)")

def demo_6_season_arc():
    """Demo 6: Track a manager's season performance"""
    print_section("Demo 6: Ivan Peula's Season Arc (GW1-10)")

    players = load_player_map()
    season = load_manager_season(3244539)

    print(f"{'GW':>4} {'Pts':>5} {'Total':>7} {'Rank':>7} {'Captain':>25}\n")

    for gw in range(1, 11):
        gw_data = season[str(gw)]
        entry = gw_data['entry_history']

        # Find captain
        captain_id = next(
            (p['element'] for p in gw_data['picks'] if p.get('is_captain')),
            None
        )
        captain_name = id_to_name(captain_id, players) if captain_id else 'None'

        print(f"{gw:4d} {entry['points']:5d} {entry['total_points']:7d} "
              f"{entry['rank']:7d} {captain_name:>25}")

def main():
    """Run all demos"""
    print("\n" + "🎯 FPL SEASON WINNERS ARCHIVE - DEMO SUITE" + "\n")

    try:
        demo_1_player_mappings()
        demo_2_elite_captaincy()
        demo_3_top_manager_squad()
        demo_4_gw_lineup()
        demo_5_compare_managers()
        demo_6_season_arc()

        print_section("✓ All demos completed!")
        print("\nFor more information:")
        print("  • player_mapping.json    - All 841 players with full details")
        print("  • name_to_id.json        - Quick name→ID lookup")
        print("  • players.csv            - Spreadsheet format (Excel/Sheets)")
        print("  • lookup.py              - Python utility functions")
        print("  • PLAYER_LOOKUP.md       - Complete guide")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

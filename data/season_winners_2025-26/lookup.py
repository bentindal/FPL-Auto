import json
from pathlib import Path

def load_player_map():
    """Load player ID → name mapping"""
    mapping_file = Path(__file__).parent / 'player_mapping.json'
    with open(mapping_file) as f:
        return json.load(f)

def load_name_map():
    """Load player name → ID mapping"""
    mapping_file = Path(__file__).parent / 'name_to_id.json'
    with open(mapping_file) as f:
        return json.load(f)

def id_to_name(player_id):
    """Convert player ID to name"""
    mapping = load_player_map()
    if str(player_id) in mapping:
        return mapping[str(player_id)]['name']
    return f"Unknown (ID: {player_id})"

def name_to_id(player_name):
    """Convert player name to ID"""
    mapping = load_name_map()
    return mapping.get(player_name)

def get_player_info(player_id):
    """Get all info for a player"""
    mapping = load_player_map()
    if str(player_id) in mapping:
        return mapping[str(player_id)]
    return None

# Example usage
if __name__ == '__main__':
    print(f"Player 430: {id_to_name(430)}")
    print(f"Player 449: {id_to_name(449)}")
    print(f"Haaland ID: {name_to_id('Haaland')}")
    
    info = get_player_info(430)
    if info:
        print(f"\nPlayer {info['id']}: {info['name']}")
        print(f"  Position: {info['position_name']}")
        print(f"  Team: {info['team']}")
        print(f"  Price: £{info['price']}")
        print(f"  Selected: {info['selected_by_percent']}%")

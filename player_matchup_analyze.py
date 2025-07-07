import json
import os
from itertools import combinations
from collections import defaultdict

def format_challenge_event(history_item, round_data, player_states, game_id):
    """
    Formats a single duel event into readable text with more details
Parameters:
        history_item: dictionary containing match information
        round_data: dictionary containing current round data
        player_states: dictionary containing all players' initial states
        game_id: string representing the game identifier
    Returns:
        Formatted text description of the duel event
    """
    # Extract duel participants' information
    player = history_item['player_name']
    next_player = history_item['next_player']

    # Find initial state of players
    player_initial_state = None
    next_player_initial_state = None
    for state in round_data['player_initial_states']:
        if state['player_name'] == player:
            player_initial_state = state
        elif state['player_name'] == next_player:
            next_player_initial_state = state

    # Build detailed duel record
    output = []

    # Add game identifier
    output.append(f"Game ID: {game_id}")

    # Add information about the player who played the card
    output.append(f"Player ({player}):")
    output.append(f"Initial hand: {', '.join(player_initial_state['initial_hand'])}")
    output.append(f"Played cards: {', '.join(history_item['played_cards'])}")
    output.append(f"Remaining hand: {', '.join(history_item['remaining_cards'])}")
    if 'play_reason' in history_item and history_item['play_reason']:
        output.append(f"Play reason: {history_item['play_reason']}")
    if 'behavior' in history_item and history_item['behavior']:
        output.append(f"Play behavior: {history_item['behavior']}")

    # Add information about the player who challenged
    output.append(f"\nChallenger ({next_player}):")
    if next_player_initial_state:
        output.append(f"Initial hand: {', '.join(next_player_initial_state['initial_hand'])}")
    
    if history_item['was_challenged']:
        output.append(f"Challenged")
        if 'challenge_reason' in history_item and history_item['challenge_reason']:
            output.append(f"Challenge reason: {history_item['challenge_reason']}")
        result_text = "Success" if history_item['challenge_result'] else "Failure"
        output.append(f"Challenge result: {result_text}")
    else:
        output.append("Chose not to challenge")
        if 'challenge_reason' in history_item and history_item['challenge_reason']:
            output.append(f"Reason for not challenging: {history_item['challenge_reason']}")
    
    # Add extra blank lines to improve readability

    output.append("")
    
    return "\n".join(output)

def extract_matchups(game_data, game_id):
    """
    Extracts all detailed duel records between players from game data
    Args:
        game_data: Complete game data dictionary
        game_id: Game identifier
    Returns:
        Dictionary containing all matchup duel records
    """
    # Get all player names and create matchup pairs
    players = game_data['player_names']
    matchups = defaultdict(list)
    
    # Process each round's data
    for round_data in game_data['rounds']:
        round_id = round_data['round_id']
        target_card = round_data['target_card']
        
        # Process each play
        for play in round_data['play_history']:
            player = play['player_name']
            next_player = play['next_player']
            
            # Only record matchups where a challenge occurred
            if play['was_challenged']:
                matchup_key = '_vs_'.join(sorted([player, next_player]))
                
                # Add round info
                round_info = [
                    f"Round {round_id} Matchup",
                    f"Target card: {target_card}",
                    "=" * 40,
                    ""
                ]
                
                # Add detailed duel record
                challenge_text = format_challenge_event(play, round_data, round_data['player_initial_states'], game_id)
                
                # Combine all info
                full_text = "\n".join(round_info) + challenge_text
                
                matchups[matchup_key].append(full_text)
                
    return matchups

def save_matchups_to_files(all_matchups, output_dir):
    """
    Save all duel records of all games into separate files
    Args:
        all_matchups: Dictionary containing all duel records for all games
        output_dir: Output folder path
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save duel records for each player pair
    for matchup_key, interactions in all_matchups.items():
        if interactions:
            # Create file in output folder
            filename = os.path.join(output_dir, f"{matchup_key}_detailed_matchups.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Detailed duel records for {matchup_key.replace('_vs_', ' vs ')}\n")
                f.write("=" * 50 + "\n\n")
                f.write("\n\n".join(interactions))
                # Add statistics at the end of the file
                f.write(f"\n\nTotal number of duels: {len(interactions)}\n")

def process_all_json_files(input_dir, output_dir):
    """
    Process all JSON files in the specified folder and merge duel records for the same player pairs
    Args:
        input_dir: Input folder path (containing JSON files)
        output_dir: Output folder path
    """
    # Ensure input folder exists
    if not os.path.exists(input_dir):
        print(f"Error: Input folder '{input_dir}' does not exist")
        return
    
    # Iterate over all JSON files
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    if not json_files:
        print(f"Warning: No JSON files found in '{input_dir}'")
        return
    
    print(f"Found {len(json_files)} JSON files")
    
    # Store all duel records for all games
    all_matchups = defaultdict(list)
    
    # Process each JSON file
    for json_file in json_files:
        print(f"Processing: {json_file}")
        file_path = os.path.join(input_dir, json_file)
        
        try:
            # Read JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
            
            # Use filename as game ID
            game_id = os.path.splitext(json_file)[0]
            
            # Extract duel records
            game_matchups = extract_matchups(game_data, game_id)
            
            # Merge into total records
            for key, value in game_matchups.items():
                all_matchups[key].extend(value)
            
            print(f"Successfully processed {json_file}")
            
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")
    
    # Save merged duel records
    save_matchups_to_files(all_matchups, output_dir)
    print("All duel records have been merged and saved")

# Main program starts here

# Define input and output folders
input_dir = "game_records"  # Folder containing JSON files
output_dir = "matchup_records"  # Output folder

# Process all JSON files
process_all_json_files(input_dir, output_dir)
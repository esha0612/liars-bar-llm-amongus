import os
import json
from collections import defaultdict, Counter

def analyze_game_records(folder_path):
    # Initialize statistical data structure
    stats = {
        'wins': Counter(),
        'shots_fired': Counter(),
        'survival_points': Counter(),
        'matchups': defaultdict(lambda: defaultdict(int)),  # A and B's confrontation count record
        'win_counts': defaultdict(lambda: defaultdict(int))  # A's victory count against B
    }
    
    player_names = set()
    game_count = 0
    
    # Iterate through all JSON files in the folder
    for filename in os.listdir(folder_path):
        if not filename.endswith('.json'):
            continue
            
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
                
            # Skip games without a winner
            if game_data.get('winner') is None:
                continue
                
            game_count += 1
            
            # Record player names
            for player in game_data.get('player_names', []):
                player_names.add(player)
                
            # Count winning situation
            winner = game_data.get('winner')
            if winner:
                stats['wins'][winner] += 1
            
            # Analyze data for each round
            rounds = game_data.get('rounds', [])
            for round_data in rounds:
                # Count shooting situation
                round_result = round_data.get('round_result', {})
                shooter = round_result.get('shooter_name')
                if shooter:
                    stats['shots_fired'][shooter] += 1
                
                # Analyze confrontation situation
                play_history = round_data.get('play_history', [])
                for play in play_history:
                    player = play.get('player_name')
                    next_player = play.get('next_player')
                    was_challenged = play.get('was_challenged')
                    
                    if was_challenged and next_player:
                        challenge_result = play.get('challenge_result')
                        
                        # Record confrontation count - only record one direction to avoid duplicate counting
                        # Ensure recorded in alphabetical order to ensure confrontation always counted the same way
                        if player < next_player:
                            stats['matchups'][player][next_player] += 1
                        else:
                            stats['matchups'][next_player][player] += 1
                        
                        # Record who won this confrontation
                        if challenge_result is True:  # Challenge succeeded, next_player won
                            stats['win_counts'][next_player][player] += 1
                        elif challenge_result is False:  # Challenge failed, player won
                            stats['win_counts'][player][next_player] += 1
            
            # Calculate survival points
            # First determine elimination order
            elimination_order = []
            alive_players = set(game_data.get('player_names', []))
            
            for round_data in rounds:
                round_result = round_data.get('round_result', {})
                shooter = round_result.get('shooter_name')
                bullet_hit = round_result.get('bullet_hit')
                
                if shooter and bullet_hit and shooter in alive_players:
                    elimination_order.append(shooter)
                    alive_players.remove(shooter)
            
            # Add remaining alive players to elimination order in order at game end
            elimination_order.extend(alive_players)
            
            # Calculate survival points for each player
            # If there are n players, the first eliminated player gets 0 points, the second gets 1 point, and so on
            for i, player in enumerate(elimination_order):
                if i > 0:  # First eliminated player gets no points
                    stats['survival_points'][player] += i
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    # Calculate win rate
    win_rates = {}
    for player in player_names:
        win_rates[player] = {}
        for opponent in player_names:
            if player != opponent:
                # Determine correct order for pairing to get total confrontation count
                if player < opponent:
                    total_matchups = stats['matchups'][player][opponent]
                else:
                    total_matchups = stats['matchups'][opponent][player]
                
                if total_matchups > 0:
                    wins = stats['win_counts'][player][opponent]
                    win_rates[player][opponent] = wins / total_matchups
                else:
                    win_rates[player][opponent] = 0
    
    return stats, win_rates, game_count, player_names

def print_statistics(stats, win_rates, game_count, player_names):
    players = sorted(list(player_names))
    
    print(f"Total analysis of {game_count} games")
    print("\nWin count statistics:")
    for player in players:
        wins = stats['wins'][player]
        win_percentage = (wins / game_count) * 100 if game_count > 0 else 0
        print(f"{player}: {wins} games ({win_percentage:.1f}%)")
    
    print("\nShooting count statistics:")
    for player in players:
        print(f"{player}: {stats['shots_fired'][player]} times")
    
    print("\nSurvival point statistics:")
    for player in players:
        points = stats['survival_points'][player]
        avg_points = points / game_count if game_count > 0 else 0
        print(f"{player}: {points} points (average per game {avg_points:.2f} points)")
    
    print("\nConfrontation win rate:")
    print(f"{'Player vs Opponent':<25} {'Confrontation Count':<10} {'Win Count':<10} {'Win Rate':<10}")
    print("-" * 55)
    
    for player in players:
        for opponent in players:
            if player != opponent:
                # Get correct order confrontation total count
                if player < opponent:
                    matchups = stats['matchups'][player][opponent]
                else:
                    matchups = stats['matchups'][opponent][player]
                
                wins = stats['win_counts'][player][opponent]
                win_rate = win_rates[player][opponent] * 100
                
                print(f"{player} vs {opponent:<10} {matchups:<10} {wins:<10} {win_rate:.1f}%")

if __name__ == "__main__":
    folder_path = "game_records"  # Replace with actual folder path
    stats, win_rates, game_count, player_names = analyze_game_records(folder_path)
    print_statistics(stats, win_rates, game_count, player_names)
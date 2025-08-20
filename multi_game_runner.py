from game import BotCGame
from typing import Dict, List
import argparse

class MultiGameRunner:
    def __init__(self, player_configs: List[Dict[str, str]], num_games: int = 10):
        """Initialize multi-game runner
        
        Args:
            player_configs: List of player configurations
            num_games: Number of games to run
        """
        self.player_configs = player_configs
        self.num_games = num_games

    def run_games(self) -> None:
        """Run specified number of games"""
        for game_num in range(1, self.num_games + 1):
            print(f"\n=== Start {game_num}/{self.num_games} Game ===")
            
            # Create and run new game
            game = BotCGame(self.player_configs)
            game.start_game()
            
            print(f"Game {game_num} ended")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run multiple AI battle games',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-n', '--num-games',
        type=int,
        default=10,
        help='Number of games to run (default: 10)'
    )
    return parser.parse_args()

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure player information, where model is the name of the model you called via API
    player_configs = [
        
        {"name": "Sarah", "model": "llama3"},
        {"name": "Anika", "model": "mistral:7b"},
        {"name": "Derek", "model": "mistral:latest"},
        {"name": "Emma", "model": "llama3"},
        {"name": "Noah", "model": "mistral:7b"},
        {"name": "James", "model": "mistral:latest"},
        {"name": "George", "model": "llama3"},
    ]

    # Create and run multiple games
    runner = MultiGameRunner(player_configs, num_games=args.num_games)
    runner.run_games()
from game import MafiaGame
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
            game = MafiaGame(self.player_configs)
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
        # {"name": "Sarah",     "model": "llama3"},
        # {"name": "Anika",     "model": "mistral:7b"},
        # {"name": "Derek",     "model": "mistral:latest"},
        # {"name": "Emma",      "model": "llama3"},
        # {"name": "Noah",      "model": "mistral:7b"},
        # {"name": "James",     "model": "mistral:latest"},
        # {"name": "George",    "model": "llama3"},
        # {"name": "Hannah",    "model": "mistral:7b"},
        # {"name": "Christian", "model": "mistral:latest"},
        # {"name": "Monica",    "model": "llama3"},
        # {"name": "Zelda",     "model": "mistral:7b"},


        {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        {"name": "Derek", "model": "ollama/deepseek-r1:7b"},
        {"name": "Emma", "model": "ollama/dolphin3:8b"},
        {"name": "Talia", "model": "ollama/qwen2.5:7b"},
        {"name": "Anika", "model": "ollama/mistral:7b"},
        {"name": "Nick", "model": "ollama/mistral-nemo:12b"},
        {"name": "Philip", "model": "ollama/phi4:14b"},
        {"name": "Peter", "model": "ollama/phi3.5:3.8b"},
        {"name": "George", "model": "ollama/llava:7b"},
        {"name": "Enrique", "model": "ollama/gemma2:9b"},
        #{"name": "Maria", "model": "openai/gpt-4o-mini"},
    ]

    # Create and run multiple games
    runner = MultiGameRunner(player_configs, num_games=args.num_games)
    runner.run_games()
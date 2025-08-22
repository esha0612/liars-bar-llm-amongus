from game import Game
from typing import Dict, List
import argparse
from collections import defaultdict, deque
import random

class MultiGameRunner:
    def __init__(self, player_configs: List[Dict[str, str]], num_games: int = 10, threshold_rounds: int = 20):
        """Initialize multi-game runner
        
        Args:
            player_configs: List of player configurations
            num_games: Number of games to run
            threshold_rounds: Number of rounds after which all models must have played at least once
        """
        self.player_configs = player_configs
        self.num_games = num_games
        self.threshold_rounds = threshold_rounds
        
        # Track model usage across games
        self.model_usage = defaultdict(int)
        self.round_count = 0
        self.last_model_usage = defaultdict(int)  # Track when each model was last used
        
        # Create a queue to track recent model usage
        self.recent_models = deque(maxlen=threshold_rounds)
        
    def _should_force_model_usage(self) -> bool:
        """Check if we should force usage of models that haven't played recently"""
        if self.round_count < self.threshold_rounds:
            return False
            
        # Check if any model hasn't been used in the last threshold_rounds
        for model_config in self.player_configs:
            model_name = model_config["model"]
            if self.last_model_usage[model_name] < (self.round_count - self.threshold_rounds):
                return True
        return False
    
    def _get_priority_models(self) -> List[str]:
        """Get models that should be prioritized (haven't played recently)"""
        priority_models = []
        for model_config in self.player_configs:
            model_name = model_config["model"]
            if self.last_model_usage[model_name] < (self.round_count - self.threshold_rounds):
                priority_models.append(model_name)
        return priority_models
    
    def _adjust_player_configs_for_threshold(self) -> List[Dict[str, str]]:
        """Adjust player configurations to ensure threshold compliance"""
        if not self._should_force_model_usage():
            return self.player_configs
        
        priority_models = self._get_priority_models()
        print(f"Threshold enforcement: Models that need to play: {priority_models}")
        
        # Create a copy of player configs
        adjusted_configs = self.player_configs.copy()
        
        # If we have priority models, ensure they are included
        if priority_models:
            # For simplicity, we'll just ensure the priority models are at the front
            # In a more sophisticated implementation, you might want to rotate players
            priority_configs = [config for config in adjusted_configs 
                              if config["model"] in priority_models]
            other_configs = [config for config in adjusted_configs 
                           if config["model"] not in priority_models]
            
            # Shuffle both lists to maintain randomness
            random.shuffle(priority_configs)
            random.shuffle(other_configs)
            
            # Put priority models first
            adjusted_configs = priority_configs + other_configs
        
        return adjusted_configs
    
    def _update_model_usage(self, game_round_count: int, used_models: List[str]) -> None:
        """Update model usage tracking after a game
        
        Args:
            game_round_count: Number of rounds in the completed game
            used_models: List of model names that actually participated in the game
        """
        self.round_count += game_round_count
        
        # Update last usage only for models that actually participated
        for model_name in used_models:
            self.model_usage[model_name] += 1
            self.last_model_usage[model_name] = self.round_count
    
    def run_games(self) -> None:
        """Run specified number of games with threshold enforcement"""
        print(f"Starting {self.num_games} games with threshold of {self.threshold_rounds} rounds")
        print("Model usage tracking enabled - all models must play at least once every 20 rounds")
        
        for game_num in range(1, self.num_games + 1):
            print(f"\n=== Start {game_num}/{self.num_games} Game ===")
            
            # Check if we need to enforce threshold
            if self._should_force_model_usage():
                print(f"Threshold enforcement active at round {self.round_count}")
                priority_models = self._get_priority_models()
                print(f"Models that need to play: {priority_models}")
            
            # Get adjusted player configs
            adjusted_configs = self._adjust_player_configs_for_threshold()
            
            # Create and run new game
            game = Game(adjusted_configs)
            game.start_game()
            
            # Update model usage tracking
            used_models = [config["model"] for config in adjusted_configs]
            self._update_model_usage(game.round_count, used_models)
            
            print(f"Game {game_num} ended after {game.round_count} rounds")
            print(f"Current model usage: {dict(self.model_usage)}")
        
        # Print final statistics
        print(f"\n=== Final Statistics ===")
        print(f"Total rounds played: {self.round_count}")
        print(f"Model usage counts: {dict(self.model_usage)}")
        print(f"Average rounds per model: {self.round_count / len(self.player_configs):.1f}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run multiple AI battle games with model usage threshold',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-n', '--num-games',
        type=int,
        default=10,
        help='Number of games to run (default: 10)'
    )
    parser.add_argument(
        '-t', '--threshold',
        type=int,
        default=20,
        help='Number of rounds after which all models must have played (default: 20)'
    )
    return parser.parse_args()

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure player information with models that are actually available
    player_configs = [
        {"name": "Sarah",   "model": "llama3.1:8b"},
        {"name": "Derek",   "model": "deepseek-r1:7b"},
        {"name": "Emma",    "model": "dolphin3:latest"},
        {"name": "Talia",   "model": "qwen2.5:7b"},
        {"name": "Anika",   "model": "mistral:7b"},
        {"name": "Nick",    "model": "mistral-nemo:12b"},
        {"name": "Philip",  "model": "phi4:14b"},
        {"name": "Peter",   "model": "phi3.5:3.8b"},
        {"name": "George",  "model": "llava:7b"},
        {"name": "Enrique", "model": "gemma2:9b"},
        {"name": "Maria",   "model": "gpt-4o-mini"}  # This will show warning but won't break
    ]

    print("Multi-Game Runner Configuration:")
    print(f"Number of games: {args.num_games}")
    print(f"Threshold rounds: {args.threshold}")
    print("Player configurations:")
    for config in player_configs:
        print(f"  Player: {config['name']}, Model: {config['model']}")
    print("-" * 50)

    # Create and run multiple games
    runner = MultiGameRunner(player_configs, num_games=args.num_games, threshold_rounds=args.threshold)
    runner.run_games()
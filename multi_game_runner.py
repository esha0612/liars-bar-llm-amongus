from game import Game
from typing import Dict, List
import argparse
import random
import sys
from collections import defaultdict, deque

class MultiGameRunner:
    def __init__(self, player_configs: List[Dict[str, str]], threshold_rounds: int = 20, min_appearances: int = 2):
        """
        Args:
            player_configs: List of player configurations [{'name': str, 'model': str}, ...]
            threshold_rounds: Number of rounds after which all models must have played at least once
            min_appearances: minimum # of games each name must appear in
        """
        if len(player_configs) < 2:
            raise ValueError("Liars Bar requires at least 2 total players in player_configs.")
        
        self.player_configs = player_configs
        self.threshold_rounds = threshold_rounds
        self.min_appearances = max(1, min_appearances)

        names = [cfg["name"] for cfg in self.player_configs]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate player names detected. Names must be unique.")

        # Track per-name appearances across all games
        self.appearances = {name: 0 for name in names}
        
        # Track model usage across games
        self.model_usage = defaultdict(int)
        self.round_count = 0
        self.last_model_usage = defaultdict(int)  # Track when each model was last used
        
        # Create a queue to track recent model usage
        self.recent_models = deque(maxlen=threshold_rounds)

    def _sample_roster(self) -> List[Dict[str, str]]:
        """
        Build a roster for the next game.
        - If >4 available, sample 4 randomly.
        - If 2..4 available, use all.
        """
        total = len(self.player_configs)
        if total > 4:
            return random.sample(self.player_configs, 4)
        return list(self.player_configs)  # total is 2..4

    def _update_counts(self, roster: List[Dict[str, str]]) -> None:
        for cfg in roster:
            self.appearances[cfg["name"]] += 1

    def _all_reached_threshold(self) -> bool:
        return min(self.appearances.values()) >= self.min_appearances

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
        """Run games until all players reach minimum appearances with threshold enforcement"""
        print(f"Running games until all players appear at least {self.min_appearances} time(s)")
        print(f"Threshold enforcement: {self.threshold_rounds} rounds")
        print("Model usage tracking enabled - all models must play at least once every 20 rounds")
        
        game_num = 0
        while not self._all_reached_threshold():
            game_num += 1
            print(f"\n=== Start Game #{game_num} ===")
            
            # Check if we need to enforce threshold
            if self._should_force_model_usage():
                print(f"Threshold enforcement active at round {self.round_count}")
                priority_models = self._get_priority_models()
                print(f"Models that need to play: {priority_models}")
            
            # Get adjusted player configs
            adjusted_configs = self._adjust_player_configs_for_threshold()
            
            # Sample roster from adjusted configs
            roster = self._sample_roster_from_configs(adjusted_configs)
            
            print(f"Roster: {[p['name'] for p in roster]}")

            # Create and run new game
            game = Game(roster)
            game.start_game()

            # Update per-name tallies
            self._update_counts(roster)

            # Update model usage tracking
            used_models = [config["model"] for config in roster]
            self._update_model_usage(game.round_count, used_models)
            
            print(f"Game {game_num} ended after {game.round_count} rounds")
            print(f"Current model usage: {dict(self.model_usage)}")

            # Progress display
            self._print_progress(game_num)

        # Print final statistics
        print(f"\n=== DONE ===")
        print(f"All {len(self.appearances)} players reached at least {self.min_appearances} appearance(s).")
        print(f"Total games played: {game_num}")
        print(f"Total rounds played: {self.round_count}")
        print(f"Model usage counts: {dict(self.model_usage)}")
        print(f"Average rounds per model: {self.round_count / len(self.player_configs):.1f}")

    def _sample_roster_from_configs(self, configs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Sample roster from given configs"""
        total = len(configs)
        if total > 4:
            return random.sample(configs, 4)
        return list(configs)

    def _print_progress(self, game_num: int) -> None:
        remaining = {n: max(0, self.min_appearances - c) for n, c in self.appearances.items()}
        pending = sum(1 for r in remaining.values() if r > 0)
        print(f"\n[Progress after Game #{game_num}]  (players still below target: {pending})")
        print("Name".ljust(18), "Appearances".rjust(12), "Remaining".rjust(12))
        for name, cnt in sorted(self.appearances.items(), key=lambda kv: (self.min_appearances - kv[1], kv[0])):
            rem = max(0, self.min_appearances - cnt)
            print(name.ljust(18), str(cnt).rjust(12), str(rem).rjust(12))

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Run Liars Bar repeatedly until every player has appeared at least N times (N = --min-appearances)."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-m", "--min-appearances",
        type=int,
        default=2,
        help="Minimum number of appearances required per player (default: 2)."
    )
    parser.add_argument(
        '-t', '--threshold',
        type=int,
        default=20,
        help='Number of rounds after which all models must have played (default: 20)'
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    # Example player configs (names MUST be unique)
    
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
        {"name": "Maria",   "model": "gpt-4o-mini"},
    ]

    print("Multi-Game Runner Configuration:")
    print(f"Min appearances per player: {args.min_appearances}")
    print(f"Threshold rounds: {args.threshold}")
    print("Player configurations:")
    for config in player_configs:
        print(f"  Player: {config['name']}, Model: {config['model']}")
    print("-" * 50)

    # Create and run multiple games
    runner = MultiGameRunner(
        player_configs, 
        threshold_rounds=args.threshold,
        min_appearances=args.min_appearances
    )
    runner.run_games()
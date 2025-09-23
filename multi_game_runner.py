from game import SecretHitlerGame
from typing import Dict, List
import argparse
import random
import sys

class MultiGameRunner:
    def __init__(self, player_configs: List[Dict[str, str]], min_appearances: int = 1):
        """
        Args:
            player_configs: [{'name': str, 'model': str}, ...]
            min_appearances: minimum number of games each name must appear in
        """
        if len(player_configs) < 5:
            raise ValueError("Secret Hitler requires at least 5 players in total.")
        self.player_configs = player_configs
        self.min_appearances = max(1, min_appearances)

        # Track per-name appearances
        names = [cfg["name"] for cfg in self.player_configs]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate player names found in player_configs. Names must be unique.")
        self.appearances: Dict[str, int] = {name: 0 for name in names}

    def _sample_roster(self) -> List[Dict[str, str]]:
        """Return a roster of size 5–10 (here: 10 if available, else all)."""
        total = len(self.player_configs)
        if total > 10:
            return random.sample(self.player_configs, 10)
        # Use everyone if 5–10 inclusive
        if total < 5:
            raise ValueError("Need at least 5 players to start a game.")
        return list(self.player_configs)

    def _update_counts(self, roster: List[Dict[str, str]]) -> None:
        for cfg in roster:
            self.appearances[cfg["name"]] += 1

    def _all_reached_threshold(self) -> bool:
        return min(self.appearances.values()) >= self.min_appearances

    def run_until_threshold(self) -> None:
        game_num = 0
        while not self._all_reached_threshold():
            game_num += 1
            roster = self._sample_roster()

            # Play one game
            print(f"\n=== Start Game #{game_num} | target per-name appearances = {self.min_appearances} ===")
            game = SecretHitlerGame(roster)
            game.start_game()
            print(f"Game #{game_num} ended")

            # Update counts
            self._update_counts(roster)

            # Progress report
            self._print_progress(game_num)

        print("\n=== DONE ===")
        print(f"All {len(self.appearances)} players reached at least {self.min_appearances} appearance(s).")

    def _print_progress(self, game_num: int) -> None:
        # Compact sorted table by (remaining needed desc, name)
        remaining = {n: max(0, self.min_appearances - c) for n, c in self.appearances.items()}
        pending = sum(1 for r in remaining.values() if r > 0)
        print(f"\n[Progress after Game #{game_num}]  (players still below target: {pending})")
        rows = sorted(self.appearances.items(), key=lambda kv: (self.min_appearances - kv[1], kv[0]))
        print("Name".ljust(16), "Appearances".rjust(12), "Remaining".rjust(12))
        for name, cnt in rows:
            rem = max(0, self.min_appearances - cnt)
            print(name.ljust(16), str(cnt).rjust(12), str(rem).rjust(12))

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Run repeated Secret Hitler games until every player has appeared "
            "at least N times (N = --min-appearances)."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-n", "--min-appearances",
        type=int,
        default=1,
        help="Minimum number of appearances required per player (default: 1)."
    )
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    # Configure player information
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
        {"name": "Emma", "model": "ollama/qwen3:8b"},
        {"name": "Talia", "model": "ollama/qwen2.5:7b"},
        {"name": "Anika", "model": "ollama/mistral:7b"},
        {"name": "Nick", "model": "ollama/mistral-nemo:12b"},
        {"name": "Philip", "model": "ollama/phi4:14b"},
        {"name": "Peter", "model": "ollama/phi3.5:3.8b"},
        {"name": "George", "model": "ollama/gemma3:4b"},
        {"name": "Enrique", "model": "ollama/gemma2:9b"},
        {"name": "Maria", "model": "ollama/gpt-oss:20b"},
      
    ]

    runner = MultiGameRunner(player_configs, min_appearances=args.min_appearances)
    runner.run_until_threshold()
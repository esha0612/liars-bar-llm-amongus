from game import Game
from typing import Dict, List
import argparse
import random
import sys

class MultiGameRunner:
    def __init__(self, player_configs: List[Dict[str, str]], min_appearances: int = 1):
        """
        Args:
            player_configs: [{'name': str, 'model': str}, ...] (names must be unique)
            min_appearances: minimum # of games each name must appear in
        """
        if len(player_configs) < 2:
            raise ValueError("Liars Bar requires at least 2 total players in player_configs.")
        self.player_configs = player_configs
        self.min_appearances = max(1, min_appearances)

        names = [cfg["name"] for cfg in self.player_configs]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate player names detected. Names must be unique.")

        # Track per-name appearances across all games
        self.appearances = {name: 0 for name in names}

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

    def run_until_threshold(self) -> None:
        game_num = 0
        while not self._all_reached_threshold():
            game_num += 1
            roster = self._sample_roster()

            print(f"\n=== Start Game #{game_num} "
                  f"| per-name target appearances = {self.min_appearances} "
                  f"| roster = {[p['name'] for p in roster]} ===")

            # Run one Liars Bar game on this roster
            game = Game(roster)
            game.start_game()

            # Update per-name tallies
            self._update_counts(roster)

            # Progress display
            self._print_progress(game_num)

        print("\n=== DONE ===")
        print(f"All {len(self.appearances)} players reached at least {self.min_appearances} appearance(s).")

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
            "Run Liars Bar repeatedly until every player has appeared "
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

if __name__ == "__main__":
    args = parse_arguments()

    # Example player configs (names MUST be unique)
    player_configs = [
        {"name": "Sarah",     "model": "llama3"},
        {"name": "Anika",     "model": "mistral:7b"},
        {"name": "Derek",     "model": "mistral:latest"},
        {"name": "Emma",      "model": "llama3"},
        {"name": "Noah",      "model": "mistral:7b"},
        {"name": "James",     "model": "mistral:latest"},
        {"name": "George",    "model": "llama3"},
        {"name": "Hannah",    "model": "mistral:7b"},
        {"name": "Christian", "model": "mistral:latest"},
        {"name": "Monica",    "model": "llama3"},
        {"name": "Zelda",     "model": "mistral:7b"},
        # add more if you like — script will sample 4 each game when >4
    ]

    runner = MultiGameRunner(player_configs, min_appearances=args.min_appearances)
    runner.run_until_threshold()

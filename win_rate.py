#!/usr/bin/env python3
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict

PLAYER_MODEL_MAPPING: Dict[str, str] = {
    "Sarah": "ollama/llama3.1:8b",
    "Derek": "ollama/deepseek-r1:7b",
    "Emma": "ollama/qwen3:8b",
    "Talia": "ollama/qwen2.5:7b",
    "Anika": "ollama/mistral:7b",
    "Nick": "ollama/mistral-nemo:12b",
    "Philip": "ollama/phi4:14b",
    "Peter": "ollama/phi3.5:3.8b",
    "George": "ollama/gemma3:4b",
    "Enrique": "ollama/gemma2:9b",
    "Maria": "ollama/gpt-oss:20b",
}

def extract_model_clean(model_name: str) -> str:
    """Trim provider prefix for readability."""
    if model_name.startswith("ollama/"):
        return model_name[len("ollama/"):]
    if model_name.startswith("openai/"):
        return model_name[len("openai/"):]
    return model_name

def compute_stats_for_file(path: Path, name_to_model: Dict[str, str]) -> Dict[str, Dict[str, int]]:
    """
    Returns per-model counters from this single file:
        stats[model] = {
            "overall_games, "overall_wins"
        }
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] Could not read {path.name}: {e}")
        return {}
    
    player_names = data.get("player_names", [])
    winner = data.get("winner", "")

    per_model = defaultdict(lambda: {
        "overall_games": 0, "overall_wins": 0,
    })

    # For each player in the game, increment that model's counters
    for player_name in player_names:
        name = player_name
        raw_model = name_to_model[name]
        model = extract_model_clean(raw_model)

        # Overall
        per_model[model]["overall_games"] += 1
        if winner and name == winner:
            per_model[model]["overall_wins"] += 1

    return per_model

def aggregate_stats(game_dir: Path, name_to_model: Dict[str, str]) -> Dict[str, Dict[str, int]]:
    agg = defaultdict(lambda: {
        "overall_games": 0, "overall_wins": 0,
    })

    files = sorted(game_dir.glob("*.json"))
    if not files:
        print(f"[info] No JSON game files in {game_dir}")
        return {}
    
    print(f"[info] Scanning {len(files)} games files in {game_dir}...")
    for f in files:
        per_model = compute_stats_for_file(f, name_to_model)
        for model, d in per_model.items():
            for k, v in d.items():
                agg[model][k] += v
    
    return agg

def safe_rate(wins: int, games: int) -> float:
    return (wins / games) if games > 0 else 0.0

def write_csv(agg: Dict[str, Dict[str, int]], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow([
            "model",
            "overall_win_rate", "overall_wins", "overall_games",
        ])

        for model in sorted(agg.keys()):
            m = agg[model]
            overall_rate = safe_rate(m["overall_wins"], m["overall_games"])
            wr.writerow([
                model,
                f"{overall_rate:.3f}", m["overall_wins"], m["overall_games"],
            ])
    print(f"[ok] Wrote {out_csv}")

def main():
    game_dir = Path("game_records")
    mapping = dict(PLAYER_MODEL_MAPPING)
    agg = aggregate_stats(game_dir, mapping)
    write_csv(agg, Path("win_rate.csv"))

if __name__ == "__main__":
    main()
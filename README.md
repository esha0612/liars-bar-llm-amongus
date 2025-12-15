# Social Simulative Games

A collection of social-simulation / social-deduction game runners that use local LLMs (via Ollama) to simulate autonomous agents.

## File structure

The program is mainly divided into two parts, the game body and the analysis tool

### Game body

`game.py` Liars Bar game main program

`player.py` LLM agent participating in the game

`game_record.py` Used to save and extract game records

`llm_client.py` Used to configure the model interface and initiate LLM requests

`multi_game_runner.py` Used to batch run multiple rounds of games

### Analysis tool

`game_analyze.py` Used to count all game data

`player_matchup_analyze.py` Used to extract game records between AI opponents for analysis

`json_convert.py` Used to convert json game records into readable text

## Configuration

Ensure you have `python3` installed on your system. The runner scripts expect `python3` on your PATH.

Dependencies
```
pip install ollama
```

Ollama setup
```
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Download the models you want to run with Ollama, for example:
```
ollama pull qwen3:8b
```

The API configuration of this project is in `multi_llm_client.py` / `llm_client_ollama.py` and we currently support local Ollama models only (OpenAI is not supported in this repository).

## Usage

### Run

After completing the project configuration, set the correct model name in the `player_configs` of `game.py` and `multi_game_runner.py` (or the runner you plan to use).

Run a single game (default for a configured game):
```bash
python3 game.py
```

Run multiple games (batched runner). Example for Mafia / Liars Bar / Paranoia:
```bash
python3 multi_game_runner.py -n 40
```

- The `-n <number>` flag specifies the minimum number of appearances each model must have (independent of rounds). The runner will continue executing games until every model has participated in at least `n` games.
- The example above (`-n 40`) is intended for bulk runs of Mafia, Liars Bar, and Paranoia game configurations. For other games (e.g., Secret Hitler), you can specify any number after `-n` to control the minimum per-model appearances.

Branch / Game selection
- Use `git checkout <branch-name>` to switch to the branch for the game you want to run. Example:
```bash
git checkout mafiaV1   # play Mafia
git checkout paranoiaRPG  # play Paranoia / Liars Bar variants
```
Each branch contains the appropriate game rules and player configurations.

### Analysis

Game records are saved as JSON in the `game_records/` folder.

Scripts to generate aggregate outputs:

- `restructured_social_dynamics_analysis.csv` (script): produces a long CSV table with main and sub-categories for all annotated statements. See `restructured_social_dynamics_analysis.csv` for expected output format.
- `generate_small_summary.py`: produces a shorter summary CSV applying confidence / frequency thresholds (the shorter summary used in analysis).

Examples:
```bash
python3 generate_small_summary.py  # produce condensed summary CSV with thresholds
```
## Known Issues

The output of local LLMs can be unstable during structured phases. When model output does not follow the expected format, the runner will retry. If runs fail repeatedly due to generation issues:

- Increase retry counts in the player code (e.g., `player.py`).
- Harden prompt templates in the `prompts/` folder to enforce structured JSON outputs.
- Use a larger local model for higher-quality structured outputs or adjust temperature toward 0.

If you need help wiring a specific model or debugging generation failures, I can add utilities to validate and sanitize model responses before they are recorded.

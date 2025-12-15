# Blood on the Clocktower LLM

An AI version of Blood on the Clocktower (Lite) driven by large language models, featuring both Ollama and OpenAI model support.

## Game Overview

Blood on the Clocktower is a social deduction game where players are divided into Good and Evil teams. The Good team must identify and eliminate the Demon (Imp) before they're all killed, while the Evil team tries to eliminate enough Good players to win.

### Roles in this Lite Version

**Good Team:**
- **Empath** - Learns if a living neighbor is Evil
- **Fortune Teller** - Learns if a specific pair of players has an Evil player
- **Undertaker** - Learns the character of the most recently executed player
- **Monk** - Protects one player each night from being killed
- **Ravenkeeper** - Learns the character of one player when they die

**Evil Team:**
- **Imp (Demon)** - Kills one player each night
- **Poisoner (Minion)** - Poisons one player each night, making their information false

## File Structure

### Game Core
- `game.py` - Blood on the Clocktower game main program (`BotCGame` class)
- `player.py` - LLM agents participating in the game with role-specific abilities
- `game_record.py` - Used to save and extract game records
- `multi_llm_client.py` - Unified interface supporting both Ollama and OpenAI models
- `multi_game_runner.py` - Used to batch run multiple rounds of games

### Analysis Tools
- `game_analyze.py` - Used to count all game data
- `player_matchup_analyze.py` - Used to extract game records between AI opponents for analysis
- `json_convert.py` - Used to convert json game records into readable text

### Prompts
- `prompt/botc_rule_base.txt` - Core game rules and mechanics
- `prompt/table_talk_botc.txt` - Day phase discussion prompts
- `prompt/nominate_execute_prompt.txt` - Execution nomination prompts
- `prompt/vote_execute_prompt.txt` - Execution voting prompts
- `prompt/imp_kill_prompt.txt` - Demon kill action prompts
- `prompt/poisoner_poison_prompt.txt` - Poisoner action prompts
- `prompt/monk_protect_prompt.txt` - Monk protection prompts
- `prompt/fortune_teller_pair_prompt.txt` - Fortune Teller investigation prompts
- `prompt/ravenkeeper_target_prompt.txt` - Ravenkeeper target selection prompts

## Configuration

### Dependencies
```bash
pip install ollama
pip install python-dotenv  # Optional, for .env file support
```

### Ollama Setup
To run models using Ollama locally:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Download models you want to use:
```bash
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull qwen2.5:7b
# Add more models as needed
```

### Model Configuration
The project uses `multi_llm_client.py` to automatically route requests to the appropriate service:
- Models like `llama3`, `mistral:7b` → Ollama (local)

## Usage

### Run Single Game
```bash
python3 game.py
```

### Run Multiple Games
```bash
python3 multi_game_runner.py -n

Specify the number of games that you want to run after `n`

### Game Flow
1. **Setup** - Players are assigned roles (Good/Evil)
2. **Day Phase** - Players discuss and vote to execute someone
3. **Night Phase** - Players with night abilities use them
4. **Repeat** - Continue until Good eliminates the Demon or Evil achieves majority

### Analysis

Game records are saved in the `game_records/` folder in JSON format.

Convert JSON to readable text:
```bash
python3 json_convert.py
```

Extract AI vs AI matchups:
```bash
python3 player_matchup_analyze.py
```

Analyze all game data:
```bash
python3 game_analyze.py
```

## Multi-LLM Support

This implementation supports both local and cloud-based models:

**Local Models (via Ollama):**
- llama3.1:8b, mistral:7b, qwen2.5:7b, deepseek-r1:8b
- phi4:14b, gemma2:9b, and many others

## Game Features

- **Role-based abilities** - Each character has unique night actions
- **Social deduction** - Players must deduce roles through discussion
- **Dynamic gameplay** - Day/night cycle with voting and executions
- **Multi-model support** - Mix local and cloud models in the same game
- **Comprehensive logging** - Detailed game records for analysis

## Known Issues

- Model outputs may occasionally be unstable during voting phases
- The system includes automatic retry logic for failed model calls
- If experiencing frequent interruptions, consider adjusting prompts in the `prompt/` folder to be more specific about output format requirements

## Contributing

This is a simplified version of Blood on the Clocktower. For the full game with all characters and mechanics, refer to the official Blood on the Clocktower rules.

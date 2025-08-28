# Mafia LLM

An AI version of the classic Mafia social deduction game driven by large language models, featuring both Ollama and OpenAI model support.

## Game Overview

Mafia is a social deduction game where players are divided into two teams: **Mafia** (Evil) and **Townspeople** (Good). The Mafia tries to eliminate enough Townspeople to gain majority, while the Townspeople must identify and eliminate all Mafia members before they're outnumbered.

### Roles in this Implementation

**Good Team (Townspeople):**
- **Doctor** - Can save one player each night from being killed
- **Detective** - Can investigate one player each night to learn if they're Mafia
- **Townsperson** - Regular villagers with no special abilities

**Evil Team (Mafia):**
- **Mafia** - Can kill one player each night

## File Structure

### Game Core
- `game.py` - Mafia game main program (`MafiaGame` class)
- `player.py` - LLM agents participating in the game with role-specific abilities
- `game_record.py` - Used to save and extract game records
- `multi_llm_client.py` - Unified interface supporting both Ollama and OpenAI models
- `multi_game_runner.py` - Used to batch run multiple rounds of games

### Analysis Tools
- `game_analyze.py` - Used to count all game data
- `player_matchup_analyze.py` - Used to extract game records between AI opponents for analysis
- `json_convert.py` - Used to convert json game records into readable text

### Prompts
- `prompt/rule_base.txt` - Core game rules and mechanics
- `prompt/mafia_night_prompt.txt` - Mafia kill target selection prompts
- `prompt/doctor_night_prompt.txt` - Doctor protection target prompts
- `prompt/detective_night_prompt.txt` - Detective investigation target prompts
- `prompt/vote_prompt.txt` - Day phase voting prompts
- `prompt/impression_prompt.txt` - Player impression and suspicion prompts

## Configuration

### Dependencies
```bash
pip install openai
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
ollama pull deepseek-r1:8b
ollama pull phi4:14b
ollama pull gemma2:9b
# Add more models as needed
```

### OpenAI Setup
For OpenAI models, set your API key in a `.env` file:
```
OPENAI_API_KEY=your_api_key_here
```

### Model Configuration
The project uses `multi_llm_client.py` to automatically route requests to the appropriate service:
- Models like `llama3`, `mistral:7b` → Ollama (local)
- Models like `gpt-4o-mini` → OpenAI API

## Usage

### Run Single Game
```bash
python3 game.py
```

### Run Multiple Games
```bash
python3 multi_game_runner.py -n 10
```
Specify the number of games you want to run after -n. Each model will continue playing until it has participated in the specified number of rounds.”


### Game Flow
1. **Setup** - Players are randomly assigned roles (1 Mafia, 1 Doctor, 1 Detective, rest Townspeople)
2. **Night Phase** - Mafia kills, Doctor protects, Detective investigates
3. **Day Phase** - Players discuss, share impressions, and vote to eliminate someone
4. **Repeat** - Continue until Mafia achieves majority or all Mafia are eliminated

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
- phi4:14b, gemma2:9b, gemma3:4b, and many others

**Cloud Models (via OpenAI API):**
- gpt-4o-mini, gpt-4o, gpt-4-turbo

The system automatically detects which service to use based on the model name and routes requests accordingly.

## Game Features

### Core Mechanics
- **Hidden roles** - Players don't know each other's roles initially
- **Day/night cycle** - Alternating phases with different actions
- **Social deduction** - Players must deduce roles through discussion and voting
- **Information gathering** - Detective learns about players, Doctor can save lives

### Night Phase Actions
- **Mafia kill** - Mafia chooses one player to eliminate
- **Doctor save** - Doctor chooses one player to protect from death
- **Detective investigate** - Detective learns if a player is Mafia

### Day Phase Activities
- **Discussion rounds** - Players discuss suspicions and share information
- **Impression sharing** - Players express their thoughts about others
- **Voting** - Democratic elimination of suspected Mafia members

### AI Features
- **Role-based decision making** - Each role has specific prompts and strategies
- **Social interaction** - LLMs engage in realistic discussion and debate
- **Strategic thinking** - AI players adapt their strategies based on game state
- **Multi-model support** - Mix different AI models in the same game

## Game Rules

### Win Conditions
- **Mafia wins** - When Mafia members equal or outnumber remaining players
- **Townspeople win** - When all Mafia members are eliminated

### Special Rules
- **Tie votes** - If multiple players tie for most votes, no one is eliminated
- **Doctor protection** - If Doctor saves the Mafia's target, no one dies that night
- **Detective information** - Detective learns if investigated player is Mafia (true/false)
- **Role revelation** - Eliminated players reveal their role when voted out

## Known Issues

- Model outputs may occasionally be unstable during voting and discussion phases
- The system includes automatic retry logic for failed model calls
- If experiencing frequent interruptions, consider adjusting prompts in the `prompt/` folder to be more specific about output format requirements
- Some complex social deduction scenarios may require multiple attempts to resolve correctly

## Contributing

This is a classic Mafia implementation with AI players. The game follows traditional Mafia rules with the addition of special roles (Doctor and Detective) to balance gameplay.

## Branch Information

This is the **Mafia** branch, featuring:
- Classic Mafia social deduction gameplay
- Role-based AI decision making
- Day/night cycle with voting and elimination
- Multi-LLM support for diverse AI interactions
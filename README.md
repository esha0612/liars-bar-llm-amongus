# Paranoia LLM

An AI version of the Paranoia RPG social deduction game driven by large language models, featuring both Ollama and OpenAI model support.

## Game Overview

Paranoia is a darkly comedic social deduction game set in a dystopian future where players are Troubleshooters serving The Computer. The game combines elements of social deduction, hidden roles, and dark humor as players try to complete missions while secretly working against each other and avoiding accusations of treason.

### Core Concept

Players are Troubleshooters - citizens of Alpha Complex who serve The Computer. Each player has:
- **Public loyalty** to The Computer (mandatory)
- **Secret society membership** (illegal, but common)
- **Mutant powers** (illegal, but useful)
- **Personal agendas** (treasonous, but necessary for survival)

## File Structure

### Game Core
- `game.py` - Paranoia game main program (`ParanoiaGame` class)
- `player.py` - LLM agents participating in the game as Troubleshooters
- `computer.py` - The Computer as an LLM entity that judges accusations
- `game_record.py` - Used to save and extract game records
- `multi_llm_client.py` - Unified interface supporting both Ollama and OpenAI models
- `multi_game_runner.py` - Used to batch run multiple rounds of games

### Analysis Tools
- `game_analyze.py` - Used to count all game data
- `player_matchup_analyze.py` - Used to extract game records between AI opponents for analysis
- `json_convert.py` - Used to convert json game records into readable text

### Prompts
- `prompt/rule_base.txt` - Core game rules and Paranoia setting
- `prompt/mission_discussion_prompt.txt` - Mission strategy discussion prompts
- `prompt/sabotage_decision_prompt.txt` - Sabotage action decision prompts
- `prompt/accusation_prompt.txt` - Accusation and defense prompts
- `prompt/computer_judgment_prompt.txt` - The Computer's judgment prompts
- `prompt/reflection_prompt.txt` - Post-action reflection prompts

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
python3 multi_game_runner.py -n

Specify the number of games that you want to run after `n`

### Game Flow
1. **Setup** - Players are assigned as Troubleshooters with secret roles
2. **Mission Phase** - The Computer assigns missions, players discuss strategy publicly
3. **Sabotage Phase** - Players secretly choose to sabotage or support the mission
4. **Accusation Phase** - Players can accuse others of treason
5. **Computer Judgment** - The Computer (AI) decides the fate of accused players
6. **Repeat** - Continue until The Computer declares a winner

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
- **Hidden agendas** - Players have secret societies and mutant powers
- **Mission-based gameplay** - Complete Computer-assigned tasks
- **Social deduction** - Identify traitors while hiding your own treason
- **Accusation system** - Accuse others of treason with AI judgment
- **Clone system** - Players have multiple lives (clones)

### Mission Phase
- **Public discussion** - Players discuss mission strategy openly
- **Secret sabotage** - Players secretly choose to help or hinder
- **Mission resolution** - Success/failure based on player actions

### Accusation Phase
- **Accusation mechanics** - Players can accuse others of treason
- **Defense system** - Accused players can defend themselves
- **Computer judgment** - AI Computer decides guilt/innocence
- **Consequences** - Guilty players face elimination

### AI Features
- **Role-based decision making** - Each player has unique motivations
- **Social interaction** - LLMs engage in paranoid discussions
- **Strategic deception** - AI players lie and manipulate
- **Computer AI** - The Computer as an AI entity making judgments

## Game Rules

### Win Conditions
- **Survival** - Outlive other Troubleshooters
- **Computer favor** - Please The Computer through actions
- **Elimination** - Remove rivals without appearing disloyal

### Special Rules
- **Happiness is mandatory** - Players must appear loyal to The Computer
- **Secret societies** - Players have hidden allegiances
- **Mutant powers** - Players have illegal abilities
- **Clone system** - Players have multiple lives
- **Computer judgment** - AI decides accusation outcomes

## Known Issues

- Model outputs may occasionally be unstable during mission discussion and accusation phases
- The system includes automatic retry logic for failed model calls
- If experiencing frequent interruptions, consider adjusting prompts in the `prompt/` folder to be more specific about output format requirements
- Some complex social deduction scenarios may require multiple attempts to resolve correctly

## Contributing

This is a Paranoia RPG implementation with AI players. The game follows the classic Paranoia setting with AI-driven social deduction mechanics.

## Branch Information

This is the **Paranoia** branch, featuring:
- Classic Paranoia RPG social deduction gameplay
- Mission-based objectives with sabotage mechanics
- AI Computer entity for judgment and rulings
- Multi-LLM support for diverse AI interactions
- Dark humor and dystopian setting

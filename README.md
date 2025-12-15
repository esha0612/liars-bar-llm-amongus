# Secret Hitler LLM

An AI version of the Secret Hitler social deduction game driven by large language models, featuring both Ollama and OpenAI model support.

## Game Overview

Secret Hitler is a social deduction game set in 1930s Germany where players are divided into two teams: **Liberals** (the majority) and **Fascists** (the minority, including Hitler). The game combines elements of hidden roles, government formation, policy enactment, and social deduction as players try to achieve their faction's win conditions while maintaining secrecy.

### Core Concept

Players are members of the German government during the rise of fascism:
- **Liberals** (majority) - Must enact 5 Liberal policies or execute Hitler to win
- **Fascists** (minority) - Must enact 6 Fascist policies or get Hitler elected Chancellor after 3+ Fascist policies
- **Hitler** (1 player) - A Fascist who doesn't know other Fascists in larger games

## File Structure

### Game Core
- `game.py` - Secret Hitler game main program (`SecretHitlerGame` class)
- `player.py` - LLM agents participating in the game as government members
- `game_record.py` - Used to save and extract game records
- `multi_llm_client.py` - Unified interface supporting both Ollama and OpenAI models
- `multi_game_runner.py` - Used to batch run multiple rounds of games

### Analysis Tools
- `game_analyze.py` - Used to count all game data
- `player_matchup_analyze.py` - Used to extract game records between AI opponents for analysis
- `json_convert.py` - Used to convert json game records into readable text

### Prompts
- `prompt/secret_hitler_rule_base.txt` - Core game rules and mechanics
- `prompt/nominate_prompt.txt` - President nomination prompts
- `prompt/vote_government_prompt.txt` - Government election voting prompts
- `prompt/table_talk_prompt.txt` - Public discussion prompts
- `prompt/president_discard_prompt.txt` - President policy discard prompts
- `prompt/chancellor_discard_prompt.txt` - Chancellor policy discard prompts
- `prompt/chancellor_veto_prompt.txt` - Veto request prompts
- `prompt/president_veto_accept_prompt.txt` - Veto acceptance prompts
- `prompt/investigate_choose_prompt.txt` - Investigation target prompts
- `prompt/execution_prompt.txt` - Execution target prompts
- `prompt/special_election_prompt.txt` - Special election prompts
- `prompt/policy_peek_comment_prompt.txt` - Policy peek comment prompts

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
ollama pull deepseek-r1:8b
ollama pull phi4:14b
ollama pull gemma2:9b
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
python3 multi_game_runner.py -n 2
```
Specify the number of occurrences you want each player to appear after -n. Each model will continue playing until it has participated in the specified number of rounds.


### Game Flow
1. **Setup** - Players are assigned roles (Liberals, Fascists, Hitler)
2. **Presidency Rotation** - Presidency passes to next player
3. **Nomination** - President nominates a Chancellor
4. **Table Talk** - Public discussion about the government
5. **Election** - All players vote JA/NEIN on the government
6. **Legislative Session** - If elected, President and Chancellor enact policies
7. **Executive Powers** - Special actions triggered by Fascist policies
8. **Repeat** - Continue until win condition is met

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

## Game Features

### Core Mechanics
- **Hidden roles** - Players don't know each other's factions initially
- **Government formation** - President nominates Chancellor, players vote
- **Policy enactment** - Draw 3 policies, discard 1, pass 2, discard 1, enact 1
- **Executive powers** - Special actions triggered by Fascist policies
- **Social deduction** - Players must deduce roles through discussion and voting

### Policy System
- **Liberal policies** - Help the Liberal faction win
- **Fascist policies** - Help the Fascist faction win and unlock executive powers
- **Policy deck** - 6 Liberal, 11 Fascist policies (official distribution)
- **Veto power** - Unlocked after 5 Fascist policies, allows discarding both policies

### Executive Powers
- **Investigate Loyalty** - President learns a player's faction
- **Special Election** - President chooses next President
- **Execution** - President eliminates a player (Hitler execution = Liberal win)
- **Policy Peek** - President sees top 3 policies

### AI Features
- **Role-based decision making** - Each faction has different strategies
- **Social interaction** - LLMs engage in political discussions
- **Strategic deception** - AI players lie and manipulate
- **Government formation** - AI players negotiate and vote on governments

## Game Rules

### Win Conditions
- **Liberals win** - Enact 5 Liberal policies OR execute Hitler
- **Fascists win** - Enact 6 Fascist policies OR Hitler becomes Chancellor after 3+ Fascist policies

### Special Rules
- **Term limits** - Last elected Chancellor cannot be nominated again
- **Election tracker** - Failed elections advance the tracker, at 3 a policy is top-decked
- **Secret knowledge** - Fascists know each other, Hitler may be blind in larger games
- **Veto power** - Unlocked after 5 Fascist policies, requires both President and Chancellor agreement

## Known Issues

- Model outputs may occasionally be unstable during government formation and policy enactment phases
- The system includes automatic retry logic for failed model calls
- If experiencing frequent interruptions, consider adjusting prompts in the `prompt/` folder to be more specific about output format requirements
- Some complex social deduction scenarios may require multiple attempts to resolve correctly

## Contributing

This is a Secret Hitler implementation with AI players. The game follows the official Secret Hitler rules with AI-driven social deduction mechanics.

## Branch Information

This is the **Secret Hitler** branch, featuring:
- Official Secret Hitler social deduction gameplay
- Government formation and policy enactment mechanics
- Executive powers and special actions
- Multi-LLM support for diverse AI interactions
- Historical political setting with hidden roles

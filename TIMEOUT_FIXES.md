# Timeout Fixes for Liars Bar LLM Game

## Problem
The game was hanging indefinitely when running the GSM (Game State Manager) due to LLM API calls without timeout mechanisms.

## Root Causes
1. **No timeout on LLM API calls**: Both OpenAI and Ollama API calls lacked timeout settings
2. **Infinite retry loops**: Player retry mechanisms could hang if LLM calls never returned
3. **No game-level timeout**: The main game loop had no maximum duration or round limits
4. **Network issues**: Slow or unresponsive LLM services could cause indefinite hanging

## Solutions Implemented

### 1. LLM Client Timeout (`multi_llm_client.py`)
- Added 30-second timeout for all API calls
- Added timeout parameter to OpenAI client initialization
- Added manual timeout checking for Ollama calls
- Graceful error handling for timeout scenarios

### 2. Player Retry Loop Timeouts (`player.py`)
- Added 60-second maximum retry time for all player operations
- Implemented fallback strategies when LLM calls fail:
  - `_fallback_play_cards()`: Plays first card in hand
  - `_fallback_challenge_decision()`: Defaults to not challenging
- Added delays between retries to avoid overwhelming APIs
- Better error logging with player identification

### 3. Game-Level Timeouts (`game.py`)
- Added 1-hour maximum game duration
- Added 50-round maximum limit
- Implemented timeout checks in main game loop
- Added graceful game ending with winner determination
- Timeout handling preserves game state and records

### 4. Reflection Timeout Handling
- Added error handling for reflection calls
- Preserves previous opinions if reflection fails
- Continues game even if some reflections fail

## Configuration

### Timeout Settings
```python
# LLM Client (multi_llm_client.py)
self.timeout = 30  # 30 seconds per API call

# Player (player.py)
self.max_retry_time = 60  # 60 seconds for all retries combined

# Game (game.py)
self.max_game_duration = 3600  # 1 hour maximum
self.max_rounds = 50  # 50 rounds maximum
```

### Fallback Strategies
- **Card Playing**: Plays first available card
- **Challenge Decisions**: Defaults to not challenging (safe option)
- **Reflection**: Keeps previous opinions
- **Game Ending**: Determines winner by card count

## Testing
Run the timeout test script to verify mechanisms:
```bash
python test_timeout.py
```

## Usage
The game now has robust timeout protection and will not hang indefinitely:
```bash
python game.py
```

## Benefits
1. **No more infinite hanging**: Game will always terminate within reasonable time
2. **Graceful degradation**: Game continues even if some LLM calls fail
3. **Better error reporting**: Clear logging of timeout and failure scenarios
4. **Preserved game state**: Game records are saved even on timeout
5. **Configurable limits**: Timeout values can be adjusted as needed

## Monitoring
The game will now print clear messages when:
- LLM calls timeout
- Fallback strategies are used
- Game ends due to timeout
- Maximum rounds are reached

This ensures you always know what's happening and why the game might end early.

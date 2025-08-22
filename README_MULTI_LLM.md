# Multi-LLM Client and Threshold System

This document describes the new multi-LLM client implementation and the threshold system for ensuring fair model usage across games.

## Overview

The system now supports both Ollama and OpenAI models through a unified client, and includes a threshold mechanism to ensure all models play at least once in every 20 rounds.

## Files Added/Modified

### New Files
- `multi_llm_client.py` - Unified client for both Ollama and OpenAI models
- `test_multi_llm.py` - Test script for the multi-LLM client
- `README_MULTI_LLM.md` - This documentation file

### Modified Files
- `player.py` - Updated to use the new multi-LLM client
- `multi_game_runner.py` - Enhanced with threshold system and updated player configurations

## Multi-LLM Client Features

### Automatic Model Detection
The `MultiLLMClient` automatically detects whether a model is an OpenAI model or an Ollama model based on the model name:

**OpenAI Models:**
- gpt-4o-mini
- gpt-4o
- gpt-4-turbo
- gpt-4
- gpt-3.5-turbo

**Ollama Models:**
- All other model names are treated as Ollama models

### Configuration
The client uses environment variables for configuration:

```bash
# OpenAI Configuration
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional, defaults to OpenAI

# Ollama Configuration  
export OLLAMA_BASE_URL="http://localhost:11434"  # Optional, defaults to localhost
```

### Usage
```python
from multi_llm_client import MultiLLMClient

client = MultiLLMClient()

# Works with both Ollama and OpenAI models
messages = [{"role": "user", "content": "Hello"}]

# Ollama model
content, reasoning = client.chat(messages, "Llama3.1:8b")

# OpenAI model
content, reasoning = client.chat(messages, "gpt-4o-mini")
```

## Threshold System

### Purpose
The threshold system ensures that all models get a fair chance to participate in games by requiring that each model plays at least once in every 20 rounds.

### How It Works
1. **Tracking**: The system tracks when each model was last used
2. **Enforcement**: After 20 rounds, if any model hasn't played recently, it gets priority in the next game
3. **Adjustment**: Player configurations are adjusted to prioritize models that need to play

### Configuration
```python
# In multi_game_runner.py
runner = MultiGameRunner(
    player_configs=player_configs,
    num_games=10,
    threshold_rounds=20  # Default: 20 rounds
)
```

### Command Line Usage
```bash
# Run 10 games with default 20-round threshold
python multi_game_runner.py

# Run 5 games with 15-round threshold
python multi_game_runner.py -n 5 -t 15

# Run 20 games with 30-round threshold
python multi_game_runner.py --num-games 20 --threshold 30
```

## Current Player Configuration

The system is configured with 11 models (10 Ollama + 1 OpenAI):

```python
player_configs = [
    {"name": "Sarah",   "model": "Llama3.1:8b"},
    {"name": "Derek",   "model": "Deepseek-r1:7b"},
    {"name": "Emma",    "model": "dolphin3:latest"},
    {"name": "Talia",   "model": "qwen 2.5:7b"},
    {"name": "Anika",   "model": "Mistral:7b"},
    {"name": "Nick",    "model": "Mistral-nemo:12b"},
    {"name": "Philip",  "model": "Phi4:14b"},
    {"name": "Peter",   "model": "Phi3.5:3.8b"},
    {"name": "George",  "model": "llava:7b"},
    {"name": "Enrique", "model": "Gemma2:9b"},
    {"name": "Maria",   "model": "gpt-4o-mini"}
]
```

## Testing

Run the test script to verify the multi-LLM client works:

```bash
python test_multi_llm.py
```

This will test both Ollama and OpenAI models to ensure they're working correctly.

## Requirements

Make sure you have the required dependencies:

```bash
pip install openai ollama
```

Also ensure:
1. Ollama is running locally (default: http://localhost:11434)
2. Required Ollama models are pulled
3. OpenAI API key is set (for OpenAI models)

## Backward Compatibility

The system maintains backward compatibility:
- `LLMClient = MultiLLMClient` alias is provided
- Existing code using `LLMClient` will continue to work
- The original `llm_client.py` and `llm_client_ollama.py` files remain unchanged

## Monitoring

The system provides detailed logging:
- Model usage statistics
- Threshold enforcement notifications
- Round counts and game statistics
- Final usage reports

Example output:
```
Threshold enforcement: Models that need to play: ['Llama3.1:8b', 'Deepseek-r1:7b']
Game 1 ended after 15 rounds
Current model usage: {'Llama3.1:8b': 1, 'Deepseek-r1:7b': 1, ...}
```

# Liars Bar LLM

An AI version of the Liars Bar battle framework driven by a large language model

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

Use the conda environment to configure the corresponding dependency packages:

```bash
pip install openai
pip install ollama
```

Also to run model using Ollama, you need to first:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```
to first initialize the ollama package on your server environment.

Then you need to download the model you need to run locally using ollama, you can find useful models in https://ollama.com/search. Also when you are trying to download model, like:
```bash
ollama pull qwen3:8b
```
to download the Qwen3 model with 8B's weights. Other models with other weights can do the same.

The API configuration of this project is in `llm_client.py`.

This project uses New API https://github.com/Calcium-Ion/new-api?tab=readme-ov-file to configure a unified interface call format. When using it, you need to configure the API interface of the corresponding model yourself.

You can also use a similar API management project One API https://github.com/songquanpeng/one-api to achieve unified interface calls.

## Usage

### Run

After completing the project configuration, set the correct model name in the `player_configs` of the main program entry of `game.py` and `multi_game_runner.py`

Run a single game:
```
python game.py
```

Run multiple games:
```
python multi_game_runner.py -n 3
```
Specify the number of games you want to run after `-n`. Each model will continue playing until it has participated in the specified number of rounds.”
### Analysis

The game records will be saved in the `game_records` folder in the directory in json format

Convert the json file to a more readable text format, and the converted file will be saved in the `converted_game_records` folder in the directory

```
python json_convert.py
```

Extract all the games between AIs in the game, and the converted files will be saved in the `matchup_records` folder in the directory

```
python player_matchup_analyze.py
```

Count and print all game data

```
python game_analyze.py
```

## Demo

The project has run 50 games with 11 models (DeepSeek-R1, o4-mini, Qwen3, Gemma3, etc) as players, and the records are stored in the `demo_records` folder.

## Known Issues

The output of the model may be unstable during the card-playing and questioning stages. When the output cannot meet the game requirements, it will automatically retry. If the run is interrupted multiple times due to output problems, you can increase the number of retries for calling large models in `choose_cards_to_play` and `decide_challenge` of `player.py`, or modify the prompts in `play_card_prompt_template.txt` and `challenge_prompt_template.txt` in the `prompt` folder to strengthen the restrictions on the output format (which may have a certain impact on the model's reasoning ability).

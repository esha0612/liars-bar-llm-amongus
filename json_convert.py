import os
import json

def convert_game_record_to_chinese_text(json_file_path):
    """Convert game record to readable text style"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        game_data = json.load(f)

    game_id = game_data["game_id"]
    player_names = game_data["player_names"]
    rounds = game_data["rounds"]
    winner = game_data.get("winner", "Game is still ongoing")

    # Introduction
    text = f"Game ID: {game_id}\n"
    text += f"Player List: {', '.join(player_names)}\n\n"
    text += "════════════════════════════\n"
    text += "          Game Start\n"
    text += "════════════════════════════\n\n"

    for round_record in rounds:
        text += "────────────────────────────\n"
        text += f"Round {round_record['round_id']}\n"
        text += "────────────────────────────\n"
        text += f"Round Players: {', '.join(round_record['round_players'])}\n"
        text += f"Round starts with {round_record['starting_player']}.\n\n"

        active_players = round_record["round_players"]
        for player_name, opinions in round_record["player_opinions"].items():
            if player_name in active_players:
                text += f"{player_name} Opinions about other players:\n"
                for other_player, opinion in opinions.items():
                    if other_player in active_players:
                        text += f"  - {other_player}: {opinion}\n"
                text += "\n"
        
        text += "Dealing cards...\n\n"
        text += f"Round Target Card: {round_record['target_card']}\n"

        if "player_initial_states" in round_record:
            text += "Initial States of Players:\n"
            for player_state in round_record["player_initial_states"]:
                player_name = player_state["player_name"]
                bullet_pos = player_state["bullet_position"]
                gun_pos = player_state["current_gun_position"]
                initial_hand = ", ".join(player_state["initial_hand"])
                
                text += f"{player_name}:\n"
                text += f"  - Bullet Position: {bullet_pos}\n"
                text += f"  - Current Gun Position: {gun_pos}\n"
                text += f"  - Initial Hand: {initial_hand}\n\n"

        text += "----------------------------------\n"
        for action in round_record["play_history"]:
            text += f"Turn for {action['player_name']} to play\n"
            text += f"{action['player_name']} {action['behavior']}\n"
            text += f"Played Cards: {'、'.join(action['played_cards'])}, Remaining Cards: {'、'.join(action['remaining_cards'])} (Target Card: {round_record['target_card']})\n"
            text += f"Play Reason: {action['play_reason']}\n\n"

            if action['was_challenged']:
                text += f"{action['next_player']} chooses to challenge\n"
                text += f"Challenge Reason: {action['challenge_reason']}\n"
            else:
                text += f"{action['next_player']} chooses not to challenge\n"
                text += f"Not Challenge Reason: {action['challenge_reason']}\n"

            if action['was_challenged']:
                if action['challenge_result']:
                    text += f"Challenge successful, {action['player_name']} exposed.\n"
                else:
                    text += f"Challenge failed, {action['next_player']} punished.\n"
            text += "\n----------------------------------\n"

        if round_record['round_result']:
            result = round_record['round_result']
            text += f"Shooting Result:\n"

            if result["bullet_hit"]:
                text += f"Bullet hit, {result['shooter_name']} died.\n"
            else:
                text += f"Bullet missed, {result['shooter_name']} survived.\n"

            text += "\n"

    text += "\n════════════════════════════\n"
    text += "          Game End\n"
    text += "════════════════════════════\n\n"
    
    text += "★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★\n"
    text += f"     Final Winner: {winner}\n"
    text += "★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★\n"
    
    return text

def process_game_records(input_directory, output_directory):
    """Process all game record JSON files in the directory and generate readable TXT files to the specified output directory"""
    # 确保输出目录存在
    os.makedirs(output_directory, exist_ok=True)
    
    for filename in os.listdir(input_directory):
        if filename.endswith('.json'):
            json_file_path = os.path.join(input_directory, filename)
            txt_file_path = os.path.join(output_directory, os.path.splitext(filename)[0] + '.txt')

            print(f"Processing {filename}...")
            game_text = convert_game_record_to_chinese_text(json_file_path)

            with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(game_text)
            print(f"Generated: {txt_file_path}")

if __name__ == '__main__':
    game_records_directory = 'game_records'
    output_directory = 'converted_game_records'  # 新的输出目录
    process_game_records(game_records_directory, output_directory)
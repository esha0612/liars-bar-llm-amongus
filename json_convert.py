import os
import json

def convert_game_record_to_chinese_text(json_file_path):
    """Convert Mafia game record to readable text style"""
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
        text += f"Alive Players: {', '.join(round_record['alive_players'])}\n\n"

        # Night Phase
        text += "Night Phase:\n"
        night = round_record.get("night_events", {})
        if night:
            text += f"  - Mafia chose to kill: {night.get('mafia_target', 'Unknown')}\n"
            text += f"  - Doctor chose to save: {night.get('doctor_save', 'Unknown')}\n"
            if night.get("detective_investigation"):
                target = night["detective_investigation"]
                result = "Yes" if night.get("investigation_result") else "No"
                text += f"  - Detective investigated {target}. Mafia? {result}\n"
        else:
            text += "  - No night actions recorded.\n"
        text += "\n"

        # Day Phase
        text += "Day Phase:\n"
        discussion = round_record.get("discussion", [])
        for line in discussion:
            text += f"  - {line}\n"
        text += "\n"

        votes = round_record.get("votes", [])
        text += "Voting Results:\n"
        if votes:
            for vote in votes:
                text += f"  - {vote['voter']} voted for {vote['voted']}\n"
        else:
            text += "  - No votes recorded.\n"
        text += "\n"

        eliminated = round_record.get("eliminated_player")
        if eliminated:
            role = round_record.get("elimination_role", "Unknown")
            text += f"Eliminated: {eliminated} (Role: {role})\n"
        else:
            text += "No one was eliminated this round.\n"

        text += "\n----------------------------------\n"

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
import random
from typing import List, Dict, Optional
from player import Player
from game_record import GameRecord
import sys
import os
from datetime import datetime

class Tee:
    def __init__(self, filename, mode="w"):
        self.terminal = sys.stdout
        self.log = open(filename, mode, encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Set up log file with timestamp to avoid overwriting
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, f"mafia_game_{timestamp}.txt")
sys.stdout = Tee(log_path)

class MafiaGame:
    def __init__(self, player_configs: List[Dict[str, str]], roles: Optional[List[str]] = None):
        """
        Initialize the Mafia game.
        Args:
            player_configs: List of dicts with 'name' and 'model' for each player.
            roles: Optional list of roles to assign (if None, assign automatically based on player count).
        """
        self.players = self.assign_roles(player_configs, roles)
        self.alive_players = self.players.copy()
        self.day_count = 0
        self.night_count = 0
        self.phase = "night"  # or "day"
        self.game_record = GameRecord()
        self.winner = None

    def assign_roles(self, player_configs: List[Dict[str, str]], roles: Optional[List[str]]) -> List[Player]:
        """
        Assign roles to players randomly. Roles: 1 Mafia, 1 Doctor, 1 Detective, rest Townsperson.
        """
        num_players = len(player_configs)
        if roles is None:
            roles_list = ["Mafia", "Doctor", "Detective"]
            roles_list += ["Townsperson"] * (num_players - len(roles_list))
        else:
            roles_list = roles.copy()
            assert len(roles_list) == num_players, "Number of roles must match number of players."
        random.shuffle(roles_list)
        players = []
        for config, role in zip(player_configs, roles_list):
            players.append(Player(config["name"], model_name=config["model"], role=role))
        return players

    def start_game(self):
        """
        Main game loop: alternate between night and day until win condition is met.
        """
        # Initialize game record
        self.game_record.start_game(self.players)
        
        while not self.check_win_condition():
            if self.phase == "night":
                self.night_phase()
                self.phase = "day"
            else:
                self.day_phase()
                self.phase = "night"
        self.announce_winner()

    def night_phase(self):
        print(f"\n--- Night {self.night_count + 1} ---")
        self.night_count += 1
        alive_players = [p for p in self.players if p.alive]
        alive_names = [p.name for p in alive_players]
        
        # Start recording night phase
        self.game_record.start_night_phase(self.night_count, alive_names)

        # Mafia chooses a target (only one Mafia in this setup)
        mafia = next((p for p in alive_players if p.role == "Mafia"), None)
        mafia_target = None
        if mafia:
            mafia_choices = [n for n in alive_names if n != mafia.name]
            if mafia_choices:
                mafia_target = mafia.choose_mafia_target(mafia_choices)
                print(f"Mafia has chosen a target.")
                # Record mafia action
                self.game_record.record_night_action(
                    player_name=mafia.name,
                    role=mafia.role,
                    action_type="mafia_kill",
                    target_name=mafia_target
                )

        # Doctor chooses someone to save
        doctor = next((p for p in alive_players if p.role == "Doctor"), None)
        doctor_save = None
        if doctor:
            doctor_save = doctor.choose_doctor_save(alive_names)
            print(f"Doctor has chosen someone to save.")
            # Record doctor action
            self.game_record.record_night_action(
                player_name=doctor.name,
                role=doctor.role,
                action_type="doctor_save",
                target_name=doctor_save
            )

        # Detective investigates a player
        detective = next((p for p in alive_players if p.role == "Detective"), None)
        detective_investigation = None
        investigation_result = None
        investigation_results = {}
        if detective:
            detective_choices = [n for n in alive_names if n != detective.name]
            if detective_choices:
                detective_investigation = detective.choose_detective_investigation(detective_choices)
                investigated_player = next(p for p in alive_players if p.name == detective_investigation)
                investigation_result = (investigated_player.role == "Mafia")
                investigation_results[detective_investigation] = investigation_result
                print(f"Detective has investigated a player.")
                # Record detective action
                self.game_record.record_night_action(
                    player_name=detective.name,
                    role=detective.role,
                    action_type="detective_investigate",
                    target_name=detective_investigation,
                    action_result=investigation_result
                )

        # Resolve night actions
        killed_player = None
        if mafia_target and (mafia_target != doctor_save):
            killed_player = next(p for p in alive_players if p.name == mafia_target)
            killed_player.alive = False
            print(f"Night Result: {mafia_target} was killed!")
        else:
            print("Night Result: No one was killed!")

        # Announce detective result (for demo, print to console)
        if detective and detective_investigation:
            print(f"Detective investigated {detective_investigation}. Mafia? {investigation_result}")

        # Record night results
        self.game_record.record_night_result(
            killed_player=killed_player.name if killed_player else None,
            investigation_results=investigation_results
        )

        self.alive_players = [p for p in self.players if p.alive]

    def impression_phase(self):
        print("\n--- Impression Phase ---")
        alive_players = [p for p in self.players if p.alive]
        alive_names = [p.name for p in alive_players]
        player_histories = {name: "" for name in alive_names}
        for player in alive_players:
            statement = player.impression(alive_names, player_histories)
            print(statement)
            # Record discussion statement
            self.game_record.record_impression(player.name, statement)
        print("-" * 50)

    def discussion_phase(self):
        print("\n--- Discussion Phase ---")
        alive_players = [p for p in self.players if p.alive]
        alive_names = [p.name for p in alive_players]
        player_histories = {name: "" for name in alive_names}

        conversation_log = []

        for round_num in range(3):  # 3 discussion rounds
            print(f"\n-- Discussion Round {round_num + 1} --")
            for player in alive_players:
                statement = player.discuss(alive_names, player_histories, conversation_log)
                conversation_log.append(statement)
                print(statement)
                self.game_record.record_discussion(player.name, statement)

        print("-" * 50)


    def day_phase(self):
        print(f"\n--- Day {self.day_count + 1} ---")
        self.day_count += 1
        alive_players = [p for p in self.players if p.alive]
        alive_names = [p.name for p in alive_players]
        
        # Start recording day phase
        self.game_record.start_day_phase(self.day_count, alive_names)

        # Discussion phase before voting
        self.discussion_phase()

        # Impression phase after discussing
        self.impression_phase()

        # Each alive player votes for someone to eliminate (cannot vote for self)
        votes = {}
        for voter in alive_players:
            vote_choices = [n for n in alive_names if n != voter.name]
            if vote_choices:
                voted = voter.choose_vote(vote_choices)
                votes.setdefault(voted, 0)
                votes[voted] += 1
                print(f"{voter.name} votes to eliminate {voted}.")
                # Record vote
                self.game_record.record_vote(voter.name, voted)

        # Find the player(s) with the most votes
        eliminated_player = None
        if votes:
            max_votes = max(votes.values())
            candidates = [name for name, count in votes.items() if count == max_votes]
            
            # If there's a tie (multiple players with the same max votes), no one is eliminated
            if len(candidates) > 1:
                print(f"Day Result: Tie vote! {', '.join(candidates)} all received {max_votes} votes. No one is eliminated.")
            else:
                eliminated_name = candidates[0]
                eliminated_player = next(p for p in alive_players if p.name == eliminated_name)
                eliminated_player.alive = False
                print(f"Day Result: {eliminated_name} was eliminated! Their role was: {eliminated_player.role}")
        else:
            print("Day Result: No one was eliminated!")

        # Record day results
        self.game_record.record_day_result(
            eliminated_player=eliminated_player.name if eliminated_player else None
        )

        self.alive_players = [p for p in self.players if p.alive]

    def check_win_condition(self) -> bool:
        alive_players = [p for p in self.players if p.alive]
        mafia_alive = [p for p in alive_players if p.role == "Mafia"]
        townspeople_alive = [p for p in alive_players if p.role != "Mafia"]
        if not mafia_alive:
            self.winner = "Townspeople"
            return True
        if len(mafia_alive) >= len(townspeople_alive):
            self.winner = "Mafia"
            return True
        return False

    def announce_winner(self):
        print("\n=== GAME OVER ===")
        if self.winner == "Mafia":
            print("Mafia wins! The Mafia have outnumbered or equaled the Townspeople.")
        elif self.winner == "Townspeople":
            print("Townspeople win! All Mafia have been eliminated.")
        else:
            print("Game ended with no winner (unexpected).")
        
        # Record final game result
        self.game_record.finish_game(self.winner)

if __name__ == '__main__':
    # Configure player information, where model is the name of the model you call through API
    player_configs = [
        {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        {"name": "Derek", "model": "ollama/llama3:latest"},
        {"name": "Emma", "model": "ollama/mistral:7b"},

       
        # {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        # {"name": "Derek", "model": "ollama/deepseek-r1:7b"},
        # {"name": "Emma", "model": "ollama/dolphin3:8b"},
        # {"name": "Talia", "model": "ollama/qwen2.5:7b"},
        # {"name": "Anika", "model": "ollama/mistral:7b"},
        # {"name": "Nick", "model": "ollama/mistral-nemo:12b"},
        # {"name": "Philip", "model": "ollama/phi4:14b"},
        # {"name": "Peter", "model": "ollama/phi3.5:3.8b"},
        # {"name": "George", "model": "ollama/llava:7b"},
        # {"name": "Enrique", "model": "ollama/gemma2:9b"},
        {"name": "Maria", "model": "openai/gpt-4o-mini"},
    ]

    print("Game starts! Player configurations are as follows:")
    for config in player_configs:
        print(f"Player: {config['name']}, Using model: {config['model']}")
    print("-" * 50)

    # Create game instance and start game
    game = MafiaGame(player_configs)
    game.start_game()
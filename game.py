import random
from typing import List, Dict, Optional
from player import Player
from game_record import GameRecord

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

        # Mafia chooses a target (only one Mafia in this setup)
        mafia = next((p for p in alive_players if p.role == "Mafia"), None)
        mafia_target = None
        if mafia:
            mafia_choices = [n for n in alive_names if n != mafia.name]
            if mafia_choices:
                mafia_target = mafia.choose_mafia_target(mafia_choices)
                print(f"Mafia has chosen a target.")

        # Doctor chooses someone to save
        doctor = next((p for p in alive_players if p.role == "Doctor"), None)
        doctor_save = None
        if doctor:
            doctor_save = doctor.choose_doctor_save(alive_names)
            print(f"Doctor has chosen someone to save.")

        # Detective investigates a player
        detective = next((p for p in alive_players if p.role == "Detective"), None)
        detective_investigation = None
        investigation_result = None
        if detective:
            detective_choices = [n for n in alive_names if n != detective.name]
            if detective_choices:
                detective_investigation = detective.choose_detective_investigation(detective_choices)
                investigated_player = next(p for p in alive_players if p.name == detective_investigation)
                investigation_result = (investigated_player.role == "Mafia")
                print(f"Detective has investigated a player.")

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

        self.alive_players = [p for p in self.players if p.alive]

    def discussion_phase(self):
        print("\n--- Discussion Phase ---")
        alive_players = [p for p in self.players if p.alive]
        alive_names = [p.name for p in alive_players]
        # Placeholder: in a real game, fill player_histories with actual behavioral summaries
        player_histories = {name: "" for name in alive_names}
        for player in alive_players:
            statement = player.discuss(alive_names, player_histories)
            print(statement)
        print("-" * 50)

    def day_phase(self):
        print(f"\n--- Day {self.day_count + 1} ---")
        self.day_count += 1
        alive_players = [p for p in self.players if p.alive]
        alive_names = [p.name for p in alive_players]

        # Discussion phase before voting
        self.discussion_phase()

        # Each alive player votes for someone to eliminate (cannot vote for self)
        votes = {}
        for voter in alive_players:
            vote_choices = [n for n in alive_names if n != voter.name]
            if vote_choices:
                voted = voter.choose_vote(vote_choices)
                votes.setdefault(voted, 0)
                votes[voted] += 1
                print(f"{voter.name} votes to eliminate {voted}.")

        # Find the player(s) with the most votes
        if votes:
            max_votes = max(votes.values())
            candidates = [name for name, count in votes.items() if count == max_votes]
            eliminated_name = random.choice(candidates) if len(candidates) > 1 else candidates[0]
            eliminated_player = next(p for p in alive_players if p.name == eliminated_name)
            eliminated_player.alive = False
            print(f"Day Result: {eliminated_name} was eliminated! Their role was: {eliminated_player.role}")
        else:
            print("Day Result: No one was eliminated!")

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

if __name__ == '__main__':
    # Configure player information, where model is the name of the model you call through API
    player_configs = [
        {"name": "Llama1", "model": "llama3"},
        {"name": "Mistral1", "model": "mistral:7b"},
        {"name": "Mistral2", "model": "mistral:latest"},
        {"name": "Llama2", "model": "llama3"},
        {"name": "Mistral3", "model": "mistral:7b"},
        {"name": "Mistral4", "model": "mistral:latest"}
    ]

    print("Game starts! Player configurations are as follows:")
    for config in player_configs:
        print(f"Player: {config['name']}, Using model: {config['model']}")
    print("-" * 50)

    # Create game instance and start game
    game = MafiaGame(player_configs)
    game.start_game()
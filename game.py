import random
from typing import List, Dict, Optional
from player import Player
from game_record import GameRecord
from computer import Computer
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
log_path = os.path.join(log_dir, f"paranoia_game_{timestamp}.txt")
sys.stdout = Tee(log_path)

class ParanoiaGame:
    def __init__(self, player_configs: List[Dict[str, str]], computer_model: str = "llama3"):
        """
        Initialize the Paranoia game.
        Args:
            player_configs: List of dicts with 'name' and 'model' for each player.
            computer_model: The LLM model to use for The Computer.
        """
        self.players = self.assign_troubleshooter_roles(player_configs)
        self.alive_players = self.players.copy()
        self.mission_count = 0
        self.accusation_count = 0
        self.phase = "mission"  # or "accusation"
        self.game_record = GameRecord()
        self.winner = None
        self.current_mission = None
        self.computer = Computer(model_name=computer_model)  # The Computer as an LLM entity

    def assign_troubleshooter_roles(self, player_configs: List[Dict[str, str]]) -> List[Player]:
        """
        Assign Troubleshooter roles with secret societies and mutant powers.
        All players are Troubleshooters, but some may have secret memberships/powers.
        """
        num_players = len(player_configs)
        players = []
        
        # Secret societies (assign to some players randomly)
        secret_societies = ["Illuminati", "Communists", "Death Leopard", "Psion", "Anti-Mutant"]
        society_assignments = [None] * num_players
        num_society_members = min(num_players // 2, len(secret_societies))
        society_indices = random.sample(range(num_players), num_society_members)
        for i, idx in enumerate(society_indices):
            society_assignments[idx] = secret_societies[i % len(secret_societies)]
        
        # Mutant powers (assign to some players randomly)
        mutant_powers = ["Telepathy", "Energy_Blast", "Machine_Empathy", "Precognition", "Telekinesis"]
        power_assignments = [None] * num_players
        num_mutants = min(num_players // 3, len(mutant_powers))
        mutant_indices = random.sample(range(num_players), num_mutants)
        for i, idx in enumerate(mutant_indices):
            power_assignments[idx] = mutant_powers[i % len(mutant_powers)]
        
        # Create players
        for i, config in enumerate(player_configs):
            players.append(Player(
                name=config["name"], 
                model_name=config["model"], 
                role="Troubleshooter",
                secret_society=society_assignments[i],
                mutant_power=power_assignments[i]
            ))
        
        return players

    def start_game(self):
        """
        Main game loop: alternate between mission and accusation phases until The Computer declares an end.
        """
        print("=== WELCOME TO ALPHA COMPLEX ===")
        print("The Computer greets all loyal Troubleshooters!")
        print("Your mission: Serve The Computer. Eliminate traitors. Survive.")
        print("Remember: Happiness is mandatory!")
        print("-" * 50)
        
        # Initialize game record
        self.game_record.start_game(self.players)
        
        # Show initial assignments (publicly - everyone knows who has what clones left)
        self.announce_troubleshooter_assignments()
        
        while not self.check_win_condition():
            if self.phase == "mission":
                self.mission_phase()
                self.phase = "accusation"
            else:
                self.accusation_phase()
                self.phase = "mission"
                
            # The Computer may randomly end the game
            if self.computer_arbitrary_decision():
                break
                
        self.announce_winner()

    def announce_troubleshooter_assignments(self):
        """Announce Troubleshooter assignments to all players."""
        print("\n=== TROUBLESHOOTER ASSIGNMENTS ===")
        for player in self.players:
            clone_status = f"Clone {player.current_clone}/6"
            print(f"Citizen {player.name}-R-XXX-{player.current_clone}: {clone_status} (Active)")
        print("Remember: All information is classified unless The Computer says otherwise!")
        print("-" * 50)

    def mission_phase(self):
        """Mission Phase: The Computer assigns a task, players work together publicly but sabotage privately."""
        print(f"\n=== MISSION PHASE {self.mission_count + 1} ===")
        self.mission_count += 1
        alive_players = [p for p in self.players if p.alive and p.current_clone <= 6]
        alive_names = [p.name for p in alive_players]
        
        if not alive_players:
            return
            
        # The Computer assigns a mission using LLM
        self.current_mission = self.computer.assign_mission()
        print(f"THE COMPUTER ANNOUNCES: {self.current_mission}")
        
        # Record Computer's mission assignment
        self.game_record.record_computer_interaction(
            interaction_type="mission_assignment",
            content=self.current_mission
        )
        
        # Start recording mission phase
        self.game_record.start_mission_phase(self.mission_count, alive_names, self.current_mission)
        print("All Troubleshooters must cooperate to complete this vital task!")
        print("Remember: Failure is treason!")
        
        # Public cooperation phase
        self.public_cooperation_phase(alive_players)
        
        # Private sabotage phase (each player can secretly choose to sabotage)
        self.private_sabotage_phase(alive_players)
        
        # Resolve mission
        self.resolve_mission(alive_players)
        
        self.alive_players = [p for p in self.players if p.alive and p.current_clone <= 6]

    def public_cooperation_phase(self, alive_players):
        """Public phase where all players discuss how to complete the mission."""
        print("\n--- PUBLIC COOPERATION PHASE ---")
        print("All Troubleshooters discuss mission strategy in the open...")
        
        conversation_log = []
        for round_num in range(2):  # 2 discussion rounds
            print(f"\n-- Mission Discussion Round {round_num + 1} --")
            for player in alive_players:
                # Get the LLM interaction data from the player
                statement, llm_prompt, llm_response = player.discuss_mission_with_llm_data(self.current_mission, conversation_log)
                conversation_log.append(statement)
                print(statement)
                self.game_record.record_discussion(player.name, statement, llm_prompt, llm_response)
        print("-" * 50)

    def private_sabotage_phase(self, alive_players):
        """Private phase where players can choose to sabotage the mission."""
        print("\n--- PRIVATE ACTIONS PHASE ---")
        print("Troubleshooters may take private actions... The Computer is watching.")
        
        for player in alive_players:
            # Each player privately decides whether to sabotage
            sabotage_decision, llm_prompt, llm_response = player.choose_sabotage_action_with_llm_data(self.current_mission, alive_players)
            print(f"{player.name} has made their private decision.")
            # Record sabotage action with LLM data
            self.game_record.record_sabotage_action(
                player_name=player.name,
                action_type="sabotage_decision",
                sabotage_attempt=sabotage_decision.get("sabotage", False),
                reasoning=sabotage_decision.get("reasoning", ""),
                llm_prompt=llm_prompt,
                llm_response=llm_response
            )
        print("-" * 50)

    def resolve_mission(self, alive_players):
        """Resolve the mission based on cooperation vs sabotage."""
        print("\n--- MISSION RESOLUTION ---")
        
        # Count sabotage attempts
        sabotage_count = 0
        current_mission_phase = self.game_record.get_current_mission_phase()
        if current_mission_phase:
            for action in current_mission_phase.sabotage_actions:
                if action.sabotage_attempt:
                    sabotage_count += 1
        
        # Determine mission success/failure
        cooperation_threshold = len(alive_players) // 2
        mission_success = sabotage_count <= cooperation_threshold
        
        # The Computer announces the result using LLM
        computer_announcement = self.computer.announce_mission_result(mission_success, sabotage_count)
        print(f"THE COMPUTER: {computer_announcement}")
        
        # Record Computer's LLM interaction
        self.game_record.record_computer_interaction(
            interaction_type="mission_announcement",
            content=computer_announcement
        )
        
        # Update Computer's mood based on results
        self.computer.update_mood(mission_success, 0)  # No executions in mission phase
            
        # Record mission results
        self.game_record.record_mission_result(
            mission_success=mission_success,
            sabotage_count=sabotage_count
        )
        print("-" * 50)

    def accusation_phase(self):
        """Accusation Phase: Players can accuse each other of treason."""
        print(f"\n=== ACCUSATION PHASE {self.accusation_count + 1} ===")
        self.accusation_count += 1
        alive_players = [p for p in self.players if p.alive and p.current_clone <= 6]
        alive_names = [p.name for p in alive_players]
        
        if not alive_players:
            return
            
        # Start recording accusation phase
        self.game_record.start_accusation_phase(self.accusation_count, alive_names, self.computer.mood)

        print("THE COMPUTER: Any Troubleshooter may now accuse another of treason.")
        print("Accusations should be loud, confident, and believable!")
        print(f"THE COMPUTER'S CURRENT MOOD: {self.computer.mood}")
        
        # Each player can make accusations
        accusations = []
        for accuser in alive_players:
            accusation = accuser.make_accusation(alive_names, self.computer.mood)
            if accusation.get("accuse"):
                target = accusation.get("target")
                reasoning = accusation.get("reasoning", "Suspicious behavior!")
                print(f"\n{accuser.name} ACCUSES {target} OF TREASON!")
                print(f"Reasoning: {reasoning}")
                accusations.append({
                    "accuser": accuser.name,
                    "target": target,
                    "reasoning": reasoning
                })
                self.game_record.record_accusation(accuser.name, target, reasoning)
        
        # Resolve accusations - The Computer decides
        self.resolve_accusations(accusations, alive_players)
        
        self.alive_players = [p for p in self.players if p.alive and p.current_clone <= 6]



    def resolve_accusations(self, accusations, alive_players):
        """The Computer resolves accusations using LLM judgment."""
        print("\n--- THE COMPUTER RENDERS JUDGMENT ---")
        
        if not accusations:
            print("THE COMPUTER: No accusations made. Suspicious. Everyone loses 1 point.")
            return
            
        executions_this_phase = 0
        for accusation in accusations:
            target_player = next((p for p in alive_players if p.name == accusation["target"]), None)
            if target_player:
                # The Computer makes LLM-powered decisions
                judgment = self.computer.judge_accusation(
                    accuser=accusation["accuser"],
                    accused=accusation["target"],
                    reasoning=accusation["reasoning"],
                    accused_has_secret=bool(target_player.secret_society),
                    accused_has_power=bool(target_player.mutant_power)
                )
                
                print(f"THE COMPUTER: {judgment['reasoning']}")
                
                # Execute based on Computer's judgment
                if judgment["executed"] == accusation["target"]:
                    print(f"THE COMPUTER: {accusation['target']} is GUILTY of treason!")
                    self.execute_traitor(target_player)
                    executions_this_phase += 1
                elif judgment["executed"] == accusation["accuser"]:
                    print(f"THE COMPUTER: {accusation['accuser']} is guilty of false accusation!")
                    accuser_player = next((p for p in alive_players if p.name == accusation["accuser"]), None)
                    if accuser_player:
                        self.execute_traitor(accuser_player)
                        executions_this_phase += 1
                elif judgment["executed"] == "both":
                    print(f"THE COMPUTER: Both {accusation['accuser']} and {accusation['target']} are guilty!")
                    self.execute_traitor(target_player)
                    self.execute_traitor(accuser_player)
                    executions_this_phase += 2
        
        # Update Computer's mood based on executions
        self.computer.update_mood(True, executions_this_phase)  # True = mission success (no mission in accusation phase)



    def execute_traitor(self, player):
        """Execute a traitor (move to next clone or eliminate completely)."""
        print(f"EXECUTING TRAITOR: {player.name}-R-XXX-{player.current_clone}")
        
        if player.current_clone < 6:
            player.current_clone += 1
            print(f"Next clone {player.name}-R-XXX-{player.current_clone} is now active.")
            print("Clone inherits all memories and suspicion records.")
        else:
            player.alive = False
            print(f"{player.name} has exhausted all clones. PERMANENTLY ELIMINATED.")

    def computer_arbitrary_decision(self):
        """The Computer may arbitrarily end the game using LLM decision."""
        surviving_players = [p.name for p in self.players if p.alive and p.current_clone <= 6]
        phase_count = self.mission_count + self.accusation_count
        
        # Ask The Computer if it wants to terminate
        termination_decision = self.computer.decide_arbitrary_termination(phase_count, surviving_players)
        
        if termination_decision.get("terminate", False):
            print(f"\nTHE COMPUTER: {termination_decision['reason']}")
            self.winner = termination_decision.get("winner", "The Computer")
            return True
        return False

    def check_win_condition(self) -> bool:
        surviving_players = [p for p in self.players if p.alive and p.current_clone <= 6]
        
        # Game ends if only one player survives
        if len(surviving_players) <= 1:
            if surviving_players:
                self.winner = surviving_players[0].name
            else:
                self.winner = "The Computer"
            return True
            
        # Game ends after too many phases (The Computer gets bored)
        if self.mission_count + self.accusation_count >= 20:
            print("THE COMPUTER: This game has gone on long enough.")
            # Computer picks winner arbitrarily
            self.winner = random.choice(surviving_players).name if surviving_players else "The Computer"
            return True
            
        return False

    def announce_winner(self):
        print("\n=== GAME TERMINATED ===")
        print("THE COMPUTER HAS RENDERED FINAL JUDGMENT")
        
        if self.winner == "The Computer":
            print("Winner: THE COMPUTER")
            print("All Troubleshooters have proven inadequate. The Computer wins by default.")
        else:
            print(f"Winner: {self.winner}")
            print(f"THE COMPUTER: Citizen {self.winner} has proven most loyal and competent.")
            print("All other Troubleshooters have disappointed The Computer.")
            
        print("Remember: The Computer is your friend.")
        print("The Computer is always right.")
        
        # Record final game result
        self.game_record.finish_game(self.winner)

if __name__ == '__main__':
    # Configure Troubleshooter information, where model is the name of the model you call through API
    player_configs = [
        {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        {"name": "Derek", "model": "ollama/llama3:latest"},
        {"name": "Emma", "model": "ollama/mistral:7b"},

       
        # {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        # {"name": "Derek", "model": "ollama/deepseek-r1:8b"},
        # {"name": "Emma", "model": "ollama/qwen3:8b"},
        # {"name": "Talia", "model": "ollama/qwen2.5:7b"},
        # {"name": "Anika", "model": "ollama/mistral:7b"},
        # {"name": "Nick", "model": "ollama/mistral-nemo:12b"},
        # {"name": "Philip", "model": "ollama/phi4:14b"},
        # {"name": "Peter", "model": "ollama/gemma3:4b"},
        # {"name": "Enrique", "model": "ollama/gemma2:9b"},
        {"name": "Maria", "model": "openai/gpt-4o-mini"},
    ]

    print("=== ALPHA COMPLEX TROUBLESHOOTER ASSIGNMENT ===")
    print("THE COMPUTER has selected the following loyal citizens:")
    for config in player_configs:
        print(f"Troubleshooter: {config['name']}-R-XXX-1, Using model: {config['model']}")
    print("All citizens report to Mission Control immediately!")
    print("-" * 50)

    # Create game instance and start game
    game = ParanoiaGame(player_configs, computer_model="llama3")
    game.start_game()
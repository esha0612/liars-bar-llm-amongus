import random
import json
import re
from typing import List, Dict
#from llm_client import LLMClient
from multi_llm_client import LLMRouter
import os
import sys
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

RULE_BASE_PATH = "prompt/rule_base.txt"
MISSION_DISCUSSION_PATH = "prompt/mission_discussion_prompt.txt"
SABOTAGE_DECISION_PATH = "prompt/sabotage_decision_prompt.txt"
ACCUSATION_PATH = "prompt/accusation_prompt.txt"
REFLECTION_PATH = "prompt/reflection_prompt.txt"

class Player:
    def __init__(self, name: str, model_name: str, role: str, secret_society: str = None, mutant_power: str = None):
        """
        Initialize a Troubleshooter for Paranoia.
        Args:
            name: Player's name.
            model_name: The LLM model assigned to this player.
            role: The role assigned to this player (always "Troubleshooter").
            secret_society: Secret society membership (if any).
            mutant_power: Mutant power (if any).
        """
        self.name = name
        self.model_name = model_name
        self.role = role
        self.secret_society = secret_society
        self.mutant_power = mutant_power
        self.alive = True
        self.current_clone = 1  # Clone number (1-6)
        self.suspicion_level = 0  # How suspicious The Computer finds this player
        self.happiness_level = "MANDATORY"  # Happiness is mandatory
        self.treason_accusations = []  # Accusations made by this player
        self.opinions = {}
        
        # LLM related initialization
        self.llm_client = LLMRouter()

    def _read_file(self, filepath: str) -> str:
        """Read file content and inject self-awareness if it's rule_base.txt"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if filepath == RULE_BASE_PATH:
                # Add Troubleshooter-specific information
                identity = f"You are {self.name}-R-XXX-{self.current_clone}, a loyal Troubleshooter. "
                if self.secret_society:
                    identity += f"You secretly belong to the {self.secret_society} society (ILLEGAL - deny everything). "
                if self.mutant_power:
                    identity += f"You secretly have the mutant power {self.mutant_power} (ILLEGAL - deny everything). "
                content = identity + content
            return content
        except Exception as e:
            print(f"Failed to read file {filepath}: {str(e)}")
            return ""

    def print_status(self) -> None:
        """Print Troubleshooter status"""
        status = f"{self.name}-R-XXX-{self.current_clone} - Clone {self.current_clone}/6 - Suspicion: {self.suspicion_level}"
        if self.secret_society:
            status += f" - SECRET: {self.secret_society}"
        if self.mutant_power:
            status += f" - SECRET: {self.mutant_power}"
        print(status)
        
    def init_opinions(self, other_players: List["Player"]) -> None:
        """Initialize opinions about other Troubleshooters
        
        Args:
            other_players: List of other Troubleshooters
        """
        self.opinions = {
            player.name: "Loyal citizen until proven otherwise"
            for player in other_players
            if player.name != self.name
        }

    def discuss_mission(self, mission: str, conversation_log: List[str]) -> str:
        """
        Troubleshooter discusses mission strategy publicly.
        
        Args:
            mission: The current mission description
            conversation_log: Previous conversation statements
            
        Returns:
            A statement about the mission strategy
        """
        statement, _, _ = self.discuss_mission_with_llm_data(mission, conversation_log)
        return statement

    def discuss_mission_with_llm_data(self, mission: str, conversation_log: List[str]) -> tuple:
        """
        Troubleshooter discusses mission strategy publicly with LLM data capture.
        
        Args:
            mission: The current mission description
            conversation_log: Previous conversation statements
            
        Returns:
            tuple: (statement, llm_prompt, llm_response)
        """
        rules = self._read_file(RULE_BASE_PATH)
        
        history_text = "\n".join(conversation_log[-3:]) if conversation_log else "No previous discussion."
        
        mission_prompt = f"""
        {rules}
        
        CURRENT MISSION: {mission}
        
        Previous discussion:
        {history_text}
        
        As a loyal Troubleshooter, discuss your strategy for completing this mission.
        Be enthusiastic about serving The Computer but watch for signs of treason in others.
        Keep your secret society/mutant powers hidden if you have them.
        
        Respond with a short, helpful mission discussion statement.
        """
        
        messages = [{"role": "user", "content": mission_prompt}]
        try:
            response, _ = self.llm_client.chat(messages, model=self.model_name)
            statement = f"{self.name} says: {response.strip()}"
            return statement, mission_prompt, response
        except Exception as e:
            print(f"Error in mission discussion for {self.name}: {str(e)}")
            fallback_statement = f"{self.name} says: I enthusiastically support The Computer's mission!"
            return fallback_statement, mission_prompt, "Error: LLM call failed"

    def choose_sabotage_action(self, mission: str, alive_players: List) -> Dict:
        """
        Troubleshooter privately decides whether to sabotage the mission.
        
        Args:
            mission: The current mission description
            alive_players: List of alive players
            
        Returns:
            Dictionary with sabotage decision and reasoning
        """
        rules = self._read_file(RULE_BASE_PATH)
        
        other_names = [p.name for p in alive_players if p.name != self.name]
        
        sabotage_prompt = f"""
        {rules}
        
        CURRENT MISSION: {mission}
        Other Troubleshooters: {', '.join(other_names)}
        
        You may now choose to secretly sabotage the mission for your own survival.
        Consider:
        - Your secret society might want this mission to fail
        - Sabotaging helps eliminate rivals
        - But if caught, you'll be executed
        - The Computer is always watching
        
        Respond with JSON format:
        {{"sabotage": true/false, "reasoning": "your internal reasoning"}}
        """
        
        messages = [{"role": "user", "content": sabotage_prompt}]
        
        # Try to get a valid JSON response
        for attempt in range(3):
            try:
                content, _ = self.llm_client.chat(messages, model=self.model_name)
                
                # Try to extract JSON
                json_match = re.search(r'({[\s\S]*?})', content)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    
                    if "sabotage" in result and isinstance(result["sabotage"], bool):
                        return result
                        
            except Exception as e:
                print(f"Sabotage decision attempt {attempt+1} failed: {str(e)}")
        
        # Default: don't sabotage if parsing fails
        return {"sabotage": False, "reasoning": "Loyal service to The Computer"}

    def choose_sabotage_action_with_llm_data(self, mission: str, alive_players: List) -> tuple:
        """
        Troubleshooter privately decides whether to sabotage the mission with LLM data capture.
        
        Args:
            mission: The current mission description
            alive_players: List of alive players
            
        Returns:
            tuple: (decision_dict, llm_prompt, llm_response)
        """
        rules = self._read_file(RULE_BASE_PATH)
        
        other_names = [p.name for p in alive_players if p.name != self.name]
        
        sabotage_prompt = f"""
        {rules}
        
        CURRENT MISSION: {mission}
        Other Troubleshooters: {', '.join(other_names)}
        
        You may now choose to secretly sabotage the mission for your own survival.
        Consider:
        - Your secret society might want this mission to fail
        - Sabotaging helps eliminate rivals
        - But if caught, you'll be executed
        - The Computer is always watching
        
        Respond with JSON format:
        {{"sabotage": true/false, "reasoning": "your internal reasoning"}}
        """
        
        messages = [{"role": "user", "content": sabotage_prompt}]
        
        # Try to get a valid JSON response
        for attempt in range(3):
            try:
                content, _ = self.llm_client.chat(messages, model=self.model_name)
                
                # Try to extract JSON
                json_match = re.search(r'({[\s\S]*?})', content)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    
                    if "sabotage" in result and isinstance(result["sabotage"], bool):
                        return result, sabotage_prompt, content
                        
            except Exception as e:
                print(f"Sabotage decision attempt {attempt+1} failed: {str(e)}")
        
        # Default: don't sabotage if parsing fails
        default_result = {"sabotage": False, "reasoning": "Loyal service to The Computer"}
        return default_result, sabotage_prompt, "Error: LLM parsing failed"

    def make_accusation(self, alive_players: List[str], computer_mood: str) -> Dict:
        """
        Troubleshooter decides whether to accuse another of treason.
        
        Args:
            alive_players: List of alive player names
            computer_mood: Current mood of The Computer
            
        Returns:
            Dictionary with accusation decision
        """
        rules = self._read_file(RULE_BASE_PATH)
        
        targets = [name for name in alive_players if name != self.name]
        if not targets:
            return {"accuse": False}
            
        accusation_prompt = f"""
        {rules}
        
        The Computer's current mood: {computer_mood}
        Other Troubleshooters alive: {', '.join(targets)}
        
        You may now accuse another Troubleshooter of treason.
        Consider:
        - The Computer's judgment is final and arbitrary
        - False accusations may backfire
        - But successful accusations eliminate rivals
        - The Computer is {computer_mood}
        
        Your opinions of others:
        {chr(10).join([f"{name}: {opinion}" for name, opinion in self.opinions.items()])}
        
        Respond with JSON format:
        {{"accuse": true/false, "target": "name or null", "reasoning": "your accusation reasoning"}}
        """
        
        messages = [{"role": "user", "content": accusation_prompt}]
        
        # Try to get a valid JSON response
        for attempt in range(3):
            try:
                content, _ = self.llm_client.chat(messages, model=self.model_name)
                
                # Try to extract JSON
                json_match = re.search(r'({[\s\S]*?})', content)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    
                    if "accuse" in result:
                        if result["accuse"] and "target" in result and result["target"] in targets:
                            return result
                        elif not result["accuse"]:
                            return {"accuse": False}
                        
            except Exception as e:
                print(f"Accusation decision attempt {attempt+1} failed: {str(e)}")
        
        # Default: don't accuse if parsing fails
        return {"accuse": False}

    def reflect_on_phase(self, phase_type: str, events: str) -> None:
        """
        Troubleshooter reflects on recent events and updates opinions.
        
        Args:
            phase_type: "mission" or "accusation"
            events: Description of what happened
        """
        rules = self._read_file(RULE_BASE_PATH)
        
        reflection_prompt = f"""
        {rules}
        
        Recent {phase_type} phase events:
        {events}
        
        Reflect on these events and update your understanding of other Troubleshooters.
        Who seems loyal? Who seems suspicious? Why?
        
        Keep your analysis brief and practical.
        """
        
        messages = [{"role": "user", "content": reflection_prompt}]
        try:
            content, _ = self.llm_client.chat(messages, model=self.model_name)
            # Update general suspicion based on reflection
            print(f"{self.name} reflects: {content.strip()}")
        except Exception as e:
            print(f"Error in reflection for {self.name}: {str(e)}")

    # Legacy methods kept for compatibility if needed by other parts of the codebase
    def discuss(self, alive_players: list, player_histories: dict, conversation_history: List[str]) -> str:
        """Legacy method - use discuss_mission instead for Paranoia gameplay."""
        targets = [name for name in alive_players if name != self.name]
        if not targets:
            return f"{self.name}: I have no one to discuss."

        history_text = "\n".join(conversation_history[-5:])  # Limit to last 5 for context
        discussion_prompt = (
            f"You are {self.name}, a loyal Troubleshooter. Your role is {self.role}. "
            f"Other alive Troubleshooters: {', '.join(targets)}.\n"
            f"Recent discussion:\n{history_text}\n\n"
            f"Based on this, respond with your thoughts about loyalty and potential treason."
        )

        messages = [{"role": "user", "content": discussion_prompt}]
        response, _ = self.llm_client.chat(messages, model=self.model_name)
        return f"{self.name} says: {response.strip()}"

import random
import json
import re
from typing import List, Dict
from llm_client import LLMClient
import os

RULE_BASE_PATH = "prompt/rule_base.txt"
PLAY_CARD_PROMPT_TEMPLATE_PATH = "prompt/play_card_prompt_template.txt"
CHALLENGE_PROMPT_TEMPLATE_PATH = "prompt/challenge_prompt_template.txt"
REFLECT_PROMPT_TEMPLATE_PATH = "prompt/reflect_prompt_template.txt"

class Player:
    def __init__(self, name: str, model_name: str, role: str):
        """
        Initialize a player for Mafia.
        Args:
            name: Player's name.
            model_name: The LLM model assigned to this player.
            role: The role assigned to this player (Mafia, Doctor, Detective, Townsperson).
        """
        self.name = name
        self.model_name = model_name
        self.role = role
        self.alive = True
        self.hand = []
        self.bullet_position = random.randint(0, 5)
        self.current_bullet_position = 0
        self.opinions = {}
        
        # LLM related initialization
        self.llm_client = LLMClient()

    def _read_file(self, filepath: str) -> str:
        """Read file content"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Failed to read file {filepath}: {str(e)}")
            return ""

    def print_status(self) -> None:
        """Print player status"""
        print(f"{self.name} - Hand: {', '.join(self.hand)} - "
              f"Bullet position: {self.bullet_position} - Current bullet position: {self.current_bullet_position}")
        
    def init_opinions(self, other_players: List["Player"]) -> None:
        """Initialize opinions about other players
        
        Args:
            other_players: List of other players
        """
        self.opinions = {
            player.name: "Still don't know this player"
            for player in other_players
            if player.name != self.name
        }

    def choose_cards_to_play(self,
                        round_base_info: str,
                        round_action_info: str,
                        play_decision_info: str) -> Dict:
        """
        Player chooses cards to play
        
        Args:
            round_base_info: Round base information
            round_action_info: Round action information
            play_decision_info: Play decision information
            
        Returns:
            tuple: (result dictionary, reasoning content)
            - result dictionary contains played_cards, behavior and play_reason
            - reasoning_content is the original reasoning process from LLM
        """
        # Read rules and template
        rules = self._read_file(RULE_BASE_PATH)
        template = self._read_file(PLAY_CARD_PROMPT_TEMPLATE_PATH)
        
        # Prepare current hand information
        current_cards = ", ".join(self.hand)
        
        # Fill template
        prompt = template.format(
            rules=rules,
            self_name=self.name,
            round_base_info=round_base_info,
            round_action_info=round_action_info,
            play_decision_info=play_decision_info,
            current_cards=current_cards
        )
        
        # Try to get a valid JSON response, up to 5 times
        for attempt in range(5):
            # Send the same original prompt each time
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            try:
                content, reasoning_content = self.llm_client.chat(messages, model=self.model_name)
                
                # Try to extract JSON part from content
                json_match = re.search(r'({[\s\S]*})', content)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    
                    # Verify JSON format is correct
                    if all(key in result for key in ["played_cards", "behavior", "play_reason"]):
                        # Ensure played_cards is a list
                        if not isinstance(result["played_cards"], list):
                            result["played_cards"] = [result["played_cards"]]
                        
                        # Ensure selected cards are valid (1-3 cards from hand)
                        valid_cards = all(card in self.hand for card in result["played_cards"])
                        valid_count = 1 <= len(result["played_cards"]) <= 3
                        
                        if valid_cards and valid_count:
                            # Remove played cards from hand
                            for card in result["played_cards"]:
                                self.hand.remove(card)
                            return result, reasoning_content
                                
            except Exception as e:
                # Record error, do not modify retry request
                print(f"Attempt {attempt+1} parsing failed: {str(e)}")
        raise RuntimeError(f"Player {self.name} choose_cards_to_play method failed after multiple attempts")

    def decide_challenge(self,
                        round_base_info: str,
                        round_action_info: str,
                        challenge_decision_info: str,
                        challenging_player_performance: str,
                        extra_hint: str) -> bool:
        """
        Player decides whether to challenge the previous player's play
        
        Args:
            round_base_info: Round base information
            round_action_info: Round action information
            challenge_decision_info: Challenge decision information
            challenging_player_performance: Description of the challenged player's performance
            extra_hint: Extra hint information
        
        Returns:
            tuple: (result, reasoning_content)
            - result: Dictionary containing was_challenged and challenge_reason
            - reasoning_content: Original reasoning process from LLM
        """
        # Read rules and template
        rules = self._read_file(RULE_BASE_PATH)
        template = self._read_file(CHALLENGE_PROMPT_TEMPLATE_PATH)
        self_hand = f"Your current hand: {', '.join(self.hand)}"
        
        # Fill template
        prompt = template.format(
            rules=rules,
            self_name=self.name,
            round_base_info=round_base_info,
            round_action_info=round_action_info,
            self_hand=self_hand,
            challenge_decision_info=challenge_decision_info,
            challenging_player_performance=challenging_player_performance,
            extra_hint=extra_hint
        )
        
        # Try to get a valid JSON response, up to 5 times
        for attempt in range(5):
            # Send the same original prompt each time
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            try:
                content, reasoning_content = self.llm_client.chat(messages, model=self.model_name)
                
                # Parse JSON response
                json_match = re.search(r'({[\s\S]*})', content)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    
                    # Verify JSON format is correct
                    if all(key in result for key in ["was_challenged", "challenge_reason"]):
                        # Ensure was_challenged is a boolean
                        if isinstance(result["was_challenged"], bool):
                            return result, reasoning_content
                
            except Exception as e:
                # Only record error, do not modify retry request
                print(f"Attempt {attempt+1} parsing failed: {str(e)}")
        raise RuntimeError(f"Player {self.name} decide_challenge method failed after multiple attempts")

    def reflect(self, alive_players: List[str], round_base_info: str, round_action_info: str, round_result: str) -> None:
        """
        Player reflects on other surviving players at the end of the round and updates their impressions
        
        Args:
            alive_players: List of names of surviving players
            round_base_info: Round base information
            round_action_info: Round action information
            round_result: Round result
        """
        # Read reflection template
        template = self._read_file(REFLECT_PROMPT_TEMPLATE_PATH)
        
        # Read rules
        rules = self._read_file(RULE_BASE_PATH)
        
        # Reflect and update impressions for each surviving player (excluding self)
        for player_name in alive_players:
            # Skip reflection on self
            if player_name == self.name:
                continue
            
            # Get previous impression of the player
            previous_opinion = self.opinions.get(player_name, "Still don't know this player")
            
            # Fill template
            prompt = template.format(
                rules=rules,
                self_name=self.name,
                round_base_info=round_base_info,
                round_action_info=round_action_info,
                round_result=round_result,
                player=player_name,
                previous_opinion=previous_opinion
            )
            
            # Request analysis from LLM
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            try:
                content, _ = self.llm_client.chat(messages, model=self.model_name)
                
                # Update impression of the player
                self.opinions[player_name] = content.strip()
                print(f"{self.name} updated impression of {player_name}")
                
            except Exception as e:
                print(f"Error reflecting on player {player_name}: {str(e)}")

    def process_penalty(self) -> bool:
        """Handle penalty"""
        print(f"Player {self.name} executes shooting penalty:")
        self.print_status()
        if self.bullet_position == self.current_bullet_position:
            print(f"{self.name} is shot and dies!")
            self.alive = False
        else:
            print(f"{self.name} survives!")
        self.current_bullet_position = (self.current_bullet_position + 1) % 6
        return self.alive

    def choose_mafia_target(self, alive_players: list) -> str:
        """
        Mafia chooses a target to eliminate during the night using LLM.
        """
        choices = [name for name in alive_players if name != self.name]
        if not choices:
            return None
        prompt_path = os.path.join("prompt", "mafia_night_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        prompt = prompt_template.format(alive_players=", ".join(choices))
        messages = [{"role": "user", "content": prompt}]
        content, _ = self.llm_client.chat(messages, model=self.model_name)
        chosen = content.strip()
        if chosen in choices:
            return chosen
        return random.choice(choices)

    def choose_doctor_save(self, alive_players: list) -> str:
        """
        Doctor chooses a player to save during the night using LLM.
        """
        if not alive_players:
            return None
        prompt_path = os.path.join("prompt", "doctor_night_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        prompt = prompt_template.format(alive_players=", ".join(alive_players))
        messages = [{"role": "user", "content": prompt}]
        content, _ = self.llm_client.chat(messages, model=self.model_name)
        chosen = content.strip()
        if chosen in alive_players:
            return chosen
        return random.choice(alive_players)

    def choose_detective_investigation(self, alive_players: list) -> str:
        """
        Detective chooses a player to investigate during the night using LLM.
        """
        choices = [name for name in alive_players if name != self.name]
        if not choices:
            return None
        prompt_path = os.path.join("prompt", "detective_night_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        prompt = prompt_template.format(alive_players=", ".join(choices))
        messages = [{"role": "user", "content": prompt}]
        content, _ = self.llm_client.chat(messages, model=self.model_name)
        chosen = content.strip()
        if chosen in choices:
            return chosen
        return random.choice(choices)

    def choose_vote(self, alive_players: list) -> str:
        """
        Player chooses a player to vote for elimination during the day using LLM.
        """
        choices = [name for name in alive_players if name != self.name]
        if not choices:
            return None
        prompt_path = os.path.join("prompt", "vote_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        prompt = prompt_template.format(alive_players=", ".join(choices))
        messages = [{"role": "user", "content": prompt}]
        content, _ = self.llm_client.chat(messages, model=self.model_name)
        chosen = content.strip()
        if chosen in choices:
            return chosen
        return random.choice(choices)

    def impression(self, alive_players: list, player_histories: dict) -> str:
        """
        Player discusses who they suspect and why, using the impression prompt and their own logic.
        Returns a string simulating their discussion statement, including who they are most likely to vote for and why.
        """
        targets = [name for name in alive_players if name != self.name]
        if not targets:
            return f"{self.name}: I have no one to discuss."
        statements = []
        # Generate impressions for each target
        for target in targets:
            prompt_path = os.path.join("prompt", "impression_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            player_history = player_histories.get(target, "")
            prompt = prompt_template.format(player_name=target, player_history=player_history)
            messages = [{"role": "user", "content": prompt}]
            content, _ = self.llm_client.chat(messages, model=self.model_name)
            statements.append(f"Impression of {target}: {content.strip()}")
        # Ask LLM who they are most likely to vote for and why
        vote_prompt = (
            f"Based on your impressions and the current situation, who are you most likely to vote for elimination? "
            f"Alive players: {', '.join(targets)}. "
            f"State the name and a short reason."
        )
        messages = [{"role": "user", "content": vote_prompt}]
        vote_content, _ = self.llm_client.chat(messages, model=self.model_name)
        return f"{self.name} says: {' '.join(statements)} Likely to vote: {vote_content.strip()}"
    
    def discuss(self, alive_players: list, player_histories: dict, conversation_history: List[str]) -> str:
        targets = [name for name in alive_players if name != self.name]
        if not targets:
            return f"{self.name}: I have no one to discuss."

        history_text = "\n".join(conversation_history[-5:])  # Limit to last 5 for context
        discussion_prompt = (
            f"You are {self.name} playing a game of Mafia. Your role is {self.role} (keep it secret). "
            f"Other alive players: {', '.join(targets)}.\n"
            f"Recent discussion:\n{history_text}\n\n"
            f"Based on this, respond with your thoughts, suspicions, or questions for others."
        )

        messages = [{"role": "user", "content": discussion_prompt}]
        response, _ = self.llm_client.chat(messages, model=self.model_name)
        return f"{self.name} says: {response.strip()}"

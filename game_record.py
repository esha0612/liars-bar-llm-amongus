from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import datetime
import json
import os

def generate_game_id():
    """Generate a game ID containing time information"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return timestamp

@dataclass
class PlayerInitialState:
    """Record Troubleshooter initial state, including role and clone status"""
    player_name: str
    role: str
    secret_society: Optional[str] = None
    mutant_power: Optional[str] = None
    alive: bool = True
    current_clone: int = 1
    
    def to_dict(self) -> Dict:
        return {
            "player_name": self.player_name,
            "role": self.role,
            "secret_society": self.secret_society,
            "mutant_power": self.mutant_power,
            "alive": self.alive,
            "current_clone": self.current_clone
        }

@dataclass
class SabotageAction:
    """Record a sabotage action during mission phase"""
    player_name: str
    action_type: str  # "sabotage_decision"
    sabotage_attempt: bool = False
    reasoning: Optional[str] = None
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "player_name": self.player_name,
            "action_type": self.action_type,
            "sabotage_attempt": self.sabotage_attempt,
            "reasoning": self.reasoning,
            "llm_prompt": self.llm_prompt,
            "llm_response": self.llm_response
        }

@dataclass
class AccusationAction:
    """Record an accusation during accusation phase"""
    accuser_name: str
    target_name: str
    reasoning: str
    computer_verdict: Optional[bool] = None  # True = guilty, False = innocent
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "accuser_name": self.accuser_name,
            "target_name": self.target_name,
            "reasoning": self.reasoning,
            "computer_verdict": self.computer_verdict,
            "llm_prompt": self.llm_prompt,
            "llm_response": self.llm_response
        }

@dataclass
class MissionPhase:
    """Record a mission phase"""
    mission_number: int
    alive_players: List[str]
    mission_description: str
    discussion_statements: List[Dict[str, str]] = field(default_factory=list)
    sabotage_actions: List[SabotageAction] = field(default_factory=list)
    computer_interactions: List[Dict] = field(default_factory=list)
    mission_success: Optional[bool] = None
    sabotage_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "mission_number": self.mission_number,
            "alive_players": self.alive_players,
            "mission_description": self.mission_description,
            "discussion_statements": self.discussion_statements,
            "sabotage_actions": [action.to_dict() for action in self.sabotage_actions],
            "computer_interactions": self.computer_interactions,
            "mission_success": self.mission_success,
            "sabotage_count": self.sabotage_count
        }
    
    def add_sabotage_action(self, action: SabotageAction) -> None:
        """Add sabotage action record"""
        self.sabotage_actions.append(action)
        
    def add_discussion(self, discussion_data: Dict) -> None:
        """Add discussion statement with LLM interaction data"""
        self.discussion_statements.append(discussion_data)

@dataclass
class AccusationPhase:
    """Record an accusation phase"""
    accusation_number: int
    alive_players: List[str]
    accusations: List[AccusationAction] = field(default_factory=list)
    executed_players: List[str] = field(default_factory=list)  # Players executed this phase
    computer_mood: str = "SATISFIED"
    
    def to_dict(self) -> Dict:
        return {
            "accusation_number": self.accusation_number,
            "alive_players": self.alive_players,
            "accusations": [accusation.to_dict() for accusation in self.accusations],
            "executed_players": self.executed_players,
            "computer_mood": self.computer_mood
        }
    
    def add_accusation(self, accusation: AccusationAction) -> None:
        """Add accusation record"""
        self.accusations.append(accusation)

@dataclass
class GameRecord:
    """Complete Paranoia game record"""
    def __init__(self):
        self.game_id: str = generate_game_id()
        self.player_names: List[str] = []
        self.player_roles: Dict[str, str] = {}
        self.player_secret_societies: Dict[str, Optional[str]] = {}
        self.player_mutant_powers: Dict[str, Optional[str]] = {}
        self.mission_phases: List[MissionPhase] = []
        self.accusation_phases: List[AccusationPhase] = []
        self.winner: Optional[str] = None
        self.game_end_reason: str = "unknown"
        self.save_directory: str = "game_records"
        
        # Ensure save directory exists
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
    
    def to_dict(self) -> Dict:
        return {
            "game_id": self.game_id,
            "player_names": self.player_names,
            "player_roles": self.player_roles,
            "player_secret_societies": self.player_secret_societies,
            "player_mutant_powers": self.player_mutant_powers,
            "mission_phases": [phase.to_dict() for phase in self.mission_phases],
            "accusation_phases": [phase.to_dict() for phase in self.accusation_phases],
            "winner": self.winner,
            "game_end_reason": self.game_end_reason,
        }
    
    def start_game(self, players: List) -> None:
        """Initialize game, record Troubleshooter information"""
        self.player_names = [p.name for p in players]
        self.player_roles = {p.name: p.role for p in players}
        self.player_secret_societies = {p.name: p.secret_society for p in players}
        self.player_mutant_powers = {p.name: p.mutant_power for p in players}
        self.auto_save()
    
    def start_mission_phase(self, mission_number: int, alive_players: List[str], mission_description: str = "") -> None:
        """Start a new mission phase"""
        mission_phase = MissionPhase(
            mission_number=mission_number,
            alive_players=alive_players,
            mission_description=mission_description
        )
        self.mission_phases.append(mission_phase)
    
    def record_sabotage_action(self, player_name: str, action_type: str, 
                              sabotage_attempt: bool = False, reasoning: str = None,
                              llm_prompt: str = None, llm_response: str = None) -> None:
        """Record a sabotage action during mission phase"""
        current_mission = self.get_current_mission_phase()
        if current_mission:
            action = SabotageAction(
                player_name=player_name,
                action_type=action_type,
                sabotage_attempt=sabotage_attempt,
                reasoning=reasoning,
                llm_prompt=llm_prompt,
                llm_response=llm_response
            )
            current_mission.add_sabotage_action(action)
    
    def record_mission_result(self, mission_success: bool = False, sabotage_count: int = 0) -> None:
        """Record mission phase results"""
        current_mission = self.get_current_mission_phase()
        if current_mission:
            current_mission.mission_success = mission_success
            current_mission.sabotage_count = sabotage_count
            self.auto_save()
    
    def record_computer_interaction(self, interaction_type: str, content: str, llm_prompt: str = None, llm_response: str = None) -> None:
        """Record Computer LLM interactions"""
        current_mission = self.get_current_mission_phase()
        if current_mission:
            computer_data = {
                "interaction_type": interaction_type,  # "mission_assignment", "mission_announcement", "accusation_judgment", etc.
                "content": content,
                "llm_prompt": llm_prompt,
                "llm_response": llm_response,
                "timestamp": "current_phase"
            }
            if not hasattr(current_mission, 'computer_interactions'):
                current_mission.computer_interactions = []
            current_mission.computer_interactions.append(computer_data)
    
    def start_accusation_phase(self, accusation_number: int, alive_players: List[str], computer_mood: str = "SATISFIED") -> None:
        """Start a new accusation phase"""
        accusation_phase = AccusationPhase(
            accusation_number=accusation_number,
            alive_players=alive_players,
            computer_mood=computer_mood
        )
        self.accusation_phases.append(accusation_phase)
    
    def record_accusation(self, accuser_name: str, target_name: str, reasoning: str,
                         computer_verdict: bool = None, llm_prompt: str = None, llm_response: str = None) -> None:
        """Record an accusation"""
        current_accusation = self.get_current_accusation_phase()
        if current_accusation:
            accusation = AccusationAction(
                accuser_name=accuser_name,
                target_name=target_name,
                reasoning=reasoning,
                computer_verdict=computer_verdict,
                llm_prompt=llm_prompt,
                llm_response=llm_response
            )
            current_accusation.add_accusation(accusation)
    
    def record_discussion(self, player_name: str, statement: str, llm_prompt: str = None, llm_response: str = None) -> None:
        """Record a discussion statement (for mission discussions)"""
        current_mission = self.get_current_mission_phase()
        if current_mission:
            # Store both the final statement and the LLM interaction
            discussion_data = {
                "player_name": player_name,
                "statement": statement,
                "llm_prompt": llm_prompt,
                "llm_response": llm_response
            }
            current_mission.add_discussion(discussion_data)
    
    def finish_game(self, winner: str, end_reason: str = "unknown") -> None:
        """Record winner and save final result"""
        self.winner = winner
        self.game_end_reason = end_reason
        self.auto_save()
    
    def get_current_mission_phase(self) -> Optional[MissionPhase]:
        """Get current mission phase"""
        return self.mission_phases[-1] if self.mission_phases else None
    
    def get_current_accusation_phase(self) -> Optional[AccusationPhase]:
        """Get current accusation phase"""
        return self.accusation_phases[-1] if self.accusation_phases else None
    
    def auto_save(self) -> None:
        """Automatically save current game record to file"""
        file_path = os.path.join(self.save_directory, f"{self.game_id}.json")
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=4, ensure_ascii=False)
        print(f"Game record has been automatically saved to {file_path}")

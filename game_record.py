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
    """Record player initial state, including role and alive status"""
    player_name: str
    role: str
    alive: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "player_name": self.player_name,
            "role": self.role,
            "alive": self.alive
        }

@dataclass
class NightAction:
    """Record a night action (Mafia kill, Doctor save, Detective investigate)"""
    player_name: str
    role: str
    action_type: str  # "mafia_kill", "doctor_save", "detective_investigate"
    target_name: Optional[str] = None
    action_result: Optional[bool] = None
    action_reasoning: Optional[str] = None
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "player_name": self.player_name,
            "role": self.role,
            "action_type": self.action_type,
            "target_name": self.target_name,
            "action_result": self.action_result,
            "action_reasoning": self.action_reasoning,
            "llm_prompt": self.llm_prompt,
            "llm_response": self.llm_response
        }

@dataclass
class DayAction:
    """Record a day action (discussion, voting)"""
    player_name: str
    action_type: str  # "discussion", "vote"
    content: str  # discussion statement or vote target
    reasoning: Optional[str] = None
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "player_name": self.player_name,
            "action_type": self.action_type,
            "content": self.content,
            "reasoning": self.reasoning,
            "llm_prompt": self.llm_prompt,
            "llm_response": self.llm_response
        }

@dataclass
class NightPhase:
    """Record a night phase"""
    night_number: int
    alive_players: List[str]
    night_actions: List[NightAction] = field(default_factory=list)
    killed_player: Optional[str] = None
    investigation_results: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "night_number": self.night_number,
            "alive_players": self.alive_players,
            "night_actions": [action.to_dict() for action in self.night_actions],
            "killed_player": self.killed_player,
            "investigation_results": self.investigation_results
        }
    
    def add_night_action(self, action: NightAction) -> None:
        """Add night action record"""
        self.night_actions.append(action)

@dataclass
class DayPhase:
    """Record a day phase"""
    day_number: int
    alive_players: List[str]
    discussion_statements: List[Dict[str, str]]
    impression_statements: Dict[str, str] = field(default_factory=dict)
    votes: Dict[str, str] = field(default_factory=dict)  # voter -> voted_for
    eliminated_player: Optional[str] = None
    vote_reasoning: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "day_number": self.day_number,
            "alive_players": self.alive_players,
            "discussion_statements": self.discussion_statements,
            "impression_statements": self.impression_statements,
            "votes": self.votes,
            "eliminated_player": self.eliminated_player,
            "vote_reasoning": self.vote_reasoning
        }
    
    def add_discussion(self, player_name: str, statement: str) -> None:
        """Add discussion statement"""
        if not self.discussion_statements or player_name in self.discussion_statements[len(self.discussion_statements)-1]:
            self.discussion_statements.append({player_name : statement})
        else:
            self.discussion_statements[len(self.discussion_statements)-1][player_name] = statement
    
    def add_impression(self, player_name: str, statement: str) -> None:
        """Add discussion statement"""
        self.impression_statements[player_name] = statement
    
    def add_vote(self, voter: str, voted_for: str, reasoning: str = None) -> None:
        """Add vote record"""
        self.votes[voter] = voted_for
        if reasoning:
            self.vote_reasoning[voter] = reasoning

@dataclass
class GameRecord:
    """Complete Mafia game record"""
    def __init__(self):
        self.game_id: str = generate_game_id()
        self.player_names: List[str] = []
        self.player_roles: Dict[str, str] = {}
        self.night_phases: List[NightPhase] = []
        self.day_phases: List[DayPhase] = []
        self.winner: Optional[str] = None
        self.save_directory: str = "game_records"
        
        # Ensure save directory exists
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
    
    def to_dict(self) -> Dict:
        return {
            "game_id": self.game_id,
            "player_names": self.player_names,
            "player_roles": self.player_roles,
            "night_phases": [phase.to_dict() for phase in self.night_phases],
            "day_phases": [phase.to_dict() for phase in self.day_phases],
            "winner": self.winner,
        }
    
    def start_game(self, players: List) -> None:
        """Initialize game, record player information"""
        self.player_names = [p.name for p in players]
        self.player_roles = {p.name: p.role for p in players}
        self.auto_save()
    
    def start_night_phase(self, night_number: int, alive_players: List[str]) -> None:
        """Start a new night phase"""
        night_phase = NightPhase(
            night_number=night_number,
            alive_players=alive_players
        )
        self.night_phases.append(night_phase)
    
    def record_night_action(self, player_name: str, role: str, action_type: str, 
                          target_name: str = None, action_result: bool = None, 
                          action_reasoning: str = None, llm_prompt: str = None, llm_response: str = None) -> None:
        """Record a night action"""
        current_night = self.get_current_night_phase()
        if current_night:
            action = NightAction(
                player_name=player_name,
                role=role,
                action_type=action_type,
                target_name=target_name,
                action_result=action_result,
                action_reasoning=action_reasoning,
                llm_prompt=llm_prompt,
                llm_response=llm_response
            )
            current_night.add_night_action(action)
    
    def record_night_result(self, killed_player: str = None, investigation_results: Dict[str, bool] = None) -> None:
        """Record night phase results"""
        current_night = self.get_current_night_phase()
        if current_night:
            current_night.killed_player = killed_player
            if investigation_results:
                current_night.investigation_results.update(investigation_results)
            self.auto_save()
    
    def start_day_phase(self, day_number: int, alive_players: List[str]) -> None:
        """Start a new day phase"""
        day_phase = DayPhase(
            day_number=day_number,
            alive_players=alive_players,
            discussion_statements=[]
        )
        self.day_phases.append(day_phase)
    
    def record_discussion(self, player_name: str, statement: str, llm_prompt: str = None, llm_response: str = None) -> None:
        """Record a discussion statement"""
        current_day = self.get_current_day_phase()
        if current_day:
            current_day.add_discussion(player_name, statement)
            if llm_prompt:
                current_day.llm_prompt = llm_prompt
            if llm_response:
                current_day.llm_response = llm_response
    
    def record_impression(self, player_name: str, statement: str, llm_prompt: str = None, llm_response: str = None) -> None:
        """Record a discussion statement"""
        current_day = self.get_current_day_phase()
        if current_day:
            current_day.add_impression(player_name, statement)
            if llm_prompt:
                current_day.llm_prompt = llm_prompt
            if llm_response:
                current_day.llm_response = llm_response
    
    def record_vote(self, voter: str, voted_for: str, reasoning: str = None, llm_prompt: str = None, llm_response: str = None) -> None:
        """Record a vote"""
        current_day = self.get_current_day_phase()
        if current_day:
            current_day.add_vote(voter, voted_for, reasoning)
            if llm_prompt:
                current_day.llm_prompt = llm_prompt
            if llm_response:
                current_day.llm_response = llm_response
    
    def record_day_result(self, eliminated_player: str = None) -> None:
        """Record day phase results"""
        current_day = self.get_current_day_phase()
        if current_day:
            current_day.eliminated_player = eliminated_player
            self.auto_save()
    
    def finish_game(self, winner: str) -> None:
        """Record winner and save final result"""
        self.winner = winner
        self.auto_save()
    
    def get_current_night_phase(self) -> Optional[NightPhase]:
        """Get current night phase"""
        return self.night_phases[-1] if self.night_phases else None
    
    def get_current_day_phase(self) -> Optional[DayPhase]:
        """Get current day phase"""
        return self.day_phases[-1] if self.day_phases else None
    
    def auto_save(self) -> None:
        """Automatically save current game record to file"""
        file_path = os.path.join(self.save_directory, f"{self.game_id}.json")
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=4, ensure_ascii=False)
        print(f"Game record has been automatically saved to {file_path}")

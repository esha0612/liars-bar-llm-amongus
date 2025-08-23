from dataclasses import dataclass, field
from typing import Dict, List, Optional
import datetime
import json
import os

# ----- structures -----
@dataclass
class TableTalkLine:
    day_number: int
    speaker: str
    text: str
    def to_dict(self) -> Dict:
        return {"day_number": self.day_number, "speaker": self.speaker, "text": self.text}

@dataclass
class NightRecord:
    night_number: int
    poison_target: Optional[str] = None
    protect_target: Optional[str] = None
    demon_kill_target: Optional[str] = None
    death: Optional[str] = None
    ravenkeeper_target: Optional[str] = None
    ravenkeeper_result: Optional[str] = None
    info_messages: List[Dict] = field(default_factory=list)  # [{"to":name,"msg":text}]
    def to_dict(self) -> Dict:
        return {
            "night_number": self.night_number,
            "poison_target": self.poison_target,
            "protect_target": self.protect_target,
            "demon_kill_target": self.demon_kill_target,
            "death": self.death,
            "ravenkeeper_target": self.ravenkeeper_target,
            "ravenkeeper_result": self.ravenkeeper_result,
            "info_messages": self.info_messages,
        }

@dataclass
class DayRecord:
    day_number: int
    last_night_death: Optional[str] = None
    nominator: Optional[str] = None
    nominee: Optional[str] = None
    votes: Dict[str, str] = field(default_factory=dict)  # name -> YES/NO
    executed: bool = False
    executed_name: Optional[str] = None
    slayer_used: bool = False
    slayer: Optional[str] = None
    slayer_target: Optional[str] = None
    mayor_cancelled: bool = False
    def to_dict(self) -> Dict:
        return {
            "day_number": self.day_number,
            "last_night_death": self.last_night_death,
            "nominator": self.nominator,
            "nominee": self.nominee,
            "votes": self.votes,
            "executed": self.executed,
            "executed_name": self.executed_name,
        }

class GameRecord:
    def __init__(self):
        os.makedirs("game_records", exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.path = os.path.join("game_records", f"botc_game_{ts}.json")

        self.mode = "BloodOnTheClocktowerLite"
        self.players: List[Dict] = []
        self.table_talk: List[TableTalkLine] = []
        self.nights: List[NightRecord] = []
        self.days: List[DayRecord] = []
        self.night_number = 0
        self.day_number = 0
        self.winner: Optional[str] = None
        self.last_night_death: Optional[str] = None
        self.last_executed: Optional[str] = None
        self.last_executed_role: Optional[str] = None

    # ----- lifecycle -----
    def start_game(self, players):
        self.players = [{"name": p.name, "model": p.model_name, "role": p.role, "team": p.team} for p in players]
        self.auto_save()

    def finish_game(self, winner: str):
        self.winner = winner
        self.auto_save()

    # ----- night/day increment -----
    def new_night(self, n: int):
        self.night_number = n
        self.nights.append(NightRecord(night_number=n))
        self.auto_save()

    def new_day(self, n: int):
        self.day_number = n
        dr = DayRecord(day_number=n, last_night_death=self.last_night_death)
        self.days.append(dr)
        self.auto_save()

    # ----- night setters -----
    def set_poison(self, name: str):
        self.nights[-1].poison_target = name; self.auto_save()

    def set_protect(self, name: str):
        self.nights[-1].protect_target = name; self.auto_save()

    def set_demon_kill(self, name: str):
        self.nights[-1].demon_kill_target = name; self.auto_save()

    def set_night_death(self, name: Optional[str]):
        self.nights[-1].death = name
        self.last_night_death = name
        self.auto_save()

    def add_info_message(self, to_name: str, msg: str):
        self.nights[-1].info_messages.append({"to": to_name, "msg": msg})
        self.auto_save()

    def set_ravenkeeper(self, target: str, result_role: str):
        self.nights[-1].ravenkeeper_target = target
        self.nights[-1].ravenkeeper_result = result_role
        self.auto_save()

    # ----- day setters -----
    def set_nomination(self, nominator: str, nominee: str):
        self.days[-1].nominator = nominator
        self.days[-1].nominee = nominee
        self.auto_save()

    def record_vote(self, voter: str, vote: str):
        self.days[-1].votes[voter] = vote
        self.auto_save()

    def set_execution(self, executed: bool, executed_name: Optional[str]):
        self.days[-1].executed = executed
        self.days[-1].executed_name = executed_name
        self.last_executed = executed_name if executed else None
        self.auto_save()
    
    def record_slayer_use(self, slayer: str, target: str, success: bool):
        self.days[-1].slayer_used = success
        self.days[-1].slayer = slayer
        self.days[-1].slayer_target = target
        self.auto_save()

    def set_mayor_cancelled(self, cancelled: bool):
        self.days[-1].mayor_cancelled = cancelled
        self.auto_save()

    # ----- talk -----
    def add_table_talk(self, speaker: str, text: str):
        self.table_talk.append(TableTalkLine(day_number=self.day_number, speaker=speaker, text=text))
        self.auto_save()

    def get_recent_table_talk(self, day_number: int, k: int = 8) -> List[Dict]:
        lines = [t for t in self.table_talk if t.day_number == day_number]
        return [t.to_dict() for t in lines[-k:]]

    def format_recent_table_talk_text(self, day_number: int, k: int = 8) -> str:
        lines = self.get_recent_table_talk(day_number, k)
        return "\n".join(f"{l['speaker']}: {l['text']}" for l in lines)

    # ----- persist -----
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode,
            "players": self.players,
            "night_number": self.night_number,
            "day_number": self.day_number,
            "last_night_death": self.last_night_death,
            "last_executed": self.last_executed,
            "last_executed_role": self.last_executed_role,
            "nights": [n.to_dict() for n in self.nights],
            "days": [d.to_dict() for d in self.days],
            "table_talk": [t.to_dict() for t in self.table_talk],
            "winner": self.winner,
        }

    def auto_save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception:
            pass
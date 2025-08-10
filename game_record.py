import json
import os
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class GovernmentProposal:
    round_number: int
    president: str
    chancellor: str
    votes: Dict[str, str] = field(default_factory=dict)  # name -> "JA"/"NEIN"
    passed: bool = False
    hitler_elected_trigger: bool = False

    def to_dict(self) -> Dict:
        return {
            "round_number": self.round_number,
            "president": self.president,
            "chancellor": self.chancellor,
            "votes": self.votes,
            "passed": self.passed,
            "hitler_elected_trigger": self.hitler_elected_trigger
        }

@dataclass
class LegislativeSession:
    round_number: int
    president: str
    chancellor: str
    president_draw: List[str] = field(default_factory=list)   # 3 policies
    president_discard: Optional[str] = None
    chancellor_received: List[str] = field(default_factory=list)  # 2 policies
    chancellor_discard: Optional[str] = None
    enacted_policy: Optional[str] = None  # "Liberal" or "Fascist"

    def to_dict(self) -> Dict:
        return {
            "round_number": self.round_number,
            "president": self.president,
            "chancellor": self.chancellor,
            "president_draw": self.president_draw,
            "president_discard": self.president_discard,
            "chancellor_received": self.chancellor_received,
            "chancellor_discard": self.chancellor_discard,
            "enacted_policy": self.enacted_policy
        }

@dataclass
class TableTalkLine:
    round_number: int
    speaker: str
    text: str

    def to_dict(self) -> Dict:
        return {
            "round_number": self.round_number,
            "speaker": self.speaker,
            "text": self.text
        }

@dataclass
class ExecutiveAction:
    round_number: int
    action: str                     # "investigate"|"special_election"|"policy_peek"|"execution"|"veto"
    president: str
    target: Optional[str] = None    # investigate/special/execute target
    result: Optional[str] = None    # e.g., "Liberal"/"Fascist" for investigate; "ACCEPT"/"REJECT" for veto
    seen_policies: Optional[List[str]] = None  # for policy peek (private info)
    chancellor: Optional[str] = None           # for veto
    private_to: Optional[str] = None          # e.g., president (peek/investigation result)

    def to_dict(self) -> Dict:
        return {
            "round_number": self.round_number,
            "action": self.action,
            "president": self.president,
            "target": self.target,
            "result": self.result,
            "seen_policies": self.seen_policies,
            "chancellor": self.chancellor,
            "private_to": self.private_to,
        }

class GameRecord:
    def __init__(self):
        # Ensure the folder exists
        self.save_dir = "game_records"
        os.makedirs(self.save_dir, exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.path = os.path.join(self.save_dir, f"{timestamp}.json")

        # Secret Hitler fields
        self.mode: str = "SecretHitler"
        self.round_number: int = 0
        self.liberal_policies: int = 0
        self.fascist_policies: int = 0
        self.election_tracker: int = 0
        self.players: List[Dict] = []
        self.governments: List[GovernmentProposal] = []
        self.sessions: List[LegislativeSession] = []
        self.winner: Optional[str] = None
        self.table_talk: List[TableTalkLine] = []
        self.executive_actions: List[ExecutiveAction] = []

    def add_table_talk(self, round_number: int, speaker: str, text: str):
        self.table_talk.append(TableTalkLine(round_number, speaker, text))
        self.auto_save()
   
    def get_recent_table_talk(self, round_number: int, k: int = 8) -> list[dict]:
        # return up to last k lines for this round
        lines = [t for t in self.table_talk if t.round_number == round_number]
        return [t.to_dict() for t in lines[-k:]]

    def format_recent_table_talk_text(self, round_number: int, k: int = 8) -> str:
        lines = self.get_recent_table_talk(round_number, k)
        return "\n".join(f"{l['speaker']}: {l['text']}" for l in lines)

    def add_executive_action(self, **kwargs):
        self.executive_actions.append(ExecutiveAction(**kwargs))
        self.auto_save()

    # ---------- lifecycle ----------
    def start_game(self, players):
        self.players = [{"name": p.name, "model": p.model_name, "role": p.role} for p in players]
        self.auto_save()

    def finish_game(self, winner: str):
        self.winner = winner
        self.auto_save()

    # ---------- rounds & elections ----------
    def new_round(self, n: int):
        self.round_number = n
        self.auto_save()

    def start_government(self, president: str, chancellor: str):
        gov = GovernmentProposal(round_number=self.round_number, president=president, chancellor=chancellor)
        self.governments.append(gov)
        self.auto_save()

    def record_vote(self, voter: str, vote: str):
        if not self.governments:
            return
        self.governments[-1].votes[voter] = vote
        self.auto_save()

    def finalize_government(self, passed: bool, hitler_trigger: bool = False):
        if not self.governments:
            return
        self.governments[-1].passed = passed
        self.governments[-1].hitler_elected_trigger = hitler_trigger
        self.auto_save()

    # ---------- legislative sessions ----------
    def start_session(self, president: str, chancellor: str, draw: List[str]):
        sess = LegislativeSession(round_number=self.round_number, president=president, chancellor=chancellor)
        sess.president_draw = draw[:]
        self.sessions.append(sess)
        self.auto_save()

    def set_president_discard(self, policy: str, chancellor_received: List[str]):
        if not self.sessions:
            return
        self.sessions[-1].president_discard = policy
        self.sessions[-1].chancellor_received = chancellor_received[:]
        self.auto_save()

    def set_chancellor_discard_and_enact(self, discard: str, enacted: str):
        if not self.sessions:
            return
        self.sessions[-1].chancellor_discard = discard
        self.sessions[-1].enacted_policy = enacted
        if enacted == "Liberal":
            self.liberal_policies += 1
        elif enacted == "Fascist":
            self.fascist_policies += 1
        self.election_tracker = 0
        self.auto_save()

    # ---------- top-deck ----------
    def top_deck_enact(self, policy: str):
        sess = LegislativeSession(round_number=self.round_number, president="TopDeck", chancellor="TopDeck")
        sess.enacted_policy = policy
        self.sessions.append(sess)
        if policy == "Liberal":
            self.liberal_policies += 1
        else:
            self.fascist_policies += 1
        self.election_tracker = 0
        self.auto_save()

    # ---------- persistence ----------
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode,
            "round_number": self.round_number,
            "liberal_policies": self.liberal_policies,
            "fascist_policies": self.fascist_policies,
            "election_tracker": self.election_tracker,
            "players": self.players,
            "governments": [g.to_dict() for g in self.governments],
            "sessions": [s.to_dict() for s in self.sessions],
            "winner": self.winner,
            "table_talk": [t.to_dict() for t in self.table_talk],
            "executive_actions": [e.to_dict() for e in self.executive_actions],
        }

    def auto_save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception:
            pass

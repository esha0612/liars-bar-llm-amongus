import random
import json
import re
from typing import List, Dict, Optional, Tuple
from llm_client import LLMClient
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
log_path = os.path.join(log_dir, f"secret_hitler_game_{timestamp}.txt")
sys.stdout = Tee(log_path)

RULE_BASE_PATH = "prompt/secret_hitler_rule_base.txt"
NOMINATE_PROMPT_PATH = "prompt/nominate_prompt.txt"
VOTE_GOV_PROMPT_PATH = "prompt/vote_government_prompt.txt"
PRES_DISCARD_PROMPT_PATH = "prompt/president_discard_prompt.txt"
CHAN_DISCARD_PROMPT_PATH = "prompt/chancellor_discard_prompt.txt"
TABLE_TALK_PROMPT_PATH = "prompt/table_talk_prompt.txt"
INVESTIGATE_CHOOSE_PROMPT_PATH = "prompt/investigate_choose_prompt.txt"
SPECIAL_ELECTION_PROMPT_PATH   = "prompt/special_election_prompt.txt"
POLICY_PEEK_COMMENT_PROMPT_PATH = "prompt/policy_peek_comment_prompt.txt"
EXECUTION_PROMPT_PATH          = "prompt/execution_prompt.txt"
CHANCELLOR_VETO_PROMPT_PATH    = "prompt/chancellor_veto_prompt.txt"
PRESIDENT_VETO_ACCEPT_PROMPT_PATH = "prompt/president_veto_accept_prompt.txt"

class _SafeDict(dict):
    def __missing__(self, key):
        # Silently blank out any missing placeholder so .format_map doesn't crash
        return ""

class Player:
    def __init__(self, name: str, model_name: str, role: str):
        """
        Initialize a player for Secret Hitler.

        Args:
            name: Player's name.
            model_name: The LLM model assigned to this player.
            role: The secret role assigned to this player. One of:
                  "Liberal", "Fascist", "Hitler".
        """
        # identity & model
        self.name = name
        self.model_name = model_name

        # role & faction
        valid_roles = {"Liberal", "Fascist", "Hitler"}
        if role not in valid_roles:
            raise ValueError(f"Invalid role '{role}'. Expected one of {sorted(valid_roles)}.")
        self.role = role
        self.faction = "Fascist" if role in ("Fascist", "Hitler") else "Liberal"
        self.is_hitler = (role == "Hitler")

        # game-state flags
        self.alive = True

        # social/belief state
        self.opinions: Dict[str, str] = {}

        # secret knowledge (populate at setup)
        self.known_allies = set()   # names known to share your team
        self.knows_fascists = False

        # light logs
        self.vote_history: List[Tuple[int, str]] = []       # (round, "JA"/"NEIN")
        self.nomination_history: List[Tuple[int, str]] = [] # (round, nominee)

        # LLM
        self.llm_client = LLMClient()

    # ---------- Prompt helpers ----------
    def _format_prompt(self, template: str, **kwargs) -> str:
        return template.format_map(_SafeDict(**kwargs))

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _read_rules(self) -> str:
        return self._read_file(RULE_BASE_PATH)

    # ---------- Secret Hitler actions ----------
    def choose_chancellor_nominee(self, alive_names: List[str], ineligible: List[str], round_no: int) -> Optional[str]:
        choices = [n for n in alive_names if n != self.name and n not in ineligible]
        if not choices:
            return None
        rules = self._read_rules()
        template = self._read_file(NOMINATE_PROMPT_PATH)
        prompt = self._format_prompt(
            template,
            rules=rules,
            self_name=self.name,
            self_role=self.role,
            alive_players=", ".join(alive_names),
            ineligible=", ".join(ineligible) if ineligible else "None"
        )
        content, _ = self.llm_client.chat([{"role": "user", "content": prompt}], model=self.model_name)
        chosen = content.strip()
        if chosen not in choices:
            chosen = random.choice(choices)
        self.nomination_history.append((round_no, chosen))
        return chosen

    def vote_on_government(self, president: str, chancellor: str, alive_names: List[str],
                           liberal_count: int, fascist_count: int, tracker: int, round_no: int) -> str:
        rules = self._read_rules()
        template = self._read_file(VOTE_GOV_PROMPT_PATH)
        prompt = self._format_prompt(
            template,
            rules=rules,
            self_name=self.name,
            self_role=self.role,
            president=president,
            chancellor=chancellor,
            alive_players=", ".join(alive_names),
            liberal_count=liberal_count,
            fascist_count=fascist_count,
            tracker=tracker
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        vote = content.strip().upper()
        vote = "JA" if vote == "JA" else "NEIN"
        self.vote_history.append((round_no, vote))
        return vote

    def president_discard(self, drawn_policies: List[str], alive_players: List[str] = None) -> str:
        rules = self._read_rules()
        template = self._read_file(PRES_DISCARD_PROMPT_PATH)
        prompt = self._format_prompt(
            template,
            rules=rules,
            self_name=self.name,
            self_role=self.role,
            drawn_policies=", ".join(drawn_policies),
            alive_players=", ".join(alive_players) if alive_players else ""
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        out = content.strip().capitalize()
        return out if out in ["Liberal","Fascist"] else random.choice(["Liberal","Fascist"])

    def chancellor_discard(self, received_policies: List[str], alive_players: List[str] = None) -> str:
        rules = self._read_rules()
        template = self._read_file(CHAN_DISCARD_PROMPT_PATH)
        prompt = self._format_prompt(
            template,
            rules=rules,
            self_name=self.name,
            self_role=self.role,
            received_policies=", ".join(received_policies),
            alive_players=", ".join(alive_players) if alive_players else ""
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        out = content.strip().capitalize()
        return out if out in ["Liberal","Fascist"] else random.choice(["Liberal","Fascist"])

    def table_talk(self, alive_names, last_president, last_chancellor,
               liberal_count, fascist_count, tracker,
               recent_discussion_text: str) -> str:
        tpl = self._read_file(TABLE_TALK_PROMPT_PATH)
        rules = self._read_rules()
        if not tpl:
            return f"{self.name}: I think {last_chancellor or 'someone'} is suspicious."
        prompt = self._format_prompt(
            tpl,
            rules=rules,
            self_name=self.name,
            self_role=self.role,
            alive_players=", ".join([n for n in alive_names if n != self.name]),
            last_president=last_president or "None",
            last_chancellor=last_chancellor or "None",
            liberal_count=liberal_count,
            fascist_count=fascist_count,
            tracker=tracker,
            recent_discussion=recent_discussion_text or "(no prior discussion)"
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        return f"{self.name}: {content.strip() or '(no comment)'}"
    
    def choose_investigation_target(self, alive_names: list[str]) -> str:
        rules = self._read_rules()
        tpl = self._read_file(INVESTIGATE_CHOOSE_PROMPT_PATH)
        choices = [n for n in alive_names if n != self.name]
        prompt = self._format_prompt(
            tpl, rules=rules, self_name=self.name, alive_players=", ".join(choices)
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = content.strip()
        return pick if pick in choices else random.choice(choices)

    def choose_special_election_president(self, alive_names: list[str]) -> str:
        rules = self._read_rules()
        tpl = self._read_file(SPECIAL_ELECTION_PROMPT_PATH)
        choices = [n for n in alive_names if n != self.name]
        prompt = self._format_prompt(
            tpl, rules=rules, self_name=self.name, alive_players=", ".join(choices)
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = content.strip()
        return pick if pick in choices else random.choice(choices)

    def choose_execution_target(self, alive_names: list[str]) -> str:
        rules = self._read_rules()
        tpl = self._read_file(EXECUTION_PROMPT_PATH)
        choices = [n for n in alive_names if n != self.name]
        prompt = self._format_prompt(
            tpl, rules=rules, self_name=self.name, alive_players=", ".join(choices)
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = content.strip()
        return pick if pick in choices else random.choice(choices)

    def chancellor_veto_decision(self, received_policies: list[str]) -> str:
        rules = self._read_rules()
        tpl = self._read_file(CHANCELLOR_VETO_PROMPT_PATH)
        prompt = self._format_prompt(
            tpl, rules=rules, self_name=self.name,
            received_policies=", ".join(received_policies)
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        out = content.strip().upper()
        return "VETO" if out == "VETO" else "CONTINUE"

    def president_veto_accept(self, chancellor_name: str, received_policies: list[str]) -> str:
        rules = self._read_rules()
        tpl = self._read_file(PRESIDENT_VETO_ACCEPT_PROMPT_PATH)
        prompt = self._format_prompt(
            tpl, rules=rules, self_name=self.name, chancellor=chancellor_name,
            received_policies=", ".join(received_policies)
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        out = content.strip().upper()
        return "ACCEPT" if out == "ACCEPT" else "REJECT"

    def policy_peek_public_comment(self, top_three: list[str]) -> str:
        # Optional flavor; safe even if prompt is missing
        tpl = self._read_file(POLICY_PEEK_COMMENT_PROMPT_PATH)
        if not tpl:
            return ""
        rules = self._read_rules()
        prompt = self._format_prompt(
            tpl, rules=rules, self_name=self.name, top_three=", ".join(top_three)
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        return content.strip()
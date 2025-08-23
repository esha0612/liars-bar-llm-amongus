import random
import json
import re
from typing import List, Dict, Optional, Tuple
# from llm_client import LLMClient
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
log_path = os.path.join(log_dir, f"botc_game_{timestamp}.txt")
sys.stdout = Tee(log_path)

# ---------- prompt paths ----------
RULE_BASE_BOTC_PATH = "prompt/botc_rule_base.txt"
TABLE_TALK_BOTC_PATH = "prompt/table_talk_botc.txt"
NOMINATE_EXEC_PROMPT_PATH = "prompt/nominate_execute_prompt.txt"
VOTE_EXEC_PROMPT_PATH = "prompt/vote_execute_prompt.txt"

IMP_KILL_PROMPT_PATH = "prompt/imp_kill_prompt.txt"
POISONER_POISON_PROMPT_PATH = "prompt/poisoner_poison_prompt.txt"
MONK_PROTECT_PROMPT_PATH = "prompt/monk_protect_prompt.txt"
FT_PAIR_PROMPT_PATH = "prompt/fortune_teller_pair_prompt.txt"
RAVENKEEPER_TARGET_PROMPT_PATH = "prompt/ravenkeeper_target_prompt.txt"

BUTLER_CHOOSE_MASTER_PROMPT_PATH = "prompt/butler_choose_master_prompt.txt"
SLAYER_DECISION_PROMPT_PATH      = "prompt/slayer_decision_prompt.txt"
MAYOR_CANCEL_PROMPT_PATH         = "prompt/mayor_cancel_prompt.txt"

# ---------- utils ----------
class _SafeDict(dict):
    def __missing__(self, key):
        return ""

def _norm_yesno(s: str) -> str:
    s = (s or "").strip().upper()
    return "YES" if s == "YES" else "NO"

def _parse_two_names(s: str, allow: List[str]) -> Tuple[Optional[str], Optional[str]]:
    if not s:
        return None, None
    raw = s.replace(" and ", ",").replace(";", ",")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    picks = [p for p in parts if p in allow]
    if len(picks) >= 2:
        return picks[0], picks[1]
    # fallback
    if len(allow) >= 2:
        a, b = random.sample(allow, 2)
        return a, b
    return None, None

class Player:
    def __init__(self, name: str, model_name: str, role: str):
        """
        Blood on the Clocktower (Lite) player.
        Roles: Good: Empath, FortuneTeller, Undertaker, Monk, Ravenkeeper
               Evil: Imp (Demon), Poisoner (Minion)
        """
        self.name = name
        self.model_name = model_name
        self.role = role
        self.team = "Evil" if role in ("Imp","Poisoner") else "Good"
        self.alive = True

        self.butler_master: Optional[str] = None
        self.slayer_used: bool = False

        # private memory for info you receive at night
        self.private_info_log: List[str] = []

        # LLM
        self.llm_client = LLMRouter()

    # ---------- IO helpers ----------
    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _format(self, template: str, **kwargs) -> str:
        return template.format_map(_SafeDict(**kwargs))

    def remember(self, msg: str):
        if msg:
            self.private_info_log.append(msg)

    def last_private_hint(self) -> str:
        return self.private_info_log[-1] if self.private_info_log else "(none)"

    # ---------- Table talk / Day ----------
    def table_talk(self, recent_discussion_text: str, last_night_death: str,
                   alive_others: List[str], day_number: int, night_number: int) -> str:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(TABLE_TALK_BOTC_PATH)
        prompt = self._format(
            tpl,
            rules=rules,
            self_name=self.name,
            recent_discussion=recent_discussion_text or "(no discussion yet)",
            last_night_death=last_night_death or "No one",
            alive_others=", ".join([n for n in alive_others if n != self.name]),
            day_number=day_number,
            night_number=night_number,
            private_info_last=self.last_private_hint()
        )
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        return f"{self.name}: {content.strip()}"

    def nominate_execution(self, alive_names: List[str]) -> Optional[str]:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(NOMINATE_EXEC_PROMPT_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name,
                              alive_players=", ".join(alive_names))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = (content or "").strip()
        return pick if pick in alive_names else random.choice(alive_names)

    def vote_execute(self, nominee: str, alive_names: List[str]) -> str:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(VOTE_EXEC_PROMPT_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name, nominee=nominee,
                              alive_players=", ".join(alive_names))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        return _norm_yesno(content)

    # ---------- Night actions ----------
    def imp_kill(self, alive_names: List[str]) -> str:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(IMP_KILL_PROMPT_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name,
                              alive_players=", ".join([n for n in alive_names if n != self.name]))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = (content or "").strip()
        choices = [n for n in alive_names if n != self.name]
        return pick if pick in choices else random.choice(choices)

    def poisoner_poison(self, alive_names: List[str]) -> str:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(POISONER_POISON_PROMPT_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name,
                              alive_players=", ".join([n for n in alive_names if n != self.name]))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = (content or "").strip()
        choices = [n for n in alive_names if n != self.name]
        return pick if pick in choices else random.choice(choices)

    def monk_protect(self, alive_names: List[str]) -> str:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(MONK_PROTECT_PROMPT_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name,
                              alive_players=", ".join(alive_names))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = (content or "").strip()
        return pick if pick in alive_names else random.choice(alive_names)

    def fortune_teller_pair(self, alive_names: List[str]) -> Tuple[Optional[str], Optional[str]]:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(FT_PAIR_PROMPT_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name,
                              alive_players=", ".join(alive_names))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        a, b = _parse_two_names((content or ""), alive_names)
        return a, b

    def ravenkeeper_target(self, alive_names: List[str]) -> Optional[str]:
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        tpl = self._read_file(RAVENKEEPER_TARGET_PROMPT_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name,
                              alive_players=", ".join(alive_names))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = (content or "").strip()
        return pick if pick in alive_names else random.choice(alive_names)

    def butler_choose_master(self, alive_names: List[str]) -> Optional[str]:
        # Butler picks a master each day (if alive)
        tpl = self._read_file(BUTLER_CHOOSE_MASTER_PROMPT_PATH)
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        choices = [n for n in alive_names if n != self.name]
        if not choices or self.role != "Butler":
            return None
        prompt = self._format(tpl, rules=rules, self_name=self.name, alive_players=", ".join(choices))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = (content or "").strip()
        self.butler_master = pick if pick in choices else random.choice(choices)
        return self.butler_master

    def slayer_decision(self, alive_names: List[str]) -> Optional[str]:
        # Once per game. Return target name or None.
        if self.role != "Slayer" or self.slayer_used:
            return None
        tpl = self._read_file(SLAYER_DECISION_PROMPT_PATH)
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name, alive_players=", ".join(alive_names))
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        pick = (content or "").strip()
        if pick == "None":
            return None
        return pick if pick in alive_names and pick != self.name else None

    def mayor_cancel_execution(self) -> bool:
        # Ask the Mayor if they cancel their own execution
        if self.role != "Mayor":
            return False
        tpl = self._read_file(MAYOR_CANCEL_PROMPT_PATH)
        rules = self._read_file(RULE_BASE_BOTC_PATH)
        prompt = self._format(tpl, rules=rules, self_name=self.name)
        content, _ = self.llm_client.chat([{"role":"user","content":prompt}], model=self.model_name)
        return (content or "").strip().upper() == "YES"
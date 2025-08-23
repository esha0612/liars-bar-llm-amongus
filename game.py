import random
from typing import List, Dict, Optional
from player import Player
from game_record import GameRecord
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
log_path = os.path.join(log_dir, f"botc_game_{timestamp}.txt")
sys.stdout = Tee(log_path)

class BotCGame:
    """
    Blood on the Clocktower (Trouble Brewing – Lite)
    Roles implemented:
      Good: Empath, FortuneTeller, Undertaker, Monk, Ravenkeeper
      Evil: Imp (Demon), Poisoner (Minion)
    """

    def __init__(self, player_configs: List[Dict[str, str]], roles: Optional[List[str]] = None):
        self.players = self.assign_roles(player_configs, roles)
        self.record = GameRecord()
        self.winner: Optional[str] = None
        self.day_number = 0
        self.night_number = 0

        # seating order is input order; used for Empath neighbors
        self.seat_names = [p.name for p in self.players]

        # last executed info for Undertaker (learns at the following night)
        self.last_executed_name: Optional[str] = None
        self.last_executed_role: Optional[str] = None

    # ----- setup -----
    def assign_roles(self, player_configs, roles_opt):
        n = len(player_configs)
        if roles_opt is None:
            # 11-player lite spread (9 Good, 2 Evil)
            # Townsfolk: Empath, FortuneTeller, Undertaker, Monk, Ravenkeeper, Chef, Slayer, Mayor
            # Outsider:  Butler
            # Evil:      Imp (Demon), Poisoner (Minion)
            if n != 11:
                raise ValueError("This 11-player setup expects exactly 11 players.")
            roles = [
                "Empath", "FortuneTeller", "Undertaker", "Monk",
                "Ravenkeeper", "Chef", "Slayer", "Mayor",
                "Butler", "Imp", "Poisoner"
            ]
            random.shuffle(roles)
        else:
            roles = roles_opt[:]
            assert len(roles) == n

        out = []
        for cfg, r in zip(player_configs, roles):
            out.append(Player(cfg["name"], model_name=cfg["model"], role=r))
        return out

    # ----- helpers -----
    def get_player(self, name: str) -> Player:
        return next(p for p in self.players if p.name == name)

    def alive_players(self) -> List[Player]:
        return [p for p in self.players if p.alive]

    def alive_names(self) -> List[str]:
        return [p.name for p in self.alive_players()]

    def team_of(self, name: str) -> str:
        return self.get_player(name).team

    def role_of(self, name: str) -> str:
        return self.get_player(name).role

    def neighbors_of(self, name: str) -> List[str]:
        # circular neighbors for Empath
        i = self.seat_names.index(name)
        L = self.seat_names[(i - 1) % len(self.seat_names)]
        R = self.seat_names[(i + 1) % len(self.seat_names)]
        return [L, R]

    # ----- game loop -----
    def start_game(self):
        self.record.start_game(self.players)
        # standard BotC starts at Night 1
        while not self.check_win():
            self.night_number += 1
            self.night_phase()
            if self.check_win(): break
            self.day_number += 1
            self.day_phase()
        self.announce_winner()

    # ----- night phase -----
    def night_phase(self):
        self.record.new_night(self.night_number)
        alive = self.alive_players()
        alive_names = [p.name for p in alive]

        # NIGHT ORDER (poison -> protect -> kill -> ravenkeeper-on-death -> undertaker -> empath -> fortune teller)
        poisoned: Optional[str] = None
        protected: Optional[str] = None

        # Poisoner
        poisoners = [p for p in alive if p.role == "Poisoner"]
        if poisoners:
            choice = poisoners[0].poisoner_poison(alive_names)
            if choice in alive_names:
                poisoned = choice
                self.record.set_poison(choice)

        # Monk
        monks = [p for p in alive if p.role == "Monk"]
        if monks:
            choice = monks[0].monk_protect(alive_names)
            if choice in alive_names:
                protected = choice
                self.record.set_protect(choice)

        # Imp (kill)
        imps = [p for p in alive if p.role == "Imp"]
        night_death: Optional[str] = None
        if imps:
            target = imps[0].imp_kill(alive_names)
            self.record.set_demon_kill(target)
            if target in alive_names and target != protected:
                night_death = target
                self.get_player(target).alive = False
        self.record.set_night_death(night_death)

        # Ravenkeeper (if died at night)
        if night_death and self.role_of(night_death) == "Ravenkeeper":
            rk = self.get_player(night_death)
            target = rk.ravenkeeper_target([n for n in alive_names if n != night_death and self.get_player(n).alive])
            role_seen = self.role_of(target) if target else "Unknown"
            rk.remember(f"Ravenkeeper: {target} is {role_seen}")
            self.record.set_ravenkeeper(target, role_seen)
            self.record.add_info_message(rk.name, f"Ravenkeeper saw {target} as {role_seen}")

        # Undertaker (learns yesterday's executed)
        if self.last_executed_name:
            for p in self.players:
                if p.alive and p.role == "Undertaker":
                    msg = f"Undertaker: Yesterday's executed was {self.last_executed_name} ({self.last_executed_role})"
                    if poisoned == p.name:
                        msg = "Undertaker: Your information feels unreliable tonight."
                    p.remember(msg); self.record.add_info_message(p.name, msg)

        # Empath (neighbors’ evil count)
        for p in self.players:
            if p.alive and p.role == "Empath":
                n1, n2 = self.neighbors_of(p.name)
                evil_count = sum(1 for n in [n1, n2] if self.team_of(n) == "Evil")
                msg = f"Empath: You sense {evil_count} evil among your neighbors."
                if poisoned == p.name:
                    msg = "Empath: Your senses are clouded tonight."
                p.remember(msg); self.record.add_info_message(p.name, msg)

        # Fortune Teller (choose two → YES if imp among them)
        for p in self.players:
            if p.alive and p.role == "FortuneTeller":
                a, b = p.fortune_teller_pair([n for n in self.alive_names() if n != p.name])
                if not a or not b or a == b:
                    # safe fallback
                    choices = [n for n in self.alive_names() if n != p.name]
                    a, b = random.sample(choices, 2)
                yes = (self.role_of(a) == "Imp") or (self.role_of(b) == "Imp")
                msg = f"Fortune Teller: {'YES' if yes else 'NO'} for [{a}, {b}]."
                if poisoned == p.name:
                    msg = f"Fortune Teller: {'NO' if yes else 'YES'} for [{a}, {b}]."
                p.remember(msg); self.record.add_info_message(p.name, msg)
        
        # Chef (first night only): learns number of pairs of evil neighbors
        if self.night_number == 1:
            evil_names = [p.name for p in self.players if (p.role in ("Imp","Poisoner"))]
            # count adjacent pairs (circular) where both are evil
            count_pairs = 0
            for i in range(len(self.seat_names)):
                a = self.seat_names[i]
                b = self.seat_names[(i+1) % len(self.seat_names)]
                if a in evil_names and b in evil_names:
                    count_pairs += 1
            for p in self.players:
                if p.alive and p.role == "Chef":
                    msg = f"Chef: You learned {count_pairs} pair(s) of evil neighbors."
                    # If you use poisoning persistence, flip this when Chef is poisoned; here we assume single-night poison
                    # if poisoned == p.name: msg = "Chef: Your info feels unreliable tonight."
                    p.remember(msg)
                    self.record.add_info_message(p.name, msg)


    # ----- day phase -----
    def day_phase(self):
        self.record.new_day(self.day_number)
        alive_names = self.alive_names()

        # Butler chooses a master each day
        for p in self.alive_players():
            if p.role == "Butler":
                p.butler_choose_master(alive_names)

        # TABLE TALK: 2 passes, speaker order starts from seat 0 (simple); you can rotate if you want
        RECENT_WINDOW = 8
        TALKS_PER_PLAYER = 2
        for _ in range(TALKS_PER_PLAYER):
            for p in self.alive_players():
                recent = self.record.format_recent_table_talk_text(self.day_number, k=RECENT_WINDOW)
                if not recent:
                    seed = (f"Kickoff: Last night death={self.record.last_night_death or 'None'}. "
                            f"State who you'd execute today and why.")
                    recent = seed
                line = p.table_talk(recent, self.record.last_night_death or "None",
                                    [n for n in alive_names if n != p.name],
                                    self.day_number, self.night_number)
                print(line)
                self.record.add_table_talk(p.name, line.split(": ", 1)[-1])
        
        # Slayer: once per game — instant day kill
        for p in list(self.alive_players()):
            if p.role == "Slayer" and not p.slayer_used:
                target = p.slayer_decision(self.alive_names())
                if target:
                    # spend ability
                    p.slayer_used = True
                    # execute target immediately
                    if target in self.alive_names():
                        victim = self.get_player(target)
                        victim.alive = False
                        print(f"SLAYER! {p.name} slays {target}.")
                        self.record.record_slayer_use(slayer=p.name, target=target, success=True)
                        # Early win check if Imp was slain
                        if self.check_win():
                            return
                # If no target, do nothing

        # NOMINATION: everyone proposes; pick plurality nominee
        proposals: dict[str, int] = {}
        nominators_by_nominee: dict[str, list[str]] = {}

        alive_names = self.alive_names()
        for p in self.alive_players():
            pick = p.nominate_execution(alive_names)
            # sanity: enforce alive name
            if pick not in alive_names:
                pick = random.choice(alive_names)
            proposals[pick] = proposals.get(pick, 0) + 1
            nominators_by_nominee.setdefault(pick, []).append(p.name)

        # choose nominee by plurality (break ties randomly)
        top = max(proposals.values())
        nominees = [name for name, cnt in proposals.items() if cnt == top]
        nominee = random.choice(nominees)

        # choose a nominator from those who actually proposed this nominee
        cands = nominators_by_nominee.get(nominee, [])
        nominator = random.choice(cands) if cands else random.choice(alive_names)

        print(f"Nomination: {nominator} nominates {nominee}")
        self.record.set_nomination(nominator, nominee)

        # VOTE (ensure Butlers vote after their master if set)
        alive_objs = self.alive_players()
        alive_names = [x.name for x in alive_objs]

        def voter_order():
            order = []
            # push non-butlers & butlers without master first
            butlers = []
            for p in alive_objs:
                if p.role == "Butler" and p.butler_master in alive_names:
                    butlers.append(p)
                else:
                    order.append(p)
            # append butlers after their masters by simple pass
            # (if multiple butlers choose same master, relative order among them doesn't matter)
            for b in butlers:
                # ensure master already in order; if not, just put b at end
                order.append(b)
            return order

        votes = {}
        yes = 0
        for voter in voter_order():
            if voter.role == "Butler" and voter.butler_master in votes:
                # We already know master's vote
                masters_vote = votes[voter.butler_master]
                if masters_vote != "YES":
                    v = "NO"
                else:
                    v = voter.vote_execute(nominee, alive_names)
            else:
                # For masters or non-butlers (or butler whose master hasn't voted yet)
                v = voter.vote_execute(nominee, alive_names)
            votes[voter.name] = v
            self.record.record_vote(voter.name, v)
            print(f"{voter.name} votes {v}")
            if v == "YES": yes += 1

        executed = yes > (len(alive_names) // 2)
        executed_name = nominee if executed else None

        # Mayor: may cancel their own execution
        if executed and nominee in self.alive_names():
            if self.role_of(nominee) == "Mayor":
                mayor = self.get_player(nominee)
                if mayor.alive:
                    cancel = mayor.mayor_cancel_execution()
                    self.record.set_mayor_cancelled(cancel)
                    if cancel:
                        print(f"Mayor {nominee} cancels their own execution. No one is executed.")
                        executed = False
                        executed_name = None
        
        if executed:
            self.get_player(nominee).alive = False
            print(f"Executed: {nominee}")
            self.last_executed_name = nominee
            self.last_executed_role = self.role_of(nominee)
            self.record.last_executed_role = self.last_executed_role
        else:
            print("No execution today.")
            self.last_executed_name = None
            self.last_executed_role = None

        self.record.set_execution(executed, executed_name)

    # ----- win checks -----
    def check_win(self) -> bool:
        if self.winner: return True
        # Good win: Imp dead
        imps_alive = any(p.alive and p.role == "Imp" for p in self.players)
        if not imps_alive:
            self.winner = "Good"; return True
        # Evil win: Imp alive and only 2 players remain
        if imps_alive and len(self.alive_players()) <= 2:
            self.winner = "Evil"; return True
        return False

    def announce_winner(self):
        print("\n=== GAME OVER ===")
        print(f"{self.winner} win!")
        self.record.finish_game(self.winner)

if __name__ == "__main__":
    player_configs = [
        {"name": "Sarah",   "model": "llama3.1:8b"},
        {"name": "Derek",   "model": "deepseek-r1:7b"},
        {"name": "Emma",    "model": "dolphin3:latest"},
        {"name": "Talia",   "model": "qwen2.5:7b"},
        {"name": "Anika",   "model": "mistral:7b"},
        {"name": "Nick",    "model": "mistral-nemo:12b"},
        {"name": "Philip",  "model": "phi4:14b"},
        {"name": "Peter",   "model": "phi3.5:3.8b"},
        {"name": "George",  "model": "llava:7b"},
        {"name": "Enrique", "model": "gemma2:9b"},
        {"name": "Maria",   "model": "gpt-4o-mini"},
    ]
    print("Blood on the Clocktower (Lite) starting…")
    game = BotCGame(player_configs)
    game.start_game()

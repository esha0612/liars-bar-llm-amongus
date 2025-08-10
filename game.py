import random
from typing import Dict, List, Optional
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
log_path = os.path.join(log_dir, f"secret_hitler_game_{timestamp}.txt")
sys.stdout = Tee(log_path)

class SecretHitlerGame:
    def __init__(self, player_configs: List[Dict[str, str]], roles: Optional[List[str]] = None):
        self.players = self.assign_roles(player_configs, roles)
        self.record = GameRecord()
        self.winner: Optional[str] = None

        # Policy deck: 6 Liberal, 11 Fascist (official)
        self.deck = ["Liberal"] * 6 + ["Fascist"] * 11
        random.shuffle(self.deck)
        self.discard: List[str] = []

        # Presidency rotation & term limits
        self.president_index = 0
        self.last_elected_president: Optional[str] = None
        self.last_elected_chancellor: Optional[str] = None

        # Optional: setup “Night 0” knowledge (only stored locally; not printed)
        self._setup_secret_knowledge()

    # --- Role assignment per official counts ---
    def assign_roles(self, player_configs, roles_opt):
        n = len(player_configs)
        if roles_opt is None:
            setup = {
                5: ("Liberal", 3, "Fascist", 1, "Hitler", 1),
                6: ("Liberal", 4, "Fascist", 1, "Hitler", 1),
                7: ("Liberal", 4, "Fascist", 2, "Hitler", 1),
                8: ("Liberal", 5, "Fascist", 2, "Hitler", 1),
                9: ("Liberal", 5, "Fascist", 3, "Hitler", 1),
                10: ("Liberal", 6, "Fascist", 3, "Hitler", 1),
            }
            if n not in setup:
                raise ValueError("Secret Hitler supports 5–10 players.")
            L, Lc, F, Fc, H, Hc = setup[n]
            roles = [L]*Lc + [F]*Fc + [H]*Hc
            random.shuffle(roles)
        else:
            roles = roles_opt[:]
            assert len(roles) == n
        players = []
        for cfg, r in zip(player_configs, roles):
            players.append(Player(cfg["name"], model_name=cfg["model"], role=r))
        return players

    def _setup_secret_knowledge(self):
        fascists = [p for p in self.players if p.role == "Fascist"]
        hitler = next((p for p in self.players if p.role == "Hitler"), None)
        # All fascists know each other and Hitler
        for f in fascists:
            f.known_allies = set([x.name for x in fascists if x is not f])
            if hitler: f.known_allies.add(hitler.name)
            f.knows_fascists = True
        # Hitler knowledge depends on count; simplest: 5–6 players, Hitler knows fascist
        if len(self.players) <= 6 and hitler and fascists:
            hitler.known_allies = set([fascists[0].name])
            hitler.knows_fascists = True

    def start_game(self):
        self.record.start_game(self.players)
        round_no = 0
        while not self.check_win():
            round_no += 1
            self.record.new_round(round_no)
            self.single_round(round_no)
        self.announce_winner()

    def single_round(self, round_no: int):
        alive = [p for p in self.players if p.alive]
        alive_names = [p.name for p in alive]
        president = alive[self.president_index]

        # Term limits: last elected Chancellor always ineligible;
        # with 5–6 players, last elected President ineligible as Chancellor too.
        ineligible = set()
        if self.last_elected_chancellor:
            ineligible.add(self.last_elected_chancellor)
        if len(alive) <= 6 and self.last_elected_president:
            ineligible.add(self.last_elected_president)

        # President nominates
        nominee = president.choose_chancellor_nominee(alive_names, list(ineligible), round_no)

        print(f"\n--- Round {round_no} ---")
        print(f"President: {president.name}, Nominee for Chancellor: {nominee}")
        self.record.start_government(president.name, nominee)

        # TABLE TALK — multi-turn discussion
        TALKS_PER_PLAYER = 2           # tweak to taste
        RECENT_WINDOW = 8              # how many prior lines to show each speaker

        for pass_idx in range(TALKS_PER_PLAYER):
            for p in alive:
                recent_txt = self.record.format_recent_table_talk_text(round_no, k=RECENT_WINDOW)
                line = p.table_talk(
                    alive_names,
                    self.last_elected_president,
                    self.last_elected_chancellor,
                    self.record.liberal_policies,
                    self.record.fascist_policies,
                    self.record.election_tracker,
                    recent_discussion_text=recent_txt
                )
                print(line)
                self.record.add_table_talk(round_no, p.name, line[len(p.name)+2:] if line.startswith(p.name + ": ") else line)

        # Vote
        votes = {}
        for p in alive:
            v = p.vote_on_government(
                president=president.name,
                chancellor=nominee,
                alive_names=alive_names,
                liberal_count=self.record.liberal_policies,
                fascist_count=self.record.fascist_policies,
                tracker=self.record.election_tracker,
                round_no=round_no
            )
            votes[p.name] = v
            self.record.record_vote(p.name, v)
            print(f"{p.name} votes {v}")

        ja = sum(1 for v in votes.values() if v == "JA")
        passed = ja > (len(alive) // 2)

        # Hitler-elected instant win check
        hitler_trigger = False
        if passed:
            ch_obj = next(p for p in alive if p.name == nominee)
            if ch_obj.role == "Hitler" and self.record.fascist_policies >= 3:
                hitler_trigger = True

        self.record.finalize_government(passed, hitler_trigger)

        if hitler_trigger:
            print(f"Government PASSED and Hitler ({nominee}) was elected Chancellor after 3+ Fascist policies. Fascists WIN!")
            self.winner = "Fascists"
            return

        if not passed:
            print("Government FAILED.")
            self.record.election_tracker += 1
            print(f"Election Tracker: {self.record.election_tracker}/3")
            if self.record.election_tracker >= 3:
                top = self.draw_policies(1)[0]
                print(f"Election Tracker reached 3. Top-deck policy enacted: {top}")
                self.record.top_deck_enact(top)
            # Rotate presidency and exit round
            self.president_index = (self.president_index + 1) % len(alive)
            return

        # Legislative Session
        draw3 = self.draw_policies(3)
        self.record.start_session(president.name, nominee, draw3)
        pres_discard = president.president_discard(draw3, alive_players=alive_names)
        if pres_discard not in draw3:
            pres_discard = random.choice(draw3)
        draw3.remove(pres_discard)
        self.discard.append(pres_discard)
        two_for_chancellor = draw3[:]
        self.record.set_president_discard(pres_discard, two_for_chancellor)

        ch_obj = next(p for p in alive if p.name == nominee)
        chan_discard = ch_obj.chancellor_discard(two_for_chancellor, alive_players=alive_names)
        if chan_discard not in two_for_chancellor:
            chan_discard = random.choice(two_for_chancellor)
        two_for_chancellor.remove(chan_discard)
        self.discard.append(chan_discard)
        enacted = two_for_chancellor[0]
        self.record.set_chancellor_discard_and_enact(chan_discard, enacted)
        print(f"Policy enacted: {enacted}")

        # Update term limits
        self.last_elected_president = president.name
        self.last_elected_chancellor = nominee

        # Rotate presidency
        self.president_index = (self.president_index + 1) % len(alive)

    def draw_policies(self, k: int) -> List[str]:
        while len(self.deck) < k:
            self.deck += self.discard
            self.discard = []
            random.shuffle(self.deck)
        out = self.deck[:k]
        self.deck = self.deck[k:]
        return out

    def check_win(self) -> bool:
        if self.winner:
            return True
        if self.record.liberal_policies >= 5:
            self.winner = "Liberals"
            return True
        if self.record.fascist_policies >= 6:
            self.winner = "Fascists"
            return True
        return False

    def announce_winner(self):
        print("\n=== GAME OVER ===")
        print(f"{self.winner} win!")
        self.record.finish_game(self.winner)


if __name__ == "__main__":
    # Example configs; keep your own
    player_configs = [
        {"name": "Llama1", "model": "llama3"},
        {"name": "Mistral1", "model": "mistral:7b"},
        {"name": "Mistral2", "model": "mistral:latest"},
        {"name": "Llama2", "model": "llama3"},
        {"name": "Mistral3", "model": "mistral:7b"},
        {"name": "Mistral4", "model": "mistral:latest"}
    ]
    print("Secret Hitler starts!")
    game = SecretHitlerGame(player_configs)
    game.start_game()
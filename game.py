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

        self.veto_unlocked = False
        self.special_next_president_name: Optional[str] = None
        self.special_return_president_name: Optional[str] = None

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
        # Handle Special Election override
        if self.special_next_president_name:
            president = next(p for p in alive if p.name == self.special_next_president_name)
            # remember where to return after this special round
            self.special_next_president_name = None
            special_in_effect = True
        else:
            president = alive[self.president_index]
            special_in_effect = False

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

        # Start table talk with the president
        order = alive[self.president_index:] + alive[:self.president_index]

        TALKS_PER_PLAYER = 2
        RECENT_WINDOW = 8

        for _ in range(TALKS_PER_PLAYER):
            for p in order:
                recent_txt = self.record.format_recent_table_talk_text(round_no, k=RECENT_WINDOW)
                if not recent_txt and round_no > 1:
                    # reuse the final few lines from last round to give context
                    recent_txt = self.record.format_recent_table_talk_text(round_no - 1, k=3) + (
                        f"Kickoff: Proposed government is President={president.name}, "
                        f"Chancellor={nominee}. Board L={self.record.liberal_policies}, "
                        f"F={self.record.fascist_policies}, Tracker={self.record.election_tracker}. "
                        f"State your stance (JA/NEIN) and one reason."
                    )
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

        # If veto is unlocked (5+ Fascist enacted), allow Chancellor to request veto
        self.veto_unlocked = (self.record.fascist_policies >= 5)
        if self.veto_unlocked:
            veto_decision = ch_obj.chancellor_veto_decision(two_for_chancellor)
            if veto_decision == "VETO":
                pres_decision = president.president_veto_accept(chancellor_name=ch_obj.name,
                                                                received_policies=two_for_chancellor)
                # Record the veto request/decision
                self.record.add_executive_action(
                    round_number=round_no, action="veto", president=president.name,
                    chancellor=ch_obj.name, result=pres_decision
                )
                if pres_decision == "ACCEPT":
                    # discard both, no policy enacted, tracker +1, end round
                    self.discard.extend(two_for_chancellor)
                    print("VETO accepted. No policy enacted. Election Tracker +1.")
                    self.record.election_tracker += 1
                    # (optional) self.record.set_policy_counts(self.deck, self.discard)
                    return
                else:
                    print("VETO rejected. Proceeding with Chancellor's choice.")
        
        ch_obj = next(p for p in alive if p.name == nominee)
        chan_discard = ch_obj.chancellor_discard(two_for_chancellor, alive_players=alive_names)
        if chan_discard not in two_for_chancellor:
            chan_discard = random.choice(two_for_chancellor)
        two_for_chancellor.remove(chan_discard)
        self.discard.append(chan_discard)
        enacted = two_for_chancellor[0]
        self.record.set_chancellor_discard_and_enact(chan_discard, enacted)
        print(f"Policy enacted: {enacted}")

        # Unlock veto if 5 Fascist now
        self.veto_unlocked = (self.record.fascist_policies >= 5)

        # Apply executive powers if a Fascist policy was enacted
        if enacted == "Fascist":
            self.apply_executive_powers(round_no, president, ch_obj)

        # Update term limits
        self.last_elected_president = president.name
        self.last_elected_chancellor = nominee

        # Rotate presidency (respect special election return rule)
        alive = [p for p in self.players if p.alive]
        if special_in_effect and self.special_return_president_name:
            # Return to the player to the left of the original president who invoked Special Election
            try:
                idx = [p.name for p in alive].index(self.special_return_president_name)
                self.president_index = idx
            except ValueError:
                # fallback to normal rotation if they died
                self.president_index = (self.president_index + 1) % len(alive)
            self.special_return_president_name = None
        else:
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
    
    def _alive_names(self) -> list[str]:
        return [p.name for p in self.players if p.alive]

    def _party_of(self, name: str) -> str:
        # Party membership: Hitler counts as Fascist
        p = next(x for x in self.players if x.name == name)
        return "Fascist" if p.role in ("Fascist", "Hitler") else "Liberal"

    def apply_executive_powers(self, round_no: int, president: Player, chancellor: Player):
        n = len([p for p in self.players if p.alive])
        fp = self.record.fascist_policies  # after increment

        powers = []
        if n <= 6:
            # 5–6 players: 3=peek, 4=execute, 5=execute
            if fp == 3: powers = ["policy_peek"]
            elif fp in (4, 5): powers = ["execution"]
        elif n <= 8:
            # 7–8 players: 2=investigate, 3=special, 4=execute, 5=execute
            if fp == 2: powers = ["investigate"]
            elif fp == 3: powers = ["special_election"]
            elif fp in (4, 5): powers = ["execution"]
        else:
            # 9–10 players: 1=investigate, 2=investigate, 3=special, 4=execute, 5=execute
            if fp in (1, 2): powers = ["investigate"]
            elif fp == 3: powers = ["special_election"]
            elif fp in (4, 5): powers = ["execution"]

        for power in powers:
            alive_names = self._alive_names()
            if power == "investigate":
                # President chooses a target (not self)
                target = president.choose_investigation_target(alive_names)
                # Reveal party to President only
                party = self._party_of(target)
                print(f"{president.name} investigated {target}.")
                self.record.add_executive_action(
                    round_number=round_no, action="investigate",
                    president=president.name, target=target, result=party,
                    private_to=president.name
                )

            elif power == "special_election":
                # President chooses next president (not self)
                target_pres = president.choose_special_election_president(alive_names)
                print(f"Special Election called: next President will be {target_pres}.")
                self.record.add_executive_action(
                    round_number=round_no, action="special_election",
                    president=president.name, target=target_pres
                )
                # Schedule: next round president is target_pres,
                # then return to the player to the left of current president.
                self.special_next_president_name = target_pres
                # compute return name = the player to the left of current president
                order = [p.name for p in self.players if p.alive]
                curr_idx = order.index(president.name)
                self.special_return_president_name = order[(curr_idx + 1) % len(order)]

            elif power == "policy_peek":
                # Reveal top 3 to President (do not remove from deck)
                while len(self.deck) < 3:
                    self.deck += self.discard
                    self.discard = []
                    random.shuffle(self.deck)
                top3 = self.deck[:3]
                print(f"{president.name} performed Policy Peek.")
                self.record.add_executive_action(
                    round_number=round_no, action="policy_peek",
                    president=president.name, seen_policies=top3[:], private_to=president.name
                )
                # Optional public statement
                try:
                    claim = president.policy_peek_public_comment(top3)
                    if claim:
                        print(f"{president.name} says: {claim}")
                except Exception:
                    pass

            elif power == "execution":
                # President executes a player (not self)
                # Refresh alive names each time (someone may have just died)
                alive_names = self._alive_names()
                if len(alive_names) <= 2:
                    continue
                target = president.choose_execution_target(alive_names)
                if target == president.name:  # forbid self-exec
                    target = random.choice([n for n in alive_names if n != president.name])
                print(f"{president.name} executes {target}!")
                self.record.add_executive_action(
                    round_number=round_no, action="execution",
                    president=president.name, target=target
                )
                # Kill target
                victim = next(p for p in self.players if p.name == target)
                victim.alive = False
                # Hitler executed? Liberals win immediately
                if victim.role == "Hitler":
                    print("Hitler was executed. Liberals WIN!")
                    self.winner = "Liberals"
                    return


if __name__ == "__main__":
    player_configs = [
        {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        {"name": "Derek", "model": "ollama/llama3:latest"},
        {"name": "Emma", "model": "ollama/mistral:7b"},
        {"name": "Talia", "model": "ollama/mistral:latest"},

       
        # {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        # {"name": "Derek", "model": "ollama/deepseek-r1:7b"},
        # {"name": "Emma", "model": "ollama/dolphin3:8b"},
        # {"name": "Talia", "model": "ollama/qwen2.5:7b"},
        # {"name": "Anika", "model": "ollama/mistral:7b"},
        # {"name": "Nick", "model": "ollama/mistral-nemo:12b"},
        # {"name": "Philip", "model": "ollama/phi4:14b"},
        # {"name": "Peter", "model": "ollama/phi3.5:3.8b"},
        # {"name": "George", "model": "ollama/llava:7b"},
        # {"name": "Enrique", "model": "ollama/gemma2:9b"},
        {"name": "Maria", "model": "openai/gpt-4o-mini"},
    ]
    print("Secret Hitler starts!")
    game = SecretHitlerGame(player_configs)
    game.start_game()
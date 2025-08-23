import random
import time
from typing import List, Optional, Dict
from player import Player
from game_record import GameRecord, PlayerInitialState


class Game:
    def __init__(self, player_configs: List[Dict[str, str]]) -> None:
        """Initialize the game
        
        Args:
            player_configs: A list of dictionaries containing player configurations, each with name and model fields
        """
        # Create player objects using the configuration
        self.players = [Player(config["name"], config["model"]) for config in player_configs]
        
        # Initialize each player's opinions about other players
        for player in self.players:
            player.init_opinions(self.players)
        
        self.deck: List[str] = []
        self.target_card: Optional[str] = None
        self.current_player_idx: int = random.randint(0, len(self.players) - 1)
        self.last_shooter_name: Optional[str] = None
        self.game_over: bool = False

        # Create game record
        self.game_record: GameRecord = GameRecord()
        self.game_record.start_game([p.name for p in self.players])
        self.round_count = 0
        
        # Game timeout settings
        self.max_game_duration = 3600  # 1 hour maximum game duration
        self.max_rounds = 50  # Maximum 50 rounds to prevent infinite loops
        self.game_start_time = None

    def _create_deck(self) -> List[str]:
        """Create and shuffle the deck"""
        deck = ['Q'] * 6 + ['K'] * 6 + ['A'] * 6 + ['Joker'] * 2
        random.shuffle(deck)
        return deck

    def deal_cards(self) -> None:
        """Deal cards and clear old hands"""
        self.deck = self._create_deck()
        for player in self.players:
            if player.alive:
                player.hand.clear()
        # Deal 5 cards to each player
        for _ in range(5):
            for player in self.players:
                if player.alive and self.deck:
                    player.hand.append(self.deck.pop())
                    player.print_status()

    def choose_target_card(self) -> None:
        """Randomly choose a target card"""
        self.target_card = random.choice(['Q', 'K', 'A'])
        print(f"Target card is: {self.target_card}")

    def start_round_record(self) -> None:
        """Start a new round and record information in `GameRecord`"""
        self.round_count += 1
        starting_player = self.players[self.current_player_idx].name
        player_initial_states = [
            PlayerInitialState(
                player_name=player.name,
                bullet_position=player.bullet_position,
                current_gun_position=player.current_bullet_position,
                initial_hand=player.hand.copy()
            ) 
            for player in self.players if player.alive
        ]

        # Get alive players
        round_players = [player.name for player in self.players if player.alive]

        # Create a deep copy instead of reference
        player_opinions = {}
        for player in self.players:
            player_opinions[player.name] = {}
            for target, opinion in player.opinions.items():
                player_opinions[player.name][target] = opinion

        self.game_record.start_round(
            round_id=self.round_count,
            target_card=self.target_card,
            round_players=round_players,
            starting_player=starting_player,
            player_initial_states=player_initial_states,
            player_opinions=player_opinions
        )

    def is_valid_play(self, cards: List[str]) -> bool:
        """
        Determine if the played cards are valid according to the target card rule:
        Each card must be the target card or Joker
        """
        return all(card == self.target_card or card == 'Joker' for card in cards)

    def find_next_player_with_cards(self, start_idx: int) -> int:
        """Return the index of the next alive player with cards"""
        idx = start_idx
        for _ in range(len(self.players)):
            idx = (idx + 1) % len(self.players)
            if self.players[idx].alive and self.players[idx].hand:
                return idx
        return start_idx  # Theoretically impossible

    def perform_penalty(self, player: Player) -> None:
        """
        Execute shooting penalty and update game state and record based on the result

        Args:
            player: The player to execute penalty
        """
        print(f"Player {player.name} shoots!")
        
        # Execute shooting and get alive status
        still_alive = player.process_penalty()
        self.last_shooter_name = player.name

        # Record shooting result
        self.game_record.record_shooting(
            shooter_name=player.name,
            bullet_hit=not still_alive  # If player dies, it means bullet hits
        )

        if not still_alive:
            print(f"{player.name} is dead!")
        
        # Check victory condition
        if not self.check_victory():
            self.reset_round(record_shooter=True)

    def reset_round(self, record_shooter: bool) -> None:
        """Reset the current round"""
        print("Round game reset, start a new round!")

        # Reflect and get alive players before dealing new cards
        alive_players = self.handle_reflection()

        # Deal new cards
        self.deal_cards()
        self.choose_target_card()

        if record_shooter and self.last_shooter_name:
            shooter_idx = next((i for i, p in enumerate(self.players)
                                if p.name == self.last_shooter_name), None)
            if shooter_idx is not None and self.players[shooter_idx].alive:
                self.current_player_idx = shooter_idx
            else:
                print(f"{self.last_shooter_name} is dead, continue to the next alive player with cards")
                self.current_player_idx = self.find_next_player_with_cards(shooter_idx or 0)
        else:
            self.last_shooter_name = None
            self.current_player_idx = self.players.index(random.choice(alive_players))

        self.start_round_record()
        print(f"Start a new round from {self.players[self.current_player_idx].name}!")

    def check_victory(self) -> bool:
        """
        Check victory condition (only one alive player left) and record the winner
        
        Returns:
            bool: Whether the game is over
        """
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) == 1:
            winner = alive_players[0]
            print(f"\n{winner.name} wins!")
            # Record winner and save game record
            self.game_record.finish_game(winner.name)
            self.game_over = True
            return True
        return False
    
    def check_other_players_no_cards(self, current_player: Player) -> bool:
        """
        Check if all other alive players have no cards
        """
        others = [p for p in self.players if p != current_player and p.alive]
        return all(not p.hand for p in others)

    def handle_play_cards(self, current_player: Player, next_player: Player) -> List[str]:
        """
        Handle player play cards
        
        Args:
            current_player: Current player
            next_player: Next player
            
        Returns:
            List[str]: Return played cards
        """
        # Get current round base information
        round_base_info = self.game_record.get_latest_round_info()
        round_action_info = self.game_record.get_latest_round_actions(current_player.name, include_latest=True)
        
        # Get play decision related information
        play_decision_info = self.game_record.get_play_decision_info(
            current_player.name,
            next_player.name
        )

        # Let current player choose played cards
        play_result, reasoning = current_player.choose_cards_to_play(
            round_base_info,
            round_action_info,
            play_decision_info
        )

        # Record play behavior
        self.game_record.record_play(
            player_name=current_player.name,
            played_cards=play_result["played_cards"].copy(),
            remaining_cards=current_player.hand.copy(),
            play_reason=play_result["play_reason"],
            behavior=play_result["behavior"],
            next_player=next_player.name,
            play_thinking=reasoning
        )

        return play_result["played_cards"]
    
    def handle_challenge(self, current_player: Player, next_player: Player, played_cards: List[str]) -> Player:
        """
        Handle player challenge
        
        Args:
            current_player: Current player (challenged player)
            next_player: Next player (challenger)
            played_cards: Played cards by challenged player
            
        Returns:
            Player: Return player to execute penalty
        """
        # Get current round base information
        round_base_info = self.game_record.get_latest_round_info()
        round_action_info = self.game_record.get_latest_round_actions(next_player.name, include_latest=False)
        
        # Get challenge decision related information
        challenge_decision_info = self.game_record.get_challenge_decision_info(
            next_player.name,
            current_player.name
        )

        # Get challenged player's behavior
        challenging_player_behavior = self.game_record.get_latest_play_behavior()

        # Check if additional hint is needed
        extra_hint = "Note: All other players' cards are empty." if self.check_other_players_no_cards(next_player) else ""

        # Let next player decide whether to challenge
        challenge_result, reasoning = next_player.decide_challenge(
            round_base_info,
            round_action_info,
            challenge_decision_info,
            challenging_player_behavior,
            extra_hint
        )

        # If choose to challenge
        if challenge_result["was_challenged"]:
            # Verify played cards are valid
            is_valid = self.is_valid_play(played_cards)
            
            # Record challenge result
            self.game_record.record_challenge(
                was_challenged=True,
                reason=challenge_result["challenge_reason"],
                result=not is_valid,  # Challenge success means played cards are invalid
                challenge_thinking=reasoning
            )
            
            # Return player to execute penalty
            return next_player if is_valid else current_player
        else:
            # Record not challenged situation
            self.game_record.record_challenge(
                was_challenged=False,
                reason=challenge_result["challenge_reason"],
                result=None,
                challenge_thinking=reasoning
            )
            return None

    def handle_system_challenge(self, current_player: Player) -> None:
        """
        Handle system automatic challenge
        When all other alive players have no cards, system automatically challenges current player
        
        Args:
            current_player: Current player (last alive player)
        """
        print(f"System automatically challenges {current_player.name}'s cards!")
        
        # Record player automatic played cards
        all_cards = current_player.hand.copy()  # Copy current cards for recording
        current_player.hand.clear()  # Clear cards
        
        # Record play behavior
        self.game_record.record_play(
            player_name=current_player.name,
            played_cards=all_cards,
            remaining_cards=[],  # Remaining cards are empty list
            play_reason="Last one, automatic play",
            behavior="No",
            next_player="No",
            play_thinking=""
        )
        
        # Verify played cards are valid
        is_valid = self.is_valid_play(all_cards)
        
        # Record system challenge
        self.game_record.record_challenge(
            was_challenged=True,
            reason="System automatic challenge",
            result=not is_valid,  # Challenge success means played cards are invalid
            challenge_thinking=""
        )
        
        if is_valid:
            print(f"System challenge failed! {current_player.name}'s cards are valid.")
            # Record a special shooting result (no shooting)
            self.game_record.record_shooting(
                shooter_name="No",
                bullet_hit=False
            )
            self.reset_round(record_shooter=False)
        else:
            print(f"System challenge success! {current_player.name}'s cards are invalid, shooting penalty will be executed.")
            self.perform_penalty(current_player)

    def handle_reflection(self) -> None:
        """
        Handle all alive players' reflection process
        Called at the end of each round, allowing players to reflect on and evaluate other players' behaviors
        """
        # Get all alive players
        alive_players = [p for p in self.players if p.alive]
        alive_player_names = [p.name for p in alive_players]
        
        # Get current round related information
        round_base_info = self.game_record.get_latest_round_info()
        
        # Let each alive player reflect
        for player in alive_players:
            # Get round action information for current player
            round_action_info = self.game_record.get_latest_round_actions(player.name, include_latest=True)
            # Get round result for current player
            round_result = self.game_record.get_latest_round_result(player.name)
            
            # Execute reflection
            player.reflect(
                alive_players=alive_player_names,
                round_base_info=round_base_info,
                round_action_info=round_action_info,
                round_result=round_result
            )

        return alive_players

    def play_round(self) -> None:
        """Execute game logic for one round"""
        current_player = self.players[self.current_player_idx]

         # When all other alive players have no cards, system automatically challenges current player
        if self.check_other_players_no_cards(current_player):
            self.handle_system_challenge(current_player)
            return

        print(f"\nRound to {current_player.name} play, target card is {self.target_card}")
        current_player.print_status()

        # Find next player with cards
        next_idx = self.find_next_player_with_cards(self.current_player_idx)
        next_player = self.players[next_idx]

        # Handle play cards
        played_cards = self.handle_play_cards(current_player, next_player)

        # Handle challenge
        if next_player != current_player:
            player_to_penalize = self.handle_challenge(current_player, next_player, played_cards)
            if player_to_penalize:
                self.perform_penalty(player_to_penalize)
                return
            else:
                print(f"{next_player.name} chooses not to challenge, game continues.")
                
        # Switch to next player
        self.current_player_idx = next_idx

    def start_game(self) -> None:
        """Start game main loop"""
        self.game_start_time = time.time()
        self.deal_cards()
        self.choose_target_card()
        self.start_round_record()
        
        while not self.game_over:
            # Check for timeout conditions
            if self._check_timeout():
                print("Game timeout reached, ending game")
                self._handle_timeout_end()
                break
                
            if self.round_count >= self.max_rounds:
                print(f"Maximum rounds ({self.max_rounds}) reached, ending game")
                self._handle_timeout_end()
                break
                
            self.play_round()
    
    def _check_timeout(self) -> bool:
        """Check if the game has exceeded the maximum duration"""
        if self.game_start_time is None:
            return False
        elapsed_time = time.time() - self.game_start_time
        return elapsed_time > self.max_game_duration
    
    def _handle_timeout_end(self) -> None:
        """Handle game ending due to timeout"""
        # Find the player with the most cards as the winner
        alive_players = [p for p in self.players if p.alive]
        if alive_players:
            winner = max(alive_players, key=lambda p: len(p.hand))
            print(f"\nGame ended due to timeout. {winner.name} wins by having the most cards ({len(winner.hand)})!")
            self.game_record.finish_game(winner.name)
        else:
            print("\nGame ended due to timeout. No winner determined.")
            self.game_record.finish_game("Timeout - No Winner")
        self.game_over = True

if __name__ == '__main__':
    # Configure player information, where model is the name of the model you call through API
    player_configs = [
        {"name": "Sarah", "model": "ollama/llama3.1:8b"},
        {"name": "Derek", "model": "ollama/llama3:latest"},
        {"name": "Emma", "model": "ollama/mistral:7b"},

       
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

    print("Game starts! Player configurations are as follows:")
    for config in player_configs:
        print(f"Player: {config['name']}, Using model: {config['model']}")
    print("-" * 50)

    # Create game instance and start game
    game = Game(player_configs)
    game.start_game()

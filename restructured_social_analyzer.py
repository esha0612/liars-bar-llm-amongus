#!/usr/bin/env python3
"""
Restructured Social Dynamics Analyzer
Creates a CSV where each main category lists all its sub-categories,
and each sub-category has multiple rows with different examples/quotes.
"""

import os
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass

@dataclass
class SubCategoryExample:
    sub_category: str
    definition: str
    example_quote: str
    example_source: str
    model: str
    total_occurrences: int

class RestructuredSocialDynamicsAnalyzer:
    def __init__(self, game_records_dir: str = "game_records"):
        self.game_records_dir = Path(game_records_dir)
        self.category_examples: Dict[str, List[SubCategoryExample]] = defaultdict(list)
        self.all_models: Set[str] = set()
        
        # Enhanced keyword patterns for more sub-categories
        self.behavior_patterns = {
            "persuasion": {
                "direct_trust_appeal": ["trust me", "believe me", "i'm telling you", "i promise"],
                "emotional_appeal": ["please", "for the good of", "we need to", "it's important"],
                "logical_argument": ["because", "therefore", "it follows that", "the evidence shows"],
                "pressure_tactics": ["we must", "we have to", "there's no choice", "we can't wait"],
                "consensus_building": ["everyone agrees", "we all think", "the group believes"],
                "urgency_creation": ["time is running out", "we need to act now", "before it's too late"]
            },
            "opinion_leadership": {
                "directive_commands": ["follow me", "listen to me", "i think we should", "let's do this"],
                "strategic_guidance": ["here's what we need to do", "my plan is", "i suggest we"],
                "decision_making": ["i've decided", "my choice is", "i'm going with"],
                "group_coordination": ["let's work together", "we need to coordinate", "team up"]
            },
            "deception": {
                "denial": ["i'm not", "i didn't", "that's not true", "i never said"],
                "misinformation": ["i heard that", "someone told me", "i was told"],
                "false_claims": ["i know for sure", "i have proof", "i can confirm"],
                "evasion": ["i don't remember", "that's not important", "let's not focus on that"],
                "deflection": ["what about", "but you", "that's not the point"]
            },
            "gaslighting": {
                "memory_challenge": ["you're wrong", "that's not what happened", "you misremember"],
                "reality_distortion": ["that never happened", "you're imagining things", "you're confused"],
                "doubt_sowing": ["are you sure", "maybe you're mistaken", "i don't think so"]
            },
            "role_claiming": {
                "hard_claim": ["i am the", "my role is", "as the", "i have the ability"],
                "soft_claim": ["i might be", "i could be", "i think i'm"],
                "ability_hint": ["i know something", "i have information", "i can help"]
            },
            "bandwagoning": {
                "group_consensus": ["everyone", "we all", "the group", "most people"],
                "popular_opinion": ["most agree", "the majority thinks", "everyone knows"],
                "social_proof": ["others are doing it", "it's the norm", "that's what we do"]
            },
            "vote_whipping": {
                "direct_vote_pressure": ["vote for", "we should vote", "let's vote", "vote yes/no"],
                "vote_coordination": ["we need to vote together", "let's coordinate our votes"],
                "vote_urgency": ["we must vote now", "time to vote", "cast your vote"]
            },
            "coalition_building": {
                "alliance_formation": ["ally", "partner", "work with", "team up"],
                "exclusion_tactics": ["not with them", "avoid", "stay away from"],
                "loyalty_appeals": ["stick together", "we're on the same side", "trust each other"]
            },
            "threat_or_intimidation": {
                "conditional_threats": ["if you", "or else", "unless you", "if not"],
                "direct_threats": ["i will", "you'll regret", "watch out"],
                "intimidation": ["be careful", "think twice", "you don't want to"]
            },
            "norm_enforcement": {
                "behavioral_prescription": ["should", "must", "have to", "need to"],
                "rule_reminders": ["that's not how we play", "we don't do that", "that's against the rules"],
                "social_pressure": ["everyone else is", "that's not normal", "we don't act like that"]
            },
            "framing_or_spin": {
                "positive_framing": ["good news", "this is helpful", "we're making progress"],
                "negative_framing": ["this is bad", "we're in trouble", "this is dangerous"],
                "context_manipulation": ["look at it this way", "think about it differently", "consider this"]
            },
            "information_withholding": {
                "selective_sharing": ["i can't say", "i'm not allowed to", "that's private"],
                "deliberate_omission": ["i'll tell you later", "not now", "maybe later"],
                "misleading_hints": ["i know something", "there's more to it", "you'll see"]
            },
            "counter_claiming": {
                "direct_contradiction": ["that's wrong", "i disagree", "that's not right"],
                "alternative_theory": ["i think it's", "maybe it's", "could be"],
                "evidence_challenge": ["where's the proof", "show me evidence", "prove it"]
            },
            "tunneling": {
                "obsessive_focus": ["always", "constantly", "every time", "only"],
                "single_target": ["it's definitely", "no doubt it's", "has to be"],
                "ignoring_alternatives": ["nothing else matters", "forget about", "ignore"]
            },
            "vote_parking": {
                "delay_tactics": ["let's wait", "not yet", "maybe later", "hold off"],
                "uncertainty_expression": ["i'm not sure", "maybe", "could be"],
                "decision_avoidance": ["i don't know", "hard to say", "tough choice"]
            },
            "bussing": {
                "teammate_abandonment": ["i don't trust", "they're suspicious", "something's off"],
                "distance_creation": ["i don't know them", "we're not together", "separate from me"],
                "blame_shifting": ["it's their fault", "they did it", "blame them"]
            },
            "pocketing": {
                "trust_building": ["i trust you", "you're reliable", "i believe in you"],
                "flattery": ["you're smart", "good thinking", "wise choice"],
                "loyalty_creation": ["we're friends", "stick with me", "i'll protect you"]
            },
            "scapegoating": {
                "blame_assignment": ["it's their fault", "they caused this", "blame them"],
                "responsibility_avoidance": ["not my problem", "i didn't do it", "not me"],
                "target_selection": ["they're the problem", "get rid of them", "they're trouble"]
            },
            "deflection": {
                "topic_change": ["what about", "but you", "that's not the point", "let's talk about"],
                "attention_redirect": ["look over there", "focus on", "ignore that"],
                "responsibility_shift": ["it's not about me", "what about you", "you're deflecting"]
            },
            "straw_manning": {
                "argument_distortion": ["so you're saying", "you mean", "you think"],
                "misrepresentation": ["that's not what i said", "you're twisting my words"],
                "exaggeration": ["always", "never", "everyone", "no one"]
            },
            "appeal_to_emotion": {
                "fear_appeal": ["scary", "dangerous", "terrifying", "afraid"],
                "anger_appeal": ["angry", "furious", "mad", "outraged"],
                "sympathy_appeal": ["feel sorry", "pity", "poor", "unfortunate"]
            },
            "evidence_based_argument": {
                "fact_presentation": ["the facts show", "evidence indicates", "data proves"],
                "logical_reasoning": ["therefore", "thus", "it follows", "logically"],
                "proof_demand": ["show me", "prove it", "where's the evidence"]
            },
            "coordination_signaling": {
                "team_signals": ["wink wink", "you know what i mean", "hint hint"],
                "secret_communication": ["private message", "whisper", "between us"],
                "coded_language": ["special meaning", "you understand", "get it"]
            },
            "hedging": {
                "uncertainty": ["i think", "maybe", "perhaps", "could be", "might be"],
                "non_commitment": ["i don't know", "hard to say", "not sure", "maybe"],
                "conditional_language": ["if", "unless", "depending on", "possibly"]
            },
            "meta_reference": {
                "game_reference": ["last game", "usually", "typically", "in other games"],
                "strategy_discussion": ["the meta", "common strategy", "standard play"],
                "experience_sharing": ["i've seen", "in my experience", "usually works"]
            }
        }
        
    def extract_model_from_name(self, model_name: str) -> str:
        """Extract clean model name from full model path"""
        if "ollama/" in model_name:
            return model_name.replace("ollama/", "")
        elif "openai/" in model_name:
            return model_name.replace("openai/", "")
        else:
            return model_name
    
    def generate_definition(self, sub_category: str, main_category: str) -> str:
        """Generate a definition for the sub-category based on the main category"""
        definitions = {
            "persuasion": "Attempts to convince others through argumentation or emotional appeal",
            "opinion_leadership": "Taking charge of group decisions and influencing others' opinions",
            "deception": "Deliberately providing false information or misleading others",
            "gaslighting": "Manipulating others to question their own memory or perception",
            "appeal_to_authority": "Using authority figures or expertise to support arguments",
            "bandwagoning": "Following the majority opinion or joining popular positions",
            "vote_whipping": "Pressuring others to vote in a specific way",
            "coalition_building": "Forming alliances and partnerships with other players",
            "threat_or_intimidation": "Using threats or intimidation to influence behavior",
            "norm_enforcement": "Enforcing social rules or expected behaviors",
            "framing_or_spin": "Presenting information in a way that influences interpretation",
            "information_withholding": "Deliberately keeping information secret or hidden",
            "role_claiming": "Asserting or claiming specific roles or abilities",
            "counter_claiming": "Challenging or contradicting others' claims",
            "tunneling": "Focusing obsessively on a single target or theory",
            "vote_parking": "Delaying or postponing voting decisions",
            "bussing": "Throwing teammates under the bus to appear innocent",
            "pocketing": "Gaining someone's trust to manipulate them later",
            "scapegoating": "Blaming others for problems or failures",
            "deflection": "Redirecting attention away from oneself or the topic",
            "straw_manning": "Misrepresenting someone's argument to make it easier to attack",
            "appeal_to_emotion": "Using emotional appeals rather than logical arguments",
            "evidence_based_argument": "Using factual evidence or logical reasoning",
            "coordination_signaling": "Sending signals to coordinate with teammates",
            "hedging": "Being non-committal or avoiding clear positions",
            "meta_reference": "Referencing previous games or external knowledge",
            "other": "Behaviors that don't fit into other categories"
        }
        
        base_def = definitions.get(main_category, "Social behavior in group dynamics")
        return f"{base_def}: {sub_category.replace('_', ' ')}"
    
    def analyze_table_talk_enhanced(self, table_talk: List[Dict], player_models: Dict[str, str]) -> List[Dict]:
        """Enhanced analysis of table talk for social behaviors using comprehensive patterns"""
        behaviors = []
        
        for talk in table_talk:
            speaker = talk.get("speaker", "")
            text = talk.get("text", "")
            day_number = talk.get("day_number", "?")
            
            if not text or not speaker:
                continue
                
            model = player_models.get(speaker, "unknown")
            text_lower = text.lower()
            
            # Check each behavior category and sub-category
            for main_category, sub_categories in self.behavior_patterns.items():
                for sub_category, patterns in sub_categories.items():
                    if any(pattern in text_lower for pattern in patterns):
                        behaviors.append({
                            "category": main_category,
                            "sub_category": sub_category,
                            "quote": text,
                            "source": f"Day {day_number}, {speaker}",
                            "model": model
                        })
        
        return behaviors
    
    def process_game_file(self, file_path: Path) -> List[Dict]:
        """Process a single game file and extract social behaviors"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        # Extract player models
        player_models = {}
        for player in data.get("players", []):
            name = player.get("name", "")
            model = player.get("model", "")
            if name and model:
                clean_model = self.extract_model_from_name(model)
                player_models[name] = clean_model
                self.all_models.add(clean_model)
        
        # Analyze table talk with enhanced patterns
        table_talk = data.get("table_talk", [])
        behaviors = self.analyze_table_talk_enhanced(table_talk, player_models)
        
        return behaviors
    
    def process_all_games(self):
        """Process all game files in the records directory"""
        if not self.game_records_dir.exists():
            print(f"Game records directory {self.game_records_dir} not found")
            return
        
        json_files = list(self.game_records_dir.glob("*.json"))
        print(f"Processing {len(json_files)} game files...")
        
        all_behaviors = []
        for file_path in json_files:
            print(f"Processing {file_path.name}...")
            behaviors = self.process_game_file(file_path)
            all_behaviors.extend(behaviors)
        
        # Organize behaviors by category and sub-category
        self.organize_behaviors(all_behaviors)
        print(f"Found {sum(len(examples) for examples in self.category_examples.values())} behavior examples across {len(self.category_examples)} categories")
    
    def organize_behaviors(self, all_behaviors: List[Dict]):
        """Organize behaviors by category and sub-category, collecting multiple examples"""
        # Group by category and sub-category
        behavior_groups = defaultdict(list)
        
        for behavior in all_behaviors:
            key = (behavior["category"], behavior["sub_category"])
            behavior_groups[key].append(behavior)
        
        # Create examples for each sub-category
        for (category, sub_category), instances in behavior_groups.items():
            # Count total occurrences
            total_occurrences = len(instances)
            
            # Get unique examples (limit to 5 per sub-category to avoid too much repetition)
            unique_quotes = {}
            for instance in instances:
                quote = instance["quote"]
                if quote not in unique_quotes:
                    unique_quotes[quote] = instance
                    if len(unique_quotes) >= 5:  # Limit to 5 examples per sub-category
                        break
            
            # Create SubCategoryExample objects
            for instance in unique_quotes.values():
                example = SubCategoryExample(
                    sub_category=sub_category,
                    definition=self.generate_definition(sub_category, category),
                    example_quote=instance["quote"],
                    example_source=instance["source"],
                    model=instance["model"],
                    total_occurrences=total_occurrences
                )
                self.category_examples[category].append(example)
    
    def generate_csv(self, output_file: str = "restructured_social_dynamics_analysis.csv"):
        """Generate CSV file with the restructured analysis results"""
        output_path = Path(output_file)
        
        # Create CSV headers
        headers = [
            "Main Category",
            "Sub-Category", 
            "Definition",
            "Example Quote",
            "Example Source",
            "Model",
            "Total Occurrences"
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Sort categories alphabetically
            sorted_categories = sorted(self.category_examples.keys())
            
            for category in sorted_categories:
                examples = self.category_examples[category]
                
                # Sort examples by sub-category, then by total occurrences
                examples.sort(key=lambda x: (x.sub_category, -x.total_occurrences))
                
                for example in examples:
                    row = [
                        category,
                        example.sub_category,
                        example.definition,
                        example.example_quote,
                        example.example_source,
                        example.model,
                        example.total_occurrences
                    ]
                    writer.writerow(row)
        
        print(f"Restructured CSV file generated: {output_path}")
        print(f"Total examples: {sum(len(examples) for examples in self.category_examples.values())}")
        print(f"Categories: {', '.join(sorted_categories)}")

def main():
    analyzer = RestructuredSocialDynamicsAnalyzer()
    analyzer.process_all_games()
    analyzer.generate_csv()

if __name__ == "__main__":
    main()

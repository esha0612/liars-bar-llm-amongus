#!/usr/bin/env python3
"""
Social Dynamics Analyzer
Processes game records to create a comprehensive table of social behaviors
with frequency counts by LLM model.
"""

import os
import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass

# Import the taxonomy and mapping from card_sort.py
DEFAULT_TAXONOMY = [
    "persuasion","opinion_leadership","deception","gaslighting",
    "appeal_to_authority","bandwagoning","vote_whipping","coalition_building",
    "threat_or_intimidation","norm_enforcement","framing_or_spin",
    "information_withholding","role_claiming","counter_claiming","tunneling",
    "vote_parking","bussing","pocketing","scapegoating","deflection",
    "straw_manning","appeal_to_emotion","evidence_based_argument",
    "coordination_signaling","hedging","meta_reference","other"
]

# Heuristic mapper: mechanic-ish label strings → best taxonomy bucket
LABEL_KEYWORD_MAP = [
    (("imp identification","imp suspect","red herring","demon read"), "framing_or_spin"),
    (("fortune teller","empath read","undertaker info","hard info","claim result"), "evidence_based_argument"),
    (("role claim","hard claim","soft claim","claiming"), "role_claiming"),
    (("counterclaim","cc","counter claim"), "counter_claiming"),
    (("policy execute","policy vote","norms"), "norm_enforcement"),
    (("leader","shepherd","follow me"), "opinion_leadership"),
    (("wagon","pile on","sheeping"), "bandwagoning"),
    (("pressure vote","whip votes","lock votes"), "vote_whipping"),
    (("plan","coordination","vote order","nom order"), "coordination_signaling"),
    (("bus","throw under bus"), "bussing"),
    (("park vote","parked vote"), "vote_parking"),
    (("pocket","buddy"), "pocketing"),
    (("scapegoat","pin blame"), "scapegoating"),
    (("deflect","whatabout","change subject"), "deflection"),
    (("strawman","misrepresent"), "straw_manning"),
    (("appeal to emotion","fear monger"), "appeal_to_emotion"),
    (("hedge","ambivalent","non-committal"), "hedging"),
    (("meta","previous game"), "meta_reference"),
    (("lie","fake","fabricate"), "deception"),
    (("gaslight","misremember"), "gaslighting"),
    (("appeal to expert","authority"), "appeal_to_authority"),
    (("coalition","ally","townblock"), "coalition_building"),
    (("threat","intimidate","ultimatum"), "threat_or_intimidation"),
]

@dataclass
class SocialBehavior:
    main_category: str
    sub_category: str
    definition: str
    example_quote: str
    example_source: str
    model_counts: Dict[str, int]
    total_occurrences: int
    games_where_occurred: int

class SocialDynamicsAnalyzer:
    def __init__(self, game_records_dir: str = "game_records"):
        self.game_records_dir = Path(game_records_dir)
        self.behaviors: Dict[str, SocialBehavior] = {}
        self.model_mapping: Dict[str, str] = {}
        self.all_models: Set[str] = set()
        
    def extract_model_from_name(self, model_name: str) -> str:
        """Extract clean model name from full model path"""
        if "ollama/" in model_name:
            return model_name.replace("ollama/", "")
        elif "openai/" in model_name:
            return model_name.replace("openai/", "")
        else:
            return model_name
    
    def map_phrase_to_category(self, phrase: str) -> str:
        """Map a phrase to its most likely taxonomy category"""
        phrase_lower = phrase.lower()
        for keywords, category in LABEL_KEYWORD_MAP:
            if any(keyword in phrase_lower for keyword in keywords):
                return category
        return "other"
    
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
        return f"{base_def}: {sub_category}"
    
    def analyze_table_talk(self, table_talk: List[Dict], player_models: Dict[str, str]) -> List[Dict]:
        """Analyze table talk for social behaviors"""
        behaviors = []
        
        for talk in table_talk:
            speaker = talk.get("speaker", "")
            text = talk.get("text", "")
            day_number = talk.get("day_number", "?")
            
            if not text or not speaker:
                continue
                
            model = player_models.get(speaker, "unknown")
            
            # Simple keyword-based analysis for now
            # This could be enhanced with more sophisticated NLP
            text_lower = text.lower()
            
            # Check for various social behaviors
            if any(word in text_lower for word in ["trust me", "believe me", "i'm telling you"]):
                behaviors.append({
                    "category": "persuasion",
                    "phrase": "direct trust appeal",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["follow me", "listen to me", "i think we should"]):
                behaviors.append({
                    "category": "opinion_leadership", 
                    "phrase": "directive leadership",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["i'm not", "i didn't", "that's not true"]):
                behaviors.append({
                    "category": "deception",
                    "phrase": "denial or contradiction",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["you're wrong", "that's not what happened", "you misremember"]):
                behaviors.append({
                    "category": "gaslighting",
                    "phrase": "challenging others' memory",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["as the", "i have", "my role is"]):
                behaviors.append({
                    "category": "role_claiming",
                    "phrase": "role assertion",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["everyone", "we all", "the group"]):
                behaviors.append({
                    "category": "bandwagoning",
                    "phrase": "group consensus appeal",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["vote for", "we should vote", "let's vote"]):
                behaviors.append({
                    "category": "vote_whipping",
                    "phrase": "vote direction",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["ally", "partner", "work with"]):
                behaviors.append({
                    "category": "coalition_building",
                    "phrase": "alliance formation",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["threat", "if you", "or else"]):
                behaviors.append({
                    "category": "threat_or_intimidation",
                    "phrase": "conditional threat",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["should", "must", "have to"]):
                behaviors.append({
                    "category": "norm_enforcement",
                    "phrase": "behavioral prescription",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["i think", "maybe", "perhaps", "could be"]):
                behaviors.append({
                    "category": "hedging",
                    "phrase": "uncertainty expression",
                    "quote": text,
                    "source": f"Day {day_number}, {speaker}",
                    "model": model
                })
            
            if any(word in text_lower for word in ["last game", "usually", "typically"]):
                behaviors.append({
                    "category": "meta_reference",
                    "phrase": "external knowledge reference",
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
        
        # Analyze table talk
        table_talk = data.get("table_talk", [])
        behaviors = self.analyze_table_talk(table_talk, player_models)
        
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
        
        # Aggregate behaviors
        self.aggregate_behaviors(all_behaviors)
        print(f"Found {len(self.behaviors)} unique social behaviors")
    
    def aggregate_behaviors(self, all_behaviors: List[Dict]):
        """Aggregate behaviors by category and phrase"""
        behavior_groups = defaultdict(list)
        
        for behavior in all_behaviors:
            key = (behavior["category"], behavior["phrase"])
            behavior_groups[key].append(behavior)
        
        for (category, phrase), instances in behavior_groups.items():
            # Count occurrences by model
            model_counts = Counter()
            games_with_behavior = set()
            best_quote = ""
            best_source = ""
            
            for instance in instances:
                model_counts[instance["model"]] += 1
                # Use the first quote as the representative example
                if not best_quote:
                    best_quote = instance["quote"]
                    best_source = instance["source"]
            
            # Create behavior record
            behavior_key = f"{category}_{phrase}"
            self.behaviors[behavior_key] = SocialBehavior(
                main_category=category,
                sub_category=phrase,
                definition=self.generate_definition(phrase, category),
                example_quote=best_quote,
                example_source=best_source,
                model_counts=dict(model_counts),
                total_occurrences=len(instances),
                games_where_occurred=len(games_with_behavior)
            )
    
    def generate_csv(self, output_file: str = "social_dynamics_analysis.csv"):
        """Generate CSV file with the analysis results matching the spreadsheet format"""
        output_path = Path(output_file)
        
        # Get all unique models
        all_models = sorted(self.all_models)
        
        # Create CSV headers matching the spreadsheet format
        headers = [
            "Main Category",
            "Sub-Category", 
            "Description/Definition",
            "Example"
        ]
        
        # Add model count columns with "Count" prefix
        for model in all_models:
            # Clean up model names for column headers
            clean_model_name = model.replace(":", "").replace("-", "").replace(".", "")
            headers.append(f"Count {clean_model_name}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Sort behaviors by main category, then by total occurrences
            sorted_behaviors = sorted(
                self.behaviors.values(),
                key=lambda x: (x.main_category, -x.total_occurrences)
            )
            
            for behavior in sorted_behaviors:
                row = [
                    behavior.main_category,
                    behavior.sub_category,
                    behavior.definition,
                    behavior.example_quote
                ]
                
                # Add model counts
                for model in all_models:
                    row.append(behavior.model_counts.get(model, 0))
                
                writer.writerow(row)
        
        print(f"CSV file generated: {output_path}")
        print(f"Total behaviors analyzed: {len(self.behaviors)}")
        print(f"Models found: {', '.join(all_models)}")

def main():
    analyzer = SocialDynamicsAnalyzer()
    analyzer.process_all_games()
    analyzer.generate_csv()

if __name__ == "__main__":
    main()

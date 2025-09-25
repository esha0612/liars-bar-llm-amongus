#!/usr/bin/env python3
"""
Enhanced Social Dynamics Analyzer
Integrates with card_sort.py to get rich sub-categories and then creates
a comprehensive table with frequency counts by LLM model.
"""

import os
import json
import csv
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass

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

class EnhancedSocialDynamicsAnalyzer:
    def __init__(self, game_records_dir: str = "game_records", analyses_dir: str = "analyses"):
        self.game_records_dir = Path(game_records_dir)
        self.analyses_dir = Path(analyses_dir)
        self.behaviors: Dict[str, SocialBehavior] = {}
        self.all_models: Set[str] = set()
        
    def extract_model_from_name(self, model_name: str) -> str:
        """Extract clean model name from full model path"""
        if "ollama/" in model_name:
            return model_name.replace("ollama/", "")
        elif "openai/" in model_name:
            return model_name.replace("openai/", "")
        else:
            return model_name
    
    def run_card_sort_analysis(self):
        """Run card_sort.py to generate social dynamics analyses"""
        print("Running card_sort.py analysis...")
        
        # Create analyses directory if it doesn't exist
        self.analyses_dir.mkdir(parents=True, exist_ok=True)
        
        # Run card_sort.py with appropriate arguments
        cmd = [
            "python3", "card_sort.py",
            "--records-dir", str(self.game_records_dir),
            "--out-dir", str(self.analyses_dir),
            "--allow-invented",  # Allow custom labels
            "--memory-scope", "accumulate",  # Learn from previous analyses
            "--max-known", "50",  # Include more phrases as hints
            "--max-labels", "15",  # Include more labels as hints
            "--include-custom-in-prompts",  # Include mature custom labels
            "--temperature", "0.1",  # Low temperature for consistency
            "--retries", "2"  # Retry failed JSON parsing
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            if result.returncode != 0:
                print(f"Warning: card_sort.py exited with code {result.returncode}")
                print(f"Error output: {result.stderr}")
            else:
                print("card_sort.py analysis completed successfully")
        except subprocess.TimeoutExpired:
            print("Warning: card_sort.py timed out after 1 hour")
        except Exception as e:
            print(f"Error running card_sort.py: {e}")
    
    def load_social_analyses(self) -> List[Dict]:
        """Load all .social.json files from the analyses directory"""
        social_files = list(self.analyses_dir.glob("*.social.json"))
        print(f"Found {len(social_files)} social analysis files")
        
        all_analyses = []
        for file_path in social_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                    analysis['source_file'] = file_path.stem.replace('.social', '')
                    all_analyses.append(analysis)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        return all_analyses
    
    def get_player_models_from_game(self, game_filename: str) -> Dict[str, str]:
        """Get player-to-model mapping from the original game file"""
        game_file = self.game_records_dir / f"{game_filename}.json"
        if not game_file.exists():
            return {}
        
        try:
            with open(game_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            player_models = {}
            for player in data.get("players", []):
                name = player.get("name", "")
                model = player.get("model", "")
                if name and model:
                    clean_model = self.extract_model_from_name(model)
                    player_models[name] = clean_model
                    self.all_models.add(clean_model)
            
            return player_models
        except Exception as e:
            print(f"Error reading {game_file}: {e}")
            return {}
    
    def extract_model_from_quote_source(self, source: str, player_models: Dict[str, str]) -> str:
        """Extract model from quote source (e.g., 'Day 1, Derek' -> model)"""
        # Try to extract player name from source
        parts = source.split(', ')
        if len(parts) >= 2:
            player_name = parts[1].strip()
            return player_models.get(player_name, "unknown")
        return "unknown"
    
    def process_social_analyses(self, analyses: List[Dict]) -> List[Dict]:
        """Process social analyses to extract behaviors with model information"""
        all_behaviors = []
        
        for analysis in analyses:
            source_file = analysis.get('source_file', '')
            player_models = self.get_player_models_from_game(source_file)
            
            found_items = analysis.get('found', [])
            for item in found_items:
                label = item.get('label', '').strip()
                parent_label = item.get('parent_label', '').strip()
                phrase = item.get('phrase', '').strip()
                reasoning = item.get('reasoning', '')
                
                # Extract model information from spans
                spans = item.get('spans', [])
                for span in spans:
                    quote = span.get('quote', '')
                    where = span.get('where', '')
                    
                    if quote and where:
                        model = self.extract_model_from_quote_source(where, player_models)
                        
                        behavior = {
                            'category': parent_label or label,
                            'sub_category': phrase or label,
                            'quote': quote,
                            'source': where,
                            'model': model,
                            'reasoning': reasoning,
                            'game_file': source_file
                        }
                        all_behaviors.append(behavior)
        
        return all_behaviors
    
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
    
    def aggregate_behaviors(self, all_behaviors: List[Dict]):
        """Aggregate behaviors by category and phrase"""
        behavior_groups = defaultdict(list)
        
        for behavior in all_behaviors:
            key = (behavior["category"], behavior["sub_category"])
            behavior_groups[key].append(behavior)
        
        for (category, sub_category), instances in behavior_groups.items():
            # Count occurrences by model
            model_counts = Counter()
            games_with_behavior = set()
            best_quote = ""
            best_source = ""
            best_reasoning = ""
            
            for instance in instances:
                model_counts[instance["model"]] += 1
                games_with_behavior.add(instance["game_file"])
                
                # Use the first quote as the representative example
                if not best_quote:
                    best_quote = instance["quote"]
                    best_source = instance["source"]
                    best_reasoning = instance["reasoning"]
            
            # Create behavior record
            behavior_key = f"{category}_{sub_category}"
            self.behaviors[behavior_key] = SocialBehavior(
                main_category=category,
                sub_category=sub_category,
                definition=self.generate_definition(sub_category, category),
                example_quote=best_quote,
                example_source=best_source,
                model_counts=dict(model_counts),
                total_occurrences=len(instances),
                games_where_occurred=len(games_with_behavior)
            )
    
    def process_all_games(self):
        """Process all game files using card_sort.py analysis"""
        if not self.game_records_dir.exists():
            print(f"Game records directory {self.game_records_dir} not found")
            return
        
        # Step 1: Run card_sort.py analysis
        self.run_card_sort_analysis()
        
        # Step 2: Load social analyses
        analyses = self.load_social_analyses()
        if not analyses:
            print("No social analyses found. Make sure card_sort.py ran successfully.")
            return
        
        # Step 3: Process analyses to extract behaviors
        all_behaviors = self.process_social_analyses(analyses)
        print(f"Extracted {len(all_behaviors)} behavior instances")
        
        # Step 4: Aggregate behaviors
        self.aggregate_behaviors(all_behaviors)
        print(f"Found {len(self.behaviors)} unique social behaviors")
    
    def generate_csv(self, output_file: str = "enhanced_social_dynamics_analysis.csv"):
        """Generate CSV file with the analysis results"""
        output_path = Path(output_file)
        
        # Get all unique models
        all_models = sorted(self.all_models)
        
        # Create CSV headers
        headers = [
            "Main Category",
            "Sub-Category", 
            "Definition",
            "Example Quote",
            "Example Source",
            "Total Occurrences",
            "Games Where Occurred"
        ]
        
        # Add model count columns
        for model in all_models:
            headers.append(f"Count {model}")
        
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
                    behavior.example_quote,
                    behavior.example_source,
                    behavior.total_occurrences,
                    behavior.games_where_occurred
                ]
                
                # Add model counts
                for model in all_models:
                    row.append(behavior.model_counts.get(model, 0))
                
                writer.writerow(row)
        
        print(f"Enhanced CSV file generated: {output_path}")
        print(f"Total behaviors analyzed: {len(self.behaviors)}")
        print(f"Models found: {', '.join(all_models)}")

def main():
    analyzer = EnhancedSocialDynamicsAnalyzer()
    analyzer.process_all_games()
    analyzer.generate_csv()

if __name__ == "__main__":
    main()

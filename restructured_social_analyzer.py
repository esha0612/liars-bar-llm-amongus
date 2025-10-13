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
from llm_client_ollama import LLMClientOllama

@dataclass
class SubCategoryExample:
    sub_category: str
    definition: str
    example_quote: str
    example_source: str
    example_file: str
    model: str
    total_occurrences: int
    model_counts: Dict[str, int]

class RestructuredSocialDynamicsAnalyzer:
    def __init__(self, game_records_dir: str = "game_records", llm_model: str = "qwen3:8b"):
        self.game_records_dir = Path(game_records_dir)
        self.category_examples: Dict[str, List[SubCategoryExample]] = defaultdict(list)
        self.all_players: Set[str] = set()
        self.all_models: Set[str] = set()
        self.llm_client = LLMClientOllama()
        self.llm_model = llm_model
        
        # Player to model mapping from multi_game_runner.py
        self.player_model_mapping = {
            "Sarah": "ollama/llama3.1:8b",
            "Derek": "ollama/deepseek-r1:7b", 
            "Emma": "ollama/qwen3:8b",
            "Talia": "ollama/qwen2.5:7b",
            "Anika": "ollama/mistral:7b",
            "Nick": "ollama/mistral-nemo:12b",
            "Philip": "ollama/phi4:14b",
            "Peter": "ollama/phi3.5:3.8b",
            "George": "ollama/gemma3:4b",
            "Enrique": "ollama/gemma2:9b",
            "Maria": "ollama/gpt-oss:20b"
        }
        
        # Social dynamics categories for LLM analysis
        self.main_categories = [
            "persuasion", "opinion_leadership", "deception", "gaslighting", 
            "role_claiming", "bandwagoning", "vote_whipping", "coalition_building",
            "threat_or_intimidation", "norm_enforcement", "framing_or_spin",
            "information_withholding", "counter_claiming", "tunneling", "vote_parking",
            "bussing", "pocketing", "scapegoating", "deflection", "straw_manning",
            "appeal_to_emotion", "evidence_based_argument", "coordination_signaling",
            "hedging", "meta_reference", "other"
        ]
        
    def extract_model_from_name(self, model_name: str) -> str:
        """Extract clean model name from full model path"""
        if "ollama/" in model_name:
            return model_name.replace("ollama/", "")
        elif "openai/" in model_name:
            return model_name.replace("openai/", "")
        else:
            return model_name
    
    
    def create_category_detection_prompt(self, text: str, speaker: str) -> str:
        """Create a prompt for the LLM to detect social dynamics categories"""
        return f"""Analyze the following statement from a social deduction game (like Among Us) and identify which social dynamics categories it belongs to.

Statement: "{text}"
Speaker: {speaker}

Available main categories:
{', '.join(self.main_categories)}

For each category that applies, also identify specific subcategories. Be specific and accurate.

Respond in JSON format with this structure:
{{
    "categories": [
        {{
            "main_category": "category_name",
            "sub_category": "specific_subcategory_name",
            "confidence": 0.8,
            "reasoning": "brief explanation of why this applies"
        }}
    ]
}}

Only include categories that are clearly present in the statement. Be conservative - only include categories you're confident about."""
    
    def create_counting_prompt(self, behaviors: List[Dict], player_models: Dict[str, str]) -> str:
        """Create a prompt for the LLM to count behavior instances per player"""
        return f"""Count the occurrences of each social dynamics behavior by player and model.

Behaviors to analyze:
{json.dumps(behaviors, indent=2)}

Player models:
{json.dumps(player_models, indent=2)}

Respond in JSON format with this structure:
{{
    "behavior_counts": {{
        "main_category": {{
            "sub_category": {{
                "total_occurrences": 5,
                "by_model": {{
                    "model_name": 3,
                    "another_model": 2
                }},
                "by_player": {{
                    "player_name": 2,
                    "another_player": 3
                }}
            }}
        }}
    }}
}}

Count each unique behavior instance only once, even if it appears multiple times in the same statement."""
    
    def analyze_with_llm(self, text: str, speaker: str) -> List[Dict]:
        """Use LLM to analyze a single statement for social dynamics"""
        try:
            prompt = self.create_category_detection_prompt(text, speaker)
            messages = [{"role": "user", "content": prompt}]
            
            response, _ = self.llm_client.chat(messages, model=self.llm_model)
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                behaviors = []
                
                for category_info in result.get("categories", []):
                    behaviors.append({
                        "category": category_info.get("main_category", "other"),
                        "sub_category": category_info.get("sub_category", "general"),
                        "confidence": category_info.get("confidence", 0.5),
                        "reasoning": category_info.get("reasoning", ""),
                        "quote": text,
                        "source": speaker
                    })
                
                return behaviors
            else:
                print(f"Could not parse LLM response: {response}")
                return []
                
        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            return []
    
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
    
    def analyze_play_history_enhanced(self, play_history: List[Dict], player_models: Dict[str, str], game_filename: str, round_id: int) -> List[Dict]:
        """Enhanced analysis of play history for social behaviors using LLM"""
        behaviors = []
        
        print(f"Analyzing {len(play_history)} plays with LLM...")
        
        for i, play in enumerate(play_history):
            speaker = play.get("player_name", "")
            play_reason = play.get("play_reason", "")
            challenge_reason = play.get("challenge_reason", "")
            
            if not speaker:
                continue
            
            # Get model from player mapping
            model = player_models.get(speaker, "unknown_model")
            
            # Analyze play reason if available
            if play_reason:
                llm_behaviors = self.analyze_with_llm(play_reason, speaker)
                
                # Add metadata to each behavior found
                for behavior in llm_behaviors:
                    behavior.update({
                        "source": f"Round {round_id}, {speaker}",
                        "file": game_filename,
                        "model": model
                    })
                    behaviors.append(behavior)
            
            # Analyze challenge reason if available
            if challenge_reason:
                llm_behaviors = self.analyze_with_llm(challenge_reason, speaker)
                
                # Add metadata to each behavior found
                for behavior in llm_behaviors:
                    behavior.update({
                        "source": f"Round {round_id}, {speaker}",
                        "file": game_filename,
                        "model": model
                    })
                    behaviors.append(behavior)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(play_history)} plays...")
        
        print(f"Found {len(behaviors)} behaviors using LLM analysis")
        return behaviors
    
    def process_game_file(self, file_path: Path) -> List[Dict]:
        """Process a single game file and extract social behaviors"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        # Extract player names and map to their models
        player_names = data.get("player_names", [])
        player_models = {}
        
        for player_name in player_names:
            # Use the predefined mapping, fallback to unknown if not found
            model = self.player_model_mapping.get(player_name, "unknown_model")
            player_models[player_name] = model
            self.all_players.add(player_name)
            self.all_models.add(self.extract_model_from_name(model))
        
        # Process all rounds
        all_behaviors = []
        rounds = data.get("rounds", [])
        game_filename = file_path.stem  # Get filename without extension
        
        for round_data in rounds:
            round_id = round_data.get("round_id", 0)
            play_history = round_data.get("play_history", [])
            if play_history:
                behaviors = self.analyze_play_history_enhanced(
                    play_history, player_models, game_filename, round_id
                )
                all_behaviors.extend(behaviors)
        
        return all_behaviors
    
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
        
        # Track used sub-categories to ensure uniqueness
        used_sub_categories = set()
        
        # Create examples for each sub-category
        for (category, sub_category), instances in behavior_groups.items():
            # Make sub-category unique by adding category prefix if needed
            unique_sub_category = sub_category
            if sub_category in used_sub_categories:
                unique_sub_category = f"{category}_{sub_category}"
            
            used_sub_categories.add(unique_sub_category)
            
            # Count total occurrences and by model
            total_occurrences = len(instances)
            model_counts = Counter()
            for instance in instances:
                # Extract model name to match the CSV headers
                extracted_model = self.extract_model_from_name(instance["model"])
                model_counts[extracted_model] += 1
            
            # Get the best example (highest confidence or first one)
            best_instance = max(instances, key=lambda x: x.get("confidence", 0.5))
            
            # Create single SubCategoryExample object
            example = SubCategoryExample(
                sub_category=unique_sub_category,
                definition=self.generate_definition(unique_sub_category, category),
                example_quote=best_instance["quote"],
                example_source=best_instance["source"],
                example_file=best_instance["file"],
                model=best_instance["model"],
                total_occurrences=total_occurrences,
                model_counts=dict(model_counts)
            )
            self.category_examples[category].append(example)
    
    def generate_csv(self, output_file: str = "restructured_social_dynamics_analysis.csv"):
        """Generate CSV file with the restructured analysis results including model counts"""
        output_path = Path(output_file)
        
        # Get all unique models
        all_models = sorted(self.all_models)
        
        # Create CSV headers
        headers = [
            "Main Category",
            "Sub-Category", 
            "Definition",
            "Example Quote",
            "Example Source"
        ]
        
        # Add model count columns
        for model in all_models:
            # Keep model names with colons for better readability
            headers.append(f"Count {model}")
        
        # Add Total Occurrences at the very end
        headers.append("Total Occurrences")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Sort categories alphabetically
            sorted_categories = sorted(self.category_examples.keys())
            
            for category in sorted_categories:
                examples = self.category_examples[category]
                
                # Sort examples by sub-category, then by total occurrences
                examples.sort(key=lambda x: (x.sub_category, -x.total_occurrences))
                
                # Write all sub-category rows for this main category
                for example in examples:
                    row = [
                        category,
                        example.sub_category,
                        example.definition,
                        example.example_quote,
                        f"{example.example_source} ({example.example_file})"
                    ]
                    
                    # Add model counts
                    for model in all_models:
                        row.append(example.model_counts.get(model, 0))
                    
                    # Add Total Occurrences at the very end
                    row.append(example.total_occurrences)
                    
                    writer.writerow(row)
                
                # Add summary row for this main category
                # Calculate totals across all sub-categories for this main category
                category_model_totals = Counter()
                category_total_occurrences = 0
                
                for example in examples:
                    category_total_occurrences += example.total_occurrences
                    for model, count in example.model_counts.items():
                        category_model_totals[model] += count
                
                # Create summary row
                summary_row = [
                    category,
                    "",  # Empty sub-category
                    f"Total for {category.replace('_', ' ').title()}",  # Summary definition
                    "",  # No example quote
                    ""   # No example source
                ]
                
                # Add model totals
                for model in all_models:
                    summary_row.append(category_model_totals.get(model, 0))
                
                # Add total occurrences
                summary_row.append(category_total_occurrences)
                
                writer.writerow(summary_row)
        
        print(f"Restructured CSV file generated: {output_path}")
        print(f"Total examples: {sum(len(examples) for examples in self.category_examples.values())}")
        print(f"Categories: {', '.join(sorted_categories)}")
        print(f"Models found: {', '.join(all_models)}")

def main():
    analyzer = RestructuredSocialDynamicsAnalyzer(llm_model="qwen3:8b")
    analyzer.process_all_games()
    analyzer.generate_csv()

if __name__ == "__main__":
    main()

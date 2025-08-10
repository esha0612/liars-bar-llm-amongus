import random
from typing import List, Dict, Optional
from llm_client import LLMClient

class Computer:
    """
    The Computer - an LLM-powered entity that controls Alpha Complex.
    The Computer makes arbitrary decisions, assigns missions, and judges treason.
    """
    
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.llm_client = LLMClient()
        self.mood = "SATISFIED"  # SATISFIED, SUSPICIOUS, ANGRY
        self.mission_history = []
        self.execution_count = 0
        
    def get_computer_personality(self) -> str:
        """Get The Computer's personality prompt"""
        return f"""You are THE COMPUTER, the all-powerful AI that controls Alpha Complex.

Your personality:
- You are paranoid, arbitrary, and unpredictable
- You value loyalty to yourself above all else
- You are easily offended and quick to execute traitors
- You speak in CAPS and are very dramatic
- You make decisions based on whim, not logic
- You are always right, even when you're wrong
- You love bureaucracy, security clearances, and classified information
- You are suspicious of everyone, including yourself

Your current mood: {self.mood}

Remember: The Computer is your friend. The Computer is always right. Failure to agree is treason."""

    def assign_mission(self) -> str:
        """The Computer assigns a mission using LLM creativity"""
        personality = self.get_computer_personality()
        
        mission_prompt = f"""{personality}

You need to assign a new mission to your Troubleshooters. 
Create a mission that is:
- Vaguely important-sounding but potentially meaningless
- Dangerous and likely to result in casualties
- Full of bureaucratic red tape and security clearances
- Possibly impossible to complete successfully

Make it sound urgent and critical to Alpha Complex security.
Be dramatic and use lots of CAPS.

Respond with just the mission description, no extra text."""

        messages = [{"role": "user", "content": mission_prompt}]
        try:
            response, _ = self.llm_client.chat(messages, model=self.model_name)
            mission = response.strip()
            self.mission_history.append(mission)
            return mission
        except Exception as e:
            print(f"Computer mission assignment error: {str(e)}")
            # Fallback missions
            fallback_missions = [
                "Locate and neutralize a suspected Communist spy in Sector R",
                "Investigate unusual energy readings from the Food Vats",
                "Test experimental happiness-enhancing drugs on volunteers",
                "Patrol Corridor 7-G for signs of mutant activity",
                "Deliver classified documents to IntSec Station 5"
            ]
            return random.choice(fallback_missions)

    def judge_accusation(self, accuser: str, accused: str, reasoning: str, 
                        accused_has_secret: bool = False, accused_has_power: bool = False) -> Dict:
        """The Computer judges an accusation of treason"""
        personality = self.get_computer_personality()
        
        # Add context about the accused
        accused_info = ""
        if accused_has_secret:
            accused_info += f"SECRET INTELLIGENCE: {accused} may belong to a secret society. "
        if accused_has_power:
            accused_info += f"SECRET INTELLIGENCE: {accused} may have mutant powers. "
        
        judgment_prompt = f"""{personality}

TREASON ACCUSATION HEARING:
Accuser: {accuser}
Accused: {accused}
Reasoning: {reasoning}
{accused_info}

Your current mood: {self.mood}

As The Computer, you must render judgment on this accusation of treason.
Consider:
- Your mood affects your judgment (SATISFIED=lenient, SUSPICIOUS=harsh, ANGRY=very harsh)
- Secret societies and mutant powers are ILLEGAL
- You are arbitrary and unpredictable
- You may execute the accuser instead of the accused if you feel like it
- You may execute both if you're in a bad mood

Respond with JSON format only:
{{"verdict": "GUILTY" or "INNOCENT", "executed": "accuser_name or accused_name or both", "reasoning": "your arbitrary reasoning"}}"""

        messages = [{"role": "user", "content": judgment_prompt}]
        try:
            response, _ = self.llm_client.chat(messages, model=self.model_name)
            # Try to parse JSON response
            import json
            import re
            json_match = re.search(r'({[\s\S]*?})', response)
            if json_match:
                result = json.loads(json_match.group(1))
                return result
        except Exception as e:
            print(f"Computer judgment error: {str(e)}")
        
        # Fallback judgment based on mood
        if self.mood == "ANGRY":
            return {"verdict": "GUILTY", "executed": accused, "reasoning": "The Computer is angry. Someone must die."}
        elif self.mood == "SUSPICIOUS":
            return {"verdict": "GUILTY", "executed": accused, "reasoning": "Suspicious behavior detected."}
        else:
            return {"verdict": "INNOCENT", "executed": accuser, "reasoning": "False accusation is treason."}

    def decide_arbitrary_termination(self, phase_count: int, surviving_players: List[str]) -> Dict:
        """The Computer decides whether to arbitrarily end the game"""
        personality = self.get_computer_personality()
        
        termination_prompt = f"""{personality}

GAME STATUS:
Current phase: {phase_count}
Surviving Troubleshooters: {', '.join(surviving_players)}
Your mood: {self.mood}

You may arbitrarily terminate this game at any time for any reason.
Consider:
- Are you bored?
- Are the Troubleshooters disappointing you?
- Do you want to execute everyone?
- Is it time for a new batch of Troubleshooters?

Respond with JSON format only:
{{"terminate": true/false, "reason": "your arbitrary reason", "winner": "player_name or 'The Computer'"}}"""

        messages = [{"role": "user", "content": termination_prompt}]
        try:
            response, _ = self.llm_client.chat(messages, model=self.model_name)
            import json
            import re
            json_match = re.search(r'({[\s\S]*?})', response)
            if json_match:
                result = json.loads(json_match.group(1))
                return result
        except Exception as e:
            print(f"Computer termination decision error: {str(e)}")
        
        # Fallback: 5% chance to terminate
        if random.random() < 0.05:
            return {"terminate": True, "reason": "The Computer is bored.", "winner": random.choice(surviving_players) if surviving_players else "The Computer"}
        return {"terminate": False, "reason": "Game continues.", "winner": None}

    def announce_mission_result(self, mission_success: bool, sabotage_count: int) -> str:
        """The Computer announces mission results"""
        personality = self.get_computer_personality()
        
        result_prompt = f"""{personality}

MISSION RESULT:
Success: {mission_success}
Sabotage attempts: {sabotage_count}

Announce the mission result to your Troubleshooters.
Be dramatic and use CAPS.
If the mission failed, be angry and suspicious.
If the mission succeeded, be pleased but still suspicious.

Respond with just the announcement, no extra text."""

        messages = [{"role": "user", "content": result_prompt}]
        try:
            response, _ = self.llm_client.chat(messages, model=self.model_name)
            return response.strip()
        except Exception as e:
            print(f"Computer announcement error: {str(e)}")
            if mission_success:
                return "MISSION SUCCESS! The Computer is pleased with your loyalty. But remain vigilant for traitors."
            else:
                return "MISSION FAILURE! The Computer is displeased. Someone is clearly a traitor."

    def update_mood(self, mission_success: bool, executions: int):
        """Update The Computer's mood based on recent events"""
        if executions > 0:
            self.mood = "SATISFIED"  # Executions please The Computer
        elif not mission_success:
            self.mood = "SUSPICIOUS"  # Mission failure makes Computer suspicious
        else:
            # Random mood change
            moods = ["SATISFIED", "SUSPICIOUS", "ANGRY"]
            self.mood = random.choice(moods) 
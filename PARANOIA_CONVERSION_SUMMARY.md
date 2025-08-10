# Paranoia Game Conversion Summary

This document summarizes the complete conversion of the codebase from a Mafia game to a Paranoia RPG game based on the rule_base.txt file.

## Major Changes Made

### 1. Game Structure (game.py)
- **Class**: `MafiaGame` → `ParanoiaGame`
- **Phases**: Night/Day → Mission/Accusation phases  
- **Roles**: Mafia/Doctor/Detective/Townsperson → All Troubleshooters with secret societies/mutant powers
- **Win Conditions**: Team-based → Individual survival with Computer approval
- **Death System**: Permanent death → 6-clone respawn system

### 2. Player System (player.py)
- **Roles**: Added secret society and mutant power assignments
- **Clone System**: Implemented 6-clone tracking per player
- **Methods**: Replaced Mafia-specific methods with Paranoia methods:
  - `discuss_mission()` - Public mission strategy discussion
  - `choose_sabotage_action()` - Private sabotage decisions  
  - `make_accusation()` - Treason accusations
  - `reflect_on_phase()` - Phase reflection and opinion updates

### 3. Game Recording (game_record.py)
- **Phase Tracking**: `NightPhase`/`DayPhase` → `MissionPhase`/`AccusationPhase`
- **Actions**: `NightAction` → `SabotageAction` and `AccusationAction`
- **Player Data**: Added secret society and mutant power tracking
- **Computer Decisions**: Added tracking of Computer judgments and mood

### 4. The Computer AI Implementation
- **Mission Assignment**: Random mission generation from 8 predefined missions
- **Arbitrary Judgment**: Computer makes biased decisions on accusations
- **Mood System**: Computer mood affects judgment (SATISFIED/SUSPICIOUS/ANGRY)
- **Random Termination**: 5% chance per phase to end game arbitrarily
- **Secret Detection**: Bias against players with secret societies/mutant powers

### 5. Prompt System
**Removed old Mafia prompts:**
- mafia_night_prompt.txt
- doctor_night_prompt.txt  
- detective_night_prompt.txt
- vote_prompt.txt
- impression_prompt.txt

**Added new Paranoia prompts:**
- mission_discussion_prompt.txt - For public mission strategy
- sabotage_decision_prompt.txt - For private sabotage decisions
- accusation_prompt.txt - For treason accusations
- reflection_prompt.txt - For phase reflections
- computer_judgment_prompt.txt - For Computer decisions

### 6. Core Gameplay Loop
1. **Mission Phase**: 
   - Computer assigns random mission
   - Public cooperation discussion
   - Private sabotage decisions
   - Mission success/failure resolution

2. **Accusation Phase**:
   - Players make treason accusations
   - Computer renders arbitrary judgment
   - Executions (with clone system)
   - Computer mood updates

### 7. Clone System Details
- Each player starts as Clone 1/6
- When executed, advances to next clone
- After Clone 6, player is permanently eliminated
- Clone inheritance: memories and suspicion records carry over

### 8. Secret Affiliations
- **Secret Societies**: Illuminati, Communists, Death Leopard, Psion, Anti-Mutant
- **Mutant Powers**: Telepathy, Energy_Blast, Machine_Empathy, Precognition, Telekinesis
- **Assignment**: Random distribution (50% get societies, 33% get powers)
- **Gameplay Impact**: Affects Computer judgment bias and sabotage motivations

### 9. Files Updated
- `game.py` - Complete rewrite for Paranoia mechanics
- `player.py` - New Troubleshooter class with Paranoia methods  
- `game_record.py` - New data structures for Paranoia tracking
- `prompt/rule_base.txt` - Updated with Paranoia rules (already provided)
- All new prompt files for Paranoia-specific interactions

### 10. Key Features Preserved
- Multi-LLM player system
- Game recording and logging
- JSON-based game state tracking
- Configurable player models
- Comprehensive conversation logging

## How to Run
The game can be started the same way as before:
```bash
python game.py
```

The game will now run as a Paranoia RPG session instead of Mafia, with all the appropriate mechanics, themes, and Computer-controlled chaos that defines the Paranoia experience.

## Compatibility
- **Pure Ollama Integration**: Removed all OpenAI dependencies, now 100% Ollama-based
- Game recording system maintains compatibility
- File structure and deployment unchanged  
- Only gameplay mechanics converted to Paranoia
- Same model support: llama3, mistral:7b, mistral:latest, etc.

The conversion successfully transforms the collaborative deduction game of Mafia into the paranoid, backstabbing, Computer-controlled chaos of Paranoia RPG while maintaining the same technical infrastructure.
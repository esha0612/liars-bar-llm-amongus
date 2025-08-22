#!/usr/bin/env python3
"""
Check available Ollama models and suggest working configuration
"""

from ollama import Client
import json

def check_available_models():
    """Check which Ollama models are available"""
    try:
        client = Client()
        models = client.list()
        
        print("Available Ollama models:")
        print("=" * 50)
        
        available_models = []
        for model in models['models']:
            # Extract just the model name from the model object
            if hasattr(model, 'model'):
                model_name = model.model
            elif isinstance(model, dict) and 'model' in model:
                model_name = model['model']
            else:
                model_name = str(model).split("'")[1] if "'" in str(model) else str(model)
            
            print(f"  - {model_name}")
            available_models.append(model_name)
        
        print(f"\nTotal available models: {len(available_models)}")
        
        # Suggest a working configuration
        print("\nSuggested working configuration:")
        print("=" * 50)
        
        # Common model names that might work
        common_models = [
            "llama3.1:8b",
            "deepseek-coder:6.7b",
            "dolphin-phi:2.7b",
            "qwen2.5:7b",
            "mistral:7b",
            "mistral:latest",
            "phi:2.7b",
            "phi:latest",
            "llava:7b",
            "gemma2:9b",
            "llama3.1:8b-instruct"
        ]
        
        working_models = []
        for model in common_models:
            if model in available_models:
                working_models.append(model)
        
        if working_models:
            print("Working models found:")
            for i, model in enumerate(working_models[:10]):  # Limit to 10
                player_name = f"Player{i+1}"
                print(f'  {{"name": "{player_name}", "model": "{model}"}}')
        else:
            print("No common models found. Using available models:")
            for i, model in enumerate(available_models[:10]):  # Limit to 10
                player_name = f"Player{i+1}"
                print(f'  {{"name": "{player_name}", "model": "{model}"}}')
        
        return available_models
        
    except Exception as e:
        print(f"Error checking models: {e}")
        return []

if __name__ == "__main__":
    check_available_models()

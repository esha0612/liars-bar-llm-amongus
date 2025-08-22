#!/usr/bin/env python3
"""
Test script for the multi-LLM client
"""

from multi_llm_client import MultiLLMClient
import os

def test_multi_llm_client():
    """Test the multi-LLM client with different model types"""
    
    # Initialize the client
    client = MultiLLMClient()
    
    # Test message
    test_message = [
        {"role": "user", "content": "Hello! Please respond with a simple greeting."}
    ]
    
    # Test with Ollama models (these should work with Ollama)
    ollama_models = [
        "Llama3.1:8b",
        "Deepseek-r1:7b", 
        "dolphin3:latest",
        "qwen 2.5:7b",
        "Mistral:7b",
        "Mistral-nemo:12b",
        "Phi4:14b",
        "Phi3.5:3.8b",
        "llava:7b",
        "Gemma2:9b"
    ]
    
    # Test with OpenAI models
    openai_models = [
        "gpt-4o-mini"
    ]
    
    print("Testing Multi-LLM Client")
    print("=" * 50)
    
    # Test Ollama models
    print("\nTesting Ollama models:")
    for model in ollama_models[:3]:  # Test first 3 to avoid too many requests
        print(f"\nTesting model: {model}")
        try:
            content, reasoning = client.chat(test_message, model)
            print(f"Response: {content[:100]}...")
            print(f"Model type detected: {'OpenAI' if client._is_openai_model(model) else 'Ollama'}")
        except Exception as e:
            print(f"Error with {model}: {str(e)}")
    
    # Test OpenAI models
    print("\nTesting OpenAI models:")
    for model in openai_models:
        print(f"\nTesting model: {model}")
        try:
            content, reasoning = client.chat(test_message, model)
            print(f"Response: {content[:100]}...")
            print(f"Model type detected: {'OpenAI' if client._is_openai_model(model) else 'Ollama'}")
        except Exception as e:
            print(f"Error with {model}: {str(e)}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_multi_llm_client()

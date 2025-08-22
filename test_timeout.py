#!/usr/bin/env python3
"""
Test script to verify timeout mechanisms work correctly
"""

import time
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_llm_client import MultiLLMClient

def test_llm_timeout():
    """Test that LLM client has proper timeout handling"""
    print("Testing LLM client timeout mechanisms...")
    
    client = MultiLLMClient()
    
    # Test with a non-existent model to trigger timeout
    test_messages = [{"role": "user", "content": "Hello, this is a test."}]
    
    print(f"Testing with timeout setting: {client.timeout} seconds")
    
    start_time = time.time()
    try:
        content, reasoning = client.chat(test_messages, "non-existent-model")
        elapsed = time.time() - start_time
        print(f"Request completed in {elapsed:.2f} seconds")
        print(f"Content: {content}")
        print(f"Reasoning: {reasoning}")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Request failed after {elapsed:.2f} seconds with error: {e}")
    
    print("LLM timeout test completed.\n")

def test_game_timeout():
    """Test that game has proper timeout handling"""
    print("Testing game timeout mechanisms...")
    
    # Import game after setting up path
    from game import Game
    
    # Create a minimal game configuration for testing
    test_configs = [
        {"name": "TestPlayer1", "model": "non-existent-model"},
        {"name": "TestPlayer2", "model": "non-existent-model"}
    ]
    
    print("Creating test game with timeout settings...")
    game = Game(test_configs)
    
    print(f"Max game duration: {game.max_game_duration} seconds")
    print(f"Max rounds: {game.max_rounds}")
    print(f"Player timeout: {game.players[0].max_retry_time} seconds")
    
    # Test timeout check
    game.game_start_time = time.time() - 3601  # Set to 1 hour + 1 second ago
    if game._check_timeout():
        print("✓ Timeout check working correctly")
    else:
        print("✗ Timeout check not working")
    
    print("Game timeout test completed.\n")

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Timeout Mechanisms")
    print("=" * 50)
    
    test_llm_timeout()
    test_game_timeout()
    
    print("All timeout tests completed!")
    print("\nTo run the actual game with timeout protection:")
    print("python game.py")

from llm_client_ollama import LLMClientOllama

# Use Ollama as the default and only LLM client
LLMClient = LLMClientOllama

# Example usage
if __name__ == "__main__":
    llm = LLMClient()
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    response = llm.chat(messages)
    print(f"Response: {response}")
from openai import OpenAI
API_BASE_URL = "YOUR_API_BASE_URL"
API_KEY = "YOUR_API_KEY"

from llm_client_ollama import LLMClientOllama

class LLMClientAPI:
    def __init__(self, api_key=API_KEY, base_url=API_BASE_URL):
        """Initialize LLM client"""
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
    def chat(self, messages, model="deepseek-r1"):
        """Interact with LLM
        
        Args:
            messages: List of messages
            model: LLM model to use
        
        Returns:
            tuple: (content, reasoning_content)
        """
        try:
            print(f"LLM request: {messages}")
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            if response.choices:
                message = response.choices[0].message
                content = message.content if message.content else ""
                reasoning_content = getattr(message, "reasoning_content", "")
                print(f"LLM reasoning content: {content}")
                return content, reasoning_content
            
            return "", ""
                
        except Exception as e:
            print(f"LLM call error: {str(e)}")
            return "", ""
        
LLMClient = LLMClientOllama

# Example usage
if __name__ == "__main__":
    llm = LLMClient()
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    response = llm.chat(messages)
    print(f"Response: {response}")
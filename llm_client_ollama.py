from ollama import Client

OLLAMA_API_BASE_URL = "http://localhost:11434"  # Default Ollama API endpoint

class LLMClientOllama:
    def __init__(self, base_url=OLLAMA_API_BASE_URL):
        """Initialize Ollama client"""
        self.client = Client(base_url)
        
    def chat(self, messages, model="deepseek-r1:8b"):
        """Interact with Ollama LLM
        
        Args:
            messages: List of messages
            model: Ollama model to use
        
        Returns:
            tuple: (content, reasoning_content)
        """
        try:
            print(f"Ollama Request: {messages}")
            
            # Call Ollama API
            response = self.client.chat(
                model=model,
                messages=messages,
                options={"temperature": 0.7}
            )
            
            # Handle different response structures
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                content = response.message.content
            elif hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, dict) and 'message' in response:
                content = response['message'].get('content', '')
            else:
                # Try to get content from response directly
                content = str(response) if response else ""
            
            # Ollama doesn't natively support reasoning_content, can be extended if needed
            reasoning_content = ""
            
            print(f"Ollama Response: {content}")
            return content, reasoning_content
                
        except Exception as e:
            print(f"Ollama API Error: {str(e)}")
            return "", ""
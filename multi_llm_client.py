import os
import time
from typing import List, Dict, Tuple

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available. Loading .env file manually...")
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print("Loaded environment variables from .env file manually")
    except FileNotFoundError:
        print("⚠️  No .env file found. Make sure to set environment variables manually.")
    except Exception as e:
        print(f"⚠️  Error loading .env file: {e}")

# Try to import OpenAI, but handle missing dependency gracefully
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: OpenAI module not available. OpenAI models will not work.")
    OPENAI_AVAILABLE = False

# Try to import Ollama, but handle missing dependency gracefully
try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError:
    print("Warning: Ollama module not available. Ollama models will not work.")
    OLLAMA_AVAILABLE = False

class MultiLLMClient:
    def __init__(self):
        """Initialize multi-LLM client that supports both Ollama and OpenAI"""
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        # Debug: Check if API key is loaded properly
        if self.openai_api_key == "YOUR_API_KEY":
            print("Warning: OpenAI API key not found in environment variables")
            print("Make sure your .env file contains: OPENAI_API_KEY=your_actual_api_key")
        else:
            print(f"OpenAI API key loaded: {self.openai_api_key[:10]}...")
        
        # Ollama configuration
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # Timeout settings (in seconds)
        self.timeout = 30  # 30 seconds timeout for API calls
        
        # Initialize clients based on availability
        if OPENAI_AVAILABLE:
            try:
                self.openai_client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url,
                    timeout=self.timeout
                )
                print("✅ OpenAI client initialized successfully")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            
        if OLLAMA_AVAILABLE:
            try:
                self.ollama_client = Client(self.ollama_base_url)
                # Test connection
                try:
                    self.ollama_client.list()
                    print("✅ Ollama client initialized and connected successfully")
                except Exception as e:
                    print(f"⚠️  Ollama client initialized but connection test failed: {e}")
                    print(f"   Ollama service may not be running at {self.ollama_base_url}")
                    print("   Run 'ollama serve' to start the service")
            except Exception as e:
                print(f"Warning: Failed to initialize Ollama client: {e}")
                self.ollama_client = None
        else:
            self.ollama_client = None
        
        # Define OpenAI models (case-insensitive)
        self.openai_models = {
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo"
        }
    
    def _is_openai_model(self, model_name: str) -> bool:
        """Check if the model is an OpenAI model"""
        return model_name.lower() in {model.lower() for model in self.openai_models}
    
    def _is_ollama_model(self, model_name: str) -> bool:
        """Check if the model is an Ollama model (not OpenAI)"""
        return not self._is_openai_model(model_name)
    
    def chat(self, messages: List[Dict[str, str]], model: str) -> Tuple[str, str]:
        """Interact with LLM (either OpenAI or Ollama)
        
        Args:
            messages: List of messages with role and content
            model: Model name to use
        
        Returns:
            tuple: (content, reasoning_content)
        """
        try:
            if self._is_openai_model(model):
                return self._chat_openai(messages, model)
            else:
                return self._chat_ollama(messages, model)
        except Exception as e:
            print(f"Multi-LLM client error for model {model}: {str(e)}")
            return "", ""
    
    def _chat_openai(self, messages: List[Dict[str, str]], model: str) -> Tuple[str, str]:
        """Chat with OpenAI model"""
        if not self.openai_client:
            print(f"Error: OpenAI client not available for model {model}")
            return "", ""
            
        try:
            print(f"OpenAI Request to {model}: {messages}")
            
            # Add timeout to the request
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=self.timeout
            )
            
            if response.choices:
                message = response.choices[0].message
                content = message.content if message.content else ""
                reasoning_content = getattr(message, "reasoning_content", "")
                print(f"OpenAI Response from {model}: {content}")
                return content, reasoning_content
            
            return "", ""
                
        except Exception as e:
            print(f"OpenAI API Error for {model}: {str(e)}")
            return "", ""
    
    def _chat_ollama(self, messages: List[Dict[str, str]], model: str) -> Tuple[str, str]:
        """Chat with Ollama model"""
        if not self.ollama_client:
            print(f"Error: Ollama client not available for model {model}")
            return "", ""
            
        try:
            print(f"Ollama Request to {model}: {messages}")
            print(f"Ollama base URL: {self.ollama_base_url}")
            
            # Add timeout to Ollama request
            start_time = time.time()
            
            # Call Ollama API with timeout
            response = self.ollama_client.chat(
                model=model,
                messages=messages,
                options={"temperature": 0.7}
            )
            
            # Check if we exceeded timeout
            if time.time() - start_time > self.timeout:
                print(f"Ollama request to {model} timed out after {self.timeout} seconds")
                return "", ""
            
            # Debug: Print response type and structure
            print(f"Ollama response type: {type(response)}")
            print(f"Ollama response: {response}")
            
            # Handle different response structures
            content = ""
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                content = response.message.content
            elif hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, dict):
                if 'message' in response and isinstance(response['message'], dict):
                    content = response['message'].get('content', '')
                elif 'content' in response:
                    content = response['content']
                else:
                    # Try to find content in the dictionary
                    content = str(response)
            else:
                # Try to get content from response directly
                content = str(response) if response else ""
            
            # Ollama doesn't natively support reasoning_content, can be extended if needed
            reasoning_content = ""
            
            print(f"Ollama Response from {model}: {content}")
            return content, reasoning_content
                
        except Exception as e:
            print(f"Ollama API Error for {model}: {str(e)}")
            print(f"Error type: {type(e)}")
            
            # Provide helpful error messages for common issues
            if "Name or service not known" in str(e) or "Connection refused" in str(e):
                print(f"⚠️  Ollama service not accessible at {self.ollama_base_url}")
                print("   Please make sure:")
                print("   1. Ollama is installed and running")
                print("   2. Run: ollama serve")
                print("   3. Check if the URL is correct in your .env file")
                print("   4. Try: curl http://localhost:11434/api/tags")
            elif "model not found" in str(e).lower():
                print(f"⚠️  Model '{model}' not found in Ollama")
                print(f"   Available models: ollama list")
                print(f"   Pull the model: ollama pull {model}")
            
            import traceback
            traceback.print_exc()
            return "", ""

# For backward compatibility, create an alias
LLMClient = MultiLLMClient

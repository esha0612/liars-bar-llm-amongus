# llm_client.py
import os
from typing import Tuple, List, Dict, Optional
from openai import OpenAI

# Allow override via env; default None lets SDK pick its own default
OPENAI_API_BASE_URL = os.getenv("OPENAI_BASE_URL", None)

class LLMClientOpenAI:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = OPENAI_API_BASE_URL):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=base_url)

    def chat(self, messages: List[Dict[str, str]], model: str = "gpt-4o-mini") -> Tuple[str, str]:
        """Interact with OpenAI LLM
        
        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            model: OpenAI model to use
        
        Returns:
            tuple: (content, reasoning_content)
        """
        try:
            print(f"OpenAI Request: {messages}")

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )

            content = ""
            reasoning_content = ""

            if response and getattr(response, "choices", None):
                msg = response.choices[0].message
                content = getattr(msg, "content", "") or ""
                # Some OpenAI models expose reasoning_content; default to ""
                reasoning_content = getattr(msg, "reasoning_content", "") or ""

            print(f"OpenAI Response: {content}")
            return content, reasoning_content

        except Exception as e:
            print(f"OpenAI API Error: {str(e)}")
            return "", ""

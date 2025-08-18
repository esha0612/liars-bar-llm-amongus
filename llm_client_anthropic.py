# llm_client_anthropic.py
import os
from typing import Tuple, List, Dict, Optional
import anthropic

ANTHROPIC_API_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", None)

class LLMClientAnthropic:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = ANTHROPIC_API_BASE_URL):
        """Initialize Anthropic client"""
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=base_url
        )

    def _to_anthropic(self, messages: List[Dict[str, str]]) -> Tuple[Optional[str], List[Dict[str, str]]]:
        """Convert OpenAI-style messages to Anthropic Messages API format."""
        system = None
        converted = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system = f"{system}\n{content}" if system else content
            elif role in ("user", "assistant"):
                converted.append({"role": role, "content": content})
            else:
                converted.append({"role": "user", "content": content})
        return system, converted

    def chat(self, messages: List[Dict[str, str]], model: str = "claude-3-5-sonnet-latest") -> Tuple[str, str]:
        """Interact with Anthropic (Claude)
        
        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            model: Anthropic model to use
        
        Returns:
            tuple: (content, reasoning_content)
        """
        try:
            print(f"Anthropic Request: {messages}")

            system, msg_list = self._to_anthropic(messages)
            response = self.client.messages.create(
                model=model,
                system=system,
                messages=msg_list,
                temperature=0.7,
                max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048")),
            )

            # Concatenate text blocks from Claude response
            content_parts: List[str] = []
            for block in getattr(response, "content", []) or []:
                if getattr(block, "type", "") == "text":
                    content_parts.append(getattr(block, "text", "") or "")
            content = "\n".join(content_parts).strip()

            reasoning_content = ""  # Anthropic doesn't generally expose a separate reasoning field

            print(f"Anthropic Response: {content}")
            return content, reasoning_content

        except Exception as e:
            print(f"Anthropic API Error: {str(e)}")
            return "", ""

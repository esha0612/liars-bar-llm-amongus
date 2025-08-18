# multi_llm_client.py
import os
from typing import List, Dict, Tuple, Optional

# Import your helpers (each with .chat(messages, model) -> (content, reasoning))
# Make sure these filenames/names match your project:
from llm_client_openai import LLMClientOpenAI
from llm_client_anthropic import LLMClientAnthropic
from llm_client_ollama import LLMClientOllama


# Defaults you can override with env vars
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.1")
OPENAI_ENABLED = os.getenv("OPENAI_ENABLED", "auto")  # "auto" | "on" | "off"
ANTHROPIC_ENABLED = os.getenv("ANTHROPIC_ENABLED", "auto")  # "auto" | "on" | "off"


class LLMRouter:
    """
    Unified client/router for OpenAI, Anthropic (Claude), and Ollama with graceful fallback.

    Routing options:
      - Prefix routing:
          model="openai/gpt-4o-mini"
          model="claude/claude-3-5-sonnet-latest"  (or "anthropic/...")
          model="ollama/llama3.1"
      - Explicit provider:
          chat(messages, model="gpt-4o-mini", provider="openai")
          chat(messages, model="claude-3-5-sonnet-latest", provider="anthropic")
          chat(messages, model="llama3.1", provider="ollama")

    Behavior:
      - If OpenAI/Anthropic are not configured (e.g., no API key), they are skipped.
      - When a requested provider is unavailable, we log and FALL BACK to Ollama.
      - Return shape is always: (content, reasoning_content)
    """

    def __init__(
        self,
        openai: Optional[LLMClientOpenAI] = None,
        anthropic: Optional[LLMClientAnthropic] = None,
        ollama: Optional[LLMClientOllama] = None,
    ):
        self._ollama = self._init_ollama(ollama)
        self._openai = self._init_openai(openai)
        self._anthropic = self._init_anthropic(anthropic)

    # ---------------------- init helpers ----------------------

    def _init_ollama(self, instance: Optional[LLMClientOllama]) -> LLMClientOllama:
        try:
            return instance or LLMClientOllama()
        except Exception as e:
            print(f"[Router] Ollama init failed: {e}")
            # In practice you'd probably want this to raise, but we keep parity with the others:
            raise

    def _env_truthy(self, name: str, default: str) -> str:
        v = (os.getenv(name, default) or "").strip().lower()
        return v

    def _init_openai(self, instance: Optional[LLMClientOpenAI]) -> Optional[LLMClientOpenAI]:
        mode = self._env_truthy("OPENAI_ENABLED", OPENAI_ENABLED)  # "auto"|"on"|"off"
        if instance is not None:
            # Caller-provided client wins
            return instance

        if mode == "off":
            print("[Router] OpenAI disabled via OPENAI_ENABLED=off")
            return None

        # auto/on: require an API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[Router] OpenAI not configured (missing OPENAI_API_KEY) — skipping")
            return None

        try:
            return LLMClientOpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))
        except Exception as e:
            print(f"[Router] OpenAI init failed: {e} — skipping")
            return None

    def _init_anthropic(self, instance: Optional[LLMClientAnthropic]) -> Optional[LLMClientAnthropic]:
        mode = self._env_truthy("ANTHROPIC_ENABLED", ANTHROPIC_ENABLED)  # "auto"|"on"|"off"
        if instance is not None:
            return instance

        if mode == "off":
            print("[Router] Anthropic disabled via ANTHROPIC_ENABLED=off")
            return None

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("[Router] Anthropic not configured (missing ANTHROPIC_API_KEY) — skipping")
            return None

        try:
            return LLMClientAnthropic(api_key=api_key, base_url=os.getenv("ANTHROPIC_BASE_URL"))
        except Exception as e:
            print(f"[Router] Anthropic init failed: {e} — skipping")
            return None

    # ---------------------- routing ----------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Route to a provider and make a chat call.

        Args:
            messages: [{"role": "...", "content": "..."}]
            model: either plain model name or prefixed:
                   "openai/...", "claude/...", "anthropic/...", "ollama/..."
            provider: Optional explicit provider: "openai" | "anthropic"|"claude" | "ollama"|"local"

        Returns:
            (content, reasoning_content)
        """
        # 1) Explicit provider
        if provider:
            p = provider.lower()
            if p in ("openai", "oai"):
                return self._safe_chat(self._openai, messages, model, fallback="openai")
            if p in ("anthropic", "claude"):
                return self._safe_chat(self._anthropic, messages, model, fallback="anthropic")
            if p in ("ollama", "local"):
                return self._safe_chat(self._ollama, messages, model, fallback="ollama")
            print(f"[Router] Unknown provider '{provider}' — falling back to Ollama")
            return self._safe_chat(self._ollama, messages, self._default_ollama_model(model), fallback="ollama")

        # 2) Prefix routing
        if model.startswith("openai/"):
            return self._safe_chat(self._openai, messages, model.split("/", 1)[1], fallback="openai")
        if model.startswith("claude/") or model.startswith("anthropic/"):
            return self._safe_chat(self._anthropic, messages, model.split("/", 1)[1], fallback="anthropic")
        if model.startswith("ollama/"):
            return self._safe_chat(self._ollama, messages, model.split("/", 1)[1], fallback="ollama")

        # 3) No provider/prefix: try OpenAI -> Anthropic -> Ollama
        content, reasoning = self._try_provider(self._openai, messages, model, tag="OpenAI")
        if content or reasoning:
            return content, reasoning

        content, reasoning = self._try_provider(self._anthropic, messages, model, tag="Anthropic")
        if content or reasoning:
            return content, reasoning

        # Final fallback
        return self._safe_chat(self._ollama, messages, self._default_ollama_model(model), fallback="ollama")

    # ---------------------- helpers ----------------------

    def _default_ollama_model(self, requested_model: str) -> str:
        # If the requested model was clearly not an Ollama model, fall back to a sensible default.
        # Otherwise, pass through the requested one.
        if any(requested_model.startswith(prefix) for prefix in ("openai/", "claude/", "anthropic/")):
            return OLLAMA_DEFAULT_MODEL
        return requested_model or OLLAMA_DEFAULT_MODEL

    def _try_provider(
        self,
        client,
        messages: List[Dict[str, str]],
        model: str,
        tag: str,
    ) -> Tuple[str, str]:
        if client is None:
            print(f"[Router] {tag} unavailable — skipping")
            return "", ""
        try:
            return client.chat(messages, model)
        except Exception as e:
            print(f"[Router] {tag} call failed: {e} — continuing to next provider")
            return "", ""

    def _safe_chat(
        self,
        client,
        messages: List[Dict[str, str]],
        model: str,
        fallback: str,
    ) -> Tuple[str, str]:
        """
        Call a client if available. If not (or if it errors), fall back to Ollama.
        """
        if client is not None:
            try:
                return client.chat(messages, model)
            except Exception as e:
                print(f"[Router] {fallback.capitalize()} call failed: {e} — falling back to Ollama")

        # Always fall back to Ollama
        try:
            return self._ollama.chat(messages, self._default_ollama_model(model))
        except Exception as e:
            # At this point even Ollama failed; return empty but don't crash the game loop.
            print(f"[Router] Ollama fallback failed: {e}")
            return "", ""

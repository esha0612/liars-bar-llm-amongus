# multi_llm_client.py
import os
from typing import List, Dict, Tuple, Optional

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
        print("✅ Loaded environment variables from .env file manually")
    except FileNotFoundError:
        print("⚠️  No .env file found. Make sure to set environment variables manually.")
    except Exception as e:
        print(f"⚠️  Error loading .env file: {e}")

# Import your helpers (each with .chat(messages, model) -> (content, reasoning))
# Make sure these filenames/names match your project:
from llm_client_openai import LLMClientOpenAI
from llm_client_ollama import LLMClientOllama


# Defaults you can override with env vars
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.1")
OPENAI_ENABLED = os.getenv("OPENAI_ENABLED", "auto")  # "auto" | "on" | "off"


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
    
    # Class-level flags to ensure debug messages are only printed once
    _api_key_logged = False
    _base_url_logged = False

    def __init__(
        self,
        openai: Optional[LLMClientOpenAI] = None,
        ollama: Optional[LLMClientOllama] = None
    ):
        self._ollama = self._init_ollama(ollama)
        self._openai = self._init_openai(openai)

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
            print("[Router] Make sure your .env file contains: OPENAI_API_KEY=your_actual_api_key")
            return None
        
        # Debug: Show API key status only once (first few characters only)
        if not LLMRouter._api_key_logged:
            if api_key and len(api_key) > 10:
                print(f"[Router] OpenAI API key found")
            else:
                print(f"[Router] OpenAI API key found but seems invalid (length: {len(api_key) if api_key else 0})")
            LLMRouter._api_key_logged = True

        try:
            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url and not LLMRouter._base_url_logged:
                print(f"[Router] Using OpenAI base URL: {base_url}")
                LLMRouter._base_url_logged = True
            return LLMClientOpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            print(f"[Router] OpenAI init failed: {e} — skipping")
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
           
            if p in ("ollama", "local"):
                return self._safe_chat(self._ollama, messages, model, fallback="ollama")
            print(f"[Router] Unknown provider '{provider}' — falling back to Ollama")
            return self._safe_chat(self._ollama, messages, self._default_ollama_model(model), fallback="ollama")

        # 2) Prefix routing
        if model.startswith("openai/"):
            return self._safe_chat(self._openai, messages, model.split("/", 1)[1], fallback="openai")
      
        if model.startswith("ollama/"):
            return self._safe_chat(self._ollama, messages, model.split("/", 1)[1], fallback="ollama")

        # 3) No provider/prefix: try OpenAI -> Anthropic -> Ollama
        
        # Final fallback
        return self._safe_chat(self._ollama, messages, self._default_ollama_model(model), fallback="ollama")

    # ---------------------- helpers ----------------------

    def _default_ollama_model(self, requested_model: str) -> str:
        # If the requested model was clearly not an Ollama model, fall back to a sensible default.
        # Otherwise, pass through the requested one.
        if any(requested_model.startswith(prefix) for prefix in ("openai/", "claude/")):
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
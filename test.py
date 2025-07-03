import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-coder:1.3b"

def query_llm(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"[Error]: {e}"

def llm_self_talk(turns=5):
    message_a = "Hi, pretend you are an animal, and I am a human. Let's have a conversation about our lives."
    for i in range(turns):
        print(f"\n🧠 A says: {message_a}")
        message_b = query_llm(message_a)
        print(f"🤖 B replies: {message_b}")

        message_a = query_llm(message_b)
        time.sleep(1)

# Start the simulation
llm_self_talk(turns=5)

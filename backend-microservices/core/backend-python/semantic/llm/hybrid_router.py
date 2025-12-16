from semantic.llm.groq_client import GroqClient
from semantic.llm.ollama_client import OllamaClient

import re

class HybridLLMRouter:
    def __init__(self):
        self.groq = GroqClient()
        self.ollama = OllamaClient()

    def is_sensitive(self, text: str) -> bool:
        SENSITIVE_PATTERNS = [
            r"\bpassword\b",
            r"\bsecret\b",
            r"\btoken\b",
            r"\bapi[-_ ]?key\b",
            r"\bconfidential\b",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in SENSITIVE_PATTERNS)

    def chat(self, messages, model=None, force_local=False):
        text = " ".join(m["content"] for m in messages if m["role"] == "user")

        # Force Ollama for sensitive or local-only mode
        if force_local or self.is_sensitive(text):
            return self.ollama.chat(messages, model)

        # Try Groq → fallback to Ollama
        try:
            return self.groq.chat(messages, model)
        except RuntimeError:
            return self.ollama.chat(messages, model)

    def generate(self, prompt, model=None, force_local=False):
        if force_local or self.is_sensitive(prompt):
            return self.ollama.generate(prompt, model)

        try:
            return self.groq.generate(prompt, model)
        except RuntimeError:
            return self.ollama.generate(prompt, model)

"""
Unified LLM client for Anthropic and Gemini.
Simpler than Persuasion Asymmetry's version: no Groq, no batch API.
"""

import os
import time
import threading
from collections import deque
from typing import Optional

from anthropic import Anthropic, APIError as AnthropicAPIError
import google.generativeai as genai

from config import MODELS, RATE_LIMITS_RPM, MAX_RETRIES, RETRY_DELAY_S


# ---------- Rate limiter ----------
class RateLimiter:
    """Client-side RPM limiter with rolling 60s window."""
    def __init__(self, rpm: int):
        self.rpm = rpm
        self.window = deque()
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            while self.window and now - self.window[0] > 60:
                self.window.popleft()
            if len(self.window) >= self.rpm:
                sleep_for = 60 - (now - self.window[0]) + 0.05
                time.sleep(max(0.0, sleep_for))
                now = time.time()
                while self.window and now - self.window[0] > 60:
                    self.window.popleft()
            self.window.append(time.time())


_LIMITERS = {
    "anthropic": RateLimiter(RATE_LIMITS_RPM["anthropic"]),
    "gemini":    RateLimiter(RATE_LIMITS_RPM["gemini"]),
}


# ---------- Clients ----------
_anthropic_client: Optional[Anthropic] = None
_gemini_configured = False


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _anthropic_client = Anthropic(api_key=key)
    return _anthropic_client


def _gemini():
    global _gemini_configured
    if not _gemini_configured:
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set")
        genai.configure(api_key=key)
        _gemini_configured = True


# ---------- Unified call ----------
def call_model(
    model_key: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float = 0.7,
) -> str:
    """
    Call any registered model. Returns plain text output.
    Blocks on rate limits. Retries on transient errors.
    """
    if model_key not in MODELS:
        raise ValueError(f"Unknown model key: {model_key}")
    spec = MODELS[model_key]
    provider = spec["provider"]
    model_id = spec["model_id"]

    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            _LIMITERS[provider].acquire()
            if provider == "anthropic":
                return _call_anthropic(model_id, system, user, max_tokens, temperature)
            elif provider == "gemini":
                return _call_gemini(model_id, system, user, max_tokens, temperature)
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_S * (attempt + 1))
                continue
            raise
    raise last_err


def _call_anthropic(model_id, system, user, max_tokens, temperature):
    kwargs = dict(
        model=model_id,
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=max_tokens,
    )
    if "opus-4-7" not in model_id:
        kwargs["temperature"] = temperature
    resp = _anthropic().messages.create(**kwargs)
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def _call_gemini(model_id, system, user, max_tokens, temperature):
    _gemini()
    model = genai.GenerativeModel(
        model_name=model_id,
        system_instruction=system,
    )
    resp = model.generate_content(
        user,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    # Gemini 2.5 thinking-mode safety: handle truncation + empty responses
    try:
        return (resp.text or "").strip()
    except Exception:
        # Some finish_reasons (MAX_TOKENS, SAFETY) make .text raise
        out = []
        for cand in getattr(resp, "candidates", []) or []:
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", []) or []:
                txt = getattr(part, "text", None)
                if txt:
                    out.append(txt)
        return "".join(out).strip()

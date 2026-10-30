"""Shared LLM client for the Groq (OpenAI-compatible) gateway.

The API key is read from the environment only. A local .env file is loaded
once as a convenience; hardcoded keys are never used.
"""

import os
import time
from pathlib import Path

from openai import OpenAI

BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "openai/gpt-oss-20b"
MODEL_FALLBACKS = ("openai/gpt-oss-120b", "qwen/qwen3.8-27b")
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

_env_loaded = False


class LLMUnavailable(RuntimeError):
    """Raised when the configured model cannot be reached."""


def _load_env_file():
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    if not ENV_FILE.exists():
        return
    try:
        for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except OSError:
        pass


def get_api_key():
    _load_env_file()
    return os.environ.get("GROQ_API_KEY", "").strip()


def get_client():
    api_key = get_api_key()
    if not api_key:
        raise LLMUnavailable(
            "GROQ_API_KEY is not set. Add it to aptitude_platform/.env or export it in the shell."
        )
    return OpenAI(base_url=BASE_URL, api_key=api_key)


def _is_rate_limit(exc):
    return getattr(exc, "status_code", None) == 429 or "rate limit" in str(exc).lower()


def chat(prompt, temperature=0.7, json_mode=False, model=MODEL, retries=4):
    """Send one prompt and return the raw text response.

    Retries transient failures with capped backoff. A rate-limited model is
    skipped immediately in favour of the next configured fallback, so one
    exhausted quota does not take the whole app down.
    """
    last_error = None
    models = [model] + [name for name in MODEL_FALLBACKS if name != model]
    for model_name in models:
        for attempt in range(retries):
            try:
                kwargs = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                response = get_client().chat.completions.create(**kwargs)
                return (response.choices[0].message.content or "").strip()
            except Exception as exc:  # noqa: BLE001 - surface a single friendly error
                last_error = exc
                if _is_rate_limit(exc):
                    break
                if attempt < retries - 1:
                    time.sleep(min(2 * (attempt + 1), 10))
    raise LLMUnavailable(f"Model request failed: {last_error}")

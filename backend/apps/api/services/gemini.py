# apps/api/services/gemini.py

import os
import time
import re
import threading
from pathlib import Path
from typing import Any, List, Optional, Dict

from google import genai
from google.genai import errors as genai_errors

# Thread-local storage so each thread gets its own client (thread-safe for parallel calls)
_thread_local = threading.local()

# Global concurrency cap to avoid 429 when you run parallel PDFs/companies
# Set env: GEMINI_MAX_CONCURRENCY=8 (recommended 6-12)
_GEMINI_SEM = threading.BoundedSemaphore(int(os.getenv("GEMINI_MAX_CONCURRENCY", "8")))


def _get_client():
    """
    Thread-safe Gemini client getter.
    Each thread gets its own client instance.
    """
    client = getattr(_thread_local, "client", None)
    if client is not None:
        return client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in .env (GEMINI_API_KEY=...)")

    _thread_local.client = genai.Client(api_key=api_key)
    return _thread_local.client


def upload_file_to_gemini(
    file_path: str,
    wait_active: bool = True,
    max_wait_sec: int = 90,
):
    """
    Upload local file (PDF) to Gemini Files API and return the File object.
    If wait_active=True, waits until state becomes ACTIVE (or timeout).
    """
    client = _get_client()

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Gate uploads too (helps when many threads upload together)
    with _GEMINI_SEM:
        f = client.files.upload(file=p)

    if not wait_active:
        return f

    name = getattr(f, "name", None)
    if not name:
        return f

    start = time.time()
    while time.time() - start < max_wait_sec:
        try:
            with _GEMINI_SEM:
                f2 = client.files.get(name=name)
            state = str(getattr(f2, "state", "")).upper()
            if state == "ACTIVE":
                return f2
        except Exception:
            pass
        time.sleep(1)

    return f


# ✅ Backward compatible alias (older code imports this)
def upload_pdf_to_gemini(file_path: str, wait_active: bool = True, max_wait_sec: int = 90):
    """
    Alias for older code that expects upload_pdf_to_gemini().
    """
    return upload_file_to_gemini(file_path, wait_active=wait_active, max_wait_sec=max_wait_sec)


def _extract_text(response: Any) -> str:
    """
    Some responses have non-text parts; this tries to safely return only text.
    """
    txt = getattr(response, "text", None)
    if txt:
        return txt

    try:
        candidates = getattr(response, "candidates", None) or []
        out = []
        for c in candidates:
            content = getattr(c, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                t = getattr(part, "text", None)
                if t:
                    out.append(t)
        return "\n".join(out).strip()
    except Exception:
        return ""


def _extract_usage(response: Any) -> Dict[str, Any]:
    """
    Best-effort extraction of token usage from different google-genai SDK response shapes.

    Returns normalized fields when possible:
      {
        "promptTokens": int,
        "outputTokens": int,
        "totalTokens": int
      }

    If not found, returns {}.
    """
    if response is None:
        return {}

    # Newer style often: response.usage_metadata or response.usageMetadata
    usage = getattr(response, "usage_metadata", None) or getattr(response, "usageMetadata", None)
    if usage is not None:
        # Try common attribute names
        pt = getattr(usage, "prompt_token_count", None) or getattr(usage, "promptTokenCount", None) or getattr(usage, "input_token_count", None) or getattr(usage, "inputTokenCount", None)
        ot = getattr(usage, "candidates_token_count", None) or getattr(usage, "candidatesTokenCount", None) or getattr(usage, "output_token_count", None) or getattr(usage, "outputTokenCount", None)
        tt = getattr(usage, "total_token_count", None) or getattr(usage, "totalTokenCount", None)

        def _to_int(v):
            try:
                return int(v)
            except Exception:
                return 0

        pt_i = _to_int(pt)
        ot_i = _to_int(ot)
        tt_i = _to_int(tt) if tt is not None else (pt_i + ot_i)

        out = {
            "promptTokens": pt_i,
            "outputTokens": ot_i,
            "totalTokens": tt_i,
        }
        # only return if anything exists
        if out["promptTokens"] or out["outputTokens"] or out["totalTokens"]:
            return out

    # Some SDK versions might attach usage into response as dict-like
    # or nested fields. We safely try a couple more patterns.
    try:
        d = response.__dict__ if hasattr(response, "__dict__") else {}
        for key in ("usage", "usageMetadata", "usage_metadata"):
            if key in d and isinstance(d[key], dict):
                u = d[key]
                pt = u.get("promptTokens") or u.get("prompt_token_count") or u.get("inputTokens") or u.get("input_token_count") or 0
                ot = u.get("outputTokens") or u.get("candidates_token_count") or u.get("candidateTokens") or u.get("output_token_count") or 0
                tt = u.get("totalTokens") or u.get("total_token_count") or (int(pt) + int(ot))
                return {
                    "promptTokens": int(pt) if str(pt).isdigit() else 0,
                    "outputTokens": int(ot) if str(ot).isdigit() else 0,
                    "totalTokens": int(tt) if str(tt).isdigit() else (0 if tt is None else int(tt)),
                }
    except Exception:
        pass

    return {}


def _sleep_from_retry_message(msg: str, default_sec: int = 10) -> int:
    """
    Parses retry delay seconds from Gemini quota error messages.
    """
    if not msg:
        return default_sec

    m = re.search(r"retry in\s+([\d.]+)s", msg, re.IGNORECASE)
    if m:
        try:
            return max(1, int(float(m.group(1))))
        except Exception:
            pass

    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", msg, re.IGNORECASE)
    if m:
        try:
            return max(1, int(m.group(1)))
        except Exception:
            pass

    return default_sec


def _generate_content_compat(client, model: str, contents: Any, temperature: float):
    """
    Compat layer for google-genai SDK differences:
    - some versions accept generation_config=
    - some accept config=
    - some accept neither
    """
    # 1) Try generation_config (newer style)
    try:
        return client.models.generate_content(
            model=model,
            contents=contents,
            generation_config={"temperature": temperature},
        )
    except TypeError:
        pass

    # 2) Try config (some versions use config)
    try:
        return client.models.generate_content(
            model=model,
            contents=contents,
            config={"temperature": temperature},
        )
    except TypeError:
        pass

    # 3) Fallback: no config at all
    return client.models.generate_content(
        model=model,
        contents=contents,
    )


def generate_with_gemini(
    contents: Any,
    model: str = "gemini-3-flash-preview",
    max_retries: int = 3,
    temperature: float = 0.1,
) -> Any:
    """
    Generic Gemini call.

    Returns (backward compatible):
      - dict: {"text": "...", "usage": {...}, "model": "..."}  (preferred)
      - raises on fatal errors

    `contents` can be:
      - a string prompt
      - a list like [uploaded_file, prompt] OR [prompt, uploaded_file] OR [file1, file2, prompt]
    """
    client = _get_client()
    last_err: Optional[Exception] = None

    for _ in range(max_retries + 1):
        try:
            t0 = time.time()
            with _GEMINI_SEM:
                response = _generate_content_compat(client, model=model, contents=contents, temperature=temperature)
            t1 = time.time()

            text = _extract_text(response)
            usage = _extract_usage(response)

            return {
                "text": text,
                "usage": usage,
                "model": model,
                "durationMs": int((t1 - t0) * 1000),
            }

        except genai_errors.ClientError as e:
            msg = str(e)

            # quota/rate limit
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                wait = _sleep_from_retry_message(msg, 10)
                time.sleep(wait)
                last_err = e
                continue

            # model not found / not allowed
            if "404" in msg or "NOT_FOUND" in msg:
                raise RuntimeError(
                    f"Model not found or not allowed: '{model}'. "
                    f"Try list_models() to see valid models for your key."
                )

            raise

        except Exception as e:
            last_err = e
            time.sleep(1)

    raise RuntimeError(f"Gemini call failed after retries: {last_err}")


def ask_gemini(prompt: str, model: str = "gemini-3-flash-preview") -> str:
    """
    Backward compatible function for views.py imports.
    Returns ONLY text (string), even though generate_with_gemini returns dict.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return ""
    out = generate_with_gemini(prompt, model=model)
    if isinstance(out, dict):
        return str(out.get("text", "") or "")
    return str(out or "")


def list_models() -> List[str]:
    """
    Debug helper: list available models for your API key.
    """
    client = _get_client()
    with _GEMINI_SEM:
        models = client.models.list()
    return [m.name for m in models]

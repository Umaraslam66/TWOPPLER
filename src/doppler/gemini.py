"""Thin, thread-safe wrapper around the Google AI Studio (google-genai) SDK.

Design points that matter for this task:

  * The API key is loaded from ``.env`` programmatically and never printed.
  * A single global counter enforces a HARD cap on total API requests. Every
    real request (including backoff retries) is counted; exceeding the cap
    raises :class:`CallCapExceeded` instead of spending more.
  * Transient 429/500/503 errors are retried with exponential backoff + jitter
    (up to ``MAX_ATTEMPTS`` per request); anything else raises immediately so a
    bad key / wrong model / exhausted quota stops the run fast.
  * ``temperature=0`` and a small output-token budget; thinking is disabled so
    the whole budget goes to the answer digit.
"""

from __future__ import annotations

import os
import random
import re
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

DEFAULT_MAX_CALLS = 600
DEFAULT_MAX_OUTPUT_TOKENS = 16
MAX_ATTEMPTS = 5

# Proactive client-side pacing. The free tier caps this model at ~15 requests
# per minute; one request every 5s (~12/min) stays comfortably under it so we
# almost never hit a 429, which keeps retry spend near zero. Sleeping to pace
# costs no API calls. Raise this if the key's quota is tighter.
DEFAULT_MIN_INTERVAL_S = 5.0

# Backoff schedule (seconds) for the rare 429/5xx that still slips through.
_BASE_DELAY = 5.0
_MAX_DELAY = 65.0
_JITTER = 1.0

# "Please retry in 11.28s" or "'retryDelay': '11s'" -> honor the server's hint.
_RETRY_DELAY_RE = re.compile(r"retry(?:Delay|\s+in)['\":\s]+([\d.]+)s", re.IGNORECASE)

_RETRYABLE_CODES = {429, 500, 503}
_RETRYABLE_STATUS = {
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "INTERNAL",
    "DEADLINE_EXCEEDED",
}

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CallCapExceeded(RuntimeError):
    """Raised when the global API-call cap would be exceeded."""


def _is_retryable(err: genai_errors.APIError) -> bool:
    code = getattr(err, "code", None)
    status = getattr(err, "status", None)
    if code in _RETRYABLE_CODES:
        return True
    if isinstance(status, str) and status.upper() in _RETRYABLE_STATUS:
        return True
    return isinstance(err, genai_errors.ServerError)


def _server_retry_delay(err: Exception) -> float | None:
    """Extract the server-suggested retry delay (seconds) from an error, if any."""
    match = _RETRY_DELAY_RE.search(str(err))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


class GeminiClient:
    """Sequential-or-parallel client with a hard global call cap."""

    def __init__(
        self,
        max_calls: int = DEFAULT_MAX_CALLS,
        temperature: float = 0.0,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
    ) -> None:
        load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")
        api_key = os.environ.get("GOOGLE_AI_STUDIO")
        self.model_name = os.environ.get("MODEL_NAME")
        if not api_key:
            raise RuntimeError("GOOGLE_AI_STUDIO is not set (checked env and .env).")
        if not self.model_name:
            raise RuntimeError("MODEL_NAME is not set (checked env and .env).")

        self._client = genai.Client(api_key=api_key)
        self.max_calls = int(max_calls)
        self.temperature = float(temperature)
        self.max_output_tokens = int(max_output_tokens)

        # No thinking_config: gemini-3.5-flash-lite rejects thinking_budget and,
        # with a thinking_level set, spends the whole token budget on hidden
        # thinking and returns no answer. Omitting it returns the digit directly.
        self._config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            candidate_count=1,
        )

        self._lock = threading.Lock()
        self._n_calls = 0
        self._n_retries = 0

        # Global request pacer (works across worker threads).
        self.min_interval_s = float(min_interval_s)
        self._pace_lock = threading.Lock()
        self._next_allowed = 0.0  # monotonic clock

    # -- counters ----------------------------------------------------------

    @property
    def n_calls(self) -> int:
        with self._lock:
            return self._n_calls

    @property
    def n_retries(self) -> int:
        with self._lock:
            return self._n_retries

    def _reserve_call(self) -> None:
        """Count one real request against the cap; raise if it would exceed."""
        with self._lock:
            if self._n_calls >= self.max_calls:
                raise CallCapExceeded(
                    f"API call cap of {self.max_calls} reached; aborting before "
                    "spending more."
                )
            self._n_calls += 1

    def _bump_retries(self) -> None:
        with self._lock:
            self._n_retries += 1

    def _pace(self) -> None:
        """Block until this thread's turn, keeping requests under the RPM cap."""
        with self._pace_lock:
            start = max(time.monotonic(), self._next_allowed)
            self._next_allowed = start + self.min_interval_s
        wait = start - time.monotonic()
        if wait > 0:
            time.sleep(wait)

    def _sleep_backoff(self, attempt: int, err: Exception | None = None) -> None:
        """Sleep before a retry: honor the server's retry hint, else exp backoff."""
        server = _server_retry_delay(err) if err is not None else None
        if server is not None:
            delay = min(server + random.uniform(0.0, _JITTER), _MAX_DELAY)
        else:
            delay = min(_BASE_DELAY * (2 ** (attempt - 1)), _MAX_DELAY)
            delay += random.uniform(0.0, _JITTER)
        time.sleep(delay)

    # -- generation --------------------------------------------------------

    def generate(self, prompt: str) -> tuple[str, int, int]:
        """Return ``(text, tokens_in, tokens_out)`` for a single prompt.

        Retries transient errors with backoff; every attempt counts against the
        global cap. Raises the underlying error if all attempts fail or a
        non-retryable error occurs, and :class:`CallCapExceeded` at the cap.
        """
        last_exc: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._reserve_call()
            self._pace()
            try:
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self._config,
                )
            except genai_errors.APIError as err:
                if _is_retryable(err) and attempt < MAX_ATTEMPTS:
                    self._bump_retries()
                    self._sleep_backoff(attempt, err)
                    last_exc = err
                    continue
                raise

            try:
                text = resp.text
            except Exception:  # noqa: BLE001 - some blocked responses raise on .text
                text = None
            text = (text or "").strip()

            usage = getattr(resp, "usage_metadata", None)
            tokens_in = int(getattr(usage, "prompt_token_count", 0) or 0)
            tokens_out = int(getattr(usage, "candidates_token_count", 0) or 0)
            return text, tokens_in, tokens_out

        # Exhausted retries on a retryable error.
        assert last_exc is not None
        raise last_exc

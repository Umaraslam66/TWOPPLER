"""Thin, thread-safe wrapper around the Google AI Studio (google-genai) SDK.

Design points that matter for this task:

  * The API key is loaded from ``.env`` programmatically and never printed.
  * A single global counter enforces a HARD cap on total API requests. Every
    real request (including backoff retries) is counted; exceeding the cap
    raises :class:`CallCapExceeded` instead of spending more.
  * Transient 429/500/503 errors are retried with exponential backoff + jitter
    (up to ``MAX_ATTEMPTS`` per request); anything else raises immediately so a
    bad key / wrong model / exhausted quota stops the run fast.
  * Safe for many worker threads: a shared token-bucket caps the request rate
    well under the account's RPM limit, and any 429 opens a global backoff
    window so the whole pool retreats together (not just the one thread).
  * ``temperature=0`` and a small output-token budget; thinking is disabled so
    the whole budget goes to the answer digit.
"""

from __future__ import annotations

import os
import random
import re
import sys
import threading
import time
from collections import deque
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

DEFAULT_MAX_CALLS = 600
DEFAULT_MAX_OUTPUT_TOKENS = 16
MAX_ATTEMPTS = 5

# Per-request timeout so a hung/half-open connection fails fast into the retry
# path instead of hanging for many minutes. google-genai's HttpOptions.timeout
# is in MILLISECONDS (verified against google-genai 2.14.0).
DEFAULT_TIMEOUT_MS = 90_000

# Official limits for gemini-3.5-flash-lite, read by the user from the Google AI
# Studio console on 2026-07-24: Tier 1 = 4,000 RPM, 4,000,000 TPM, 150,000 RPD.
OFFICIAL_LIMITS = (
    "gemini-3.5-flash-lite Tier 1: 4,000 RPM / 4,000,000 TPM / 150,000 RPD "
    "(console-verified 2026-07-24 by user)"
)

# Client-side request-per-minute guard: a token bucket capped well under the
# official 4,000 RPM (25% of it), deliberately gentle. At ~520 tokens/call this
# is < 600K TPM even at the ceiling, so TPM is never the binding limit, and
# 150K RPD means even a full 10K-call gate run is < 7% of the daily budget.
RPM_GUARD_PER_MIN = 1000       # sustained requests/minute ceiling (editable)
RPM_GUARD_BURST = 100          # token-bucket burst capacity (editable)

# Connection/transport-level failures that escape the SDK unwrapped (i.e. NOT as
# an APIError): the SDK only wraps HTTP *status* responses in APIError, so a
# dropped socket, read timeout, or protocol error surfaces as a raw httpx error.
# All of RemoteProtocolError / ConnectError / ReadError / ReadTimeout subclass
# httpx.HTTPError; builtin ConnectionError is OSError-based and separate. These
# are always transient -> retry with the same backoff as a 5xx.
_RETRYABLE_CONN_ERRORS = (httpx.HTTPError, ConnectionError)

# Optional extra per-request spacing. On paid Tier 1 we rely on the token-bucket
# RPM guard and the 429 throttle instead, so this defaults to 0 (no spacing).
DEFAULT_MIN_INTERVAL_S = 0.0

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


class _TokenBucket:
    """Thread-safe token bucket: caps sustained rate, allows a small burst."""

    def __init__(self, rate_per_sec: float, capacity: float) -> None:
        self._rate = float(rate_per_sec)
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._capacity, self._tokens + (now - self._last) * self._rate)
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate if self._rate > 0 else 0.05
            time.sleep(wait)


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


def _is_rate_limit(err: Exception) -> bool:
    """True for a 429 / RESOURCE_EXHAUSTED error (triggers the global throttle)."""
    code = getattr(err, "code", None)
    status = getattr(err, "status", None)
    return code == 429 or (isinstance(status, str)
                           and status.upper() == "RESOURCE_EXHAUSTED")


class GeminiClient:
    """Sequential-or-parallel client with a hard global call cap."""

    def __init__(
        self,
        max_calls: int = DEFAULT_MAX_CALLS,
        temperature: float = 0.0,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        rpm_guard: int = RPM_GUARD_PER_MIN,
        thinking_budget: int | None = None,
    ) -> None:
        load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")
        api_key = os.environ.get("GOOGLE_AI_STUDIO")
        self.model_name = os.environ.get("MODEL_NAME")
        if not api_key:
            raise RuntimeError("GOOGLE_AI_STUDIO is not set (checked env and .env).")
        if not self.model_name:
            raise RuntimeError("MODEL_NAME is not set (checked env and .env).")

        self.timeout_ms = int(timeout_ms)
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=self.timeout_ms),
        )
        self.max_calls = int(max_calls)
        self.temperature = float(temperature)
        self.max_output_tokens = int(max_output_tokens)

        # ``thinking_budget=None`` (the default) sends NO thinking_config, which
        # is the setting every existing caller was built and measured on:
        # gemini-3.5-flash-lite rejects thinking_budget and, with a
        # thinking_level set, spends the whole token budget on hidden thinking
        # and returns no answer. Omitting it returns the digit directly.
        #
        # ``thinking_budget=0`` sends an EXPLICIT disable. It exists for models
        # that think BY DEFAULT, where omitting the config is not neutral:
        # gemini-3.5-flash charges hidden thinking against max_output_tokens,
        # and the OE-1 judge probe measured 243 of 256 and then 980 of 1024
        # tokens going to thoughts, both ending MAX_TOKENS with the visible
        # reply cut mid-sentence -- and the label itself moved between the two
        # budgets at temperature 0. Opt-in rather than default so no existing
        # caller's measured behaviour changes.
        self.thinking_budget = thinking_budget
        self._config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            candidate_count=1,
            **({} if thinking_budget is None else {
                "thinking_config": types.ThinkingConfig(
                    thinking_budget=int(thinking_budget))}),
        )

        self._lock = threading.Lock()
        self._n_calls = 0
        self._n_retries = 0

        # Optional per-request spacing (default 0 on Tier 1).
        self.min_interval_s = float(min_interval_s)
        self._pace_lock = threading.Lock()
        self._next_allowed = 0.0  # monotonic clock

        # Client-side RPM guard (token bucket) shared across worker threads.
        self.rpm_guard = int(rpm_guard)
        self._bucket = _TokenBucket(self.rpm_guard / 60.0, RPM_GUARD_BURST)

        # Global 429 throttle: on a rate-limit the whole pool backs off together.
        self._throttle_lock = threading.Lock()
        self._throttle_until = 0.0  # monotonic clock
        self._req_times: deque[float] = deque()  # request starts, for effective RPM

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

    def _backoff_delay(self, attempt: int, err: Exception | None = None) -> float:
        """Seconds to back off: the server's retry hint if present, else exp."""
        server = _server_retry_delay(err) if err is not None else None
        if server is not None:
            return min(server + random.uniform(0.0, _JITTER), _MAX_DELAY)
        return min(_BASE_DELAY * (2 ** (attempt - 1)), _MAX_DELAY) \
            + random.uniform(0.0, _JITTER)

    def _sleep_backoff(self, attempt: int, err: Exception | None = None) -> None:
        """Per-request backoff (used for non-rate-limit transient errors)."""
        time.sleep(self._backoff_delay(attempt, err))

    def _rpm_acquire(self) -> None:
        """Block on the token bucket, then record the request time for RPM."""
        self._bucket.acquire()
        now = time.monotonic()
        with self._throttle_lock:
            self._req_times.append(now)
            cutoff = now - 60.0
            while self._req_times and self._req_times[0] < cutoff:
                self._req_times.popleft()

    def _effective_rpm(self) -> int:
        now = time.monotonic()
        with self._throttle_lock:
            cutoff = now - 60.0
            while self._req_times and self._req_times[0] < cutoff:
                self._req_times.popleft()
            return len(self._req_times)

    def _await_throttle(self) -> None:
        """Wait out any active global 429 backoff window."""
        while True:
            with self._throttle_lock:
                wait = self._throttle_until - time.monotonic()
            if wait <= 0:
                return
            time.sleep(min(wait, 1.0))

    def _trip_throttle(self, delay: float) -> None:
        """Open/extend the global backoff window and log a [ratelimit] line."""
        with self._throttle_lock:
            self._throttle_until = max(self._throttle_until,
                                       time.monotonic() + delay)
        print(f"[ratelimit] 429; global backoff {delay:.1f}s; "
              f"effective RPM ~{self._effective_rpm()}", file=sys.stderr)

    # -- generation --------------------------------------------------------

    def generate(self, prompt: str) -> tuple[str, int, int]:
        """Return ``(text, tokens_in, tokens_out)`` for a single prompt.

        Retries transient errors with backoff; every attempt counts against the
        global cap. Raises the underlying error if all attempts fail or a
        non-retryable error occurs, and :class:`CallCapExceeded` at the cap.
        """
        last_exc: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._await_throttle()   # wait out any active global 429 backoff
            self._rpm_acquire()      # client-side RPM guard (token bucket)
            self._reserve_call()     # hard call cap
            self._pace()             # optional extra spacing (default none)
            try:
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self._config,
                )
            except genai_errors.APIError as err:
                if _is_retryable(err) and attempt < MAX_ATTEMPTS:
                    self._bump_retries()
                    if _is_rate_limit(err):
                        # Pool-wide backoff: every worker waits at the gate.
                        self._trip_throttle(self._backoff_delay(attempt, err))
                    else:
                        self._sleep_backoff(attempt, err)
                    last_exc = err
                    continue
                raise
            except _RETRYABLE_CONN_ERRORS as err:
                # Dropped socket / read timeout / protocol error: always transient.
                if attempt < MAX_ATTEMPTS:
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

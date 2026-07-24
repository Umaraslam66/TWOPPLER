"""GeminiClient tests. The underlying SDK is fully faked -> zero real calls."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import doppler.gemini as gm


def _fake_usage(t_in=11, t_out=1):
    return SimpleNamespace(prompt_token_count=t_in, candidates_token_count=t_out)


class _FakeModels:
    """Records prompts and returns scripted responses/exceptions."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

    def generate_content(self, *, model, contents, config):
        self.calls += 1
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item, usage_metadata=_fake_usage())


class _FakeAPIError(gm.genai_errors.APIError):
    def __init__(self, code, status=None):
        self.code = code
        self.status = status
        self.message = "fake error"


@pytest.fixture
def patched(monkeypatch):
    """Return a factory that builds a GeminiClient over a scripted fake SDK."""
    monkeypatch.setenv("GOOGLE_AI_STUDIO", "fake-key-not-real")
    monkeypatch.setenv("MODEL_NAME", "fake-model")
    # No real sleeping in tests: neutralise backoff, pacing, RPM bucket, throttle.
    monkeypatch.setattr(gm.GeminiClient, "_sleep_backoff", lambda *a, **k: None)
    monkeypatch.setattr(gm.GeminiClient, "_pace", lambda self: None)
    monkeypatch.setattr(gm.GeminiClient, "_rpm_acquire", lambda self: None)
    monkeypatch.setattr(gm.GeminiClient, "_await_throttle", lambda self: None)

    def factory(script, **kwargs):
        kwargs.setdefault("min_interval_s", 0.0)
        fake_models = _FakeModels(script)
        monkeypatch.setattr(
            gm.genai, "Client", lambda **kw: SimpleNamespace(models=fake_models)
        )
        client = gm.GeminiClient(**kwargs)
        return client, fake_models

    return factory


def test_generate_returns_text_and_tokens(patched):
    client, fake = patched(["5"])
    text, t_in, t_out = client.generate("hi")
    assert text == "5"
    assert (t_in, t_out) == (11, 1)
    assert client.n_calls == 1
    assert fake.calls == 1


def test_counter_increments(patched):
    client, _ = patched(["1", "2", "3"])
    for _ in range(3):
        client.generate("x")
    assert client.n_calls == 3


def test_cap_enforced(patched):
    client, _ = patched(["1", "2", "3"], max_calls=2)
    client.generate("x")
    client.generate("x")
    with pytest.raises(gm.CallCapExceeded):
        client.generate("x")
    assert client.n_calls == 2  # the blocked attempt did not count


def test_retryable_error_then_success(patched):
    client, fake = patched([_FakeAPIError(429), "6"])
    text, _, _ = client.generate("x")
    assert text == "6"
    assert client.n_retries == 1
    assert client.n_calls == 2  # both attempts counted against the cap


def test_nonretryable_error_raises(patched):
    client, _ = patched([_FakeAPIError(400)])
    with pytest.raises(gm.genai_errors.APIError):
        client.generate("x")
    assert client.n_calls == 1


def test_retries_exhaust_and_raise(patched):
    script = [_FakeAPIError(503) for _ in range(gm.MAX_ATTEMPTS)]
    client, _ = patched(script)
    with pytest.raises(gm.genai_errors.APIError):
        client.generate("x")
    assert client.n_calls == gm.MAX_ATTEMPTS


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Please retry in 11.284834957s.", 11.284834957),
        ("'retryDelay': '11s'", 11.0),
        ("no delay here", None),
    ],
)
def test_server_retry_delay_parsing(message, expected):
    got = gm._server_retry_delay(RuntimeError(message))
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected)


def test_rate_limit_trips_global_throttle(patched):
    # A 429 opens the pool-wide backoff window (then the retry succeeds).
    client, _ = patched([_FakeAPIError(429), "6"])
    text, _, _ = client.generate("x")
    assert text == "6"
    assert client.n_retries == 1
    assert client._throttle_until > 0.0  # global throttle opened


def test_is_rate_limit_predicate():
    assert gm._is_rate_limit(_FakeAPIError(429))
    assert gm._is_rate_limit(_FakeAPIError(400, status="RESOURCE_EXHAUSTED"))
    assert not gm._is_rate_limit(_FakeAPIError(503))


def test_token_bucket_bursts_then_rate_limits():
    import time
    bucket = gm._TokenBucket(rate_per_sec=20.0, capacity=2)
    t0 = time.monotonic()
    bucket.acquire()
    bucket.acquire()          # 2-token burst is ~instant
    assert time.monotonic() - t0 < 0.03
    t1 = time.monotonic()
    bucket.acquire()          # 3rd waits ~1/20s for a refill
    assert time.monotonic() - t1 >= 0.03

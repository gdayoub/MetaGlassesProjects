import base64
import json

import httpx
import pytest
from google import genai
from lensagent.config import Settings
from lensagent.errors import AppError
from lensagent.images import SafeImage
from lensagent.providers import GeminiProvider, OllamaProvider, Turn


def mock_gemini(monkeypatch, handler):
    real_client = genai.Client

    def client(**kwargs):
        options = kwargs["http_options"]
        options.httpx_client = httpx.Client(transport=httpx.MockTransport(handler))
        return real_client(**kwargs)

    monkeypatch.setattr("lensagent.providers.genai.Client", client)


def test_actual_gemini_sdk_serializes_text_image_history_and_limits(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"role": "model", "parts": [{"text": "A blue square."}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 22, "candidatesTokenCount": 4},
            },
        )

    mock_gemini(monkeypatch, handler)
    settings = Settings(api_token="t" * 32, gemini_enabled=True, gemini_api_key="test-key")
    result = GeminiProvider(settings).generate(
        [
            Turn("user", "Previous question"),
            Turn("assistant", "Previous answer"),
            Turn("user", "Describe"),
        ],
        SafeImage(b"JPEG-data", "image/jpeg", 1, 1),
    )
    assert result.text == "A blue square."
    assert result.input_tokens == 22
    body = json.loads(requests[0].content)
    assert "gemini-3.5-flash-lite:generateContent" in str(requests[0].url)
    assert [item["role"] for item in body["contents"]] == ["user", "model", "user"]
    inline = body["contents"][-1]["parts"][-1]["inlineData"]
    assert base64.b64decode(inline["data"]) == b"JPEG-data"
    assert inline["mime_type"] == "image/jpeg"
    assert body["generationConfig"]["maxOutputTokens"] == 768
    assert "tools" not in body


@pytest.mark.parametrize(
    "status,code,calls",
    [
        (429, "provider_rate_limit", 2),
        (503, "provider_error", 2),
        (403, "provider_credentials", 1),
        (400, "provider_error", 1),
    ],
)
def test_gemini_retry_cap_and_sanitized_errors(monkeypatch, status, code, calls):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json={"error": {"code": status, "message": "secret payload"}})

    mock_gemini(monkeypatch, handler)
    monkeypatch.setattr("lensagent.providers.time.sleep", lambda _: None)
    provider = GeminiProvider(
        Settings(api_token="t" * 32, gemini_enabled=True, gemini_api_key="test-key")
    )
    with pytest.raises(AppError) as error:
        provider.generate([Turn("user", "hello")], None)
    assert error.value.code == code
    assert "secret payload" not in error.value.message
    assert len(seen) == calls


def test_gemini_timeout_is_not_retried(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret", request=request)

    mock_gemini(monkeypatch, handler)
    with pytest.raises(AppError) as error:
        GeminiProvider(
            Settings(api_token="t" * 32, gemini_enabled=True, gemini_api_key="test-key")
        ).generate([Turn("user", "hello")], None)
    assert error.value.code == "provider_timeout"
    assert len(calls) == 1


def test_gemini_empty_response_is_not_invented(monkeypatch):
    mock_gemini(monkeypatch, lambda _: httpx.Response(200, json={"candidates": []}))
    with pytest.raises(AppError, match="no text"):
        GeminiProvider(
            Settings(api_token="t" * 32, gemini_enabled=True, gemini_api_key="test-key")
        ).generate([Turn("user", "hello")], None)


def mock_ollama(monkeypatch, handler):
    real_client = httpx.Client
    monkeypatch.setattr(
        "lensagent.providers.httpx.Client",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(handler)),
    )


def test_ollama_local_vision_wire_format(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": "Local answer"}, "prompt_eval_count": 11, "eval_count": 4},
        )

    mock_ollama(monkeypatch, handler)
    provider = OllamaProvider(
        Settings(api_token="t" * 32, ollama_enabled=True, ollama_context_length=2048)
    )
    result = provider.generate([Turn("user", "what?")], SafeImage(b"image", "image/jpeg", 1, 1))
    assert result.text == "Local answer"
    body = json.loads(requests[0].content)
    assert requests[0].url.host == "127.0.0.1"
    assert body["stream"] is False
    assert body["messages"][-1]["images"] == [base64.b64encode(b"image").decode()]
    assert body["options"]["num_predict"] == 768
    assert body["options"]["num_ctx"] == 2048


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={}),
        httpx.Response(200, text="not json"),
        httpx.Response(302, headers={"location": "http://example.com/private"}),
        httpx.Response(200, content=b"x" * 65537),
    ],
)
def test_ollama_invalid_redirect_and_oversize_responses(monkeypatch, response):
    mock_ollama(monkeypatch, lambda _: response)
    with pytest.raises(AppError):
        OllamaProvider(Settings(api_token="t" * 32, ollama_enabled=True)).generate(
            [Turn("user", "hello")], None
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://192.168.1.1",
        "http://localhost:11434/api",
        "http://user:pass@localhost",
    ],
)
def test_ollama_remote_or_credential_urls_forbidden(url):
    with pytest.raises(ValueError):
        Settings(api_token="t" * 32, ollama_base_url=url)

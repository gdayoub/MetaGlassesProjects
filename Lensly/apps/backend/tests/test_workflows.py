import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from lensagent.api import create_app
from lensagent.config import Settings
from lensagent.errors import AppError
from lensagent.images import sanitize_image
from lensagent.providers import Generation
from PIL import Image


class RecordingProvider:
    model = "explicit-test-double"
    configured = True

    def __init__(self):
        self.calls = []
        self.error = None

    def generate(self, history, image):
        self.calls.append((history, image))
        if self.error:
            raise self.error
        return Generation("Test double response", self.model, 20, 5)


@pytest.fixture
def setup(tmp_path):
    settings = Settings(api_token="t" * 32, data_dir=tmp_path)
    provider = RecordingProvider()
    app = create_app(settings, {"gemini": provider, "ollama": provider})
    with TestClient(app, headers={"Authorization": "Bearer " + "t" * 32}) as client:
        yield settings, provider, client


def question(text="What is this?", **kwargs):
    return {"text": text, "request_id": str(uuid4()), **kwargs}


def png():
    output = io.BytesIO()
    Image.new("RGB", (24, 16), "blue").save(output, format="PNG")
    return output.getvalue()


def test_persisted_multiturn_image_replace_clear_and_reselect(setup):
    settings, provider, client = setup
    conversation = client.post("/api/conversations", json={"title": "Visual notes"}).json()
    path = "/api/conversations/" + conversation["id"]
    first = client.post(path + "/images", files={"file": ("one.png", png(), "image/png")}).json()
    response = client.post(path + "/messages", json=question()).json()
    assert response["image_id"] == first["id"]
    assert provider.calls[-1][1].mime_type == "image/jpeg"
    response = client.post(path + "/messages", json=question("Explain the second part.")).json()
    assert response["image_id"] == first["id"]
    assert len(provider.calls[-1][0]) == 3
    second = client.post(path + "/images", files={"file": ("two.png", png(), "image/png")}).json()
    response = client.post(path + "/messages", json=question()).json()
    assert response["image_id"] == second["id"]
    response = client.post(path + "/messages", json=question(use_recent_image=False)).json()
    assert response["image_id"] is None
    assert provider.calls[-1][1] is None
    response = client.post(path + "/messages", json=question(image_id=first["id"])).json()
    assert response["image_id"] == first["id"]
    restored = TestClient(create_app(settings, {"gemini": provider}))
    restored.headers["Authorization"] = "Bearer " + "t" * 32
    detail = restored.get(path).json()
    assert detail["title"] == "Visual notes"
    assert len(detail["messages"]) == 10
    assert detail["active_image_id"] == first["id"]
    assert restored.delete(path).status_code == 204
    assert restored.get(path + "/images/" + first["id"]).status_code == 404
    restored.close()


def test_repeated_id_is_not_billed_again_and_mismatch_rejected(setup):
    _, provider, client = setup
    cid = client.post("/api/conversations", json={}).json()["id"]
    path = f"/api/conversations/{cid}/messages"
    payload = question()
    first = client.post(path, json=payload)
    assert first.status_code == 200
    assert client.post(path, json=payload).json() == first.json()
    assert len(provider.calls) == 1
    assert client.post(path, json={**payload, "text": "different"}).status_code == 409
    assert len(provider.calls) == 1


def test_first_success_titles_conversation_and_preserves_message_order(setup):
    _, _, client = setup
    cid = client.post("/api/conversations", json={}).json()["id"]
    path = f"/api/conversations/{cid}"
    assert (
        client.post(path + "/messages", json=question("Describe this diagram")).status_code == 200
    )
    assert client.post(path + "/messages", json=question("Explain its labels")).status_code == 200
    detail = client.get(path).json()
    assert detail["title"] == "Describe this diagram"
    assert [message["role"] for message in detail["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


@pytest.mark.parametrize(
    "error", [AppError(504, "provider_timeout", "Timed out"), RuntimeError("private-secret")]
)
def test_failed_generation_is_atomic_and_same_id_does_not_retry(setup, error):
    _, provider, client = setup
    cid = client.post("/api/conversations", json={}).json()["id"]
    path = f"/api/conversations/{cid}"
    provider.error = error
    payload = question()
    failed = client.post(path + "/messages", json=payload)
    assert failed.status_code in {500, 504}
    assert "private-secret" not in failed.text
    assert client.post(path + "/messages", json=payload).json() == failed.json()
    assert len(provider.calls) == 1
    assert client.get(path).json()["messages"] == []
    provider.error = None
    assert client.post(path + "/messages", json=question()).status_code == 200


def test_provider_unconfigured_is_truthful(tmp_path):
    app = create_app(Settings(api_token="t" * 32, data_dir=tmp_path))
    with TestClient(app, headers={"Authorization": "Bearer " + "t" * 32}) as client:
        assert all(not p["configured"] for p in client.get("/api/config").json()["providers"])
        cid = client.post("/api/conversations", json={}).json()["id"]
        response = client.post(f"/api/conversations/{cid}/messages", json=question())
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "provider_unconfigured"


def test_daily_budget_is_durable_and_not_reset_by_deletion(tmp_path):
    settings = Settings(api_token="t" * 32, data_dir=tmp_path, daily_request_limit=1)
    fake = RecordingProvider()
    with TestClient(
        create_app(settings, {"gemini": fake}), headers={"Authorization": "Bearer " + "t" * 32}
    ) as client:
        cid = client.post("/api/conversations", json={}).json()["id"]
        assert client.post(f"/api/conversations/{cid}/messages", json=question()).status_code == 200
        assert client.delete(f"/api/conversations/{cid}").status_code == 204
    with TestClient(
        create_app(settings, {"gemini": fake}), headers={"Authorization": "Bearer " + "t" * 32}
    ) as client:
        cid = client.post("/api/conversations", json={}).json()["id"]
        assert (
            client.post(f"/api/conversations/{cid}/messages", json=question()).json()["error"][
                "code"
            ]
            == "daily_limit"
        )
    assert len(fake.calls) == 1


@pytest.mark.parametrize(
    "body",
    [
        question(text=" "),
        question(text="a" * 4001),
        question(provider="unknown"),
        question(image_id="http://127.0.0.1/private"),
        {"text": "missing id"},
    ],
)
def test_invalid_request_never_reaches_model(setup, body):
    _, provider, client = setup
    cid = client.post("/api/conversations", json={}).json()["id"]
    assert client.post(f"/api/conversations/{cid}/messages", json=body).status_code == 422
    assert provider.calls == []


def test_history_is_bounded(setup):
    settings, provider, client = setup
    settings.max_history_chars = 20
    settings.max_history_messages = 2
    cid = client.post("/api/conversations", json={}).json()["id"]
    for _ in range(3):
        assert client.post(f"/api/conversations/{cid}/messages", json=question()).status_code == 200
    assert len(provider.calls[-1][0]) == 1


@pytest.mark.parametrize("kind", ["mime", "corrupt", "dimensions", "bytes"])
def test_unsafe_images_rejected(tmp_path, kind):
    settings = Settings(api_token="t" * 32, data_dir=tmp_path)
    data, mime = png(), "image/png"
    if kind == "mime":
        mime = "image/jpeg"
    elif kind == "corrupt":
        data = b"not an image"
    elif kind == "dimensions":
        settings.max_image_pixels = 10
    else:
        settings.max_image_bytes = 10
    with pytest.raises(AppError):
        sanitize_image(data, mime, settings)


def test_image_metadata_removed_and_large_dimensions_downsampled(tmp_path):
    output = io.BytesIO()
    source = Image.new("RGB", (3000, 1500), "white")
    exif = source.getexif()
    exif[0x010E] = "private metadata"
    source.save(output, format="JPEG", exif=exif)
    safe = sanitize_image(
        output.getvalue(), "image/jpeg", Settings(api_token="t" * 32, data_dir=tmp_path)
    )
    assert (safe.width, safe.height) == (2048, 1024)
    assert b"private metadata" not in safe.data
    with Image.open(io.BytesIO(safe.data)) as normalized:
        assert not normalized.getexif()


def test_expired_image_removed_and_inactive_conversation_pruned(setup):
    settings, _, client = setup
    cid = client.post("/api/conversations", json={}).json()["id"]
    image_id = client.post(
        f"/api/conversations/{cid}/images", files={"file": ("image.png", png(), "image/png")}
    ).json()["id"]
    store = client.app.state.store
    with store.connection() as db:
        db.execute("UPDATE images SET created_at='2000-01-01T00:00:00+00:00'")
    assert client.get(f"/api/conversations/{cid}/images/{image_id}").status_code == 404
    assert client.get(f"/api/conversations/{cid}").json()["active_image_id"] is None
    with store.connection() as db:
        db.execute("UPDATE conversations SET updated_at='2000-01-01T00:00:00+00:00'")
    assert client.get("/api/conversations").json() == []
    assert Path(settings.data_dir / "lensagent.sqlite3").exists()


def test_pairing_failures_rate_limited_and_code_expires(setup):
    _, _, client = setup
    issued = client.post("/api/pairing").json()
    assert len(issued["code"]) == 8
    with client.app.state.store.connection() as db:
        db.execute("UPDATE pairing_codes SET expires_at=0")
    assert client.post("/api/pairing/redeem", json={"code": issued["code"]}).status_code == 401
    for _ in range(2):
        assert client.post("/api/pairing/redeem", json={"code": "00000000"}).status_code == 401
    assert client.post("/api/pairing/redeem", json={"code": "00000000"}).status_code == 429

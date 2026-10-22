"""Adversarial checks of privacy boundaries and concurrent request handling."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from lensagent.api import create_app
from lensagent.config import Settings
from lensagent.errors import AppError
from lensagent.images import SafeImage
from lensagent.providers import Generation, Turn
from lensagent.storage import Store
from PIL import Image

ADMIN_TOKEN = "q" * 64


class ReviewProvider:
    model = "security-review-test-double"
    configured = True

    def __init__(self) -> None:
        self.calls = 0
        self.images: list[SafeImage | None] = []

    def generate(self, history: list[Turn], image: SafeImage | None) -> Generation:
        self.calls += 1
        self.images.append(image)
        return Generation("Test double; no live inference.", self.model)


@pytest.fixture
def reviewed_client(tmp_path: Path) -> Iterator[tuple[TestClient, ReviewProvider]]:
    settings = Settings(
        api_token=ADMIN_TOKEN,
        data_dir=tmp_path,
        gemini_api_key="test-secret-never-return-this",
    )
    provider = ReviewProvider()
    app = create_app(settings, {"gemini": provider})
    with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
        yield client, provider


def admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def test_missing_auth_cannot_read_or_mutate_private_api(
    reviewed_client: tuple[TestClient, ReviewProvider],
) -> None:
    client, provider = reviewed_client
    for path in ["/api/config", "/api/conversations", "/api/devices"]:
        response = client.get(path)
        assert response.status_code == 401, (path, response.text)
    assert client.post("/api/pairing").status_code == 401
    assert client.post("/api/conversations", json={}).status_code == 401
    assert client.get("/api/config", params={"token": ADMIN_TOKEN}).status_code == 401
    assert provider.calls == 0


def test_malformed_non_ascii_bearer_is_rejected_without_crashing(
    reviewed_client: tuple[TestClient, ReviewProvider],
) -> None:
    client, _ = reviewed_client
    response = client.get("/api/config", headers={b"authorization": b"Bearer \xff"})
    assert response.status_code == 401, response.text


def test_host_origin_and_browser_headers_protect_the_local_server(
    reviewed_client: tuple[TestClient, ReviewProvider],
) -> None:
    client, _ = reviewed_client
    assert (
        client.get(
            "/api/config", headers={**admin_headers(), "Host": "attacker.example"}
        ).status_code
        == 400
    )
    for origin in ["https://attacker.example", "http://localhost:9999", "null", "http://["]:
        response = client.get("/api/config", headers={**admin_headers(), "Origin": origin})
        assert response.status_code == 403
    response = client.get("/api/config", headers={**admin_headers(), "Origin": "http://localhost"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "access-control-allow-origin" not in response.headers
    assert ADMIN_TOKEN not in response.text
    assert "test-secret-never-return-this" not in response.text


def test_streamed_body_cannot_bypass_request_size_guard(
    reviewed_client: tuple[TestClient, ReviewProvider],
) -> None:
    client, provider = reviewed_client

    def chunks() -> Iterator[bytes]:
        yield b"x" * 40_000
        yield b"x" * 40_000

    response = client.post(
        "/api/conversations",
        headers={**admin_headers(), "Content-Type": "application/json"},
        content=chunks(),
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_size"
    assert provider.calls == 0


def test_image_api_isolation_deletion_and_followup_context(
    reviewed_client: tuple[TestClient, ReviewProvider],
) -> None:
    client, provider = reviewed_client
    client.headers.update(admin_headers())
    first = client.post("/api/conversations", json={}).json()["id"]
    second = client.post("/api/conversations", json={}).json()["id"]
    buffer = BytesIO()
    Image.new("RGB", (12, 8), "green").save(buffer, format="PNG")
    uploaded = client.post(
        f"/api/conversations/{first}/images",
        files={"file": ("private.png", buffer.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    image_id = uploaded.json()["id"]
    wrong_path = f"/api/conversations/{second}/images/{image_id}"
    assert client.get(wrong_path).status_code == 404
    assert client.delete(wrong_path).status_code == 404
    bad_request = client.post(
        f"/api/conversations/{second}/messages",
        json={
            "text": "Read the other conversation's image",
            "image_id": image_id,
            "request_id": str(uuid4()),
        },
    )
    assert bad_request.status_code == 404
    assert provider.calls == 0
    for question in ["Describe the image", "What color is it?"]:
        response = client.post(
            f"/api/conversations/{first}/messages",
            json={"text": question, "request_id": str(uuid4())},
        )
        assert response.status_code == 200, response.text
    assert len(provider.images) == 2
    assert all(image is not None for image in provider.images)
    assert client.delete(f"/api/conversations/{first}/images/{image_id}").status_code == 204
    assert client.get(f"/api/conversations/{first}/images/{image_id}").status_code == 404
    conversation = client.get(f"/api/conversations/{first}").json()
    assert conversation["active_image_id"] is None
    assert all(message["image_id"] is None for message in conversation["messages"])
    after_delete = client.post(
        f"/api/conversations/{first}/messages",
        json={"text": "Do you have an image attached?", "request_id": str(uuid4())},
    )
    assert after_delete.status_code == 200, after_delete.text
    assert provider.images[-1] is None


def test_paired_device_cannot_manage_devices_and_revocation_takes_effect(
    reviewed_client: tuple[TestClient, ReviewProvider],
) -> None:
    client, _ = reviewed_client
    created = client.post("/api/pairing", headers=admin_headers())
    assert created.status_code == 201
    redeemed = client.post("/api/pairing/redeem", json={"code": created.json()["code"]})
    assert redeemed.status_code == 200
    device = redeemed.json()
    device_headers = {"Authorization": f"Bearer {device['token']}"}
    assert client.get("/api/config", headers=device_headers).status_code == 200
    assert client.post("/api/pairing", headers=device_headers).status_code == 403
    assert client.get("/api/devices", headers=device_headers).status_code == 403
    assert (
        client.delete(f"/api/devices/{device['device_id']}", headers=device_headers).status_code
        == 403
    )
    assert (
        client.delete(f"/api/devices/{device['device_id']}", headers=admin_headers()).status_code
        == 204
    )
    assert client.get("/api/config", headers=device_headers).status_code == 401


@pytest.fixture
def reviewed_store(tmp_path: Path) -> Store:
    settings = Settings(api_token="q" * 64, data_dir=tmp_path)
    return Store(tmp_path / "review.sqlite3", settings)


def test_parallel_reservations_do_not_start_two_generations(reviewed_store: Store) -> None:
    conversation_id = reviewed_store.create_conversation("Concurrent requests")["id"]
    barrier = Barrier(2)

    def reserve_once() -> str:
        barrier.wait(timeout=5)
        try:
            reviewed_store.reserve(conversation_id, str(uuid4()), "different request")
            return "reserved"
        except AppError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(reserve_once)
        second = executor.submit(reserve_once)
        outcomes = [first.result(timeout=10), second.result(timeout=10)]
    assert sorted(outcomes) == ["conversation_busy", "reserved"]
    with reviewed_store.connection() as db:
        assert db.execute("SELECT count(*) FROM requests").fetchone()[0] == 1
        assert db.execute("SELECT sum(count) FROM daily_usage").fetchone()[0] == 1


def test_images_cannot_cross_conversation_boundary(reviewed_store: Store) -> None:
    first = reviewed_store.create_conversation("Private image")["id"]
    second = reviewed_store.create_conversation("Other conversation")["id"]
    safe = SafeImage(b"already-sanitized-image", "image/jpeg", 8, 8)
    image_id = reviewed_store.add_image(first, safe)["id"]

    with pytest.raises(AppError, match="not found"):
        reviewed_store.image(second, image_id)
    with pytest.raises(AppError, match="not found"):
        reviewed_store.delete_image(second, image_id)

    assert reviewed_store.image(first, image_id).data == safe.data
    assert reviewed_store.images(second) == []


def test_pending_generation_prevents_image_and_conversation_mutation(
    reviewed_store: Store,
) -> None:
    conversation_id = reviewed_store.create_conversation("Busy conversation")["id"]
    safe = SafeImage(b"already-sanitized-image", "image/jpeg", 8, 8)
    image_id = reviewed_store.add_image(conversation_id, safe)["id"]
    reviewed_store.reserve(conversation_id, str(uuid4()), "in-flight")

    with pytest.raises(AppError) as delete_image:
        reviewed_store.delete_image(conversation_id, image_id)
    assert delete_image.value.code == "conversation_busy"
    with pytest.raises(AppError) as add_image:
        reviewed_store.add_image(conversation_id, safe)
    assert add_image.value.code == "conversation_busy"
    with pytest.raises(AppError) as delete_conversation:
        reviewed_store.delete_conversation(conversation_id)
    assert delete_conversation.value.code == "conversation_busy"
    assert reviewed_store.image(conversation_id, image_id).data == safe.data


def test_pairing_code_redemption_is_atomic_and_only_hashes_are_stored(
    reviewed_store: Store,
) -> None:
    code = reviewed_store.pair_code()["code"]
    barrier = Barrier(2)

    def redeem_once() -> dict[str, object]:
        barrier.wait(timeout=5)
        try:
            return reviewed_store.redeem(code, "127.0.0.1")
        except AppError as error:
            return {"error": error.code}

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(redeem_once)
        second = executor.submit(redeem_once)
        results = [first.result(timeout=10), second.result(timeout=10)]
    issued = [item for item in results if "token" in item]
    assert len(issued) == 1
    assert {"error": "invalid_pairing_code"} in results
    token = str(issued[0]["token"])
    assert reviewed_store.device_valid(token)
    with reviewed_store.connection() as db:
        stored_hash = db.execute("SELECT hash FROM devices").fetchone()[0]
        assert stored_hash != token
        assert db.execute("SELECT count(*) FROM pairing_codes").fetchone()[0] == 0
    reviewed_store.revoke(str(issued[0]["device_id"]))
    assert not reviewed_store.device_valid(token)

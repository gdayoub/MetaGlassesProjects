"""Exercise live local inference with a synthetic image, never private user data."""

import io
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw

from lensagent.config import Settings

settings = Settings.from_env()
base = "http://127.0.0.1:8765"
output = Path("work/live-local-smoke.json")
output.parent.mkdir(exist_ok=True)
canvas = Image.new("RGB", (600, 400), "white")
draw = ImageDraw.Draw(canvas)
draw.rectangle((60, 110, 240, 290), fill="red")
draw.ellipse((360, 110, 540, 290), fill="blue")
buffer = io.BytesIO()
canvas.save(buffer, format="PNG")
canvas.save("work/live-vision-input.png")
results = {"provider": "ollama", "model": settings.ollama_model, "synthetic_image": "red square left, blue circle right", "calls": []}
with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + settings.api_token.get_secret_value()}, timeout=150) as client:
    response = client.post("/api/conversations", json={"title": "Local vision verification"})
    response.raise_for_status()
    cid = response.json()["id"]
    results["conversation_id"] = cid
    image = client.post(f"/api/conversations/{cid}/images", files={"file": ("shapes.png", buffer.getvalue(), "image/png")})
    image.raise_for_status()
    image_id = image.json()["id"]
    for question, use_image in [
        ("Describe the shapes and colors in this image. Which shape is on the right?", True),
        ("What color is that shape on the right? Answer briefly.", True),
        ("Without viewing an image now, what is 19 plus 23?", False),
    ]:
        body = {"text": question, "provider": "ollama", "image_id": image_id if use_image else None, "use_recent_image": False, "request_id": str(uuid4())}
        started = time.perf_counter()
        reply = client.post(f"/api/conversations/{cid}/messages", json=body)
        elapsed = round(time.perf_counter() - started, 2)
        entry = {"question": question, "image_attached": use_image, "seconds": elapsed, "http_status": reply.status_code, "response": reply.json()}
        results["calls"].append(entry)
        output.write_text(json.dumps(results, indent=2), encoding="utf-8")
        reply.raise_for_status()
        repeated = client.post(f"/api/conversations/{cid}/messages", json=body)
        repeated.raise_for_status()
        assert repeated.json() == reply.json(), "Idempotent replay returned a different result"
        entry["duplicate_replay_identical"] = True
    detail = client.get(f"/api/conversations/{cid}")
    detail.raise_for_status()
    results["stored_messages"] = len(detail.json()["messages"])
    results["active_image_cleared"] = detail.json()["active_image_id"] is None
output.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))

"""Run browser acceptance tests against the real API with all inference disabled."""

import os
import tempfile
from pathlib import Path

import uvicorn

from lensagent.api import create_app
from lensagent.config import Settings

with tempfile.TemporaryDirectory(prefix="lensagent-browser-") as directory:
    settings = Settings(
        api_token="browser-test-token-only-not-for-deployment",
        data_dir=Path(directory),
        gemini_enabled=False,
        ollama_enabled=False,
    )
    uvicorn.run(create_app(settings), host="127.0.0.1", port=int(os.environ.get("TEST_PORT", "8766")), access_log=False)

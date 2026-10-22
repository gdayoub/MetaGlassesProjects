"""Read-only readiness checks; never starts inference, pairs a device or publishes."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
from lensagent.config import Settings
from pydantic import ValidationError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-url", help="Optional existing HTTPS origin; no credentials sent")
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
    except ValidationError:
        print("FAIL: Invalid configuration. Check .env against .env.example; secrets omitted.")
        return 1
    checks: list[dict[str, str]] = []

    def record(name: str, state: str, detail: str) -> None:
        checks.append({"check": name, "state": state, "detail": detail})
        print(f"{state}: {name}: {detail}")

    with httpx.Client(timeout=10, trust_env=False, follow_redirects=False) as client:
        try:
            health = client.get("http://127.0.0.1:8765/health")
            healthy = health.status_code == 200 and health.json().get("service") == "LensAgent"
            record("Local server", "PASS" if healthy else "FAIL", f"HTTP {health.status_code}")
            unauthorized = client.get("http://127.0.0.1:8765/api/config")
            record(
                "Local API authentication",
                "PASS" if unauthorized.status_code == 401 else "FAIL",
                f"Unauthenticated request returned {unauthorized.status_code}; expected 401",
            )
            config = client.get(
                "http://127.0.0.1:8765/api/config",
                headers={"Authorization": "Bearer " + settings.api_token.get_secret_value()},
            )
            config.raise_for_status()
            providers = config.json()["providers"]
            local = next(p for p in providers if p["id"] == "ollama")
            matches = (
                local["model"] == settings.ollama_model
                and local["configured"] == settings.ollama_enabled
            )
            record(
                "Applied Ollama settings",
                "PASS" if matches else "FAIL",
                f"Running server selects {local['model']}; enabled={local['configured']}",
            )
            record(
                "Enabled provider",
                "PASS" if any(p["configured"] for p in providers) else "FAIL",
                "At least one provider must be enabled for device questions",
            )
            if local["configured"]:
                shown = client.post(
                    settings.ollama_base_url + "/api/show", json={"model": local["model"]}
                )
                shown.raise_for_status()
                vision = "vision" in shown.json().get("capabilities", [])
                record(
                    "Installed vision model",
                    "PASS" if vision else "FAIL",
                    f"{local['model']}: vision={vision}; metadata check only, no model loaded",
                )
        except (httpx.HTTPError, ValueError, KeyError, StopIteration):
            record(
                "Local connectivity/configuration",
                "FAIL",
                "Could not complete local checks; start LensAgent/Ollama and check .env",
            )

        if args.public_url:
            try:
                parsed = urlparse(args.public_url)
            except ValueError:
                parsed = urlparse("")
            valid = (
                parsed.scheme == "https"
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and parsed.path in {"", "/"}
                and not parsed.query
                and not parsed.fragment
            )
            if not valid:
                record(
                    "Public origin",
                    "FAIL",
                    "Use a plain HTTPS origin without credentials, path, query or fragment",
                )
            else:
                base = args.public_url.rstrip("/")
                allowed = parsed.hostname in settings.allowed_hosts
                record(
                    "Configured public host",
                    "PASS" if allowed else "FAIL",
                    "Exact hostname must be in LENSAGENT_ALLOWED_HOSTS; restart after editing",
                )
                try:
                    health = client.get(base + "/health")
                    healthy = (
                        health.status_code == 200 and health.json().get("service") == "LensAgent"
                    )
                    record(
                        "HTTPS health",
                        "PASS" if healthy else "FAIL",
                        f"HTTP {health.status_code}; certificate verification enabled",
                    )
                    response = client.get(base + "/api/config")
                    record(
                        "Public API authentication",
                        "PASS" if response.status_code == 401 else "FAIL",
                        f"Unauthenticated request returned {response.status_code}; expected 401",
                    )
                except (httpx.HTTPError, ValueError):
                    record(
                        "HTTPS connectivity",
                        "FAIL",
                        "Could not verify this HTTPS origin; redirects are not followed",
                    )
        else:
            record(
                "Glasses HTTPS origin",
                "PENDING",
                "No public URL supplied. Loopback is not reachable from the glasses",
            )
    record(
        "Real glasses and iPhone acceptance",
        "PENDING",
        "Pairing, handwriting, image selection and actual display still need hardware testing",
    )
    output = Path("work/glasses-preflight.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"checks": checks}, indent=2), encoding="utf-8")
    print(f"Saved non-secret report: {output.resolve()}")
    return int(any(check["state"] == "FAIL" for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())

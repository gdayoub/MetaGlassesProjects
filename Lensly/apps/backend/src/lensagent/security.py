import hmac
from urllib.parse import urlparse

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lensagent.config import Settings
from lensagent.storage import Store


class RequestGuard:
    def __init__(self, app: ASGIApp, settings: Settings, store: Store):
        self.app = app
        self.settings = settings
        self.store = store

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope["headers"]
        }
        path = scope.get("path", "")

        async def reject(status: int, code: str, message: str) -> None:
            response = JSONResponse(
                {"error": {"code": code, "message": message}}, status_code=status
            )
            await response(scope, receive, safe_send)

        async def safe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"cache-control", b"no-store"),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; img-src 'self' blob: data:; "
                            b"style-src 'self'; script-src 'self'; connect-src 'self'; "
                            b"frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                        ),
                    ]
                )
                message["headers"] = response_headers
            await send(message)

        if path.startswith("/api/"):
            origin = headers.get("origin")
            if origin:
                try:
                    parsed = urlparse(origin)
                    same_origin = (
                        parsed.netloc == headers.get("host")
                        and parsed.scheme == scope.get("scheme")
                        and not (parsed.path or parsed.params or parsed.query or parsed.fragment)
                    )
                except ValueError:
                    same_origin = False
                if not same_origin:
                    await reject(403, "origin_rejected", "Requests must come from the same origin.")
                    return
            if path != "/api/pairing/redeem":
                authorization = headers.get("authorization", "")
                token = authorization[7:] if authorization.startswith("Bearer ") else ""
                admin = bool(token) and hmac.compare_digest(
                    token.encode("utf-8"),
                    self.settings.api_token.get_secret_value().encode("utf-8"),
                )
                if not admin and (
                    not token or len(token) > 512 or not self.store.device_valid(token)
                ):
                    await reject(
                        401,
                        "unauthorized",
                        "Connect using the local access token or a pairing code.",
                    )
                    return
                if not admin and (path == "/api/pairing" or path.startswith("/api/devices")):
                    await reject(
                        403,
                        "admin_required",
                        "Use the desktop administrator token for device management.",
                    )
                    return
        limit = (
            self.settings.max_image_bytes + 65536
            if path.endswith("/images") and scope["method"] == "POST"
            else 65536
        )
        try:
            length = int(headers.get("content-length", "0"))
        except ValueError:
            await reject(400, "invalid_length", "Invalid request length.")
            return
        if length < 0 or length > limit:
            await reject(413, "request_size", "The request is too large.")
            return
        body = bytearray()
        while True:
            incoming = await receive()
            if incoming["type"] == "http.disconnect":
                return
            body.extend(incoming.get("body", b""))
            if len(body) > limit:
                await reject(413, "request_size", "The request is too large.")
                return
            if not incoming.get("more_body", False):
                break
        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, bounded_receive, safe_send)

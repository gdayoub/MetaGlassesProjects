import hashlib
import logging
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from lensagent.config import PROJECT_ROOT, Settings
from lensagent.errors import AppError
from lensagent.images import sanitize_image
from lensagent.models import ConversationCreate, MessageCreate
from lensagent.providers import GeminiProvider, OllamaProvider, Provider, Turn
from lensagent.security import RequestGuard
from lensagent.storage import Store, now_iso

logger = logging.getLogger("lensagent")


class PairingCode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^\d{8}$", min_length=8, max_length=8)


def create_app(
    settings: Settings | None = None, providers: dict[str, Provider] | None = None
) -> FastAPI:
    try:
        settings = settings or Settings.from_env()
    except ValidationError:
        # Pydantic's default repr can include the rejected secret, so do not propagate it.
        raise RuntimeError(
            "Invalid LensAgent configuration. Check .env against .env.example; "
            "LENSAGENT_API_TOKEN must have at least 32 characters."
        ) from None
    store = Store(settings.data_dir / "lensagent.sqlite3", settings)
    provider_map: dict[str, Provider] = (
        providers
        if providers is not None
        else {
            "gemini": GeminiProvider(settings),
            "ollama": OllamaProvider(settings),
        }
    )
    app = FastAPI(
        title="LensAgent", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.store = store
    app.state.providers = provider_map
    app.state.settings = settings
    app.add_middleware(RequestGuard, settings=settings, store=store)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "invalid_request",
                    "message": "Check the request fields, question length, and identifier format.",
                }
            },
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "http_error",
                    "message": "The requested resource or method is unavailable.",
                }
            },
            status_code=exc.status_code,
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "LensAgent",
            "version": "0.1.0",
            "hardware_verified": False,
        }

    @app.get("/api/config")
    def config() -> dict[str, Any]:
        return {
            "providers": [
                {"id": key, "model": provider.model, "configured": provider.configured}
                for key, provider in provider_map.items()
            ],
            "limits": {
                "max_image_bytes": settings.max_image_bytes,
                "max_text_length": settings.max_text_length,
                "max_output_tokens": settings.max_output_tokens,
                "daily_requests": settings.daily_request_limit,
            },
            "retention_days": settings.retention_days,
        }

    @app.get("/api/conversations")
    def conversations() -> list[dict[str, Any]]:
        store.prune()
        return store.conversations()

    @app.post("/api/conversations", status_code=201)
    def create_conversation(body: ConversationCreate) -> dict[str, Any]:
        store.prune()
        return store.create_conversation(body.title.strip() or "New conversation")

    @app.get("/api/conversations/{conversation_id}")
    def conversation(conversation_id: UUID) -> dict[str, Any]:
        store.prune()
        return store.conversation(str(conversation_id))

    @app.delete("/api/conversations/{conversation_id}", status_code=204)
    def delete_conversation(conversation_id: UUID) -> Response:
        store.delete_conversation(str(conversation_id))
        return Response(status_code=204)

    @app.get("/api/conversations/{conversation_id}/images")
    def images(conversation_id: UUID) -> list[dict[str, Any]]:
        store.prune()
        return store.images(str(conversation_id))

    @app.post("/api/conversations/{conversation_id}/images", status_code=201)
    def upload_image(conversation_id: UUID, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
        store.prune()
        data = file.file.read(settings.max_image_bytes + 1)
        return store.add_image(
            str(conversation_id), sanitize_image(data, file.content_type, settings)
        )

    @app.get("/api/conversations/{conversation_id}/images/{image_id}")
    def image(conversation_id: UUID, image_id: UUID) -> Response:
        store.prune()
        selected = store.image(str(conversation_id), str(image_id))
        return Response(selected.data, media_type=selected.mime_type)

    @app.delete("/api/conversations/{conversation_id}/images/{image_id}", status_code=204)
    def delete_image(conversation_id: UUID, image_id: UUID) -> Response:
        store.delete_image(str(conversation_id), str(image_id))
        return Response(status_code=204)

    @app.post("/api/conversations/{conversation_id}/messages")
    def message(conversation_id: UUID, body: MessageCreate) -> dict[str, Any]:
        store.prune()
        cid, rid = str(conversation_id), str(body.request_id)
        fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        previous = store.reserve(cid, rid, fingerprint)
        if previous is not None:
            return previous
        try:
            conversation_data = store.conversation(cid)
            image_id = (
                str(body.image_id)
                if body.image_id
                else (conversation_data["active_image_id"] if body.use_recent_image else None)
            )
            selected = store.image(cid, image_id) if image_id else None
            history: list[Turn] = []
            remaining = settings.max_history_chars
            for item in reversed(conversation_data["messages"][-settings.max_history_messages :]):
                if len(item["text"]) > remaining:
                    break
                history.append(Turn(item["role"], item["text"]))
                remaining -= len(item["text"])
            history.reverse()
            if history and history[0].role == "assistant":
                history.pop(0)
            history.append(Turn("user", body.text))
            provider = provider_map[body.provider]
            result = provider.generate(history, selected)
            response = {
                "id": str(uuid4()),
                "text": result.text,
                "role": "assistant",
                "provider": body.provider,
                "model": result.model,
                "image_id": image_id,
                "request_id": rid,
                "created_at": now_iso(),
                "usage": {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                },
            }
            store.finish(cid, rid, body.text, response, image_id)
            logger.info(
                "generation_completed provider=%s input_tokens=%d output_tokens=%d",
                body.provider,
                result.input_tokens,
                result.output_tokens,
            )
            return response
        except AppError as exc:
            store.fail(cid, rid, exc)
            raise
        except Exception as exc:
            # Persist the unknown outcome without logging payloads or provider exception strings.
            error = AppError(
                500,
                "internal_error",
                "The request failed unexpectedly. Its provider outcome may be unknown.",
            )
            store.fail(cid, rid, error)
            logger.error("generation_failed exception_type=%s", type(exc).__name__)
            raise error from None

    @app.post("/api/pairing", status_code=201)
    def pairing() -> dict[str, Any]:
        return store.pair_code()

    @app.post("/api/pairing/redeem")
    def redeem(body: PairingCode, request: Request) -> dict[str, Any]:
        ip = request.client.host if request.client else "unknown"
        return store.redeem(body.code, ip)

    @app.get("/api/devices")
    def devices() -> list[dict[str, Any]]:
        return store.devices()

    @app.delete("/api/devices/{device_id}", status_code=204)
    def revoke(device_id: UUID) -> Response:
        store.revoke(str(device_id))
        return Response(status_code=204)

    web_root = PROJECT_ROOT / "apps" / "web" / "dist"
    if web_root.is_dir():
        app.mount("/", StaticFiles(directory=web_root, html=True), name="web")
    return app

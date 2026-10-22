import hashlib
import json
import secrets
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from lensagent.config import Settings
from lensagent.errors import AppError
from lensagent.images import SafeImage


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path: Path, settings: Settings):
        self.path = path
        self.settings = settings
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, active_image_id TEXT
                );
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id)
                    ON DELETE CASCADE, mime_type TEXT NOT NULL, width INTEGER NOT NULL,
                    height INTEGER NOT NULL, size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL, data BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id)
                    ON DELETE CASCADE, role TEXT NOT NULL, text TEXT NOT NULL, image_id TEXT,
                    provider TEXT, model TEXT, created_at TEXT NOT NULL, request_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requests (
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
                    response TEXT, created_at REAL NOT NULL,
                    PRIMARY KEY(conversation_id, request_id)
                );
                CREATE TABLE IF NOT EXISTS daily_usage (
                    day TEXT PRIMARY KEY, count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS recent_calls (at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS pairing_codes (
                    hash TEXT PRIMARY KEY, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY, hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pairing_attempts (at REAL NOT NULL, ip TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS message_conversation
                    ON messages(conversation_id, created_at);
                CREATE INDEX IF NOT EXISTS image_conversation
                    ON images(conversation_id, created_at);
            """)
            # An interrupted generation must never be silently sent to a paid provider again.
            db.execute(
                "UPDATE requests SET status='error', response=? WHERE status='pending'",
                (
                    json.dumps(
                        {
                            "status": 409,
                            "code": "request_interrupted",
                            "message": "Request interrupted; provider outcome unknown. "
                            "Use a new request ID only if you intend to submit again.",
                        }
                    ),
                ),
            )
        self.prune()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA secure_delete=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def prune(self) -> None:
        cutoff = datetime.fromtimestamp(
            time.time() - self.settings.retention_days * 86400, UTC
        ).isoformat()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            expired = [
                row[0]
                for row in db.execute(
                    "SELECT id FROM images WHERE created_at < ? AND conversation_id NOT IN "
                    "(SELECT conversation_id FROM requests WHERE status='pending')",
                    (cutoff,),
                )
            ]
            for image_id in expired:
                db.execute("UPDATE messages SET image_id=NULL WHERE image_id=?", (image_id,))
                db.execute(
                    "UPDATE conversations SET active_image_id=NULL WHERE active_image_id=?",
                    (image_id,),
                )
            db.execute(
                "DELETE FROM images WHERE created_at < ? AND conversation_id NOT IN "
                "(SELECT conversation_id FROM requests WHERE status='pending')",
                (cutoff,),
            )
            db.execute(
                "DELETE FROM conversations WHERE updated_at < ? AND id NOT IN "
                "(SELECT conversation_id FROM requests WHERE status='pending')",
                (cutoff,),
            )
            db.execute("DELETE FROM recent_calls WHERE at < ?", (time.time() - 60,))
            db.execute("DELETE FROM pairing_codes WHERE expires_at < ?", (time.time(),))
            db.execute("DELETE FROM devices WHERE expires_at < ?", (time.time(),))
            db.execute("DELETE FROM pairing_attempts WHERE at < ?", (time.time() - 60,))

    @staticmethod
    def require_conversation(db: sqlite3.Connection, conversation_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if row is None:
            raise AppError(404, "conversation_not_found", "Conversation not found.")
        return dict(row)

    @staticmethod
    def require_idle(db: sqlite3.Connection, conversation_id: str) -> None:
        if db.execute(
            "SELECT 1 FROM requests WHERE conversation_id=? AND status='pending'",
            (conversation_id,),
        ).fetchone():
            raise AppError(
                409,
                "conversation_busy",
                "Wait for the current response before changing this conversation.",
            )

    def create_conversation(self, title: str) -> dict[str, Any]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] >= 200:
                raise AppError(
                    429, "conversation_limit", "Delete an old conversation before creating another."
                )
            conversation_id, stamp = str(uuid4()), now_iso()
            db.execute(
                "INSERT INTO conversations VALUES (?,?,?,?,NULL)",
                (conversation_id, title, stamp, stamp),
            )
            return self.require_conversation(db, conversation_id)

    def conversations(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
            ]

    def conversation(self, conversation_id: str) -> dict[str, Any]:
        with self.connection() as db:
            result = self.require_conversation(db, conversation_id)
            result["messages"] = [
                dict(row)
                for row in db.execute(
                    "SELECT id,role,text,image_id,provider,model,created_at,request_id "
                    "FROM messages "
                    "WHERE conversation_id=? ORDER BY rowid",
                    (conversation_id,),
                )
            ]
            return result

    def delete_conversation(self, conversation_id: str) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_conversation(db, conversation_id)
            self.require_idle(db, conversation_id)
            db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))

    def add_image(self, conversation_id: str, image: SafeImage) -> dict[str, Any]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_conversation(db, conversation_id)
            self.require_idle(db, conversation_id)
            count = db.execute(
                "SELECT COUNT(*) FROM images WHERE conversation_id=?", (conversation_id,)
            ).fetchone()[0]
            if count >= 20:
                raise AppError(
                    429,
                    "image_limit",
                    "Delete an older image before uploading another (20 per conversation).",
                )
            image_id, stamp = str(uuid4()), now_iso()
            db.execute(
                "INSERT INTO images VALUES (?,?,?,?,?,?,?,?)",
                (
                    image_id,
                    conversation_id,
                    image.mime_type,
                    image.width,
                    image.height,
                    len(image.data),
                    stamp,
                    image.data,
                ),
            )
            db.execute(
                "UPDATE conversations SET active_image_id=?,updated_at=? WHERE id=?",
                (image_id, stamp, conversation_id),
            )
            row = db.execute(
                "SELECT id,mime_type,width,height,size_bytes,created_at FROM images WHERE id=?",
                (image_id,),
            ).fetchone()
            return dict(row)

    def images(self, conversation_id: str) -> list[dict[str, Any]]:
        with self.connection() as db:
            self.require_conversation(db, conversation_id)
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,mime_type,width,height,size_bytes,created_at FROM images "
                    "WHERE conversation_id=? ORDER BY created_at DESC",
                    (conversation_id,),
                )
            ]

    def image(self, conversation_id: str, image_id: str) -> SafeImage:
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM images WHERE id=? AND conversation_id=?", (image_id, conversation_id)
            ).fetchone()
            if row is None:
                raise AppError(404, "image_not_found", "Image not found in this conversation.")
            return SafeImage(row["data"], row["mime_type"], row["width"], row["height"])

    def delete_image(self, conversation_id: str, image_id: str) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_conversation(db, conversation_id)
            self.require_idle(db, conversation_id)
            if not db.execute(
                "SELECT 1 FROM images WHERE id=? AND conversation_id=?", (image_id, conversation_id)
            ).fetchone():
                raise AppError(404, "image_not_found", "Image not found in this conversation.")
            db.execute(
                "UPDATE conversations SET active_image_id=NULL WHERE id=? AND active_image_id=?",
                (conversation_id, image_id),
            )
            db.execute(
                "UPDATE messages SET image_id=NULL WHERE conversation_id=? AND image_id=?",
                (conversation_id, image_id),
            )
            db.execute("DELETE FROM images WHERE id=?", (image_id,))

    def reserve(
        self, conversation_id: str, request_id: str, fingerprint: str
    ) -> dict[str, Any] | None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_conversation(db, conversation_id)
            previous = db.execute(
                "SELECT * FROM requests WHERE conversation_id=? AND request_id=?",
                (conversation_id, request_id),
            ).fetchone()
            if previous:
                if previous["fingerprint"] != fingerprint:
                    raise AppError(
                        409,
                        "idempotency_conflict",
                        "This request ID was already used with different content.",
                    )
                if previous["status"] == "pending":
                    raise AppError(409, "request_pending", "This request is still running.")
                result: dict[str, Any] = json.loads(previous["response"])
                if previous["status"] == "error":
                    raise AppError(result["status"], result["code"], result["message"])
                return result
            self.require_idle(db, conversation_id)
            moment = time.time()
            count = db.execute(
                "SELECT COUNT(*) FROM recent_calls WHERE at > ?", (moment - 60,)
            ).fetchone()[0]
            if count >= self.settings.requests_per_minute:
                raise AppError(
                    429, "local_rate_limit", "Local request limit reached. Wait one minute."
                )
            day = datetime.now(UTC).date().isoformat()
            row = db.execute("SELECT count FROM daily_usage WHERE day=?", (day,)).fetchone()
            if row and row[0] >= self.settings.daily_request_limit:
                raise AppError(
                    429,
                    "daily_limit",
                    "Local daily request budget is exhausted (resets at 00:00 UTC).",
                )
            db.execute(
                "INSERT INTO daily_usage VALUES (?,1) ON CONFLICT(day) DO UPDATE SET count=count+1",
                (day,),
            )
            db.execute("INSERT INTO recent_calls VALUES (?)", (moment,))
            db.execute(
                "INSERT INTO requests VALUES (?,?,?,'pending',NULL,?)",
                (conversation_id, request_id, fingerprint, moment),
            )
            return None

    def finish(
        self,
        conversation_id: str,
        request_id: str,
        text: str,
        response: dict[str, Any],
        image_id: str | None,
    ) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            stamp = now_iso()
            for role, message_id, content in [
                ("user", str(uuid4()), text),
                ("assistant", response["id"], response["text"]),
            ]:
                db.execute(
                    "INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        message_id,
                        conversation_id,
                        role,
                        content,
                        image_id,
                        response["provider"],
                        response["model"],
                        stamp,
                        request_id,
                    ),
                )
            db.execute(
                "UPDATE conversations SET active_image_id=?,updated_at=? WHERE id=?",
                (image_id, stamp, conversation_id),
            )
            db.execute(
                "UPDATE conversations SET title=? WHERE id=? AND title='New conversation' "
                "AND (SELECT COUNT(*) FROM messages WHERE conversation_id=?)=2",
                (text[:60], conversation_id, conversation_id),
            )
            db.execute(
                "UPDATE requests SET status='done',response=? "
                "WHERE conversation_id=? AND request_id=?",
                (json.dumps(response), conversation_id, request_id),
            )

    def fail(self, conversation_id: str, request_id: str, error: AppError) -> None:
        with self.connection() as db:
            db.execute(
                "UPDATE requests SET status='error',response=? "
                "WHERE conversation_id=? AND request_id=?",
                (
                    json.dumps(
                        {"status": error.status, "code": error.code, "message": error.message}
                    ),
                    conversation_id,
                    request_id,
                ),
            )

    def pair_code(self) -> dict[str, Any]:
        code = f"{secrets.randbelow(100_000_000):08d}"
        expires = time.time() + 300
        with self.connection() as db:
            db.execute("DELETE FROM pairing_codes")
            db.execute(
                "INSERT INTO pairing_codes VALUES (?,?)",
                (hashlib.sha256(code.encode()).hexdigest(), expires),
            )
        return {"code": code, "expires_at": datetime.fromtimestamp(expires, UTC).isoformat()}

    def redeem(self, code: str, ip: str) -> dict[str, Any]:
        moment = time.time()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            total = db.execute(
                "SELECT COUNT(*) FROM pairing_attempts WHERE at > ?", (moment - 60,)
            ).fetchone()[0]
            peer = db.execute(
                "SELECT COUNT(*) FROM pairing_attempts WHERE at > ? AND ip=?", (moment - 60, ip)
            ).fetchone()[0]
            if total >= 5 or peer >= 3:
                raise AppError(
                    429, "pairing_rate_limit", "Too many pairing attempts. Wait one minute."
                )
            db.execute("INSERT INTO pairing_attempts VALUES (?,?)", (moment, ip))
            # Commit the attempt even when the code is wrong, so failures cannot bypass throttling.
            db.commit()
            db.execute("BEGIN IMMEDIATE")
            digest = hashlib.sha256(code.encode()).hexdigest()
            row = db.execute(
                "SELECT * FROM pairing_codes WHERE hash=? AND expires_at>?", (digest, moment)
            ).fetchone()
            if row is None:
                raise AppError(
                    401,
                    "invalid_pairing_code",
                    "The pairing code is incorrect, expired, or already used.",
                )
            db.execute("DELETE FROM pairing_codes WHERE hash=?", (digest,))
            token, device_id, expires = secrets.token_urlsafe(32), str(uuid4()), moment + 7 * 86400
            db.execute(
                "INSERT INTO devices VALUES (?,?,?,?)",
                (
                    device_id,
                    hashlib.sha256(token.encode()).hexdigest(),
                    now_iso(),
                    expires,
                ),
            )
            return {
                "token": token,
                "device_id": device_id,
                "expires_at": datetime.fromtimestamp(expires, UTC).isoformat(),
            }

    def device_valid(self, token: str) -> bool:
        with self.connection() as db:
            return (
                db.execute(
                    "SELECT 1 FROM devices WHERE hash=? AND expires_at>?",
                    (hashlib.sha256(token.encode()).hexdigest(), time.time()),
                ).fetchone()
                is not None
            )

    def devices(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            return [
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "expires_at": datetime.fromtimestamp(row["expires_at"], UTC).isoformat(),
                }
                for row in db.execute(
                    "SELECT id,created_at,expires_at FROM devices WHERE expires_at>?",
                    (time.time(),),
                )
            ]

    def revoke(self, device_id: str) -> None:
        with self.connection() as db:
            db.execute("DELETE FROM devices WHERE id=?", (device_id,))

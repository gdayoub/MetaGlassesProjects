import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from lensagent.config import Settings
from lensagent.errors import AppError


@dataclass(frozen=True)
class SafeImage:
    data: bytes
    mime_type: str
    width: int
    height: int


def sanitize_image(data: bytes, content_type: str | None, settings: Settings) -> SafeImage:
    if not data or len(data) > settings.max_image_bytes:
        raise AppError(413, "image_size", "Choose an image smaller than 5 MiB.")
    formats = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as opened:
                if opened.format not in formats or content_type != formats[opened.format]:
                    raise AppError(415, "image_type", "Upload a genuine JPEG, PNG, or WebP image.")
                if opened.width * opened.height > settings.max_image_pixels:
                    raise AppError(413, "image_dimensions", "Image exceeds the 20 megapixel limit.")
                if getattr(opened, "n_frames", 1) != 1:
                    raise AppError(415, "animated_image", "Animated images are not supported.")
                opened.load()
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.thumbnail((2048, 2048))
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=90)
                return SafeImage(output.getvalue(), "image/jpeg", image.width, image.height)
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise AppError(415, "invalid_image", "The image could not be safely decoded.") from exc

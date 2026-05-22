"""Preprocess diagram images before sending to the LLM vision API."""

import io

from PIL import Image, ImageChops, ImageEnhance, ImageOps

# Maximum dimension (width or height) in pixels. Larger images are downscaled.
MAX_DIMENSION = 2048

# Enhancement factors (1.0 = no change)
CONTRAST_FACTOR = 1.3
SHARPNESS_FACTOR = 1.5


def preprocess_image(image_bytes: bytes) -> bytes:
    """Apply a sequence of preprocessing steps to a diagram image.

    Steps (in order):
    1. Auto-orient based on EXIF data.
    2. Convert to RGB (strip alpha / palette).
    3. Trim uniform background borders.
    4. Downscale if the longest side exceeds MAX_DIMENSION.
    5. Enhance contrast and sharpness for better LLM legibility.

    Args:
        image_bytes: Raw bytes of any PIL-supported image format (PNG, JPEG, …).

    Returns:
        Preprocessed image serialised as PNG bytes.
    """
    img = Image.open(io.BytesIO(image_bytes))

    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img = _trim_whitespace(img)
    img = _downscale(img)
    img = _enhance(img)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _trim_whitespace(img: Image.Image) -> Image.Image:
    """Crop uniform-colour borders using the top-left pixel as background reference."""
    bg_color = img.getpixel((0, 0))
    bg = Image.new("RGB", img.size, bg_color)
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        padding = 10
        left = max(0, bbox[0] - padding)
        upper = max(0, bbox[1] - padding)
        right = min(img.width, bbox[2] + padding)
        lower = min(img.height, bbox[3] + padding)
        img = img.crop((left, upper, right, lower))
    return img


def _downscale(img: Image.Image) -> Image.Image:
    """Downscale so the longest side is at most MAX_DIMENSION."""
    longest = max(img.width, img.height)
    if longest <= MAX_DIMENSION:
        return img
    scale = MAX_DIMENSION / longest
    new_size = (int(img.width * scale), int(img.height * scale))
    return img.resize(new_size, Image.LANCZOS)


def _enhance(img: Image.Image) -> Image.Image:
    """Boost contrast and sharpness to improve diagram legibility."""
    img = ImageEnhance.Contrast(img).enhance(CONTRAST_FACTOR)
    img = ImageEnhance.Sharpness(img).enhance(SHARPNESS_FACTOR)
    return img

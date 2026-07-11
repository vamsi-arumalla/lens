import io

from PIL import Image, ImageOps


def downscale_jpeg(data: bytes, max_edge: int) -> bytes:
    """Re-encode an image as JPEG with its longest edge capped at max_edge."""
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > max_edge:
        img.thumbnail((max_edge, max_edge))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()

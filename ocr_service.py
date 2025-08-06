"""Simple OCR service placeholder."""
import asyncio


async def extract_text(image_content: bytes) -> str:
    """Simulate text extraction from image bytes.

    Args:
        image_content: Raw image data.
    Returns:
        Decoded string if possible, otherwise empty string.
    """
    await asyncio.sleep(0)  # ensure function is async
    try:
        return image_content.decode("utf-8")
    except Exception:
        return ""

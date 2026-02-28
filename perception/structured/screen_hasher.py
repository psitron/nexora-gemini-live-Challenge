from __future__ import annotations

"""
Hybrid AI Agent – ScreenHasher.

Provides a fast perceptual hash for detecting whether the screen has
changed between iterations.
"""

from pathlib import Path
from typing import Union

from PIL import Image
import imagehash


class ScreenHasher:
    def hash_image(self, img: Union[Image.Image, Path, str]) -> str:
        """
        Compute a perceptual hash (phash) for the given image.
        Accepts a PIL Image instance or a path.
        """
        if isinstance(img, (str, Path)):
            with Image.open(img) as im:
                return str(imagehash.phash(im))
        return str(imagehash.phash(img))


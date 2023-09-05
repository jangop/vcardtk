import os
from pathlib import Path

from loguru import logger
from PIL import Image


def optimize_photo(
    photo_path: Path, max_file_size: int, max_width: int, max_height: int
):
    # Open the photo using Pillow
    image = Image.open(photo_path)

    # Resize the photo if necessary
    image.thumbnail((max_width, max_height))

    # Perform binary search to optimize file size
    quality_min = 0
    quality_max = 100
    while quality_min < quality_max - 1:
        quality = (quality_min + quality_max) // 2

        # Save the photo with the current quality setting
        image.save(photo_path, optimize=True, quality=quality)

        # Check the resulting file size
        file_size = os.path.getsize(photo_path)

        logger.debug(f"Quality: {quality}; File size: {file_size}")

        if file_size <= max_file_size:
            quality_min = quality
        else:
            quality_max = quality

    # Save the photo with the optimal quality setting
    image.save(photo_path, optimize=True, quality=quality_min)

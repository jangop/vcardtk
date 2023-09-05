from pathlib import Path

import tqdm
from loguru import logger

from .core import process_vcards


@logger.catch()
def enter(
    input_directory: Path = Path("/home/jgoepfert/tmp/in"),
    output_directory: Path = Path("/home/jgoepfert/tmp/out"),
    max_photo_file_size: int = 10000,
    max_photo_width: int = 512,
    max_photo_height: int = 512,
):
    # Configure logger.
    logger.remove()
    logger.add(lambda msg: tqdm.tqdm.write(msg, end=""), colorize=True, level="INFO")

    # Process vCards.
    process_vcards(
        input_directory,
        output_directory,
        max_photo_file_size,
        max_photo_width,
        max_photo_height,
    )

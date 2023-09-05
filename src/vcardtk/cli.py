from pathlib import Path

import click
import tqdm
from loguru import logger

from .core import process_vcards


@click.command()
@click.argument(
    "input_directory", type=click.Path(path_type=Path, exists=True, file_okay=False)
)
@click.argument("output_directory", type=click.Path(path_type=Path, file_okay=False))
@click.option(
    "--max-photo-file-size",
    type=int,
    default=1_000,
    help="Maximum photo file size in bytes",
)
@click.option(
    "--max-photo-width",
    type=int,
    default=512,
    help="Maximum photo width in pixels",
)
@click.option(
    "--max-photo-height",
    type=int,
    default=512,
    help="Maximum photo height in pixels",
)
def enter(
    input_directory,
    output_directory,
    max_photo_file_size,
    max_photo_width,
    max_photo_height,
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

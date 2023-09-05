from pathlib import Path

import click
import tqdm
from loguru import logger

from .core import Normalization, process_vcards


@click.command()
@click.argument(
    "input_directory", type=click.Path(path_type=Path, exists=True, file_okay=False)
)
@click.argument("output_directory", type=click.Path(path_type=Path, file_okay=False))
@click.option(
    "--normalizations",
    type=click.Choice([normalization.name for normalization in Normalization]),
    multiple=True,
    default=[normalization.name for normalization in Normalization],
    help="Normalizations to apply.",
)
@click.option(
    "--fallback-region",
    type=str,
    default=None,
    help="Fallback region for phone numbers, e.g., 'US' or 'DE'.",
)
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
    normalizations,
    fallback_region,
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
        normalizations=[
            Normalization[normalization] for normalization in normalizations
        ],
        fallback_region=fallback_region,
        max_file_size=max_photo_file_size,
        max_width=max_photo_width,
        max_height=max_photo_height,
    )

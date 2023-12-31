import enum
from pathlib import Path

import click
import phonenumbers
import tqdm
from loguru import logger

from .core import Normalization, process_sources


class PhoneNumberFormat(enum.Enum):
    E164 = phonenumbers.PhoneNumberFormat.E164
    INTERNATIONAL = phonenumbers.PhoneNumberFormat.INTERNATIONAL
    NATIONAL = phonenumbers.PhoneNumberFormat.NATIONAL
    RFC3966 = phonenumbers.PhoneNumberFormat.RFC3966


@click.command()
@click.argument(
    "source",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    nargs=-1,
)
@click.argument(
    "destination",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False, writable=True),
    nargs=1,
)
@click.option("--interactive", is_flag=True, help="Interactive mode")
@click.option(
    "--split",
    type=int,
    default=0,
    help="Split the output into multiple files with "
    "up to this many vCards per file.",
)
@click.option(
    "--normalizations",
    type=click.Choice([normalization.name for normalization in Normalization]),
    multiple=True,
    default=[normalization.name for normalization in Normalization],
    help="Normalizations to apply.",
)
@click.option(
    "--phone-number-format",
    type=click.Choice([format.name for format in PhoneNumberFormat]),
    default=PhoneNumberFormat.E164.name,
    help="Phone number format.",
)
@click.option(
    "--default-region",
    type=str,
    default=None,
    help="Default region for phone numbers, e.g., 'US' or 'DE'.",
)
@click.option("--strip-photos", is_flag=True, help="Remove all photos")
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
    source,
    destination,
    interactive,
    split,
    normalizations,
    phone_number_format,
    default_region,
    strip_photos,
    max_photo_file_size,
    max_photo_width,
    max_photo_height,
):
    # Configure logger.
    logger.remove()
    logger.add(lambda msg: tqdm.tqdm.write(msg, end=""), colorize=True, level="INFO")

    # Process vCards.
    process_sources(
        source,
        destination,
        interactive=interactive,
        split=split if split > 0 else None,
        normalizations=[
            Normalization[normalization] for normalization in normalizations
        ],
        phone_number_format=PhoneNumberFormat[phone_number_format].value,
        default_region=default_region,
        strip_photos=strip_photos,
        max_file_size=max_photo_file_size,
        max_width=max_photo_width,
        max_height=max_photo_height,
    )

import base64
import enum
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

import vobject
from loguru import logger

from .normalization.addresses import validate_email_addresses
from .normalization.names import normalize_name
from .normalization.numbers import normalize_dates, normalize_phone_numbers
from .normalization.photos import optimize_photo
from .normalization.urls import normalize_urls


class Normalization(str, enum.Enum):
    NAME = "name"
    DATE = "date"
    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    PHOTO = "photo"


def _normalize_vcard(
    vcard,
    *,
    normalizations: Iterable[Normalization],
    phone_number_format: int,
    default_region: str | None,
) -> None:
    if Normalization.NAME in normalizations:
        normalize_name(vcard)
    if Normalization.DATE in normalizations:
        normalize_dates(vcard)
    if Normalization.PHONE in normalizations:
        normalize_phone_numbers(
            vcard,
            phone_number_format=phone_number_format,
            default_region=default_region,
        )
    if Normalization.EMAIL in normalizations:
        validate_email_addresses(vcard)
    if Normalization.URL in normalizations:
        normalize_urls(vcard)
    if Normalization.PHOTO in normalizations:
        pass


def process_single_vcard(
    vcard,
    *,
    normalizations: Iterable[Normalization],
    phone_number_format: int,
    default_region: str | None,
    max_file_size: int,
    max_width: int,
    max_height: int,
):
    _normalize_vcard(
        vcard,
        normalizations=normalizations,
        phone_number_format=phone_number_format,
        default_region=default_region,
    )

    # Optimize included photo if available
    if "photo" in vcard.contents:
        first_photo = vcard.contents["photo"][0]
        try:
            photo_type = first_photo.params["ENCODING"][0]
            photo_data = first_photo.value
        except KeyError:
            try:
                photo_type = "base64"
                photo_data = first_photo.value
                photo_data = base64.b64decode(photo_data)
            except Exception as error:
                if type(error) != base64.binascii.Error:
                    raise
                if first_photo.value.startswith("http"):
                    logger.error(f"Photo URL given: {first_photo.value}")
                    return
                else:
                    logger.debug(f"Invalid photo format: {first_photo.value}")
                    return

        if photo_type == "b":
            # Save the photo to a temporary file
            temp_dir = tempfile.gettempdir()
            photo_file = Path(temp_dir) / "temp_photo.jpg"
            with open(photo_file, "wb") as file:
                file.write(photo_data)

            # Optimize the photo
            optimize_photo(photo_file, max_file_size, max_width, max_height)

            # Read the optimized photo and update the vCard
            with open(photo_file, "rb") as file:
                optimized_photo_data = file.read()

            vcard.contents["photo"][0].value = optimized_photo_data

            # Remove the temporary file
            os.remove(photo_file)


def process_vcards(
    sources: Iterable[Path],
    destination: Path,
    *,
    normalizations: Iterable[Normalization],
    phone_number_format: int,
    default_region: str | None,
    max_file_size: int,
    max_width: int,
    max_height: int,
):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as destination_file:
        for source in sources:
            with open(source, encoding="utf-8") as source_file:
                source_content = source_file.read()

            for single_vcard in vobject.readComponents(source_content):
                process_single_vcard(
                    single_vcard,
                    normalizations=normalizations,
                    phone_number_format=phone_number_format,
                    default_region=default_region,
                    max_file_size=max_file_size,
                    max_width=max_width,
                    max_height=max_height,
                )
                destination_file.write(single_vcard.serialize())
                destination_file.write("\n")

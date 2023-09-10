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
    interactive: bool,
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
            interactive=interactive,
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
    interactive: bool,
    normalizations: Iterable[Normalization],
    phone_number_format: int,
    default_region: str | None,
    strip_photos: bool,
    max_file_size: int,
    max_width: int,
    max_height: int,
):
    _normalize_vcard(
        vcard,
        interactive=interactive,
        normalizations=normalizations,
        phone_number_format=phone_number_format,
        default_region=default_region,
    )

    if strip_photos:
        # Remove all photos
        if "photo" in vcard.contents:
            del vcard.contents["photo"]

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


def process_sources(
    sources: Iterable[Path],
    destination: Path,
    *,
    interactive: bool,
    split: int | None,
    normalizations: Iterable[Normalization],
    phone_number_format: int,
    default_region: str | None,
    strip_photos: bool,
    max_file_size: int,
    max_width: int,
    max_height: int,
):
    destination.parent.mkdir(parents=True, exist_ok=True)
    given_destination = destination
    i_vcard = 0
    if split is not None:
        destination = given_destination.with_name(
            f"{given_destination.stem}"
            f"_{i_vcard // split}"
            f"{given_destination.suffix}"
        )
    destination_file = open(destination, "w", encoding="utf-8")
    try:
        for source in sources:
            with open(source, encoding="utf-8") as source_file:
                source_content = source_file.read()

            for single_vcard in vobject.readComponents(source_content):
                process_single_vcard(
                    single_vcard,
                    interactive=interactive,
                    normalizations=normalizations,
                    phone_number_format=phone_number_format,
                    default_region=default_region,
                    strip_photos=strip_photos,
                    max_file_size=max_file_size,
                    max_width=max_width,
                    max_height=max_height,
                )
                destination_file.write(single_vcard.serialize())
                destination_file.write("\n")

                i_vcard += 1
                if split is not None and i_vcard % split == 0:
                    destination_file.close()
                    destination = given_destination.with_name(
                        f"{given_destination.stem}"
                        f"_{i_vcard // split}"
                        f"{given_destination.suffix}"
                    )
                    destination_file = open(destination, "w", encoding="utf-8")
    finally:
        destination_file.close()

import base64
import enum
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

import tqdm
import vobject
from loguru import logger

from .normalization.addresses import normalize_addresses, validate_email_addresses
from .normalization.names import normalize_name
from .normalization.numbers import normalize_dates, normalize_phone_numbers
from .normalization.photos import optimize_photo
from .normalization.urls import normalize_urls


class Normalization(str, enum.Enum):
    NAME = "name"
    DATE = "date"
    PHONE = "phone"
    EMAIL = "email"
    PLACE = "place"
    URL = "url"
    PHOTO = "photo"


def _normalize_vcard(
    vcard, *, normalizations: Iterable[Normalization], fallback_region: str | None
) -> None:
    if Normalization.NAME in normalizations:
        normalize_name(vcard)
    if Normalization.DATE in normalizations:
        normalize_dates(vcard)
    if Normalization.PHONE in normalizations:
        normalize_phone_numbers(vcard, fallback_region=fallback_region)
    if Normalization.EMAIL in normalizations:
        validate_email_addresses(vcard)
    if Normalization.PLACE in normalizations:
        normalize_addresses(vcard)
    if Normalization.URL in normalizations:
        normalize_urls(vcard)
    if Normalization.PHOTO in normalizations:
        pass


def process_single_vcard(
    vcard,
    *,
    normalizations: Iterable[Normalization],
    fallback_region: str | None,
    max_file_size: int,
    max_width: int,
    max_height: int,
):
    _normalize_vcard(
        vcard, normalizations=normalizations, fallback_region=fallback_region
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
                    return vcard
                else:
                    logger.debug(f"Invalid photo format: {first_photo.value}")
                    return vcard

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

    return vcard


def process_vcards(
    input_directory: Path,
    output_directory: Path,
    *,
    normalizations: Iterable[Normalization],
    fallback_region: str | None,
    max_file_size: int,
    max_width: int,
    max_height: int,
):
    for filename in os.listdir(input_directory):
        if filename.endswith(".vcf"):
            vcard_path = input_directory / filename
            with open(vcard_path, encoding="utf-8") as file:
                vcard_content = file.read()

            normalized_vcards = []
            for single_vcard in tqdm.tqdm(vobject.readComponents(vcard_content)):
                # Process single vCard
                normalized_vcard = process_single_vcard(
                    single_vcard,
                    normalizations=normalizations,
                    fallback_region=fallback_region,
                    max_file_size=max_file_size,
                    max_width=max_width,
                    max_height=max_height,
                )

                # Add to list of normalized vCards
                normalized_vcards.append(normalized_vcard)

            # Create a new vCard with all normalized vCards
            new_vcard = vobject.vCard()
            for normalized_vcard in normalized_vcards:
                new_vcard.add(normalized_vcard)

            # Save the normalized and optimized vCard
            output_directory.mkdir(exist_ok=True)
            output_path = output_directory / f"normalized_{filename}"
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(new_vcard.serialize())

            logger.debug(f"Processed: {filename} -> {output_path}")

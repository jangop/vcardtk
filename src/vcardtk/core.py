import base64
import os
import tempfile
from pathlib import Path

import tqdm
import vobject
from loguru import logger

from .normalization.addresses import normalize_addresses, validate_email_addresses
from .normalization.names import normalize_name
from .normalization.numbers import normalize_dates, normalize_phone_numbers
from .normalization.photos import optimize_photo
from .normalization.urls import normalize_urls


def _normalize_vcard(vcard):
    # Normalize vCard properties
    normalize_name(vcard)
    normalize_dates(vcard)
    normalize_phone_numbers(vcard)
    validate_email_addresses(vcard)
    normalize_addresses(vcard)
    normalize_urls(vcard)


def process_single_vcard(
    vcard,
    *,
    max_file_size: int,
    max_width: int,
    max_height: int,
):
    _normalize_vcard(vcard)

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

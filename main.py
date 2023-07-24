import base64
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import phonenumbers
import tqdm
import vobject
from PIL import Image
from geopy.geocoders import Nominatim
from loguru import logger

geolocator = Nominatim(user_agent="vcardtk")


def normalize_vcard(vcard):
    # Normalize vCard properties
    normalize_name(vcard)
    normalize_dates(vcard)
    normalize_phone_numbers(vcard)
    validate_email_addresses(vcard)
    normalize_addresses(vcard)
    normalize_urls(vcard)


def normalize_name(vcard):
    field = "n"
    if field in vcard.contents:
        attrs = ["family", "given", "additional", "prefix", "suffix"]
        for attr in attrs:
            value = vcard.contents[field][0].value.__getattribute__(attr).strip()
            value = re.sub(r"\s+", " ", value)  # Remove extra white spaces
            value = value.title()  # Capitalize first letters
            vcard.contents[field][0].value.__setattr__(attr, value)
    field = "fn"
    if field in vcard.contents:
        value = vcard.contents[field][0].value.strip()
        value = re.sub(r"\s+", " ", value)  # Remove extra white spaces
        value = value.title()  # Capitalize first letters
        vcard.contents[field][0].value = value


def normalize_dates(vcard):
    # Normalize date fields to the format YYYY-MM-DD
    fields = ["bday", "anniversary"]
    for field in fields:
        if field in vcard.contents:
            value = vcard.contents[field][0].value.strip()
            try:
                datetime.strptime(value, "%Y%m%d")
            except ValueError as error:
                logger.error(f"Invalid date format for {field}: {value}; {error}")


def normalize_phone_numbers(vcard):
    fields = ["tel"]
    for field in fields:
        if field in vcard.contents:
            numbers = vcard.contents[field]
            for number in numbers:
                value = number.value.strip()
                try:
                    parsed_number = phonenumbers.parse(value, "DE")
                    formatted_number = phonenumbers.format_number(
                        parsed_number, phonenumbers.PhoneNumberFormat.E164
                    )
                    if formatted_number != value:
                        logger.critical(
                            f"Normalized phone number: {value} -> {formatted_number}")
                    number.value = formatted_number
                except phonenumbers.phonenumberutil.NumberParseException as error:
                    logger.error(f"Invalid phone number format: {value}; {error}")


def validate_email_addresses(vcard):
    fields = ["email"]
    for field in fields:
        if field in vcard.contents:
            addresses = vcard.contents[field]
            for address in addresses:
                value = address.value.strip()
                if not validate_email_address(value):
                    logger.error(f"Invalid email address format: {value}")
                    address.value = ""  # Remove invalid email addresses


def validate_email_address(email):
    # Validate email address format using regular expression
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def normalize_addresses(vcard):
    fields = ["adr"]
    for field in fields:
        if field in vcard.contents:
            addresses = vcard.contents[field]
            for address in addresses:
                geolocator.geocode(address)


def normalize_urls(vcard):
    # Normalize URL fields by ensuring proper schemes (http:// or https://)
    fields = ["url"]
    for field in fields:
        if field in vcard.contents:
            urls = vcard.contents[field]
            for url in urls:
                value = url.value.strip()
                parsed_url = urlparse(value)
                if not parsed_url.scheme:
                    value = "http://" + value  # Add default scheme
                url.value = value


def optimize_photo(photo_path, max_file_size, max_width, max_height):
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


def process_single_vcard(vcard, max_file_size: int,
                         max_width: int,
                         max_height: int, ):
    normalize_vcard(vcard)

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
            with open(vcard_path, "r", encoding="utf-8") as file:
                vcard_content = file.read()

            normalized_vcards = []
            for single_vcard in tqdm.tqdm(vobject.readComponents(vcard_content)):
                # Process single vCard
                normalized_vcard = process_single_vcard(single_vcard, max_file_size,
                                                        max_width, max_height)

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


@logger.catch()
def main():
    logger.remove()
    logger.add(lambda msg: tqdm.tqdm.write(msg, end=""), colorize=True, level="INFO")
    # Usage example
    input_directory = Path("/home/jgoepfert/tmp/in")
    output_directory = Path("/home/jgoepfert/tmp/out")
    max_photo_file_size = 10000  # Maximum file size in bytes
    max_photo_width = 512  # Maximum width in pixels
    max_photo_height = 512  # Maximum height in pixels

    process_vcards(
        input_directory,
        output_directory,
        max_photo_file_size,
        max_photo_width,
        max_photo_height,
    )


if __name__ == "__main__":
    main()

from datetime import datetime

import phonenumbers
from loguru import logger


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
                            f"Normalized phone number: {value} -> {formatted_number}"
                        )
                    number.value = formatted_number
                except phonenumbers.phonenumberutil.NumberParseException as error:
                    logger.error(f"Invalid phone number format: {value}; {error}")

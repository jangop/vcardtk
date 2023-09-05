from datetime import datetime

import click
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


def normalize_phone_numbers(
    vcard,
    *,
    phone_number_format: int,
    default_region: str | None,
):
    fields = ["tel"]
    for field in fields:
        if field not in vcard.contents:
            continue
        numbers = vcard.contents[field]
        for number in numbers:
            original_number = number.value
            region = None
            while True:
                try:
                    parsed_number = phonenumbers.parse(original_number, region)
                except phonenumbers.phonenumberutil.NumberParseException as error:
                    logger.error(
                        f"Invalid phone number format: {original_number}; {error}"
                    )
                    vcard.prettyPrint()
                    try:
                        region = click.prompt(
                            "Enter region code",
                            type=str,
                            default=default_region,
                            value_proc=lambda x: x.upper(),
                        )
                    except click.exceptions.Abort:
                        logger.info("Leaving phone number unchanged")
                        return
                else:
                    break

            formatted_number = phonenumbers.format_number(
                parsed_number, phone_number_format
            )

            if formatted_number != original_number:
                logger.info(
                    f"Normalized phone number: {original_number} "
                    f"-> {formatted_number}"
                )
                number.value = formatted_number

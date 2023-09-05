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


def _guess_region(vcard) -> str:
    # If there is an address, use the country code from there.
    if "adr" in vcard.contents:
        addresses = vcard.contents["adr"]
        for address in addresses:
            if "country" in address.params:
                country = address.params["country"][0]
                if len(country) == 2:
                    return country.upper()
                if country == "USA":
                    return "US"
                if country == "UK":
                    return "GB"
                if country == "Germany":
                    return "DE"
                if country == "Deutschland":
                    return "DE"

    # If there is an email address, use the top-level domain from there.
    if "email" in vcard.contents:
        addresses = vcard.contents["email"]
        for address in addresses:
            if "." in address.value:
                tld = address.value.split(".")[-1]
                if tld.lower() == "de":
                    return "DE"

    # If there is a URL, use the top-level domain from there.
    if "url" in vcard.contents:
        addresses = vcard.contents["url"]
        for address in addresses:
            if "." in address.value:
                tld = address.value.split(".")[-1]
                if tld.lower() == "de":
                    return "DE"

    return ""


def normalize_phone_numbers(vcard, *, fallback_region: str | None):
    fields = ["tel"]
    for field in fields:
        if field not in vcard.contents:
            continue
        numbers = vcard.contents[field]
        for number in numbers:
            original_number = number.value

            try:
                parsed_number = phonenumbers.parse(original_number)

                formatted_number = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )

            except phonenumbers.phonenumberutil.NumberParseException as error:
                logger.error(
                    f"Invalid phone number format: {original_number}; "
                    f"{error}; guessing region..."
                )
                guessed_region = _guess_region(vcard)
                if guessed_region:
                    logger.critical(f"Guessed region: {guessed_region}")
                vcard.prettyPrint()
            else:
                if formatted_number != original_number:
                    logger.info(
                        f"Normalized phone number: {original_number} "
                        f"-> {formatted_number}"
                    )
                # Replace value.
                number.value = formatted_number

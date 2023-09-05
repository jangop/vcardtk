import re

from geopy import Nominatim
from loguru import logger


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


geolocator = Nominatim(user_agent="vcardtk")

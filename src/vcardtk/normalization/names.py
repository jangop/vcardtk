import re


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

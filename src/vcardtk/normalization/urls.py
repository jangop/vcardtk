from urllib.parse import urlparse


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

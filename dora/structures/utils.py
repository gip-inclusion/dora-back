from typing import Tuple

from django.utils.text import Truncator


def normalize_description(desc: str, limit: int) -> Tuple[str, str]:
    if len(desc) < limit:
        return desc, ""
    else:
        return Truncator(desc).chars(limit), desc


def normalize_phone_number(phone: str) -> str:
    ret = phone.replace(" ", "").replace("-", "").replace(".", "")
    if len(ret) < 10:
        return ""
    return ret[:10]

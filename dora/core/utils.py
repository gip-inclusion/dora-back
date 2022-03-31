from typing import Tuple

from django.utils.text import Truncator


def normalize_description(desc: str, limit: int) -> Tuple[str, str]:
    if len(desc) < limit:
        return desc, ""
    else:
        return Truncator(desc).chars(limit), desc


def normalize_phone_number(phone: str) -> str:
    return "".join([c for c in phone if c.isdigit()])[:10]


def code_insee_to_code_dept(code_insee):
    return code_insee[:3] if code_insee.startswith("97") else code_insee[:2]

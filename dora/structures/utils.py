from typing import Tuple

from django.contrib.gis.geos import GEOSGeometry


def normalize_description(desc: str, limit: int) -> Tuple[str, str]:
    if len(desc) < limit:
        return desc, ""
    else:
        return desc[: limit - 3] + "...", desc


def normalize_phone_number(phone: str) -> str:
    ret = phone.replace(" ", "").replace("-", "").replace(".", "")
    if len(ret) < 10:
        return ""
    return ret[:10]


def normalize_coords(coords: str) -> Tuple[float, float]:
    pos = GEOSGeometry(coords)
    return pos.x, pos.y

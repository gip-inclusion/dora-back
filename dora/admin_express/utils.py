from unidecode import unidecode


def normalize_string_for_search(str):
    return unidecode(str).upper().replace("-", " ").replace("’", "'").rstrip()

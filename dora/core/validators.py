from django.core.exceptions import ValidationError
from osm_time import ParseException
from osm_time.opening_hours import OpeningHours


# From: https://github.com/betagouv/itou/blob/master/itou/utils/validators.py
def validate_siret(siret):
    if not siret.isdigit() or len(siret) != 14:
        raise ValidationError("Le numéro SIRET doit être composé de 14 chiffres.")


def validate_opening_hours_str(opening_hours_str):
    try:
        OpeningHours(opening_hours_str)
    except ParseException:
        raise ValidationError("Le format des horaires d’ouverture est incorrect")


def validate_accesslibre_url(url):
    if url and not url.startswith("https://acceslibre.beta.gouv.fr/"):
        raise ValidationError("L’URL doit débuter par https://acceslibre.beta.gouv.fr/")


def validate_safir(safir):
    if not safir.isdigit() or len(safir) != 5:
        raise ValidationError("Le code SAFIR doit être composé de 14 chiffres.")

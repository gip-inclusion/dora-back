import pyopening_hours
from django.core.exceptions import ValidationError


# From: https://github.com/betagouv/itou/blob/master/itou/utils/validators.py
def validate_siret(siret):
    if not siret.isdigit() or len(siret) != 14:
        raise ValidationError("Le numéro SIRET doit être composé de 14 chiffres.")


def validate_osm_hours_str(osm_hours_str):
    try:
        pyopening_hours.OpeningHours(osm_hours_str)
    except pyopening_hours.ParseException:
        raise ValidationError("Le format des horaires d'ouverture est incorrecte")


def validate_accesslibre_url(url):
    if url and not url.startswith("https://acceslibre.beta.gouv.fr/"):
        raise ValidationError("L'URL doit débuter par https://acceslibre.beta.gouv.fr/")


def validate_safir(safir):
    if not safir.isdigit() or len(safir) != 5:
        raise ValidationError("Le code SAFIR doit être composé de 14 chiffres.")

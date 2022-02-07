from django.core.exceptions import ValidationError


# From: https://github.com/betagouv/itou/blob/master/itou/utils/validators.py
def validate_siret(siret):
    if not siret.isdigit() or len(siret) != 14:
        raise ValidationError("Le numéro SIRET doit être composé de 14 chiffres.")


def validate_safir(safir):
    if not safir.isdigit() or len(safir) != 5:
        raise ValidationError("Le code SAFIR doit être composé de 14 chiffres.")

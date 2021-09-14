from rest_framework.authtoken.models import Token as DRFToken


class Token(DRFToken):
    class Meta:
        abstract = False

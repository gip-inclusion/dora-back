from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GinIndex


class AdminDivisionType(models.TextChoices):
    CITY = ("city", "Commune")
    EPCI = ("epci", "Intercommunalité (EPCI)")
    DEPARTMENT = ("department", "Département")
    REGION = ("region", "Région")
    COUNTRY = ("country", "France entière")


class GeoManager(models.Manager):
    def get_from_code(self, insee_code):
        # TODO: cache it
        try:
            return self.get(code=insee_code)
        except self.model.DoesNotExist:
            return None


class AdminDivision(models.Model):
    code = models.CharField(max_length=9, primary_key=True)
    name = models.CharField(max_length=230)
    normalized_name = models.CharField(max_length=230)
    geom = models.MultiPolygonField(srid=4326, geography=True, spatial_index=True)

    objects = GeoManager()

    class Meta:
        abstract = True


class City(AdminDivision):
    department = models.CharField(max_length=3, db_index=True)
    region = models.CharField(max_length=2, db_index=True)
    epci = models.CharField(max_length=20, db_index=True)
    population = models.IntegerField()

    class Meta:
        indexes = [
            GinIndex(
                name="city_name_trgm_idx",
                fields=("normalized_name",),
                opclasses=("gin_trgm_ops",),
            )
        ]


class EPCI(AdminDivision):
    geom = models.MultiPolygonField(srid=4326, geography=True, spatial_index=True)
    nature = models.CharField(max_length=150, db_index=True)

    class Meta:
        indexes = [
            GinIndex(
                name="epci_name_trgm_idx",
                fields=("normalized_name",),
                opclasses=("gin_trgm_ops",),
            )
        ]


class Department(AdminDivision):
    region = models.CharField(max_length=2, db_index=True)

    class Meta:
        indexes = [
            GinIndex(
                name="department_name_trgm_idx",
                fields=("normalized_name",),
                opclasses=("gin_trgm_ops",),
            )
        ]


class Region(AdminDivision):
    class Meta:
        indexes = [
            GinIndex(
                name="region_name_trgm_idx",
                fields=("normalized_name",),
                opclasses=("gin_trgm_ops",),
            )
        ]

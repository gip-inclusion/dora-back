from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GinIndex


class AdminDivisionType(models.TextChoices):
    CITY = ("city", "Commune")
    EPCI = ("epci", "Intercommunalité (EPCI)")
    DEPARTMENT = ("department", "Département")
    REGION = ("region", "Région")
    COUNTRY = ("country", "France entière")


sentinel = object()


# Cache progressif pour les tables comportant de nombreuses géometries
class ManyGeoManager(models.Manager):
    def get_from_code(self, insee_code):
        value = self.model._cache.get(insee_code, sentinel)
        if value is not sentinel:
            return value

        try:
            value = self.defer("geom").get(code=insee_code)
        except self.model.DoesNotExist:
            value = None
        self.model._cache[insee_code] = value
        return value


# Cache instantané pour les tables comportant peu de géometries
# on fait la requête une fois pour toute
class FewGeoManager(models.Manager):
    def get_from_code(self, insee_code):
        if len(self.model._cache):
            return self.model._cache.get(insee_code)

        values = self.defer("geom").all()
        self.model._cache = {value.code: value for value in values}


class AdminDivision(models.Model):
    code = models.CharField(max_length=9, primary_key=True)
    name = models.CharField(max_length=230)
    normalized_name = models.CharField(max_length=230)
    geom = models.MultiPolygonField(srid=4326, geography=True, spatial_index=True)

    class Meta:
        abstract = True


class City(AdminDivision):
    department = models.CharField(max_length=3, db_index=True)
    region = models.CharField(max_length=2, db_index=True)
    epci = models.CharField(max_length=20, db_index=True)
    population = models.IntegerField()
    objects = ManyGeoManager()
    _cache = {}

    class Meta:
        indexes = [
            GinIndex(
                name="city_name_trgm_idx",
                fields=("normalized_name",),
                opclasses=("gin_trgm_ops",),
            )
        ]


class EPCI(AdminDivision):
    nature = models.CharField(max_length=150, db_index=True)
    objects = ManyGeoManager()
    _cache = {}

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
    objects = FewGeoManager()
    _cache = {}

    class Meta:
        indexes = [
            GinIndex(
                name="department_name_trgm_idx",
                fields=("normalized_name",),
                opclasses=("gin_trgm_ops",),
            )
        ]


class Region(AdminDivision):
    objects = FewGeoManager()
    _cache = {}

    class Meta:
        indexes = [
            GinIndex(
                name="region_name_trgm_idx",
                fields=("normalized_name",),
                opclasses=("gin_trgm_ops",),
            )
        ]

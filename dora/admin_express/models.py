from django.contrib.gis.db import models


class CityManager(models.Manager):
    def get_from_code(self, insee_code):
        # TODO: cache it
        return self.get(code=insee_code)


class City(models.Model):
    code = models.CharField(max_length=5, primary_key=True)
    name = models.CharField(max_length=50)
    department = models.CharField(max_length=3, db_index=True)
    region = models.CharField(max_length=2, db_index=True)
    siren_epci = models.CharField(max_length=20, db_index=True)
    geom = models.MultiPolygonField(srid=4326, geography=True, spatial_index=True)

    objects = CityManager()

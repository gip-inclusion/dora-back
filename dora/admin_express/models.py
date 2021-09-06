from django.contrib.gis.db import models


class City(models.Model):
    code = models.CharField(max_length=5, primary_key=True)
    name = models.CharField(max_length=50)
    department = models.CharField(max_length=3, db_index=True)
    region = models.CharField(max_length=2, db_index=True)
    siren_epci = models.CharField(max_length=20, db_index=True)
    geom = models.MultiPolygonField(srid=4326, spatial_index=True)

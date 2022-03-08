from django.db import models


class EnumModel(models.Model):
    value = models.CharField(max_length=255, unique=True, db_index=True)
    label = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return self.label
